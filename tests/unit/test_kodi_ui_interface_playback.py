import pytest
from unittest.mock import patch, MagicMock
from kodi_ui_interface import KodiUIInterface
from .unittest_data import MOCK_PROJECT_DATA, MOCK_EPISODE_DATA
import copy
from datetime import timedelta


class TestEpisodePlayback:
    @pytest.mark.parametrize("cache_hit", [False, True])
    @pytest.mark.parametrize("project_data", MOCK_PROJECT_DATA.values())
    def test_play_episode(self, ui_interface, mock_xbmc, mock_cache, project_data, cache_hit):
        """Test play_episode with cache hit/miss."""
        ui, logger_mock, angel_interface_mock = ui_interface
        mock_add_item, mock_end_dir, mock_list_item = mock_xbmc

        project_slug = project_data["slug"]
        episode_data = project_data["seasons"][0]["episodes"][0]
        episode_guid = episode_data["guid"]

        # Full data structure as expected by the code
        full_episode_data = {'episode': episode_data, 'project': project_data}

        # Setup mocks based on cache_hit
        if cache_hit:
            ui.cache.get.return_value = full_episode_data
        else:
            ui.cache.get.return_value = None
            angel_interface_mock.get_episode_data.return_value = full_episode_data
            print(f"Mocked episode data for GUID {episode_guid}: {full_episode_data}")
            angel_interface_mock.get_project.return_value = project_data

        with patch.object(ui, "play_video") as mock_play_video:
            ui.play_episode(episode_guid, project_slug)

            # Assertions
            ui.cache.get.assert_called_once_with(f"episode_data_{episode_guid}_{project_slug}")
            if cache_hit:
                angel_interface_mock.get_episode_data.assert_not_called()
                ui.cache.set.assert_not_called()
            else:
                angel_interface_mock.get_episode_data.assert_called_once_with(episode_guid, project_slug)
                ui.cache.set.assert_called_once_with(
                    f"episode_data_{episode_guid}_{project_slug}",
                    full_episode_data,
                    expiration=timedelta(hours=12)
                )
            mock_play_video.assert_called_once_with(episode_data=full_episode_data)

    def test_play_episode_no_stream(self, ui_interface, mock_xbmc, mock_cache):
        """Test play_episode when episode has no stream."""
        ui, logger_mock, angel_interface_mock = ui_interface
        mock_add_item, mock_end_dir, mock_list_item = mock_xbmc

        episode_guid = "test-episode-guid"
        project_slug = "test-project"

        # Setup mocks: Episode data without stream
        episode_data_no_stream = copy.deepcopy(MOCK_EPISODE_DATA)
        episode_data_no_stream['episode']["source"] = None
        ui.cache.get.return_value = episode_data_no_stream

        with patch.object(ui, "show_error") as mock_show_error:
            ui.play_episode(episode_guid, project_slug)

            # Assertions: Error shown
            mock_show_error.assert_called_once_with("No playable stream URL found for this episode")

    def test_play_episode_no_data(self, ui_interface, mock_xbmc, mock_cache):
        """Test play_episode when episode data is not found."""
        ui, logger_mock, angel_interface_mock = ui_interface
        mock_add_item, mock_end_dir, mock_list_item = mock_xbmc

        episode_guid = "test-episode-guid"
        project_slug = "test-project"

        # Setup mocks: No episode data
        ui.cache.get.return_value = None
        angel_interface_mock.get_episode_data.return_value = None

        with patch.object(ui, "show_error") as mock_show_error:
            ui.play_episode(episode_guid, project_slug)

            # Assertions: Error shown
            mock_show_error.assert_called_once_with("Episode not found: test-episode-guid")

    def test_play_episode_exception(self, ui_interface, mock_xbmc, mock_cache):
        """Test play_episode handles exceptions."""
        ui, logger_mock, angel_interface_mock = ui_interface
        mock_add_item, mock_end_dir, mock_list_item = mock_xbmc

        episode_guid = "test-episode-guid"
        project_slug = "test-project"

        # Setup mocks: Exception in get_episode_data
        ui.cache.get.return_value = None
        angel_interface_mock.get_episode_data.side_effect = Exception("Test exception")

        with patch.object(ui, "show_error") as mock_show_error:
            ui.play_episode(episode_guid, project_slug)

            # Assertions: Error shown
            mock_show_error.assert_called_once_with("Failed to play episode: Test exception")

