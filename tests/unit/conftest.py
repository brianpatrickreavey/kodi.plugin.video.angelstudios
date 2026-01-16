"""
conftest.py for unit tests.
Provides fixtures and setup for mocking Kodi dependencies.

Fixture Organization:
- Kodi Module Mocks (Global): Pre-configured sys.modules patches for all Kodi-related modules
- Individual Fixtures (Composable): Single-purpose mocks for addon, logger, cache, session, UI methods
- Composed Fixtures (High-level): Pre-configured KodiUIInterface and convenience wrappers

All Kodi modules are mocked globally before any imports to prevent RuntimeError from actual Kodi unavailability.
Tests receive fresh fixtures per test to avoid cross-test side effects.
"""

import pytest
import sys
import os
from unittest.mock import MagicMock, patch

# ==============================================================================
# KODI MODULE MOCKS (Global - must be patched before any imports)
# ==============================================================================

# Mock xbmc module with standard log level constants
sys.modules["xbmc"] = MagicMock()
sys.modules["xbmc"].LOGDEBUG = 0
sys.modules["xbmc"].LOGINFO = 1
sys.modules["xbmc"].LOGWARNING = 2
sys.modules["xbmc"].LOGERROR = 3
sys.modules["xbmc"].LOGFATAL = 4
sys.modules["xbmc"].log = MagicMock()

# Mock xbmcgui, xbmcplugin, xbmcaddon, xbmcvfs modules
sys.modules["xbmcgui"] = MagicMock()
sys.modules["xbmcplugin"] = MagicMock()
sys.modules["xbmcaddon"] = MagicMock()
sys.modules["xbmcvfs"] = MagicMock()
sys.modules["xbmcvfs"].mkdirs = MagicMock()

# ==============================================================================
# ADDON CONFIGURATION (Default settings used across tests)
# ==============================================================================

