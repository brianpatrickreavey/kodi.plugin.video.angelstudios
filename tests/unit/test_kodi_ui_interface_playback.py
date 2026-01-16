from unittest.mock import patch, MagicMock
import pytest
from .unittest_data import MOCK_PROJECT_DATA, MOCK_EPISODE_DATA, TEST_EXCEPTION_MESSAGE
import copy


class TestEpisodePlayback:
    @pytest.mark.parametrize("cache_hit", [False, True])
    @pytest.mark.parametrize("project_data", MOCK_PROJECT_DATA.values())
    def test_play_episode(self, ui_interface, mock_xbmc, mock_cache, project_data, cache_hit):
        """Test refactored play_episode using cached project data."""
        ui, logger_mock, angel_interface_mock = ui_interface
        mock_add_item, mock_end_dir, mock_list_item = mock_xbmc

        project_slug = project_data["slug"]
        episode_data = project_data["seasons"][0]["episodes"][0]
        episode_guid = episode_data["guid"]

        # Setup _get_project to return project data
        with (
            patch.object(ui, "_get_project", return_value=project_data) as mock_get_project,
            patch.object(ui, "play_video") as mock_play_video,
        ):
            ui.play_episode(episode_guid, project_slug)

            # Assertions
            mock_get_project.assert_called_once_with(project_slug)
            mock_play_video.assert_called_once_with(episode_data={"episode": episode_data, "project": project_data})

    def test_play_episode_project_not_found(self, ui_interface, mock_xbmc, mock_cache):
        """Test play_episode when project is not found."""
        ui, logger_mock, angel_interface_mock = ui_interface
        mock_add_item, mock_end_dir, mock_list_item = mock_xbmc

        with (
            patch.object(ui, "_get_project", return_value=None),
            patch.object(ui, "show_error") as mock_show_error,
        ):
            ui.play_episode("guid", "project-slug")

            mock_show_error.assert_called_once_with("Project not found: project-slug")

    def test_play_episode_episode_not_found_in_project(self, ui_interface, mock_xbmc, mock_cache):
        """Test play_episode when episode GUID not found in project."""
        ui, logger_mock, angel_interface_mock = ui_interface
        mock_add_item, mock_end_dir, mock_list_item = mock_xbmc

        project_data = copy.deepcopy(MOCK_PROJECT_DATA["single_season_project"])

        with (
            patch.object(ui, "_get_project", return_value=project_data),
            patch.object(ui, "show_error") as mock_show_error,
        ):
            ui.play_episode("nonexistent-guid", project_data["slug"])

            mock_show_error.assert_called_once_with("Episode not found: nonexistent-guid")

    def test_play_episode_no_stream(self, ui_interface, mock_xbmc, mock_cache):
        """Test play_episode when episode has no stream."""
        ui, logger_mock, angel_interface_mock = ui_interface
        mock_add_item, mock_end_dir, mock_list_item = mock_xbmc

        # Setup project with episode that has no source
        project_data = copy.deepcopy(MOCK_PROJECT_DATA["single_season_project"])
        project_data["seasons"][0]["episodes"][0]["source"] = None

        with (
            patch.object(ui, "_get_project", return_value=project_data),
            patch.object(ui, "show_error") as mock_show_error,
        ):
            episode_guid = project_data["seasons"][0]["episodes"][0]["guid"]
            ui.play_episode(episode_guid, project_data["slug"])

            mock_show_error.assert_called_once_with("No playable stream URL found for this episode")

    def test_play_episode_no_url_in_source(self, ui_interface, mock_xbmc, mock_cache):
        """Test play_episode when source exists but url is missing."""
        ui, logger_mock, angel_interface_mock = ui_interface
        mock_add_item, mock_end_dir, mock_list_item = mock_xbmc

        # Setup project with episode that has source but no URL
        project_data = copy.deepcopy(MOCK_PROJECT_DATA["single_season_project"])
        project_data["seasons"][0]["episodes"][0]["source"] = {"duration": 3600}

        with (
            patch.object(ui, "_get_project", return_value=project_data),
            patch.object(ui, "show_error") as mock_show_error,
        ):
            episode_guid = project_data["seasons"][0]["episodes"][0]["guid"]
            ui.play_episode(episode_guid, project_data["slug"])

            # Assertions: Error shown
            mock_show_error.assert_called_once_with("No playable stream URL found for this episode")

    def test_play_episode_exception_handling(self, ui_interface, mock_xbmc, mock_cache):
        """Test play_episode handles exceptions gracefully."""
        ui, logger_mock, angel_interface_mock = ui_interface
        mock_add_item, mock_end_dir, mock_list_item = mock_xbmc

        with (
            patch.object(ui, "_get_project", side_effect=Exception(TEST_EXCEPTION_MESSAGE)),
            patch.object(ui, "show_error") as mock_show_error,
        ):
            ui.play_episode("guid", "slug")

            # Verify error handling
            mock_show_error.assert_called_once_with(f"Failed to play episode: {TEST_EXCEPTION_MESSAGE}")


