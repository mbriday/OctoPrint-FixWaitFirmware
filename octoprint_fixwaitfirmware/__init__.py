# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals

import re

import octoprint.plugin


class FixWaitFirmwarePlugin(octoprint.plugin.OctoPrintPlugin):

    def __init__(self):
        self._logged_replacement = {}
        self.updateWait = False

    def initialize(self):
        self._logger.info("Plugin active, working around broken 'Wait/Busy' firmware")

    def rewrite_sending(
        self, comm_instance, phase, cmd, cmd_type, gcode, subcode=None, *args, **kwargs
    ):
        """ hook """
        if gcode == "G1": #go (may return a busy)
            self.updateWait = True
        if gcode == "M140" or gcode == "M104": #set temperature (beginning…)
            self.updateWait = False

    def rewrite_received(self, comm_instance, line, *args, **kwargs):
        """ hook """
        line = self._rewrite_wait_to_busy(line)
        return line

    def _rewrite_wait_to_busy(self, line):
        if self.updateWait:
            # firmware wrongly assumes "wait" to mean "busy", fix that
            if line == "wait" or line.startswith("wait"):
                self._log_replacement("wait", "wait", "echo:busy processing", only_once=False)
                return "echo:busy processing"
        return line

    def _log_replacement(self, t, orig, repl, only_once=False):
        if not only_once or not self._logged_replacement.get(t, False):
            self._logger.info("Replacing {} with {}".format(orig, repl))
            self._logged_replacement[t] = True
            if only_once:
                self._logger.info(
                    "Further replacements of this kind will be logged at DEBUG level."
                )
        else:
            self._logger.debug("Replacing {} with {}".format(orig, repl))
        self._log_to_terminal("{} -> {}".format(orig, repl))

    def _log_to_terminal(self, *lines, **kwargs):
        prefix = kwargs.pop(b"prefix", "Repl:")
        if self._printer:
            self._printer.log_lines(
                *list(map(lambda x: "{} {}".format(prefix, x), lines))
            )

    ##~~ Softwareupdate hook

    def get_update_information(self):
        return {
            "fixwaitfirmware": {
                "displayName": "Fix Wait Firmware Plugin",
                "displayVersion": self._plugin_version,
                "type": "github_release",
                "user": "OctoPrint",
                "repo": "OctoPrint-FixWaitFirmware",
                "current": self._plugin_version,
                "stable_branch": {
                    "name": "Stable",
                    "branch": "master",
                    "commitish": ["devel", "master"],
                },
                "prerelease_branches": [
                    {
                        "name": "Prerelease",
                        "branch": "devel",
                        "commitish": ["devel", "master"],
                    }
                ],
                "pip": "https://github.com/mbriday/OctoPrint-FixWaitFirmware/archive/{target_version}.zip",
            }
        }


__plugin_name__ = "Fix Wait Firmware Plugin"
__plugin_pythoncompat__ = ">=2.7,<4"  # python 2 and 3


def __plugin_load__():
    global __plugin_implementation__
    __plugin_implementation__ = FixWaitFirmwarePlugin()

    global __plugin_hooks__
    __plugin_hooks__ = {
        "octoprint.plugin.softwareupdate.check_config": __plugin_implementation__.get_update_information,
        "octoprint.comm.protocol.gcode.received": (
            __plugin_implementation__.rewrite_received,
            1,
        ),
        "octoprint.comm.protocol.gcode.sending": (
            __plugin_implementation__.rewrite_sending,
            1,
        ),
    }
