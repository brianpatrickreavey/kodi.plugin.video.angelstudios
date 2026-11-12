"""Load checks from resources/lib/tests and write one result file.

Each module in that folder registers one or more checks. A new check is a
new module. This runner does not import the video addon.
"""

import importlib
import json
import os
import traceback

import xbmc  # type: ignore

from notices import step_notice
from selection import SIGN_IN, expand, known_names, run_order

RESULT_PATH = "/tmp/script.angelstudios.integration-testing.json"
_TESTS = {}


def register(name):
    """Record a check function under name."""

    def wrap(func):
        _TESTS[name] = func
        return func

    return wrap


def tests():
    return dict(_TESTS)


def load_tests():
    """Import every test module so its register() calls run."""
    folder = os.path.join(os.path.dirname(__file__), "tests")
    for filename in sorted(os.listdir(folder)):
        if not filename.endswith(".py") or filename.startswith("_"):
            continue
        importlib.import_module(f"tests.{filename[:-3]}")


def parse_args(argv):
    """Return (check name, run id) from sys.argv."""
    extra = [arg for arg in argv[1:] if isinstance(arg, str) and arg]
    if len(extra) == 1 and "," in extra[0]:
        extra = [part for part in extra[0].split(",") if part]
    name = extra[0] if extra else "all"
    run_id = extra[1] if len(extra) > 1 else ""
    options = extra[2:]
    return name, run_id, options


class KodiSession:
    """JSON-RPC helpers shared by every check."""

    def __init__(self):
        self.checks = []
        self.monitor = xbmc.Monitor()

    def check(self, name, passed, detail, needs_human=False):
        """Record one check. A human check is not counted as passed or failed."""
        item = {"name": name, "detail": detail}
        if needs_human:
            item["needs_human"] = True
            item["passed"] = None
            xbmc.log(f"Angel integration {name}: needs a person. {detail}", xbmc.LOGINFO)
        else:
            item["passed"] = bool(passed)
            level = xbmc.LOGINFO if passed else xbmc.LOGWARNING
            xbmc.log(f"Angel integration {name}: {detail}", level)
        self.checks.append(item)

    def prepare(self, selected):
        """Remember where each leaf sits in this run, for the on-screen count."""
        self.step_total = len(selected)
        self.step_at = {name: index + 1 for index, name in enumerate(selected)}

    def wants_look(self):
        return "look" in getattr(self, "options", ())

    def gate(self, name, confirm):
        """Run confirm once per name during this run. Later leaves reuse the result."""
        found = getattr(self, "_gates", None)
        if found is None:
            self._gates = {}
            found = self._gates
        if name not in found:
            found[name] = bool(confirm())
        return found[name]

    def announce(self, leaf, text, milliseconds):
        """Show this step's notice and return at once."""
        if not self.wants_look():
            return
        self._notify_step(leaf, text, milliseconds)

    def hold(self, leaf, text, seconds):
        """Show this step's notice and leave the picture up."""
        if not self.wants_look():
            return
        self._notify_step(leaf, text, int(seconds * 1000))
        self.wait(lambda: None, seconds)

    def _notify_step(self, leaf, text, milliseconds):
        number = self.step_at[leaf]
        title, message = step_notice(number, self.step_total, text)
        self.notify(title, message, milliseconds)

    def notify(self, title, message, milliseconds=10000):
        """Show a short notice. The text cannot contain a comma."""
        xbmc.executebuiltin(f"Notification({title},{message},{int(milliseconds)})")

    def rpc(self, method, params=None):
        request = {"jsonrpc": "2.0", "id": 1, "method": method}
        if params is not None:
            request["params"] = params
        raw = xbmc.executeJSONRPC(json.dumps(request))
        if not isinstance(raw, str):
            raise RuntimeError(f"{method} did not return text")
        payload = json.loads(raw)
        if not isinstance(payload, dict):
            raise RuntimeError(method)
        if payload.get("error"):
            raise RuntimeError(f"{method} was rejected")
        return payload.get("result")

    def setting(self, name):
        result = self.rpc("Settings.GetSettingValue", {"setting": name})
        if not isinstance(result, dict) or "value" not in result:
            raise RuntimeError(f"Could not read {name}")
        return result["value"]

    def set_setting(self, name, value):
        self.rpc("Settings.SetSettingValue", {"setting": name, "value": value})

    def player(self):
        """Return the active video player, or playing False."""
        players = self.rpc("Player.GetActivePlayers", {})
        playerid = None
        if isinstance(players, list):
            for player in players:
                if isinstance(player, dict) and player.get("type") == "video":
                    playerid = player.get("playerid")
                    break
        if not isinstance(playerid, int):
            return {"playing": False, "playerid": None, "subtitles": [], "current": None, "enabled": False}
        result = self.rpc(
            "Player.GetProperties",
            {
                "playerid": playerid,
                "properties": ["subtitles", "currentsubtitle", "subtitleenabled"],
            },
        )
        if not isinstance(result, dict):
            raise RuntimeError("Player.GetProperties")
        tracks = result.get("subtitles")
        if not isinstance(tracks, list):
            tracks = []
        return {
            "playing": True,
            "playerid": playerid,
            "subtitles": tracks,
            "current": result.get("currentsubtitle"),
            "enabled": result.get("subtitleenabled") is True,
        }

    def stop(self):
        state = self.player()
        if not state["playing"]:
            return
        self.rpc("Player.Stop", {"playerid": state["playerid"]})
        self.wait(lambda: not self.player()["playing"], 15)

    def open_video(self, url):
        self.rpc("Player.Open", {"item": {"file": url}, "options": {"resume": False}})

    def seek(self, seconds):
        """Move to a time in the current video. Return False when the player cannot."""
        state = self.player()
        if not state["playing"]:
            return False
        minutes, secs = divmod(int(seconds), 60)
        hours, minutes = divmod(minutes, 60)
        try:
            self.rpc(
                "Player.Seek",
                {
                    "playerid": state["playerid"],
                    "value": {"time": {"hours": hours, "minutes": minutes, "seconds": secs, "milliseconds": 0}},
                },
            )
        except RuntimeError:
            return False
        return self.wait(lambda: self._at_least(seconds - 30), 15) is not None

    def _at_least(self, seconds):
        clock = self.play_time()
        return clock is not None and clock >= seconds

    def play_time(self):
        """Return the current playback position in seconds, or None."""
        state = self.player()
        if not state["playing"]:
            return None
        try:
            result = self.rpc("Player.GetProperties", {"playerid": state["playerid"], "properties": ["time"]})
        except RuntimeError:
            return None
        clock = result.get("time") if isinstance(result, dict) else None
        if not isinstance(clock, dict):
            return None
        return (
            int(clock.get("hours") or 0) * 3600 + int(clock.get("minutes") or 0) * 60 + int(clock.get("seconds") or 0)
        )

    def set_subtitle_off(self):
        state = self.player()
        if not state["playing"]:
            raise RuntimeError("The player is not running")
        self.rpc("Player.SetSubtitle", {"playerid": state["playerid"], "subtitle": "off"})

    def wait(self, predicate, seconds):
        """Return the first true result, or None when seconds pass."""
        polls = int(seconds / 0.5)
        for _ in range(polls):
            if self.monitor.abortRequested():
                return None
            try:
                result = predicate()
            except Exception:
                result = None
            if result:
                return result
            if self.monitor.waitForAbort(0.5):
                return None
        return None