class TestVideoPlayback:
    def test_play_video_with_stream(self, ui_interface, mock_xbmc, mock_cache):
        """Test play_video with stream URL."""
        ui, logger_mock, angel_interface_mock = ui_interface
        mock_add_item, mock_end_dir, mock_list_item = mock_xbmc

        stream_url = "http://example.com/stream"

        with patch('xbmcplugin.setResolvedUrl') as mock_set_resolved_url:
            ui.play_video(stream_url=stream_url)

            # Assertions: setResolvedUrl called
            mock_set_resolved_url.assert_called_once()

    def test_play_video_with_data(self, ui_interface, mock_xbmc, mock_cache):
        """Test play_video with episode data."""
        ui, logger_mock, angel_interface_mock = ui_interface
        mock_add_item, mock_end_dir, mock_list_item = mock_xbmc

        episode_data = MOCK_EPISODE_DATA

        with patch('xbmcplugin.setResolvedUrl') as mock_set_resolved_url:
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
            patch('xbmcplugin.setResolvedUrl', side_effect=Exception("Test exception")),
            patch.object(ui, "show_error") as mock_show_error,
        ):
            ui.play_video(stream_url=stream_url)

            # Assertions: Error shown
            mock_show_error.assert_called_once_with("Error playing video: Test exception")

    def test_play_video_use_isa_properties(self, ui_interface, mock_cache):
        """When use_isa is enabled, playback should set ISA properties on the ListItem."""
        ui, _, _ = ui_interface

        list_item = MagicMock()
        info_tag = MagicMock()
        list_item.getVideoInfoTag.return_value = info_tag

        addon = MagicMock()
        addon.getSettingBool.return_value = True

        with (
            patch('xbmcaddon.Addon', return_value=addon),
            patch.object(ui, '_ensure_isa_available', return_value=True),
            patch('xbmcgui.ListItem', return_value=list_item),
            patch('xbmcplugin.setResolvedUrl'),
            patch('xbmc.Player'),
        ):
            ui.play_video(episode_data=MOCK_EPISODE_DATA)

        list_item.setProperty.assert_any_call('inputstream', 'inputstream.adaptive')
        list_item.setProperty.assert_any_call('inputstream.adaptive.manifest_type', 'hls')
        list_item.setProperty.assert_any_call('inputstream.adaptive.stream_selection_type', 'adaptive')
        list_item.setMimeType.assert_called_once_with('application/vnd.apple.mpegurl')
        list_item.setContentLookup.assert_called_once_with(False)

    def test_play_video_quality_exact_match_no_isa(self, ui_interface, monkeypatch):
        ui, _, _ = ui_interface

        manifest_url = "http://example.com/master.m3u8"
        addon = MagicMock()
        addon.getSettingBool.return_value = False
        addon.getSettingString.return_value = '1080p'

        list_item = MagicMock()
        info_tag = MagicMock()
        list_item.getVideoInfoTag.return_value = info_tag

        with (
            patch('xbmcaddon.Addon', return_value=addon),
            patch('xbmcgui.ListItem', return_value=list_item),
            patch('xbmcplugin.setResolvedUrl'),
        ):
            ui.play_video(episode_data={'episode': {'source': {'url': manifest_url}}, 'project': {}})

        list_item.setPath.assert_called_once_with(manifest_url)

    def test_get_quality_pref_fallback_to_get_setting(self, ui_interface):
        """Test _get_quality_pref fallback when getSettingString is not callable."""
        ui, _, _ = ui_interface

        addon = MagicMock()
        # Make getSettingString attribute exist but not be callable
        addon.getSettingString = None
        addon.getSetting.return_value = '720p'

        with patch('xbmcaddon.Addon', return_value=addon):
            result = ui._get_quality_pref()

        assert result == {'mode': 'fixed', 'target_height': 720}
        addon.getSetting.assert_called_once_with('video_quality')

    def test_get_quality_pref_exception_defaults_to_auto(self, ui_interface):
        """Test _get_quality_pref returns auto when an exception occurs."""
        ui, _, _ = ui_interface

        with patch('xbmcaddon.Addon', side_effect=Exception("Addon initialization failed")):
            result = ui._get_quality_pref()

        assert result == {'mode': 'auto', 'target_height': None}


    def test_play_video_no_manifest_logs_warning(self, ui_interface):
        ui, logger_mock, _ = ui_interface

        addon = MagicMock()
        addon.getSettingBool.return_value = False

        list_item = MagicMock()
        info_tag = MagicMock()
        list_item.getVideoInfoTag.return_value = info_tag

        with (
            patch('xbmcaddon.Addon', return_value=addon),
            patch('xbmcgui.ListItem', return_value=list_item),
            patch('xbmcplugin.setResolvedUrl'),
        ):
            ui.play_video(episode_data={'episode': {'source': {}}, 'project': {}})

        logger_mock.warning.assert_any_call("No manifest URL available; skipping quality selection")

    def test_play_video_sets_isa_chooser_resolution(self, ui_interface):
        ui, _, _ = ui_interface

        addon = MagicMock()
        addon.getSettingBool.return_value = True
        addon.getSettingString.return_value = '720p'

        list_item = MagicMock()
        info_tag = MagicMock()
        list_item.getVideoInfoTag.return_value = info_tag

        manifest_url = "http://example.com/master.m3u8"

        with (
            patch('xbmcaddon.Addon', return_value=addon),
            patch.object(ui, '_ensure_isa_available', return_value=True),
            patch('xbmcgui.ListItem', return_value=list_item),
            patch('xbmcplugin.setResolvedUrl'),
        ):
            ui.play_video(episode_data={'episode': {'source': {'url': manifest_url}}, 'project': {}})

        list_item.setProperty.assert_any_call('inputstream.adaptive.chooser_resolution_max', '720p')
        list_item.setProperty.assert_any_call('inputstream.adaptive.chooser_resolution_secure_max', '720p')
        list_item.setProperty.assert_any_call('inputstream.adaptive.stream_selection_type', 'fixed-res')

    def test_play_video_sets_isa_stream_selection_manual(self, ui_interface):
        ui, _, _ = ui_interface

        addon = MagicMock()
        addon.getSettingBool.return_value = True
        addon.getSettingString.return_value = 'manual'

        list_item = MagicMock()
        info_tag = MagicMock()
        list_item.getVideoInfoTag.return_value = info_tag

        manifest_url = "http://example.com/master.m3u8"

        with (
            patch('xbmcaddon.Addon', return_value=addon),
            patch.object(ui, '_ensure_isa_available', return_value=True),
            patch('xbmcgui.ListItem', return_value=list_item),
            patch('xbmcplugin.setResolvedUrl'),
        ):
            ui.play_video(episode_data={'episode': {'source': {'url': manifest_url}}, 'project': {}})

        list_item.setProperty.assert_any_call('inputstream.adaptive.stream_selection_type', 'ask-quality')
        assert not any(
            call_args.args[0] == 'inputstream.adaptive.chooser_resolution_max'
            for call_args in list_item.setProperty.call_args_list
        )

    def test_play_video_isa_unavailable_logs_fallback(self, ui_interface):
        ui, logger_mock, _ = ui_interface

        addon = MagicMock()
        addon.getSettingBool.return_value = True
        addon.getSettingString.return_value = '1080p'

        list_item = MagicMock()
        info_tag = MagicMock()
        list_item.getVideoInfoTag.return_value = info_tag

        manifest_url = "http://example.com/master.m3u8"

        with (
            patch('xbmcaddon.Addon', return_value=addon),
            patch.object(ui, '_ensure_isa_available', return_value=False),
            patch('kodi_ui_interface.xbmc.getCondVisibility', return_value=False),
            patch('xbmcgui.ListItem', return_value=list_item),
            patch('xbmcplugin.setResolvedUrl'),
        ):
            ui.play_video(episode_data={'episode': {'source': {'url': manifest_url}}, 'project': {}})

        logger_mock.info.assert_any_call("ISA requested but unavailable; falling back to native playback")

    def test_play_video_isa_helper_missing_but_addon_present(self, ui_interface):
        ui, _, _ = ui_interface

        addon = MagicMock()
        addon.getSettingBool.return_value = True
        addon.getSettingString.return_value = '1080p'

        list_item = MagicMock()
        info_tag = MagicMock()
        list_item.getVideoInfoTag.return_value = info_tag

        manifest_url = "http://example.com/master.m3u8"

        with (
            patch('xbmcaddon.Addon', return_value=addon),
            patch.object(ui, '_ensure_isa_available', return_value=False),
            patch('kodi_ui_interface.xbmc.getCondVisibility', return_value=True),
            patch('xbmcgui.ListItem', return_value=list_item),
            patch('xbmcplugin.setResolvedUrl'),
        ):
            ui.play_video(episode_data={'episode': {'source': {'url': manifest_url}}, 'project': {}})

        list_item.setProperty.assert_any_call('inputstream', 'inputstream.adaptive')
