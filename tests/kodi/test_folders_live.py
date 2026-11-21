"""Ask Kodi to show and hide each folder setting.

KODI_FOLDERS_TEST picks the name. The default is folders. The settings are
put back when the check ends. Top Picks is not opened.

Run this with `make kodi-test-folders` from the addon repo. A Kodi that is
already open is left open. Angel has to be signed in.

This file is not part of `make unittest`.
"""

import os

from live_run import assert_bundle

_NAME = os.environ.get("KODI_FOLDERS_TEST") or "folders"


def test_folders_in_kodi(running_kodi):
    del running_kodi
    assert_bundle(_NAME, 180)
