import pytest
from unittest.mock import patch, MagicMock
from kodi_ui_interface import KodiUIInterface
from .unittest_data import MOCK_EPISODE_DATA


def test_set_angel_interface():
    """Test setAngelInterface sets the angel interface."""
    logger_mock = MagicMock()
    ui_interface = KodiUIInterface(handle=1, url="test_url", logger=logger_mock, angel_interface=None)

    angel_interface_mock = MagicMock()
    ui_interface.setAngelInterface(angel_interface_mock)

    assert ui_interface.angel_interface == angel_interface_mock


class TestUtils:
    @pytest.mark.parametrize(
        "watch_position,duration,expected_resume",
        [
            (0.0, 100.0, 0.0),
            (50.0, 100.0, 0.5),
            (100.0, 100.0, 1.0),
            (25.5, 102.0, 0.25),
            (1.0, 3600.0, 0.000278),
        ],
    )
    def test_apply_progress_bar_valid(self, ui_interface, watch_position, duration, expected_resume):
        """Test _apply_progress_bar with valid watch position and duration."""
        ui, _, _ = ui_interface

        mock_list_item = MagicMock()
        mock_info_tag = MagicMock()
        mock_list_item.getVideoInfoTag.return_value = mock_info_tag

        ui._apply_progress_bar(mock_list_item, watch_position, duration)

        mock_list_item.getVideoInfoTag.assert_called_once()
        # Allow small floating point difference
        actual_resume = mock_info_tag.setResumePoint.call_args[0][0]
        assert abs(actual_resume - expected_resume) < 0.001

    @pytest.mark.parametrize(
        "watch_position,duration",
        [
            (None, 100.0),
            (50.0, None),
            (None, None),
            (50.0, 0),
            (50.0, 0.0),
        ],
    )
    def test_apply_progress_bar_invalid_input(self, ui_interface, watch_position, duration):
        """Test _apply_progress_bar gracefully handles invalid input."""
        ui, _, _ = ui_interface

        mock_list_item = MagicMock()
        mock_info_tag = MagicMock()
        mock_list_item.getVideoInfoTag.return_value = mock_info_tag

        # Should not raise exception
        ui._apply_progress_bar(mock_list_item, watch_position, duration)

        # Should not call setResumePoint for invalid input
        mock_info_tag.setResumePoint.assert_not_called()

    def test_apply_progress_bar_clamps_to_range(self, ui_interface):
        """Test _apply_progress_bar clamps resume point to [0.0, 1.0]."""
        ui, _, _ = ui_interface

        mock_list_item = MagicMock()
        mock_info_tag = MagicMock()
        mock_list_item.getVideoInfoTag.return_value = mock_info_tag

        # Test watch position > duration (clamped to 1.0)
        ui._apply_progress_bar(mock_list_item, 150.0, 100.0)
        actual_resume = mock_info_tag.setResumePoint.call_args[0][0]
        assert actual_resume == 1.0

        # Test negative watch position (clamped to 0.0)
        mock_info_tag.reset_mock()
        ui._apply_progress_bar(mock_list_item, -10.0, 100.0)
        actual_resume = mock_info_tag.setResumePoint.call_args[0][0]
        assert actual_resume == 0.0

    def test_apply_progress_bar_handles_type_conversion(self, ui_interface):
        """Test _apply_progress_bar handles string inputs that can be converted to float."""
        ui, _, _ = ui_interface

        mock_list_item = MagicMock()
        mock_info_tag = MagicMock()
        mock_list_item.getVideoInfoTag.return_value = mock_info_tag

        # String inputs that are valid floats
        ui._apply_progress_bar(mock_list_item, "50.0", "100.0")

        mock_info_tag.setResumePoint.assert_called_once()
        actual_resume = mock_info_tag.setResumePoint.call_args[0][0]
        assert actual_resume == 0.5

    def test_apply_progress_bar_handles_value_error(self, ui_interface):
        """Test _apply_progress_bar gracefully handles ValueError from invalid string conversion."""
        ui, logger_mock, _ = ui_interface

        mock_list_item = MagicMock()
        mock_info_tag = MagicMock()
        mock_list_item.getVideoInfoTag.return_value = mock_info_tag

        # String that cannot be converted to float should raise ValueError
        ui._apply_progress_bar(mock_list_item, "not-a-number", "100.0")

        # Should not call setResumePoint on error
        mock_info_tag.setResumePoint.assert_not_called()
        # Should log warning
        logger_mock.warning.assert_called()

    def test_apply_progress_bar_handles_type_error(self, ui_interface):
        """Test _apply_progress_bar gracefully handles TypeError from incompatible types."""
        ui, logger_mock, _ = ui_interface

        mock_list_item = MagicMock()
        mock_info_tag = MagicMock()
        mock_list_item.getVideoInfoTag.return_value = mock_info_tag

        # Object that cannot be converted to float should raise TypeError
        ui._apply_progress_bar(mock_list_item, {"nested": "dict"}, 100.0)

        # Should not call setResumePoint on error
        mock_info_tag.setResumePoint.assert_not_called()
        # Should log warning
        logger_mock.warning.assert_called()

    def test_apply_progress_bar_handles_list_item_error(self, ui_interface):
        """Test _apply_progress_bar gracefully handles exceptions from Kodi ListItem methods."""
        ui, logger_mock, _ = ui_interface

        mock_list_item = MagicMock()
        # Simulate getVideoInfoTag() raising an exception (unexpected Kodi behavior)
        mock_list_item.getVideoInfoTag.side_effect = RuntimeError("Kodi error")

        # Should not raise exception, but catch it
        ui._apply_progress_bar(mock_list_item, 50.0, 100.0)

        # Should log warning
        logger_mock.warning.assert_called()

    @pytest.mark.parametrize("is_playback", [True, False])
    @pytest.mark.parametrize("episode_available", [True, False])
    def test_create_list_item_from_episode(self, ui_interface, mock_xbmc, is_playback, episode_available):
        """Test _create_list_item_from_episode creates a ListItem with episode metadata."""
        ui, logger_mock, angel_interface_mock = ui_interface
        mock_add_item, mock_end_dir, mock_list_item = mock_xbmc

        episode = MOCK_EPISODE_DATA["episode"]
        project = MOCK_EPISODE_DATA["project"]
        stream_url = episode.get("source", {}).get("url", None)

        if not episode_available:
            episode.pop("source", None)

        with (
            patch("xbmcgui.ListItem") as mock_list_item,
            patch("xbmc.VideoStreamDetail") as mock_video_stream_detail,
            patch.object(ui, "_process_attributes_to_infotags") as mock_process_attrs,
        ):

            mock_list_item.return_value = MagicMock()

            result = ui._create_list_item_from_episode(
                episode=episode, project=project, content_type="series", stream_url=stream_url, is_playback=is_playback
            )

            # Ensure ListItem was created
            mock_list_item.assert_called_once()
            list_item_instance = mock_list_item.return_value
            list_item_instance.setProperty.assert_any_call("IsPlayable", "true" if episode_available else "false")

            # Conditional assertions based on is_playback
            if is_playback:
                list_item_instance.setPath.assert_called_once_with(stream_url)
                list_item_instance.setIsFolder.assert_called_once_with(False)

                # Ensure _process_attributes_to_infotags was called
                mock_video_stream_detail.assert_called_once_with()
                video_stream_mock = mock_video_stream_detail.return_value
                video_stream_mock.setCodec.assert_called_once_with("h264")
                video_stream_mock.setWidth.assert_called_once_with(1920)
                video_stream_mock.setHeight.assert_called_once_with(1080)

            else:
                list_item_instance.setIsFolder.assert_called_once_with(True)

            mock_process_attrs.assert_called_once_with(list_item_instance, episode)

            # Ensure the result is the ListItem
            assert result == list_item_instance

    def test_process_attributes_to_infotags(self, ui_interface, mock_xbmc):
        """Test _process_attributes_to_infotags sets info tags on ListItem."""
        ui, logger_mock, angel_interface_mock = ui_interface
        mock_add_item, mock_end_dir, mock_list_item = mock_xbmc

        episode = MOCK_EPISODE_DATA["episode"]
        mock_list_item = MagicMock()
        mock_info_tag = MagicMock()
        mock_list_item.getVideoInfoTag.return_value = mock_info_tag

        # Mock Cloudinary URL calls
        angel_interface_mock.get_cloudinary_url.return_value = "http://example.com/poster.jpg"

        ui._process_attributes_to_infotags(mock_list_item, episode)

        # Ensure getVideoInfoTag was called
        mock_list_item.getVideoInfoTag.assert_called_once()

        # Check that setTitle is called for 'name'
        mock_info_tag.setTitle.assert_called_with(episode["name"])

        # Art assertions: Cloudinary keys should result in setArt call
        expected_art = {
            "poster": "http://example.com/poster.jpg",
            "logo": "http://example.com/poster.jpg",
            "clearlogo": "http://example.com/poster.jpg",
            "icon": "http://example.com/poster.jpg",
            "fanart": "http://example.com/poster.jpg",
            "landscape": "http://example.com/poster.jpg",
        }
        mock_list_item.setArt.assert_called_once_with(expected_art)
        angel_interface_mock.get_cloudinary_url.assert_called()  # Ensure Cloudinary processing happened

        logger_mock.info.assert_any_call(f"Processing attributes for list item: {mock_list_item.getLabel.return_value}")
        logger_mock.debug.assert_any_call(f"Attribute dict: {episode}")

    def test_process_attributes_to_infotags_with_nested_season_dict(self, ui_interface, mock_xbmc):
        """Test _process_attributes_to_infotags extracts seasonNumber from nested season dict."""
        ui, logger_mock, angel_interface_mock = ui_interface
        mock_add_item, mock_end_dir, mock_list_item = mock_xbmc

        # Episode with nested season dict containing seasonNumber
        episode = {
            "name": "Test Episode",
            "media_type": "episode",
            "season": {"seasonNumber": 2, "name": "Season 2"},  # Nested dict with seasonNumber
        }
        mock_list_item = MagicMock()
        mock_info_tag = MagicMock()
        mock_list_item.getVideoInfoTag.return_value = mock_info_tag
        mock_list_item.getLabel.return_value = "Test Episode"

        ui._process_attributes_to_infotags(mock_list_item, episode)

        # Verify title and media_type were set
        mock_info_tag.setTitle.assert_called_with("Test Episode")
        mock_info_tag.setMediaType.assert_called_with("episode")
        # Verify season was extracted and set
        mock_info_tag.setSeason.assert_called_with(2)

    def test_process_attributes_to_infotags_with_nested_source_dict(self, ui_interface, mock_xbmc):
        """Test _process_attributes_to_infotags skips nested source dict."""
        ui, logger_mock, angel_interface_mock = ui_interface
        mock_add_item, mock_end_dir, mock_list_item = mock_xbmc

        # Episode with nested source dict that should be skipped
        episode = {
            "name": "Test Episode",
            "media_type": "episode",
            "source": {"id": "source-1", "name": "Source Name"},  # Nested dict - should be skipped
        }
        mock_list_item = MagicMock()
        mock_info_tag = MagicMock()
        mock_list_item.getVideoInfoTag.return_value = mock_info_tag
        mock_list_item.getLabel.return_value = "Test Episode"

        ui._process_attributes_to_infotags(mock_list_item, episode)

        # Verify title and media_type were set
        mock_info_tag.setTitle.assert_called_with("Test Episode")
        mock_info_tag.setMediaType.assert_called_with("episode")
        # Verify no error logged (source was quietly skipped)
        logger_mock.info.assert_any_call("Processing attributes for list item: Test Episode")

    def test_process_attributes_to_infotags_with_nested_watchposition_dict(self, ui_interface, mock_xbmc):
        """Test _process_attributes_to_infotags skips nested watchPosition dict."""
        ui, logger_mock, angel_interface_mock = ui_interface
        mock_add_item, mock_end_dir, mock_list_item = mock_xbmc

        # Episode with nested watchPosition dict that should be skipped
        episode = {
            "name": "Test Episode",
            "media_type": "episode",
            "watchPosition": {"position": 0.5, "duration": 1.0},  # Nested dict - should be skipped
        }
        mock_list_item = MagicMock()
        mock_info_tag = MagicMock()
        mock_list_item.getVideoInfoTag.return_value = mock_info_tag
        mock_list_item.getLabel.return_value = "Test Episode"

        ui._process_attributes_to_infotags(mock_list_item, episode)

        # Verify title and media_type were set
        mock_info_tag.setTitle.assert_called_with("Test Episode")
        mock_info_tag.setMediaType.assert_called_with("episode")
        # Verify no error logged (watchPosition was quietly skipped)
        logger_mock.info.assert_any_call("Processing attributes for list item: Test Episode")

    def test_show_error(self, ui_interface, mock_xbmc):
        """Test show_error displays an error dialog."""
        ui, logger_mock, angel_interface_mock = ui_interface
        mock_add_item, mock_end_dir, mock_list_item = mock_xbmc

        with (
            patch("xbmcgui.Dialog") as mock_dialog,
            patch("xbmc.log") as mock_xbmc_log,
            patch("xbmc.LOGERROR") as mock_log_error,
        ):
            mock_dialog_instance = MagicMock()
            mock_dialog.return_value = mock_dialog_instance

            ui.show_error("Test error message")

            mock_dialog_instance.ok.assert_called_once_with("Angel Studios", "Test error message")
            mock_xbmc_log.assert_called_once_with("Error shown to user: Test error message", mock_log_error)

    def test_show_notification(self, ui_interface, mock_xbmc):
        """Test show_notification displays a notification."""
        ui, logger_mock, angel_interface_mock = ui_interface
        mock_add_item, mock_end_dir, mock_list_item = mock_xbmc

        with patch("xbmcgui.Dialog") as mock_dialog:
            mock_dialog_instance = MagicMock()
            mock_dialog.return_value = mock_dialog_instance

            ui.show_notification("Test notification message")

            mock_dialog_instance.notification.assert_called_once_with(
                "Angel Studios", "Test notification message", time=5000
            )

    def test_clear_cache_sql_path_non_empty(self, ui_interface):
        """clear_cache deletes all SQL rows and window properties, returns True."""
        ui, logger_mock, angel_interface_mock = ui_interface
        cache_mock = MagicMock()
        ui.cache = cache_mock

        cache_mock._execute_sql = MagicMock()
        cache_mock._execute_sql.side_effect = [
            MagicMock(fetchall=MagicMock(return_value=[("id1",), ("id2",)])),  # initial ids
            None,  # delete id1
            None,  # delete id2
            MagicMock(fetchall=MagicMock(return_value=[])),  # after ids
        ]
        cache_mock._win = MagicMock()

        assert ui.clear_cache() is True
        assert cache_mock._execute_sql.call_count == 4
        assert cache_mock._win.clearProperty.call_count == 2

    def test_clear_cache_sql_path_empty(self, ui_interface):
        """clear_cache returns True on empty cache."""
        ui, logger_mock, angel_interface_mock = ui_interface
        cache_mock = MagicMock()
        ui.cache = cache_mock

        cache_mock._execute_sql = MagicMock()
        cache_mock._execute_sql.side_effect = [
            MagicMock(fetchall=MagicMock(return_value=[])),  # initial ids
        ]
        cache_mock._win = MagicMock()

        assert ui.clear_cache() is True
        assert cache_mock._execute_sql.call_count == 1
        cache_mock._win.clearProperty.assert_not_called()

    def test_clear_cache_sql_exception(self, ui_interface):
        """clear_cache returns False on SQL failures."""
        ui, logger_mock, angel_interface_mock = ui_interface
        cache_mock = MagicMock()
        ui.cache = cache_mock

        cache_mock._execute_sql = MagicMock(side_effect=Exception("boom"))
        cache_mock._win = MagicMock()
        assert ui.clear_cache() is False

    def test_clear_cache_no_introspection(self, ui_interface):
        """clear_cache returns False and logs when cache lacks SQL helpers."""
        ui, logger_mock, angel_interface_mock = ui_interface
        ui.cache = object()

        assert ui.clear_cache() is False
        logger_mock.info.assert_any_call("SimpleCache before clear: introspection not available")

    def test_clear_cache_clear_property_exception(self, ui_interface):
        """clear_cache swallows window clear exceptions and still returns True."""
        ui, logger_mock, angel_interface_mock = ui_interface
        cache_mock = MagicMock()
        ui.cache = cache_mock

        cache_mock._execute_sql = MagicMock()
        cache_mock._execute_sql.side_effect = [
            MagicMock(fetchall=MagicMock(return_value=[("id1",), ("id2",)])),  # initial ids
            None,  # delete id1
            None,  # delete id2
            MagicMock(fetchall=MagicMock(return_value=[])),  # after ids
        ]
        cache_mock._win = MagicMock()
        cache_mock._win.clearProperty.side_effect = [Exception("win boom"), Exception("win boom 2")]

        assert ui.clear_cache() is True
        assert cache_mock._execute_sql.call_count == 4
        assert cache_mock._win.clearProperty.call_count == 2


