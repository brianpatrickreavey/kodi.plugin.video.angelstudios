"""Ask Kodi to clear the cache and the debug data.

KODI_MAINTENANCE_TEST picks the name. The default is maintenance. Neither
check signs out.

Run this with `make kodi-test-maintenance` from the addon repo. A Kodi that
is already open is left open. Angel has to be signed in.

This file is not part of `make unittest`.
"""

import os

from live_run import assert_bundle

_NAME = os.environ.get("KODI_MAINTENANCE_TEST") or "maintenance"


def test_maintenance_in_kodi(running_kodi):
    del running_kodi
    assert_bundle(_NAME, 90)
