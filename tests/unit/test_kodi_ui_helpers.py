"""
Tests for KodiUIHelpers class.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'plugin.video.angelstudios', 'resources', 'lib'))

import pytest
from unittest.mock import patch, MagicMock
from kodi_ui_helpers import KodiUIHelpers


@pytest.fixture
def ui_helpers():
    """Fixture for KodiUIHelpers instance."""
    parent_mock = MagicMock()
    parent_mock.addon.getAddonInfo.return_value = "profile_path"
    parent_mock.addon.getSettingString.return_value = "off"
    parent_mock.log = MagicMock()
    return KodiUIHelpers(parent_mock)


def test_set_angel_interface(ui_helpers):
    """Test setAngelInterface sets the angel interface."""
    angel_interface_mock = MagicMock()
    ui_helpers.setAngelInterface(angel_interface_mock)
    assert ui_helpers.parent.angel_interface == angel_interface_mock


def test_show_error(ui_helpers):
    """Test show_error displays error dialog and logs."""
    with patch('xbmcgui.Dialog') as mock_dialog:
        ui_helpers.show_error("Test error", "Test Title")
        mock_dialog().ok.assert_called_once_with("Test Title", "Test error")
        ui_helpers.parent.log.error.assert_called_once()


def test_show_notification(ui_helpers):
    """Test show_notification displays notification and logs."""
    with patch('xbmcgui.Dialog') as mock_dialog:
        ui_helpers.show_notification("Test message", "Test Title", 3000)
        mock_dialog().notification.assert_called_once_with("Test Title", "Test message", time=3000)
        ui_helpers.parent.log.info.assert_called_once()


def test_show_auth_details_dialog_no_session(ui_helpers):
    """Test show_auth_details_dialog when no session available."""
    ui_helpers.parent.angel_interface = None
    with patch('xbmcgui.Dialog') as mock_dialog:
        ui_helpers.show_auth_details_dialog()
        mock_dialog().ok.assert_called_once()


def test_clear_debug_data_no_dir(ui_helpers):
    """Test clear_debug_data when trace dir does not exist."""
    with patch('os.path.isdir', return_value=False):
        result = ui_helpers.clear_debug_data()
        assert result is True
        ui_helpers.parent.log.info.assert_called_once()


def test_clear_debug_data_with_files(ui_helpers):
    """Test clear_debug_data removes files."""
    with patch('os.path.isdir', return_value=True), \
         patch('os.listdir', return_value=['file1.json', 'file2.json']), \
         patch('os.path.isfile', return_value=True), \
         patch('os.remove') as mock_remove:
        result = ui_helpers.clear_debug_data()
        assert result is True
        assert mock_remove.call_count == 2


def test_clear_debug_data_with_notification(ui_helpers):
    """Test clear_debug_data_with_notification."""
    with patch.object(ui_helpers, 'clear_debug_data', return_value=True), \
         patch.object(ui_helpers, 'show_notification') as mock_show:
        ui_helpers.clear_debug_data_with_notification()
        mock_show.assert_called_once_with("Debug data cleared.")


def test_force_logout_with_notification(ui_helpers):
    """Test force_logout_with_notification."""
    ui_helpers.parent.angel_interface = MagicMock()
    ui_helpers.parent.angel_interface.force_logout.return_value = True
    with patch.object(ui_helpers, 'show_notification') as mock_show:
        ui_helpers.force_logout_with_notification()
        mock_show.assert_called_once_with("Logged out locally.")


def test_get_debug_mode(ui_helpers):
    """Test _get_debug_mode returns setting."""
    ui_helpers.parent.addon.getSettingString.return_value = "debug"
    assert ui_helpers._get_debug_mode() == "debug"


def test_is_debug(ui_helpers):
    """Test _is_debug returns True for debug or trace."""
    ui_helpers.parent.addon.getSettingString.return_value = "debug"
    assert ui_helpers._is_debug() is True
    ui_helpers.parent.addon.getSettingString.return_value = "trace"
    assert ui_helpers._is_debug() is True
    ui_helpers.parent.addon.getSettingString.return_value = "off"
    assert ui_helpers._is_debug() is False


def test_is_trace(ui_helpers):
    """Test _is_trace returns True only for trace."""
    ui_helpers.parent.addon.getSettingString.return_value = "trace"
    assert ui_helpers._is_trace() is True
    ui_helpers.parent.addon.getSettingString.return_value = "debug"
    assert ui_helpers._is_trace() is False


def test_ensure_trace_dir_not_trace(ui_helpers):
    """Test _ensure_trace_dir does nothing when not trace mode."""
    ui_helpers.parent.addon.getSettingString.return_value = "off"
    assert ui_helpers._ensure_trace_dir() is False


def test_redact_sensitive_dict(ui_helpers):
    """Test _redact_sensitive redacts dict."""
    data = {"password": "secret", "normal": "value"}
    redacted = ui_helpers._redact_sensitive(data)
    assert redacted["password"] == "<redacted>"
    assert redacted["normal"] == "value"


def test_redact_sensitive_string(ui_helpers):
    """Test _redact_sensitive redacts string."""
    data = 'Authorization: Bearer token123'
    redacted = ui_helpers._redact_sensitive(data)
    assert "<redacted>" in redacted


def test_trim_trace_files_not_trace(ui_helpers):
    """Test _trim_trace_files does nothing when not trace."""
    ui_helpers.parent.addon.getSettingString.return_value = "off"
    ui_helpers._trim_trace_files()


def test_get_trace_callback_not_trace(ui_helpers):
    """Test get_trace_callback returns None when not trace."""
    ui_helpers.parent.addon.getSettingString.return_value = "off"
    assert ui_helpers.get_trace_callback() is None


def test_get_trace_callback_trace(ui_helpers):
    """Test get_trace_callback returns callback when trace."""
    ui_helpers.parent.addon.getSettingString.return_value = "trace"
    callback = ui_helpers.get_trace_callback()
    assert callable(callback)


def test_normalize_contentseries_episode(ui_helpers):
    """Test _normalize_contentseries_episode."""
    episode = {"id": "1", "name": "Test", "extra": "ignored"}
    normalized = ui_helpers._normalize_contentseries_episode(episode)
    assert "id" in normalized
    assert "name" in normalized
    assert "extra" not in normalized


def test_create_plugin_url(ui_helpers):
    """Test create_plugin_url."""
    ui_helpers.parent.kodi_url = "plugin://test"
    url = ui_helpers.create_plugin_url(action="test", id="123")
    assert url == "plugin://test?action=test&id=123"


def test_get_angel_project_type(ui_helpers):
    """Test _get_angel_project_type."""
    assert ui_helpers._get_angel_project_type("movies") == "movie"
    assert ui_helpers._get_angel_project_type("unknown") == "unknown"


def test_get_kodi_content_type(ui_helpers):
    """Test _get_kodi_content_type."""
    assert ui_helpers._get_kodi_content_type("movies") == "movies"
    assert ui_helpers._get_kodi_content_type("unknown") == "videos"
