"""Ask Kodi to sign in again after the saved token is cleared.

KODI_AUTH_TEST picks the name. The default is auth. The username and password
stay. A failed check puts the old token back when the new one is missing.

Run this with `make kodi-test-auth` from the addon repo. A Kodi that is
already open is left open.

This file is not part of `make unittest`.
"""

import os

from live_run import assert_bundle

_NAME = os.environ.get("KODI_AUTH_TEST") or "auth"


def test_auth_in_kodi(running_kodi):
    del running_kodi
    assert_bundle(_NAME, 180)
