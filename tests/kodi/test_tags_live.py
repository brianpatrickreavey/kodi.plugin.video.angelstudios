"""Ask Kodi to read watch-page title tags.

KODI_TAGS_TEST picks the name. The default is title-tags. Nothing is played.

Run this with `make kodi-test-tags` from the addon repo. A Kodi that is
already open is left open. Angel has to be signed in.

This file is not part of `make unittest`.
"""

import os

from live_run import assert_bundle

_NAME = os.environ.get("KODI_TAGS_TEST") or "title-tags"


def test_title_tags_in_kodi(running_kodi):
    del running_kodi
    assert_bundle(_NAME, 180)
