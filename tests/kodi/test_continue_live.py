"""Ask Kodi to read Continue Watching and resume one title.

KODI_CONTINUE_TEST picks the name. The default is continue. The resume play
stops as soon as the saved position is confirmed. It does not play a torch.

Run this with `make kodi-test-continue` from the addon repo. A Kodi that is
already open is left open. Angel has to be signed in.

This file is not part of `make unittest`.
"""

import os

from live_run import assert_bundle

_NAME = os.environ.get("KODI_CONTINUE_TEST") or "continue"


def test_continue_in_kodi(running_kodi):
    del running_kodi
    assert_bundle(_NAME, 240)
