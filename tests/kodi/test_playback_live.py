"""Ask Kodi to play Kensuke's Kingdom from the start.

KODI_PLAYBACK_TEST picks the name. The default is playback. The movie stops
after a few seconds. KODI_PLAYBACK_LOOK=1 leaves the picture up.

Run this with `make kodi-test-playback` from the addon repo. A Kodi that is
already open is left open. Angel has to be signed in.

This file is not part of `make unittest`.
"""

import os

from live_run import assert_bundle

_NAME = os.environ.get("KODI_PLAYBACK_TEST") or "playback"
_LOOK = os.environ.get("KODI_PLAYBACK_LOOK") == "1"


def test_playback_in_kodi(running_kodi):
    del running_kodi
    options = ["look"] if _LOOK else []
    result = assert_bundle(_NAME, 180, options)
    if _LOOK and _NAME == "playback":
        human = [check["name"] for check in result["checks"] if check.get("needs_human")]
        assert human, "The picture check was not marked as needing a person"
