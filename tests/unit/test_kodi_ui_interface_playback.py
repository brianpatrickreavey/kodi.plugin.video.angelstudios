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
                    expiration=timedelta(hours=1)
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

        with patch('xbmcplugin.setResolvedUrl', side_effect=Exception("Test exception")), \
             patch.object(ui, "show_error") as mock_show_error:
            ui.play_video(stream_url=stream_url)

            # Assertions: Error shown
            mock_show_error.assert_called_once_with("Error playing video: Test exception")