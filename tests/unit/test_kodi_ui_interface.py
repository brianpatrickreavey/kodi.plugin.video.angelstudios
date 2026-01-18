"""
Integration tests for KodiUIInterface main class.
Tests delegation to handlers and overall integration.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'plugin.video.angelstudios', 'resources', 'lib'))

import pytest
from unittest.mock import MagicMock
from kodi_ui_interface import KodiUIInterface


@pytest.fixture
def ui_interface():
    """Fixture for KodiUIInterface instance with mocked dependencies."""
    handle = 1
    url = "plugin://plugin.video.angelstudios/"
    logger = MagicMock()
    angel_interface = MagicMock()
    
    ui = KodiUIInterface(handle, url, logger, angel_interface)
    
    # Mock addon
    ui.addon = MagicMock()
    ui.addon.getAddonInfo.return_value = "profile_path"
    ui.addon.getSettingString.return_value = "off"
    ui.addon.getSettingBool.return_value = True
    
    # Mock handlers
    ui.menu_handler = MagicMock()
    ui.playback_handler = MagicMock()
    ui.cache_manager = MagicMock()
    ui.ui_helpers = MagicMock()
    
    return ui


def test_initialization(ui_interface):
    """Test that KodiUIInterface initializes correctly."""
    ui = ui_interface
    assert ui.handle == 1
    assert ui.kodi_url == "plugin://plugin.video.angelstudios/"
    assert ui.log is not None
    assert ui.angel_interface is not None
    assert ui.addon is not None
    assert ui.menu_handler is not None
    assert ui.playback_handler is not None
    assert ui.cache_manager is not None
    assert ui.ui_helpers is not None


def test_main_menu_delegation(ui_interface):
    """Test main_menu delegates to menu_handler."""
    ui = ui_interface
    ui.menu_handler.main_menu.return_value = True
    
    result = ui.main_menu()
    
    ui.menu_handler.main_menu.assert_called_once()
    assert result is True


def test_projects_menu_delegation(ui_interface):
    """Test projects_menu delegates to menu_handler."""
    ui = ui_interface
    ui.menu_handler.projects_menu.return_value = True
    
    result = ui.projects_menu("movies")
    
    ui.menu_handler.projects_menu.assert_called_once_with("movies")
    assert result is True


def test_seasons_menu_delegation(ui_interface):
    """Test seasons_menu delegates to menu_handler."""
    ui = ui_interface
    ui.menu_handler.seasons_menu.return_value = True
    
    result = ui.seasons_menu("movies", "test-slug")
    
    ui.menu_handler.seasons_menu.assert_called_once_with("movies", "test-slug")
    assert result is True


def test_episodes_menu_delegation(ui_interface):
    """Test episodes_menu delegates to menu_handler."""
    ui = ui_interface
    ui.menu_handler.episodes_menu.return_value = True
    
    result = ui.episodes_menu("movies", "test-slug", "season-1")
    
    ui.menu_handler.episodes_menu.assert_called_once_with("movies", "test-slug", "season-1")
    assert result is True


def test_watchlist_menu_delegation(ui_interface):
    """Test watchlist_menu delegates to menu_handler."""
    ui = ui_interface
    ui.menu_handler.watchlist_menu.return_value = None
    
    result = ui.watchlist_menu()
    
    ui.menu_handler.watchlist_menu.assert_called_once()
    assert result is None


def test_continue_watching_menu_delegation(ui_interface):
    """Test continue_watching_menu delegates to menu_handler."""
    ui = ui_interface
    ui.menu_handler.continue_watching_menu.return_value = True
    
    result = ui.continue_watching_menu("cursor")
    
    ui.menu_handler.continue_watching_menu.assert_called_once_with("cursor")
    assert result is True


def test_top_picks_menu_delegation(ui_interface):
    """Test top_picks_menu delegates to menu_handler."""
    ui = ui_interface
    ui.menu_handler.top_picks_menu.return_value = None
    
    result = ui.top_picks_menu()
    
    ui.menu_handler.top_picks_menu.assert_called_once()
    assert result is None


def test_play_episode_delegation(ui_interface):
    """Test play_episode delegates to playback_handler."""
    ui = ui_interface
    ui.playback_handler.play_episode.return_value = None
    
    result = ui.play_episode("guid", "slug")
    
    ui.playback_handler.play_episode.assert_called_once_with("guid", "slug")
    assert result is None


def test_play_video_delegation(ui_interface):
    """Test play_video delegates to playback_handler."""
    ui = ui_interface
    ui.playback_handler.play_video.return_value = None
    
    result = ui.play_video("url", {"data": "test"})
    
    ui.playback_handler.play_video.assert_called_once_with("url", {"data": "test"})
    assert result is None


def test_show_error_delegation(ui_interface):
    """Test show_error delegates to ui_helpers."""
    ui = ui_interface
    ui.ui_helpers.show_error.return_value = None
    
    result = ui.show_error("message", "title")
    
    ui.ui_helpers.show_error.assert_called_once_with("message", "title")
    assert result is None


def test_show_notification_delegation(ui_interface):
    """Test show_notification delegates to ui_helpers."""
    ui = ui_interface
    ui.ui_helpers.show_notification.return_value = None
    
    result = ui.show_notification("message", "title", 3000)
    
    ui.ui_helpers.show_notification.assert_called_once_with("message", "title", 3000)
    assert result is None


def test_show_auth_details_dialog_delegation(ui_interface):
    """Test show_auth_details_dialog delegates to ui_helpers."""
    ui = ui_interface
    ui.ui_helpers.show_auth_details_dialog.return_value = None
    
    result = ui.show_auth_details_dialog()
    
    ui.ui_helpers.show_auth_details_dialog.assert_called_once()
    assert result is None


def test_clear_cache_delegation(ui_interface):
    """Test clear_cache delegates to cache_manager."""
    ui = ui_interface
    ui.cache_manager.clear_cache.return_value = True
    
    result = ui.clear_cache()
    
    ui.cache_manager.clear_cache.assert_called_once()
    assert result is True


def test_clear_debug_data_delegation(ui_interface):
    """Test clear_debug_data delegates to ui_helpers."""
    ui = ui_interface
    ui.ui_helpers.clear_debug_data.return_value = True
    
    result = ui.clear_debug_data()
    
    ui.ui_helpers.clear_debug_data.assert_called_once()
    assert result is True


def test_set_angel_interface_delegation(ui_interface):
    """Test setAngelInterface delegates to ui_helpers."""
    ui = ui_interface
    angel_mock = MagicMock()
    ui.ui_helpers.setAngelInterface.return_value = None
    
    result = ui.setAngelInterface(angel_mock)
    
    ui.ui_helpers.setAngelInterface.assert_called_once_with(angel_mock)
    assert result is None


def test_create_plugin_url_delegation(ui_interface):
    """Test create_plugin_url delegates to ui_helpers."""
    ui = ui_interface
    ui.ui_helpers.create_plugin_url.return_value = "url"
    
    result = ui.create_plugin_url(action="test", id="123")
    
    ui.ui_helpers.create_plugin_url.assert_called_once_with(action="test", id="123")
    assert result == "url"


def test_get_trace_callback_delegation(ui_interface):
    """Test get_trace_callback delegates to ui_helpers."""
    ui = ui_interface
    ui.ui_helpers.get_trace_callback.return_value = None
    
    result = ui.get_trace_callback()
    
    ui.ui_helpers.get_trace_callback.assert_called_once()
    assert result is None


def test_force_logout_with_notification_delegation(ui_interface):
    """Test force_logout_with_notification delegates to ui_helpers."""
    ui = ui_interface
    ui.ui_helpers.force_logout_with_notification.return_value = None
    
    result = ui.force_logout_with_notification()
    
    ui.ui_helpers.force_logout_with_notification.assert_called_once()
    assert result is None


def test_clear_debug_data_with_notification_delegation(ui_interface):
    """Test clear_debug_data_with_notification delegates to ui_helpers."""
    ui = ui_interface
    ui.ui_helpers.clear_debug_data_with_notification.return_value = None
    
    result = ui.clear_debug_data_with_notification()
    
    ui.ui_helpers.clear_debug_data_with_notification.assert_called_once()
    assert result is None


def test_clear_cache_with_notification_delegation(ui_interface):
    """Test clear_cache_with_notification delegates to cache_manager."""
    ui = ui_interface
    ui.cache_manager.clear_cache_with_notification.return_value = None
    
    result = ui.clear_cache_with_notification()
    
    ui.cache_manager.clear_cache_with_notification.assert_called_once()
    assert result is None


def test_private_method_delegations(ui_interface):
    """Test private method delegations."""
    ui = ui_interface
    
    # Test cache-related delegations
    ui.cache_manager._cache_ttl.return_value = 3600
    assert ui._cache_ttl() == 3600
    ui.cache_manager._cache_ttl.assert_called_once()
    
    ui.cache_manager._project_cache_ttl.return_value = 7200
    assert ui._project_cache_ttl() == 7200
    ui.cache_manager._project_cache_ttl.assert_called_once()
    
    ui.cache_manager._episode_cache_ttl.return_value = 1800
    assert ui._episode_cache_ttl() == 1800
    ui.cache_manager._episode_cache_ttl.assert_called_once()
    
    # Test UI helpers delegations
    ui.ui_helpers._get_angel_project_type.return_value = "movie"
    assert ui._get_angel_project_type("movies") == "movie"
    ui.ui_helpers._get_angel_project_type.assert_called_once_with("movies")
    
    ui.ui_helpers._get_kodi_content_type.return_value = "movies"
    assert ui._get_kodi_content_type("movie") == "movies"
    ui.ui_helpers._get_kodi_content_type.assert_called_once_with("movie")
    
    ui.ui_helpers._get_debug_mode.return_value = "debug"
    assert ui._get_debug_mode() == "debug"
    ui.ui_helpers._get_debug_mode.assert_called_once()
    
    ui.ui_helpers._is_debug.return_value = True
    assert ui._is_debug() is True
    ui.ui_helpers._is_debug.assert_called_once()
    
    ui.ui_helpers._is_trace.return_value = False
    assert ui._is_trace() is False
    ui.ui_helpers._is_trace.assert_called_once()
    
    ui.ui_helpers._ensure_trace_dir.return_value = True
    assert ui._ensure_trace_dir() is True
    ui.ui_helpers._ensure_trace_dir.assert_called_once()
    
    ui.ui_helpers._redact_sensitive.return_value = {"redacted": True}
    assert ui._redact_sensitive({"data": "test"}) == {"redacted": True}
    ui.ui_helpers._redact_sensitive.assert_called_once_with({"data": "test"})
    
    ui.ui_helpers._trim_trace_files.return_value = None
    assert ui._trim_trace_files(10) is None
    ui.ui_helpers._trim_trace_files.assert_called_once_with(10)
    
    ui.ui_helpers._trace_callback.return_value = None
    assert ui._trace_callback({"payload": "test"}) is None
    ui.ui_helpers._trace_callback.assert_called_once_with({"payload": "test"})
    
    # Test playback handler delegations
    ui.playback_handler._ensure_isa_available.return_value = True
    assert ui._ensure_isa_available("hls") is True
    ui.playback_handler._ensure_isa_available.assert_called_once_with("hls")
    
    ui.playback_handler._get_quality_pref.return_value = {"mode": "auto"}
    assert ui._get_quality_pref() == {"mode": "auto"}
    ui.playback_handler._get_quality_pref.assert_called_once()
    
    # Test cache manager delegations
    ui.cache_manager._cache_enabled.return_value = True
    assert ui._cache_enabled() is True
    ui.cache_manager._cache_enabled.assert_called_once()
    
    ui.cache_manager._get_project.return_value = {"project": "data"}
    assert ui._get_project("slug") == {"project": "data"}
    ui.cache_manager._get_project.assert_called_once_with("slug")
    
    ui.cache_manager._deferred_prefetch_project.return_value = None
    assert ui._deferred_prefetch_project(["slug1"], 5) is None
    ui.cache_manager._deferred_prefetch_project.assert_called_once_with(["slug1"], 5)
    
    # Test UI helpers delegations
    ui.ui_helpers._normalize_contentseries_episode.return_value = {"normalized": True}
    assert ui._normalize_contentseries_episode({"raw": "data"}) == {"normalized": True}
    ui.ui_helpers._normalize_contentseries_episode.assert_called_once_with({"raw": "data"})