class TestAdditionalCoverage:
    def test_cache_enabled_disable_cache_true_probe_false(self, ui_interface):
        from unittest.mock import MagicMock, patch

        ui, logger_mock, angel_interface_mock = ui_interface

        # Fresh addon scoped to this test only to avoid leaking disable_cache state
        fresh_addon = MagicMock()
        fresh_addon.getSettingBool.side_effect = lambda key: True if key == "disable_cache" else False
        fresh_addon.getSettingString.return_value = "off"
        fresh_addon.getSettingInt.return_value = 12

        ui.addon = fresh_addon

        with patch("xbmcaddon.Addon", return_value=fresh_addon):
            assert ui._cache_enabled() is False

    def test_cache_enabled_not_callable(self, ui_interface):
        ui, _, _ = ui_interface
        ui.addon.getSettingBool = None

        assert ui._cache_enabled() is True

        ui.addon.getSettingBool = MagicMock(return_value=False)

    def test_cache_enabled_disabled_false_returns_true(self, ui_interface):
        ui, _, _ = ui_interface
        ui.addon.getSettingBool = MagicMock(return_value=False)

        assert ui._cache_enabled() is True

    def test_cache_enabled_exception_returns_true(self, ui_interface):
        ui, _, _ = ui_interface
        ui.addon.getSettingBool = MagicMock(side_effect=RuntimeError("boom"))

        assert ui._cache_enabled() is True

    def test_cache_enabled_non_bool_disable_value(self, ui_interface):
        ui, _, _ = ui_interface

        def fake_get(key):
            if key == "disable_cache":
                return "y"
            if key == "__cache_probe__":
                return False
            return False

        ui.addon.getSettingBool = MagicMock(side_effect=fake_get)

        assert ui._cache_enabled() is True

    def test_cache_enabled_probe_not_bool(self, ui_interface):
        ui, _, _ = ui_interface

        ui.addon.getSettingBool = MagicMock()

        def fake_get(key):
            if key == "disable_cache":
                return True
            if key == "__cache_probe__":
                return "maybe"
            return False

        ui.addon.getSettingBool.side_effect = fake_get

        assert ui._cache_enabled() is False

    def test_get_debug_mode_invalid(self, ui_interface):
        ui, logger_mock, angel_interface_mock = ui_interface
        ui.addon.getSettingString.return_value = "nonsense"

        assert ui._get_debug_mode() == "off"

    def test_get_debug_mode_exception(self, ui_interface):
        ui, _, _ = ui_interface
        ui.addon.getSettingString.side_effect = RuntimeError("boom")

        assert ui._get_debug_mode() == "off"

    def test_is_debug_true_for_debug_mode(self, ui_interface):
        ui, _, _ = ui_interface
        ui.addon.getSettingString.return_value = "debug"

        assert ui._is_debug() is True

    def test_is_debug_false_for_off_mode(self, ui_interface):
        ui, _, _ = ui_interface
        ui.addon.getSettingString.return_value = "off"

        assert ui._is_debug() is False

    def test_is_trace_true_for_trace_mode(self, ui_interface):
        ui, _, _ = ui_interface
        ui.addon.getSettingString.return_value = "trace"

        assert ui._is_trace() is True

    def test_ensure_trace_dir_not_trace(self, ui_interface):
        ui, logger_mock, angel_interface_mock = ui_interface
        ui.addon.getSettingString.return_value = "off"

        assert ui._ensure_trace_dir() is False

    def test_ensure_trace_dir_exception(self, ui_interface, monkeypatch):
        ui, logger_mock, angel_interface_mock = ui_interface
        ui.addon.getSettingString.return_value = "trace"
        monkeypatch.setattr(ui, "_is_trace", lambda: True)
        monkeypatch.setattr("os.makedirs", MagicMock(side_effect=OSError("boom")))

        assert ui._ensure_trace_dir() is False
        logger_mock.error.assert_any_call(f"Failed to ensure trace directory {ui.trace_dir}: boom")

    def test_redact_sensitive_list(self, ui_interface):
        ui, _, _ = ui_interface
        data = [{"token": "abc", "nested": {"password": "secret"}, "ok": "v"}]

        redacted = ui._redact_sensitive(data)

        assert redacted[0]["token"] == "<redacted>"
        assert redacted[0]["nested"]["password"] == "<redacted>"
        assert redacted[0]["ok"] == "v"

    def test_trim_trace_files_removes_oldest(self, ui_interface, monkeypatch):
        ui, logger_mock, angel_interface_mock = ui_interface
        ui.trace_dir = "/tmp/trace"
        files = ["a.json", "b.json", "c.json"]
        monkeypatch.setattr("os.listdir", MagicMock(return_value=files))
        monkeypatch.setattr("os.path.isfile", MagicMock(return_value=True))
        monkeypatch.setattr("os.path.getmtime", MagicMock(side_effect=[3, 2, 1]))
        removed = []

        def fake_remove(path):
            removed.append(path)

        monkeypatch.setattr("os.remove", fake_remove)

        ui._trim_trace_files(max_files=1)

        assert len(removed) == 2

    def test_trim_trace_files_remove_exception(self, ui_interface, monkeypatch):
        ui, _, _ = ui_interface
        ui.trace_dir = "/tmp/trace"
        files = ["a.json", "b.json"]
        monkeypatch.setattr("os.listdir", MagicMock(return_value=files))
        monkeypatch.setattr("os.path.isfile", MagicMock(return_value=True))
        monkeypatch.setattr("os.path.getmtime", MagicMock(side_effect=[1, 2]))

        def boom(path):
            raise RuntimeError("remove boom")

        monkeypatch.setattr("os.remove", boom)

        ui._trim_trace_files(max_files=0)

    def test_trim_trace_files_listdir_exception(self, ui_interface, monkeypatch):
        ui, logger_mock, _ = ui_interface
        ui.trace_dir = "/tmp/trace"
        monkeypatch.setattr("os.listdir", MagicMock(side_effect=RuntimeError("ls boom")))

        ui._trim_trace_files(max_files=1)

        logger_mock.error.assert_any_call("Failed to trim trace files: ls boom")

    def test_trace_callback_not_trace(self, ui_interface, monkeypatch):
        ui, logger_mock, angel_interface_mock = ui_interface
        monkeypatch.setattr(ui, "_is_trace", lambda: False)

        assert ui._trace_callback({"a": 1}) is None

    def test_trace_callback_ensure_dir_fails(self, ui_interface, monkeypatch):
        ui, logger_mock, angel_interface_mock = ui_interface
        monkeypatch.setattr(ui, "_is_trace", lambda: True)
        monkeypatch.setattr(ui, "_ensure_trace_dir", lambda: False)

        assert ui._trace_callback({"a": 1}) is None

    def test_trace_callback_write_error(self, ui_interface, monkeypatch):
        ui, logger_mock, angel_interface_mock = ui_interface
        monkeypatch.setattr(ui, "_is_trace", lambda: True)
        monkeypatch.setattr(ui, "_ensure_trace_dir", lambda: True)
        monkeypatch.setattr("builtins.open", MagicMock(side_effect=OSError("boom")))

        ui._trace_callback({"token": "secret"})

        assert any("Failed to write trace file" in call.args[0] for call in logger_mock.error.call_args_list)

    def test_projects_menu_non_serializable_projects_logs(self, ui_interface, mock_xbmc):
        ui, logger_mock, angel_interface_mock = ui_interface
        ui._cache_enabled = MagicMock(return_value=False)
        projects = [
            {
                "name": "Bad",
                "slug": "bad",
                "projectType": "movies",
                "seasons": [],
            }
        ]
        angel_interface_mock.get_projects.return_value = projects

        with patch("kodi_ui_interface.json.dumps", side_effect=[TypeError("boom"), "{}", "{}"]):
            ui.projects_menu(content_type="movies")

        logger_mock.info.assert_any_call("Projects: <non-serializable type list>")

    def test_play_episode_cache_disabled_path(self, ui_interface, monkeypatch):
        """Test play_episode with cache disabled uses _get_project without caching."""
        ui, logger_mock, angel_interface_mock = ui_interface
        monkeypatch.setattr(ui, "_cache_enabled", lambda: False)

        from .unittest_data import MOCK_PROJECT_DATA

        project_data = MOCK_PROJECT_DATA["single_season_project"]

        with patch.object(ui, "_get_project", return_value=project_data) as mock_get_project:
            ui.play_episode(project_data["seasons"][0]["episodes"][0]["guid"], project_data["slug"])
            # Verify _get_project was called (which handles cache internally)
            mock_get_project.assert_called_once_with(project_data["slug"])

    def test_clear_debug_data_dir_missing(self, ui_interface, monkeypatch):
        ui, logger_mock, angel_interface_mock = ui_interface
        monkeypatch.setattr("os.path.isdir", MagicMock(return_value=False))

        assert ui.clear_debug_data() is True
        logger_mock.info.assert_any_call("Trace directory does not exist; nothing to clear")

    def test_clear_debug_data_exception(self, ui_interface, monkeypatch):
        ui, logger_mock, angel_interface_mock = ui_interface
        monkeypatch.setattr("os.path.isdir", MagicMock(side_effect=RuntimeError("boom")))

        assert ui.clear_debug_data() is False
        logger_mock.error.assert_any_call("Failed to clear debug data: boom")

    def test_clear_debug_data_success_path(self, ui_interface, monkeypatch, tmp_path):
        ui, logger_mock, angel_interface_mock = ui_interface
        trace_dir = tmp_path / "trace"
        trace_dir.mkdir()
        file1 = trace_dir / "a.log"
        file2 = trace_dir / "b.log"
        file1.write_text("x")
        file2.write_text("y")

        ui.trace_dir = str(trace_dir)
        monkeypatch.setattr("os.path.isdir", MagicMock(return_value=True))
        monkeypatch.setattr("os.listdir", MagicMock(return_value=["a.log", "b.log"]))
        monkeypatch.setattr("os.path.isfile", MagicMock(return_value=True))

        assert ui.clear_debug_data() is True
        logger_mock.info.assert_any_call(f"Cleared 2 trace files from {ui.trace_dir}")

    def test_clear_debug_data_remove_exception(self, ui_interface, monkeypatch, tmp_path):
        ui, logger_mock, angel_interface_mock = ui_interface
        trace_dir = tmp_path / "trace"
        trace_dir.mkdir()
        file1 = trace_dir / "a.log"
        file1.write_text("x")

        ui.trace_dir = str(trace_dir)
        monkeypatch.setattr("os.path.isdir", MagicMock(return_value=True))
        monkeypatch.setattr("os.listdir", MagicMock(return_value=["a.log"]))
        monkeypatch.setattr("os.path.isfile", MagicMock(return_value=True))
        monkeypatch.setattr("os.remove", MagicMock(side_effect=RuntimeError("rm boom")))

        assert ui.clear_debug_data() is True

    def test_get_project_cache_disabled(self, ui_interface, monkeypatch):
        ui, logger_mock, angel_interface_mock = ui_interface
        monkeypatch.setattr(ui, "_cache_enabled", lambda: False)
        angel_interface_mock.get_project.return_value = {"slug": "s"}

        ui._get_project("slug")
        logger_mock.debug.assert_any_call("Cache disabled; bypassing project cache")