class TestVideoPlayback:
    def test_play_video_with_stream(self, ui_interface, mock_xbmc, mock_cache):
        """Test play_video with stream URL."""
        ui, logger_mock, angel_interface_mock = ui_interface
        mock_add_item, mock_end_dir, mock_list_item = mock_xbmc

        stream_url = "http://example.com/stream"

        with patch("xbmcplugin.setResolvedUrl") as mock_set_resolved_url:
            ui.play_video(stream_url=stream_url)

            # Assertions: setResolvedUrl called
            mock_set_resolved_url.assert_called_once()

    def test_play_video_with_data(self, ui_interface, mock_xbmc, mock_cache):
        """Test play_video with episode data."""
        ui, logger_mock, angel_interface_mock = ui_interface
        mock_add_item, mock_end_dir, mock_list_item = mock_xbmc

        episode_data = MOCK_EPISODE_DATA

        with patch("xbmcplugin.setResolvedUrl") as mock_set_resolved_url:
            ui.play_video(episode_data=episode_data)

            # Assertions: setResolvedUrl called
            mock_set_resolved_url.assert_called_once()

    def test_play_video_both_params(self, ui_interface, mock_xbmc, mock_cache):
        """Test play_video with both stream and data (prioritizes stream)."""
        ui, logger_mock, angel_interface_mock = ui_interface
        mock_add_item, mock_end_dir, mock_list_item = mock_xbmc

        stream_url = "http://example.com/stream"
        episode_data = MOCK_EPISODE_DATA

        with pytest.raises(ValueError, match="Provide only stream_url or episode_data, not both"):
            ui.play_video(stream_url=stream_url, episode_data=episode_data)

    def test_play_video_no_params(self, ui_interface, mock_xbmc, mock_cache):
        """Test play_video with no params."""
        ui, logger_mock, angel_interface_mock = ui_interface
        mock_add_item, mock_end_dir, mock_list_item = mock_xbmc

        with pytest.raises(ValueError, match="Must provide either stream_url or episode_data to play video"):
            ui.play_video()

    def test_play_video_exception(self, ui_interface, mock_xbmc, mock_cache):
        """Test play_video handles exceptions."""
        ui, logger_mock, angel_interface_mock = ui_interface
        mock_add_item, mock_end_dir, mock_list_item = mock_xbmc

        stream_url = "http://example.com/stream"

        with (
            patch("xbmcplugin.setResolvedUrl", side_effect=Exception(TEST_EXCEPTION_MESSAGE)),
            patch.object(ui, "show_error") as mock_show_error,
        ):
            ui.play_video(stream_url=stream_url)

            # Assertions: Error shown
            mock_show_error.assert_called_once_with(f"Error playing video: {TEST_EXCEPTION_MESSAGE}")

    def test_play_video_use_isa_properties(self, ui_interface, mock_cache):
        """When use_isa is enabled, playback should set ISA properties on the ListItem."""
        ui, _, _ = ui_interface

        list_item = MagicMock()
        info_tag = MagicMock()
        list_item.getVideoInfoTag.return_value = info_tag

        addon = MagicMock()
        addon.getSettingBool.return_value = True

        with (
            patch("xbmcaddon.Addon", return_value=addon),
            patch.object(ui, "_ensure_isa_available", return_value=True),
            patch("xbmcgui.ListItem", return_value=list_item),
            patch("xbmcplugin.setResolvedUrl"),
            patch("xbmc.Player"),
        ):
            ui.play_video(episode_data=MOCK_EPISODE_DATA)

        list_item.setProperty.assert_any_call("inputstream", "inputstream.adaptive")
        list_item.setProperty.assert_any_call("inputstream.adaptive.manifest_type", "hls")
        list_item.setProperty.assert_any_call("inputstream.adaptive.stream_selection_type", "adaptive")
        list_item.setMimeType.assert_called_once_with("application/vnd.apple.mpegurl")
        list_item.setContentLookup.assert_called_once_with(False)

    def test_play_video_quality_exact_match_no_isa(self, ui_interface, monkeypatch):
        ui, _, _ = ui_interface

        manifest_url = "http://example.com/master.m3u8"
        addon = MagicMock()
        addon.getSettingBool.return_value = False
        addon.getSettingString.return_value = "1080p"

        list_item = MagicMock()
        info_tag = MagicMock()
        list_item.getVideoInfoTag.return_value = info_tag

        with (
            patch("xbmcaddon.Addon", return_value=addon),
            patch("xbmcgui.ListItem", return_value=list_item),
            patch("xbmcplugin.setResolvedUrl"),
        ):
            ui.play_video(episode_data={"episode": {"source": {"url": manifest_url}}, "project": {}})

        list_item.setPath.assert_called_once_with(manifest_url)

    def test_get_quality_pref_fallback_to_get_setting(self, ui_interface):
        """Test _get_quality_pref fallback when getSettingString is not callable."""
        ui, _, _ = ui_interface

        addon = MagicMock()
        # Make getSettingString attribute exist but not be callable
        addon.getSettingString = None
        addon.getSetting.return_value = "720p"

        with patch("xbmcaddon.Addon", return_value=addon):
            result = ui._get_quality_pref()

        assert result == {"mode": "fixed", "target_height": 720}
        addon.getSetting.assert_called_once_with("video_quality")

    def test_get_quality_pref_exception_defaults_to_auto(self, ui_interface):
        """Test _get_quality_pref returns auto when an exception occurs."""
        ui, _, _ = ui_interface

        with patch("xbmcaddon.Addon", side_effect=Exception("Addon initialization failed")):
            result = ui._get_quality_pref()

        assert result == {"mode": "auto", "target_height": None}

    def test_play_video_no_manifest_logs_warning(self, ui_interface):
        ui, logger_mock, _ = ui_interface

        addon = MagicMock()
        addon.getSettingBool.return_value = False

        list_item = MagicMock()
        info_tag = MagicMock()
        list_item.getVideoInfoTag.return_value = info_tag

        with (
            patch("xbmcaddon.Addon", return_value=addon),
            patch("xbmcgui.ListItem", return_value=list_item),
            patch("xbmcplugin.setResolvedUrl"),
        ):
            ui.play_video(episode_data={"episode": {"source": {}}, "project": {}})

        logger_mock.warning.assert_any_call("No manifest URL available; skipping quality selection")

    def test_play_video_sets_isa_chooser_resolution(self, ui_interface):
        ui, _, _ = ui_interface

        addon = MagicMock()
        addon.getSettingBool.return_value = True
        addon.getSettingString.return_value = "720p"

        list_item = MagicMock()
        info_tag = MagicMock()
        list_item.getVideoInfoTag.return_value = info_tag

        manifest_url = "http://example.com/master.m3u8"

        with (
            patch("xbmcaddon.Addon", return_value=addon),
            patch.object(ui, "_ensure_isa_available", return_value=True),
            patch("xbmcgui.ListItem", return_value=list_item),
            patch("xbmcplugin.setResolvedUrl"),
        ):
            ui.play_video(episode_data={"episode": {"source": {"url": manifest_url}}, "project": {}})

        list_item.setProperty.assert_any_call("inputstream.adaptive.chooser_resolution_max", "720p")
        list_item.setProperty.assert_any_call("inputstream.adaptive.chooser_resolution_secure_max", "720p")
        list_item.setProperty.assert_any_call("inputstream.adaptive.stream_selection_type", "fixed-res")

    def test_play_video_sets_isa_stream_selection_manual(self, ui_interface):
        ui, _, _ = ui_interface

        addon = MagicMock()
        addon.getSettingBool.return_value = True
        addon.getSettingString.return_value = "manual"

        list_item = MagicMock()
        info_tag = MagicMock()
        list_item.getVideoInfoTag.return_value = info_tag

        manifest_url = "http://example.com/master.m3u8"

        with (
            patch("xbmcaddon.Addon", return_value=addon),
            patch.object(ui, "_ensure_isa_available", return_value=True),
            patch("xbmcgui.ListItem", return_value=list_item),
            patch("xbmcplugin.setResolvedUrl"),
        ):
            ui.play_video(episode_data={"episode": {"source": {"url": manifest_url}}, "project": {}})

        list_item.setProperty.assert_any_call("inputstream.adaptive.stream_selection_type", "ask-quality")
        assert not any(
            call_args.args[0] == "inputstream.adaptive.chooser_resolution_max"
            for call_args in list_item.setProperty.call_args_list
        )

    def test_play_video_isa_unavailable_logs_fallback(self, ui_interface):
        ui, logger_mock, _ = ui_interface

        addon = MagicMock()
        addon.getSettingBool.return_value = True
        addon.getSettingString.return_value = "1080p"

        list_item = MagicMock()
        info_tag = MagicMock()
        list_item.getVideoInfoTag.return_value = info_tag

        manifest_url = "http://example.com/master.m3u8"

        with (
            patch("xbmcaddon.Addon", return_value=addon),
            patch.object(ui, "_ensure_isa_available", return_value=False),
            patch("kodi_ui_interface.xbmc.getCondVisibility", return_value=False),
            patch("xbmcgui.ListItem", return_value=list_item),
            patch("xbmcplugin.setResolvedUrl"),
        ):
            ui.play_video(episode_data={"episode": {"source": {"url": manifest_url}}, "project": {}})

        logger_mock.info.assert_any_call("ISA requested but unavailable; falling back to native playback")

    def test_play_video_isa_helper_missing_but_addon_present(self, ui_interface):
        ui, _, _ = ui_interface

        addon = MagicMock()
        addon.getSettingBool.return_value = True
        addon.getSettingString.return_value = "1080p"

        list_item = MagicMock()
        info_tag = MagicMock()
        list_item.getVideoInfoTag.return_value = info_tag

        manifest_url = "http://example.com/master.m3u8"

        with (
            patch("xbmcaddon.Addon", return_value=addon),
            patch.object(ui, "_ensure_isa_available", return_value=False),
            patch("kodi_ui_interface.xbmc.getCondVisibility", return_value=True),
            patch("xbmcgui.ListItem", return_value=list_item),
            patch("xbmcplugin.setResolvedUrl"),
        ):
            ui.play_video(episode_data={"episode": {"source": {"url": manifest_url}}, "project": {}})

        list_item.setProperty.assert_any_call("inputstream", "inputstream.adaptive")
