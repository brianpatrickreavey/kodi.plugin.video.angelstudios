"""
Unit tests for menu_utils.py - MenuUtils class.
Tests menu utility functions for Kodi addon.
"""

import pytest
from unittest.mock import MagicMock, patch
from resources.lib.menu_utils import MenuUtils


@pytest.fixture
def mock_parent():
    """Mock parent KodiUIInterface for MenuUtils testing."""
    parent = MagicMock()
    parent.handle = 1
    parent.kodi_url = "plugin://plugin.video.angelstudios/"
    parent.log = MagicMock()
    parent.angel_interface = MagicMock()
    parent.angel_interface.get_cloudinary_url.return_value = "https://example.com/image.jpg"
    parent.addon = MagicMock()
    parent.addon.getSettingBool.return_value = True
    parent._get_quality_pref.return_value = {"mode": "adaptive", "target_height": 1080}
    parent._ensure_isa_available.return_value = True
    return parent


@pytest.fixture
def menu_utils(mock_parent):
    """MenuUtils instance with mocked parent."""
    return MenuUtils(mock_parent)


class TestMenuUtils:
    """Test suite for MenuUtils class."""

    def test_initialization(self, menu_utils, mock_parent):
        """Test MenuUtils initialization."""
        assert menu_utils.parent == mock_parent
        assert menu_utils.kodi_handle == 1
        assert menu_utils.kodi_url == "plugin://plugin.video.angelstudios/"
        assert menu_utils.log == mock_parent.log

    def test_get_angel_project_type(self, menu_utils):
        """Test mapping menu content types to Angel Studios project types."""
        assert menu_utils._get_angel_project_type("movies") == "movie"
        assert menu_utils._get_angel_project_type("series") == "series"
        assert menu_utils._get_angel_project_type("specials") == "special"
        assert menu_utils._get_angel_project_type("unknown") == "videos"

    def test_get_kodi_content_type(self, menu_utils):
        """Test mapping content types to Kodi media types."""
        assert menu_utils._get_kodi_content_type("movies") == "movies"
        assert menu_utils._get_kodi_content_type("series") == "tvshows"
        assert menu_utils._get_kodi_content_type("specials") == "videos"
        assert menu_utils._get_kodi_content_type("unknown") == "video"

    def test_create_plugin_url(self, menu_utils):
        """Test creating plugin URLs with query parameters."""
        url = menu_utils.create_plugin_url(action="test", id="123")
        assert "plugin://plugin.video.angelstudios/" in url
        assert "action=test" in url
        assert "id=123" in url

    @patch("xbmcgui.ListItem")
    def test_build_list_item_for_project(self, mock_listitem, menu_utils, mock_parent):
        """Test building list item for project content."""
        mock_listitem.return_value.getVideoInfoTag.return_value = MagicMock()

        content = {"name": "Test Project", "description": "Test description"}
        list_item = menu_utils._build_list_item_for_content(
            content, "project", content_type="movies"
        )

        assert list_item is not None
        list_item.setIsFolder.assert_called_with(True)
        list_item.getVideoInfoTag().setMediaType.assert_called_with("movies")

    @patch("xbmcgui.ListItem")
    def test_build_list_item_for_episode_available(self, mock_listitem, menu_utils, mock_parent):
        """Test building list item for available episode."""
        mock_listitem.return_value.getVideoInfoTag.return_value = MagicMock()

        content = {
            "name": "Test Episode",
            "source": {"url": "https://example.com/manifest.m3u8", "duration": 1800},
            "watchPosition": {"position": 300}
        }
        list_item = menu_utils._build_list_item_for_content(
            content, "episode", overlay_progress=True, content_type="series"
        )

        assert list_item is not None
        list_item.setProperty.assert_called_with("IsPlayable", "true")
        list_item.setIsFolder.assert_called_with(True)

    @patch("xbmcgui.ListItem")
    def test_build_list_item_for_episode_unavailable(self, mock_listitem, menu_utils, mock_parent):
        """Test building list item for unavailable episode."""
        mock_listitem.return_value.getVideoInfoTag.return_value = MagicMock()

        content = {"name": "Test Episode"}  # No source
        list_item = menu_utils._build_list_item_for_content(
            content, "episode", content_type="series"
        )

        assert list_item is not None
        list_item.setProperty.assert_called_with("IsPlayable", "false")
        mock_listitem.assert_called_with(label="[I] Test Episode (Unavailable)[/I]", offscreen=False)

    @patch("xbmcgui.ListItem")
    def test_process_attributes_to_infotags_basic(self, mock_listitem, menu_utils, mock_parent):
        """Test processing basic attributes to info tags."""
        list_item = MagicMock()
        info_tag = MagicMock()
        list_item.getVideoInfoTag.return_value = info_tag
        list_item.getLabel.return_value = "Test Item"

        info_dict = {
            "name": "Test Name",
            "description": "Test Description",
            "duration": 1800,
            "episodeNumber": 1,
            "seasonNumber": 1,
            "media_type": "episode"
        }

        menu_utils._process_attributes_to_infotags(list_item, info_dict)

        info_tag.setTitle.assert_called_with("Test Name")
        info_tag.setPlot.assert_called_with("Test Description")
        info_tag.setDuration.assert_called_with(1800)
        info_tag.setEpisode.assert_called_with(1)
        info_tag.setSeason.assert_called_with(1)
        info_tag.setMediaType.assert_called_with("episode")

    @patch("xbmcgui.ListItem")
    def test_process_attributes_to_infotags_cast(self, mock_listitem, menu_utils, mock_parent):
        """Test processing cast information."""
        list_item = MagicMock()
        info_tag = MagicMock()
        list_item.getVideoInfoTag.return_value = info_tag
        list_item.getLabel.return_value = "Test Item"

        info_dict = {
            "cast": [
                {"name": "Actor 1"},
                {"name": "Actor 2"},
                {"name": ""},  # Empty name should be skipped
                {"name": "   "},  # Whitespace only should be skipped
            ]
        }

        menu_utils._process_attributes_to_infotags(list_item, info_dict)

        # Should have called setCast with valid actors only
        assert info_tag.setCast.call_count == 1
        call_args = info_tag.setCast.call_args[0][0]
        assert len(call_args) == 2  # Only valid actors

    @patch("xbmcgui.ListItem")
    def test_process_attributes_to_infotags_metadata(self, mock_listitem, menu_utils, mock_parent):
        """Test processing nested metadata."""
        list_item = MagicMock()
        info_tag = MagicMock()
        list_item.getVideoInfoTag.return_value = info_tag
        list_item.getLabel.return_value = "Test Item"

        info_dict = {
            "metadata": {
                "contentRating": "PG-13",
                "genres": ["Action", "Adventure"]
            },
            "season": {
                "seasonNumber": 2
            }
        }

        menu_utils._process_attributes_to_infotags(list_item, info_dict)

        info_tag.setMpaa.assert_called_with("PG-13")
        info_tag.setGenres.assert_called_with(["Action", "Adventure"])
        info_tag.setSeason.assert_called_with(2)

    @patch("xbmcgui.ListItem")
    def test_process_attributes_to_infotags_artwork(self, mock_listitem, menu_utils, mock_parent):
        """Test processing artwork URLs."""
        list_item = MagicMock()
        info_tag = MagicMock()
        list_item.getVideoInfoTag.return_value = info_tag
        list_item.getLabel.return_value = "Test Item"

        info_dict = {
            "discoveryPosterCloudinaryPath": "poster/path",
            "discoveryPosterLandscapeCloudinaryPath": "landscape/path",
            "logoCloudinaryPath": "logo/path",
            "portraitStill1": {"cloudinaryPath": "still1/path"},
            "landscapeStill1": {"cloudinaryPath": "landscape_still/path"}
        }

        menu_utils._process_attributes_to_infotags(list_item, info_dict)

        # Check that setArt was called with expected artwork
        list_item.setArt.assert_called_once()
        art_dict = list_item.setArt.call_args[0][0]

        assert "poster" in art_dict
        assert "landscape" in art_dict
        assert "fanart" in art_dict
        assert "logo" in art_dict
        assert "clearlogo" in art_dict
        assert "icon" in art_dict

        # Verify cloudinary URL calls
        assert mock_parent.angel_interface.get_cloudinary_url.call_count == 5

    @patch("xbmcgui.ListItem")
    @patch("xbmc.VideoStreamDetail")
    def test_create_list_item_from_episode_directory_mode(self, mock_videostream, mock_listitem, menu_utils, mock_parent):
        """Test creating list item for episode in directory mode."""
        mock_listitem.return_value.getVideoInfoTag.return_value = MagicMock()

        episode = {
            "name": "Test Episode",
            "source": {"url": "https://example.com/manifest.m3u8", "duration": 1800},
            "episodeNumber": 1,
            "seasonNumber": 1
        }
        project = {"name": "Test Series"}

        list_item = menu_utils._create_list_item_from_episode(
            episode, project=project, content_type="series", is_playback=False
        )

        assert list_item is not None
        mock_listitem.assert_called_with(label="Test Episode", offscreen=False)
        list_item.setProperty.assert_called_with("IsPlayable", "true")
        list_item.setIsFolder.assert_called_with(True)

    @patch("xbmcgui.ListItem")
    @patch("xbmc.VideoStreamDetail")
    @patch("xbmc.getCondVisibility")
    def test_create_list_item_from_episode_playback_mode(self, mock_cond_visibility, mock_videostream, mock_listitem, menu_utils, mock_parent):
        """Test creating list item for episode in playback mode."""
        mock_listitem.return_value.getVideoInfoTag.return_value = MagicMock()
        mock_cond_visibility.return_value = True  # ISA available

        episode = {
            "name": "Test Episode",
            "source": {"url": "https://example.com/manifest.m3u8", "duration": 1800},
            "episodeNumber": 1,
            "seasonNumber": 1,
            "watch_position": 300
        }
        project = {"name": "Test Series"}

        list_item = menu_utils._create_list_item_from_episode(
            episode, project=project, content_type="series", is_playback=True
        )

        assert list_item is not None
        mock_listitem.assert_called_with(label="Test Episode", offscreen=True)
        # Check that IsPlayable was set to true at some point
        list_item.setProperty.assert_any_call("IsPlayable", "true")
        list_item.setIsFolder.assert_called_with(False)
        list_item.setPath.assert_called_with("https://example.com/manifest.m3u8")

    @patch("xbmcgui.ListItem")
    def test_create_list_item_from_episode_unavailable(self, mock_listitem, menu_utils, mock_parent):
        """Test creating list item for unavailable episode."""
        mock_listitem.return_value.getVideoInfoTag.return_value = MagicMock()

        episode = {"name": "Test Episode"}  # No source

        list_item = menu_utils._create_list_item_from_episode(
            episode, is_playback=False
        )

        assert list_item is not None
        mock_listitem.assert_called_with(label="[I] Test Episode (Unavailable)[/I]", offscreen=False)
        list_item.setProperty.assert_called_with("IsPlayable", "false")

    @patch("xbmcgui.ListItem")
    def test_apply_progress_bar_valid(self, mock_listitem, menu_utils, mock_parent):
        """Test applying progress bar with valid watch position."""
        list_item = MagicMock()
        info_tag = MagicMock()
        list_item.getVideoInfoTag.return_value = info_tag

        menu_utils._apply_progress_bar(list_item, {"position": 900}, 1800)

        info_tag.setResumePoint.assert_called_once()
        resume_point = info_tag.setResumePoint.call_args[0][0]
        assert 0.0 <= resume_point <= 1.0  # Should be clamped between 0 and 1

    @patch("xbmcgui.ListItem")
    def test_apply_progress_bar_invalid_data(self, mock_listitem, menu_utils, mock_parent):
        """Test applying progress bar with invalid/missing data."""
        list_item = MagicMock()
        info_tag = MagicMock()
        list_item.getVideoInfoTag.return_value = info_tag

        # Test with None position
        menu_utils._apply_progress_bar(list_item, {"position": None}, 1800)
        info_tag.setResumePoint.assert_not_called()

        # Reset mock
        info_tag.reset_mock()

        # Test with None duration
        menu_utils._apply_progress_bar(list_item, {"position": 900}, None)
        info_tag.setResumePoint.assert_not_called()

        # Reset mock
        info_tag.reset_mock()

        # Test with zero duration
        menu_utils._apply_progress_bar(list_item, {"position": 900}, 0)
        info_tag.setResumePoint.assert_not_called()

    @patch("xbmcgui.ListItem")
    def test_apply_progress_bar_numeric_position(self, mock_listitem, menu_utils, mock_parent):
        """Test applying progress bar with numeric watch position."""
        list_item = MagicMock()
        info_tag = MagicMock()
        list_item.getVideoInfoTag.return_value = info_tag

        menu_utils._apply_progress_bar(list_item, 600, 1200)  # 50% progress

        info_tag.setResumePoint.assert_called_once_with(0.5)

    @patch("xbmcgui.ListItem")
    def test_apply_progress_bar_clamping(self, mock_listitem, menu_utils, mock_parent):
        """Test progress bar clamping to valid range."""
        list_item = MagicMock()
        info_tag = MagicMock()
        list_item.getVideoInfoTag.return_value = info_tag

        # Test negative position (should clamp to 0)
        menu_utils._apply_progress_bar(list_item, -100, 1000)
        info_tag.setResumePoint.assert_called_with(0.0)

        info_tag.reset_mock()

        # Test position > duration (should clamp to 1.0)
        menu_utils._apply_progress_bar(list_item, 1500, 1000)
        info_tag.setResumePoint.assert_called_with(1.0)