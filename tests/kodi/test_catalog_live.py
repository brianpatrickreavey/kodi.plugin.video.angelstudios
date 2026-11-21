"""Ask Kodi to open Movies, Series, and Dry Bar Comedy Specials.

KODI_CATALOG_TEST picks the name. The default is catalog. Nothing is played.

Run this with `make kodi-test-catalog` from the addon repo. A Kodi that is
already open is left open. Angel has to be signed in.

This file is not part of `make unittest`.
"""

import os

from live_run import assert_bundle

_NAME = os.environ.get("KODI_CATALOG_TEST") or "catalog"


def test_catalog_in_kodi(running_kodi):
    del running_kodi
    assert_bundle(_NAME, 240)