class TestInputStreamAdaptive:
    """Tests for InputStream Adaptive availability checking."""

    @staticmethod
    def _make_cond_visibility(helper_installed: bool, isa_installed: bool):
        """Helper to create fake getCondVisibility function."""

        def _fake(query: str, *_args, **_kwargs) -> bool:
            if query == "System.HasAddon(script.module.inputstreamhelper)":
                return helper_installed
            if query == "System.HasAddon(inputstream.adaptive)":
                return isa_installed
            return False

        return _fake

    @staticmethod
    def _install_helper_module(monkeypatch, helper_cls):
        """Install fake inputstreamhelper module for testing."""
        import sys
        from types import ModuleType

        helper_module = ModuleType("inputstreamhelper")
        helper_module.Helper = helper_cls  # type: ignore[attr-defined]
        monkeypatch.setitem(sys.modules, "inputstreamhelper", helper_module)

    def test_ensure_isa_available_helper_missing_no_isa(self, ui_interface, monkeypatch):
        """Test ISA check when both helper and ISA are missing."""
        ui, logger_mock, angel_interface_mock = ui_interface
        monkeypatch.setattr("xbmc.getCondVisibility", self._make_cond_visibility(False, False))
        assert ui._ensure_isa_available("hls") is False

    def test_ensure_isa_available_helper_missing_with_isa(self, ui_interface, monkeypatch):
        """Test ISA check when helper missing but ISA is installed."""
        ui, logger_mock, angel_interface_mock = ui_interface
        monkeypatch.setattr("xbmc.getCondVisibility", self._make_cond_visibility(False, True))
        assert ui._ensure_isa_available("hls") is True

    def test_ensure_isa_available_success(self, ui_interface, monkeypatch):
        """Test ISA check when helper successfully validates ISA."""
        ui, logger_mock, angel_interface_mock = ui_interface

        class DummyHelper:
            def __init__(self, manifest_type):
                self.manifest_type = manifest_type

            def check_inputstream(self):
                return True

        monkeypatch.setattr("xbmc.getCondVisibility", self._make_cond_visibility(True, True))
        self._install_helper_module(monkeypatch, DummyHelper)
        assert ui._ensure_isa_available("hls") is True

    def test_ensure_isa_available_failure(self, ui_interface, monkeypatch):
        """Test ISA check when helper validation fails."""
        ui, logger_mock, angel_interface_mock = ui_interface

        class DummyHelper:
            def __init__(self, manifest_type):
                self.manifest_type = manifest_type

            def check_inputstream(self):
                return False

        monkeypatch.setattr("xbmc.getCondVisibility", self._make_cond_visibility(True, False))
        self._install_helper_module(monkeypatch, DummyHelper)
        assert ui._ensure_isa_available("hls") is False

    def test_ensure_isa_available_import_failure_falls_back_to_isa(self, ui_interface, monkeypatch):
        """Test ISA check falls back to direct check when helper import fails."""
        ui, logger_mock, angel_interface_mock = ui_interface
        monkeypatch.setattr("xbmc.getCondVisibility", self._make_cond_visibility(True, True))

        import builtins

        real_import = builtins.__import__

        def _fake_import(name, *args, **kwargs):
            if name == "inputstreamhelper":
                raise ImportError("inject import failure")
            return real_import(name, *args, **kwargs)

        monkeypatch.setattr(builtins, "__import__", _fake_import)
        assert ui._ensure_isa_available("hls") is True
