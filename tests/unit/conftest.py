"""
conftest.py for unit tests.
Provides fixtures and setup for mocking Kodi dependencies.
"""

import pytest
import sys
import os
from unittest.mock import MagicMock, patch

# Add resources/lib to path (from unittest directory)
lib_path = os.path.join(
    os.path.dirname(__file__), "../..", "plugin.video.angelstudios/resources/lib"
)
sys.path.insert(0, lib_path)

# Mock Kodi modules
sys.modules["xbmc"] = MagicMock()
sys.modules["xbmcgui"] = MagicMock()
sys.modules["xbmcplugin"] = MagicMock()
sys.modules["xbmcaddon"] = MagicMock()
sys.modules["xbmcvfs"] = MagicMock()

# Mock simplecache module
sys.modules["simplecache"] = MagicMock()
sys.modules["simplecache"].SimpleCache = MagicMock

from kodi_ui_interface import KodiUIInterface


@pytest.fixture
def ui_interface():
    """Fixture for KodiUIInterface with mocked dependencies."""
    logger_mock = MagicMock()
    angel_interface_mock = MagicMock()
    ui = KodiUIInterface(
        handle=1,
        url="plugin://plugin.video.angelstudios/",
        logger=logger_mock,
        angel_interface=angel_interface_mock,
    )
    return ui, logger_mock, angel_interface_mock


@pytest.fixture
def mock_xbmc():
    """Fixture for mocked XBMC functions."""
    with (
        patch("xbmcplugin.addDirectoryItem") as mock_add_item,
        patch("xbmcplugin.endOfDirectory") as mock_end_dir,
        patch("xbmcgui.ListItem") as mock_list_item,
    ):
        mock_list_item.return_value = MagicMock()
        yield mock_add_item, mock_end_dir, mock_list_item


@pytest.fixture
def mock_cache():
    """Fixture for mocked cache methods."""
    with patch("simplecache.SimpleCache") as mock_simple_cache:
        mock_cache_instance = MagicMock()
        mock_simple_cache.return_value = mock_cache_instance
        yield mock_cache_instance
