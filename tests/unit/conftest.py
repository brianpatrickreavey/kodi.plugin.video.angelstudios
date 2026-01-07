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

# Provide a default Addon mock for settings access (e.g., use_isa toggle)
_default_addon = MagicMock()

_menu_defaults = {
    "show_movies": True,
    "show_series": True,
    "show_specials": True,
    "show_podcasts": False,
    "show_livestreams": False,
    "show_continue_watching": False,
    "show_top_picks": False,
    "show_other_content": False,
    "disable_cache": False,
}

_default_addon.getSettingBool.side_effect = lambda key: _menu_defaults.get(key, False)
_default_addon.getSettingString.return_value = "off"
_default_addon.getSettingInt.return_value = 12
sys.modules["xbmcaddon"].Addon = MagicMock(return_value=_default_addon)

# xbmcvfs translatePath passthrough for file operations (overrideable in tests)
sys.modules["xbmcvfs"].translatePath = MagicMock()
_translate_mock = sys.modules["xbmcvfs"].translatePath
_translate_mock.return_value = None
_translate_mock.side_effect = lambda path, _m=_translate_mock: (
    _m.return_value if _m.return_value is not None else path
)

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

    # Give each test its own addon instance to avoid side-effect leakage on the
    # shared default mock configured above.
    fresh_addon = MagicMock()
    fresh_addon.getSettingBool.side_effect = lambda key: _menu_defaults.get(key, False)
    fresh_addon.getSettingString.return_value = "off"
    fresh_addon.getSettingInt.return_value = 12
    ui.addon = fresh_addon
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
