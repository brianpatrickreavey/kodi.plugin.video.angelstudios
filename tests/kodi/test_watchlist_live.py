"""Ask Kodi to run the watchlist checks.

KODI_WATCHLIST_TEST picks the name. The default is watchlist. That bundle
reads the signed-in list. It does not play video. watchlist-add-remove saves
one title that is not already saved, then removes it.

Run this with `make kodi-test-watchlist` from the addon repo. Kodi can be
closed. This test starts it, then quits it when the test is done. A Kodi that
is already open is left open. Angel has to be signed in, and the program addon
Angel Studios integration testing has to be enabled.

This file is not part of `make unittest`.
"""

import json
import os
import sys
import time
import uuid
from pathlib import Path

from event_client import send_builtin

sys.path.insert(
    0, str(Path(__file__).resolve().parents[2] / "dev/script.angelstudios.integration-testing/resources/lib")
)

from selection import expand  # noqa: E402

_ADDON_ID = "script.angelstudios.integration-testing"
_RESULT = Path("/tmp/script.angelstudios.integration-testing.json")
_TIMEOUT_SECONDS = 240
_NAME = os.environ.get("KODI_WATCHLIST_TEST") or "watchlist"


def test_watchlist_in_kodi(running_kodi):
    del running_kodi
    result = _run(_NAME)
    failed = [check for check in result["checks"] if not check.get("needs_human") and not check["passed"]]
    lines = [f"{check['name']}: {check['detail']}" for check in result["checks"]]
    assert not failed, "Watchlist checks failed\n" + "\n".join(lines)
    assert expand(_NAME) is not None


def _run(name):
    run_id = uuid.uuid4().hex
    if _RESULT.exists():
        _RESULT.unlink()
    send_builtin(f"RunScript({_ADDON_ID},{name},{run_id})")
    deadline = time.time() + _TIMEOUT_SECONDS
    while time.time() < deadline:
        result = _read_result(run_id)
        if result is not None:
            return result
        time.sleep(0.5)
    raise AssertionError(
        "Kodi did not write a result. "
        "Sign in to Angel if a login dialog is on screen, and enable "
        "Angel Studios integration testing under Program add-ons."
    )


def _read_result(run_id):
    if not _RESULT.exists():
        return None
    try:
        result = json.loads(_RESULT.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(result, dict) or result.get("run_id") != run_id:
        return None
    return result
