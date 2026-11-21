"""Ask Kodi to sign out and then sign back in.

KODI_SIGNED_OUT_TEST picks the name. The default is signed-out. Force Logout
opens an OK dialog. Press OK. The check signs back in before it finishes.

Run this with `make kodi-test-signed-out` from the addon repo. A Kodi that is
already open is left open.

This file is not part of `make unittest`.
"""

import os

from live_run import assert_bundle

_NAME = os.environ.get("KODI_SIGNED_OUT_TEST") or "signed-out"


def test_signed_out_in_kodi(running_kodi):
    del running_kodi
    assert_bundle(_NAME, 240)
