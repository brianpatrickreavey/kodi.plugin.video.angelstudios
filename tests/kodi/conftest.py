"""Make the event client importable when pytest is started from the repo root."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))


@pytest.fixture(scope="session")
def running_kodi():
    """Start Kodi when it is closed. Quit it only if this run started it."""
    from kodi_app import KodiApp

    app = KodiApp()
    app.open_for_test()
    try:
        yield app
    finally:
        app.close_if_opened()
