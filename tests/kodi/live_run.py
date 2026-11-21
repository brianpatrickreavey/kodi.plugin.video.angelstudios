"""Ask the open Kodi to run one integration bundle and read the result file."""

import json
import time
import uuid
from pathlib import Path

from event_client import send_builtin

_ADDON_ID = "script.angelstudios.integration-testing"
_RESULT = Path("/tmp/script.angelstudios.integration-testing.json")


def assert_bundle(name, timeout, options=()):
    """Fail when any automatic check failed or the name is unknown."""
    result = run_bundle(name, timeout, options)
    failed = [check for check in result["checks"] if not check.get("needs_human") and not check["passed"]]
    lines = [f"{check['name']}: {check['detail']}" for check in result["checks"]]
    assert not failed, "Kodi checks failed\n" + "\n".join(lines)
    return result


def run_bundle(name, timeout, options=()):
    """Start the program addon and return its result mapping."""
    run_id = uuid.uuid4().hex
    if _RESULT.exists():
        _RESULT.unlink()
    arguments = ",".join((name, run_id) + tuple(options))
    send_builtin(f"RunScript({_ADDON_ID},{arguments})")
    deadline = time.time() + timeout
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