def run(argv):
    """Run the requested checks and return the result mapping."""
    load_tests()
    name, run_id, options = parse_args(argv)
    session = KodiSession()
    session.options = options
    session.requested = name
    selected = run_order(name)
    if selected is None:
        known = ", ".join(known_names())
        session.check("load", False, f"No check named {name}. Checks: {known}")
    else:
        missing = [item for item in selected if item not in _TESTS]
        if missing:
            session.check("load", False, f"No check named {missing[0]}.")
        else:
            session.prepare(expand(name) or [])
            for item in selected:
                try:
                    _TESTS[item](session)
                except Exception:
                    session.check(item, False, traceback.format_exc(limit=3))
                if item == SIGN_IN and not _passed(session, SIGN_IN):
                    break
    automatic = [item for item in session.checks if not item.get("needs_human")]
    passed = bool(automatic) and all(item["passed"] for item in automatic)
    if not session.checks:
        session.check(name, False, "The check did not report a result")
        passed = False
    return {
        "addon": "script.angelstudios.integration-testing",
        "test": name,
        "run_id": run_id,
        "passed": passed,
        "needs_human": [item["name"] for item in session.checks if item.get("needs_human")],
        "checks": session.checks,
    }


def _passed(session, name):
    found = [item for item in session.checks if item["name"] == name]
    return bool(found) and all(item["passed"] for item in found)


def write_result(result):
    temporary = RESULT_PATH + ".tmp"
    with open(temporary, "w", encoding="utf-8") as handle:
        json.dump(result, handle)
    os.replace(temporary, RESULT_PATH)


def main(argv):
    try:
        name, run_id, _options = parse_args(argv)
    except Exception:
        name, run_id = "", ""
    try:
        result = run(argv)
    except Exception:
        result = {
            "addon": "script.angelstudios.integration-testing",
            "test": name,
            "run_id": run_id,
            "passed": False,
            "checks": [{"name": "runner", "passed": False, "detail": traceback.format_exc(limit=3)}],
        }
    try:
        write_result(result)
    except Exception as exc:
        xbmc.log(f"Angel integration could not write the result: {exc}", xbmc.LOGERROR)
    status = "passed" if result["passed"] else "failed"
    if result["passed"] and result.get("needs_human"):
        status = "passed. Kodi will close."
    label = result["test"] or "checks"
    xbmc.executebuiltin(f"Notification(Angel tests,{label} {status},5000)")
    xbmc.log(f"Angel integration {label} {status}", xbmc.LOGINFO)