# Menu feature toggles (default: most disabled for isolated unit tests)
_MENU_DEFAULTS = {
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

# Provide a default Addon mock for settings access (e.g., use_isa toggle)
_default_addon = MagicMock()
_default_addon.getSettingBool.side_effect = lambda key: _MENU_DEFAULTS.get(key, False)
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

# Add plugin.video.angelstudios and its resources/lib to sys.path so tests can import modules directly
plugin_path = os.path.join(os.path.dirname(__file__), "../..", "plugin.video.angelstudios")
lib_path = os.path.join(plugin_path, "resources", "lib")
if plugin_path not in sys.path:
    sys.path.insert(0, plugin_path)
if lib_path not in sys.path:
    sys.path.insert(0, lib_path)
from resources.lib.kodi_ui_interface import KodiUIInterface  # noqa: E402


# ==============================================================================
# INDIVIDUAL FIXTURES (Composable, single-purpose, reusable)
# ==============================================================================


@pytest.fixture
def mock_kodi_addon():
    """Mock Kodi addon with common settings for unit tests.

    Returns a MagicMock with standard settings pre-configured (menus disabled,
    cache enabled, etc.). Tests can override individual settings by modifying
    side_effect or return_value as needed for specific test scenarios.

    Returns:
        MagicMock: Addon mock with getSettingBool, getSettingString, getSettingInt
                   methods pre-configured with menu defaults.

    Example:
        mock_kodi_addon.getSettingBool.side_effect = lambda key: True  # Override for test
    """
    addon = MagicMock()
    addon.getSettingBool.side_effect = lambda key: _MENU_DEFAULTS.get(key, False)
    addon.getSettingString.return_value = "off"
    addon.getSettingInt.return_value = 12
    addon.getAddonInfo.side_effect = lambda key: {
        "path": "/fake/addon/path",
        "profile": "/fake/profile",
        "id": "plugin.video.angelstudios",
    }.get(key, "")
    return addon


@pytest.fixture
def mock_logger():
    """Mock Kodi logger for capturing log calls in tests.

    Returns:
        MagicMock: Logger with debug, info, warning, error methods.
                   Tests can assert on call_args to verify logging behavior.

    Example:
        mock_logger.error.assert_called_with("Expected error message")
    """
    return MagicMock()


@pytest.fixture
def mock_angel_interface():
    """Mock AngelStudiosInterface (API client) for testing UI without API calls.

    Returns a MagicMock configured to return empty lists/dicts by default,
    simulating cache misses and empty responses. Tests override return_value
    to inject specific API response data.

    Returns:
        MagicMock: API client with get_projects, get_project, get_episode_data
                   methods returning empty by default.

    Example:
        mock_angel_interface.get_projects.return_value = [{"name": "Test"}]
    """
    mock = MagicMock()
    mock.get_projects.return_value = []
    mock.get_project.return_value = {}
    mock.get_episode_data.return_value = {}
    return mock


@pytest.fixture
def mock_simplecache_instance():
    """Mock SimpleCache for testing cache behavior in isolation.

    Returns a MagicMock with get() and set() methods. Default: get() returns
    None (cache miss). Tests can override get.return_value to simulate cache
    hits or set up side_effect for more complex scenarios.

    Returns:
        MagicMock: Cache with get() and set() methods.

    Example:
        mock_simplecache_instance.get.return_value = {"cached": "data"}  # Cache hit
    """
    cache = MagicMock()
    cache.get.return_value = None  # Default: miss
    cache.set.return_value = True
    return cache


# ==============================================================================
# KODI UI METHOD MOCKS (For xbmcplugin and xbmcgui patches)
# ==============================================================================


@pytest.fixture
def mock_kodi_xbmcplugin():
    """Mock xbmcplugin module methods used for menu rendering.

    Patches xbmcplugin.addDirectoryItem, endOfDirectory, setResolvedUrl, and
    setContent. Returns dict with named references for assertion/verification
    in tests.

    Yields:
        dict: Named mocks {'addDirectoryItem', 'endOfDirectory', 'setResolvedUrl', 'setContent'}

    Example:
        mock_kodi_xbmcplugin['addDirectoryItem'].assert_called_once()
    """
    with (
        patch("xbmcplugin.addDirectoryItem") as mock_add_item,
        patch("xbmcplugin.endOfDirectory") as mock_end_dir,
        patch("xbmcplugin.setResolvedUrl") as mock_resolve,
        patch("xbmcplugin.setContent") as mock_set_content,
    ):
        yield {
            "addDirectoryItem": mock_add_item,
            "endOfDirectory": mock_end_dir,
            "setResolvedUrl": mock_resolve,
            "setContent": mock_set_content,
        }


@pytest.fixture
def mock_kodi_xbmcgui():
    """Mock xbmcgui module (ListItem, Dialog) for UI element testing.

    Patches xbmcgui.ListItem and xbmcgui.Dialog. Pre-configures ListItem to
    return proper mock with getVideoInfoTag() method. Returns dict with named
    references.

    Yields:
        dict: Named mocks {'ListItem', 'Dialog'}

    Example:
        list_item_mock = mock_kodi_xbmcgui['ListItem'].return_value
        list_item_mock.getVideoInfoTag.assert_called()
    """
    with (
        patch("xbmcgui.ListItem") as mock_listitem,
        patch("xbmcgui.Dialog") as mock_dialog,
    ):
        # Configure ListItem to return proper mock with VideoInfoTag capability
        mock_listitem.return_value.getVideoInfoTag.return_value = MagicMock()
        yield {
            "ListItem": mock_listitem,
            "Dialog": mock_dialog,
        }


# ==============================================================================
# COMPOSED FIXTURES (High-level; use individual fixtures as dependencies)
# ==============================================================================


@pytest.fixture
def ui_interface(mock_kodi_addon, mock_logger, mock_angel_interface, mock_simplecache_instance):
    """Fully configured KodiUIInterface for end-to-end menu testing.

    Patches Kodi modules and wires all dependencies (addon, logger, API client,
    cache) together in a fresh KodiUIInterface instance. Each test receives
    isolated fixtures to avoid cross-test side effects.

    Useful for testing complete menu flows (fetch → render → cache) without
    mocking individual Kodi methods. For granular testing of specific Kodi calls,
    use mock_xbmc or mock_kodi_xbmcplugin / mock_kodi_xbmcgui directly.

    Args (injected):
        mock_kodi_addon: Pre-configured addon mock
        mock_logger: Mock logger for capturing logs
        mock_angel_interface: Mock API client
        mock_simplecache_instance: Mock cache instance

    Returns:
        tuple: (ui_interface, logger_mock, angel_interface_mock)
               ui_interface is ready to call (e.g., ui.projects_menu())
               logger/angel_interface exposed for test assertions

    Example:
        ui, logger, api = ui_interface
        ui.projects_menu()
        logger.info.assert_called()
    """
    ui = KodiUIInterface(
        handle=1,
        url="plugin://plugin.video.angelstudios/",
        logger=mock_logger,
        angel_interface=mock_angel_interface,
    )

    # Override with test-scoped addon and cache (fresh per test)
    ui.addon = mock_kodi_addon
    ui.cache = mock_simplecache_instance

    return ui, mock_logger, mock_angel_interface


@pytest.fixture
def mock_xbmc():
    """Convenience fixture combining common xbmcplugin and xbmcgui patches.

    Patches addDirectoryItem, endOfDirectory, and ListItem in a single yield.
    Useful for quick menu rendering tests without needing full ui_interface.

    Yields:
        tuple: (mock_add_item, mock_end_dir, mock_list_item)

    Example:
        mock_xbmc[1].assert_called()  # Check endOfDirectory called
    """
    with (
        patch("xbmcplugin.addDirectoryItem") as mock_add_item,
        patch("xbmcplugin.endOfDirectory") as mock_end_dir,
        patch("xbmcgui.ListItem") as mock_list_item,
    ):
        mock_list_item.return_value = MagicMock()
        yield mock_add_item, mock_end_dir, mock_list_item


@pytest.fixture
def mock_cache():
    """Convenience fixture for SimpleCache module patching.

    Patches the simplecache.SimpleCache constructor to return a controlled
    mock instance. Useful for testing cache-specific behavior (hit/miss logic,
    TTL handling, etc.) without full ui_interface.

    Yields:
        MagicMock: Cache instance mock with get() and set() methods.

    Example:
        mock_cache.get.return_value = {"data": "cached"}
        # ... run code that calls cache ...
        mock_cache.get.assert_called_with("key")
    """
    with patch("simplecache.SimpleCache") as mock_simple_cache:
        mock_cache_instance = MagicMock()
        mock_simple_cache.return_value = mock_cache_instance
        yield mock_cache_instance
