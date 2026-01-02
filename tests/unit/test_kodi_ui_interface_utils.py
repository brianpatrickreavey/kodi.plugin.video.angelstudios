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
    @pytest.mark.parametrize("is_playback", [True, False])
    @pytest.mark.parametrize("episode_available", [True, False])
    def test_create_list_item_from_episode(self, ui_interface, mock_xbmc, is_playback, episode_available):
        """Test _create_list_item_from_episode creates a ListItem with episode metadata."""
        ui, logger_mock, angel_interface_mock = ui_interface
        mock_add_item, mock_end_dir, mock_list_item = mock_xbmc

        episode = MOCK_EPISODE_DATA['episode']
        project = MOCK_EPISODE_DATA['project']
        stream_url = episode.get('source', {}).get('url', None)

        if not episode_available:
            episode.pop('source', None)

        with patch('xbmcgui.ListItem') as mock_list_item, \
            patch('xbmc.VideoStreamDetail') as mock_video_stream_detail, \
            patch.object(ui, '_process_attributes_to_infotags') as mock_process_attrs:

            mock_list_item.return_value = MagicMock()

            result = ui._create_list_item_from_episode(
                episode=episode,
                project=project,
                content_type='series',
                stream_url=stream_url,
                is_playback=is_playback
            )

            # Ensure ListItem was created
            mock_list_item.assert_called_once()
            list_item_instance = mock_list_item.return_value

            # Conditional assertions based on is_playback
            if is_playback:
                list_item_instance.setPath.assert_called_once_with(stream_url)
                list_item_instance.setIsFolder.assert_called_once_with(False)
                list_item_instance.setProperty.assert_called_once_with('IsPlayable', 'true')

                # Ensure _process_attributes_to_infotags was called
                mock_video_stream_detail.assert_called_once_with()
                video_stream_mock = mock_video_stream_detail.return_value
                video_stream_mock.setCodec.assert_called_once_with('h264')
                video_stream_mock.setWidth.assert_called_once_with(1920)
                video_stream_mock.setHeight.assert_called_once_with(1080)

            else:
                list_item_instance.setIsFolder.assert_called_once_with(True)
                list_item_instance.setProperty.assert_called_once_with('IsPlayable', 'false')

            mock_process_attrs.assert_called_once_with(list_item_instance, episode)

            # Ensure the result is the ListItem
            assert result == list_item_instance

    def test_process_attributes_to_infotags(self, ui_interface, mock_xbmc):
        """Test _process_attributes_to_infotags sets info tags on ListItem."""
        ui, logger_mock, angel_interface_mock = ui_interface
        mock_add_item, mock_end_dir, mock_list_item = mock_xbmc

        episode = MOCK_EPISODE_DATA['episode']
        mock_list_item = MagicMock()
        mock_info_tag = MagicMock()
        mock_list_item.getVideoInfoTag.return_value = mock_info_tag

        # Mock Cloudinary URL calls
        angel_interface_mock.get_cloudinary_url.return_value = 'http://example.com/poster.jpg'

        ui._process_attributes_to_infotags(mock_list_item, episode)

        # Ensure getVideoInfoTag was called
        mock_list_item.getVideoInfoTag.assert_called_once()

        # Check that setTitle is called for 'name'
        mock_info_tag.setTitle.assert_called_with(episode['name'])

        # Art assertions: Cloudinary keys should result in setArt call
        expected_art = {
            'poster': 'http://example.com/poster.jpg',
            'logo': 'http://example.com/poster.jpg',
            'clearlogo': 'http://example.com/poster.jpg',
            'icon': 'http://example.com/poster.jpg',
            'fanart': 'http://example.com/poster.jpg',
            'landscape': 'http://example.com/poster.jpg'
        }
        mock_list_item.setArt.assert_called_once_with(expected_art)
        angel_interface_mock.get_cloudinary_url.assert_called()  # Ensure Cloudinary processing happened

        logger_mock.info.assert_any_call(f"Processing attributes for list item: {mock_list_item.getLabel.return_value}")
        logger_mock.debug.assert_any_call(f"Attribute dict: {episode}")

    def test_show_error(self, ui_interface, mock_xbmc):
        """Test show_error displays an error dialog."""
        ui, logger_mock, angel_interface_mock = ui_interface
        mock_add_item, mock_end_dir, mock_list_item = mock_xbmc

        with patch('xbmcgui.Dialog') as mock_dialog, \
             patch('xbmc.log') as mock_xbmc_log, \
             patch('xbmc.LOGERROR') as mock_log_error:
            mock_dialog_instance = MagicMock()
            mock_dialog.return_value = mock_dialog_instance

            ui.show_error("Test error message")

            mock_dialog_instance.ok.assert_called_once_with("Angel Studios", "Test error message")
            mock_xbmc_log.assert_called_once_with("Error shown to user: Test error message", mock_log_error)

    def test_show_notification(self, ui_interface, mock_xbmc):
        """Test show_notification displays a notification."""
        ui, logger_mock, angel_interface_mock = ui_interface
        mock_add_item, mock_end_dir, mock_list_item = mock_xbmc

        with patch('xbmcgui.Dialog') as mock_dialog:
            mock_dialog_instance = MagicMock()
            mock_dialog.return_value = mock_dialog_instance

            ui.show_notification("Test notification message")

            mock_dialog_instance.notification.assert_called_once_with("Angel Studios", "Test notification message", time=5000)