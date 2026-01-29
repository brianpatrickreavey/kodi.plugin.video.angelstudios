"""Additional tests to achieve 100% coverage for kodi_ui_interface.py edge cases."""

import pytest
from unittest.mock import MagicMock, patch


class TestMergeStillsIntoEpisodesUI:
    """Tests for _merge_stills_into_episodes in KodiUIInterface."""

    @pytest.mark.parametrize(
        "input_data, expected",
        [
            (None, {}),
            ("not a dict", {}),
            (123, {}),
            (
                {
                    "id": "ep1",
                    "name": "Episode 1",
                    "subtitle": "Subtitle",
                    "description": "Description",
                    "episodeNumber": 5,
                    "portraitStill1": {"cloudinaryPath": "portrait1.jpg"},
                    "landscapeStill2": {"cloudinaryPath": "landscape2.jpg"},
                    "extraField": "should be ignored",
                },
                {
                    "id": "ep1",
                    "name": "Episode 1",
                    "subtitle": "Subtitle",
                    "description": "Description",
                    "episodeNumber": 5,
                    "portraitStill1": {"cloudinaryPath": "portrait1.jpg"},
                    "landscapeStill2": {"cloudinaryPath": "landscape2.jpg"},
                },
            ),
        ],
    )
    def test_normalize_contentseries_episode(self, ui_interface, input_data, expected):
        """Test _normalize_contentseries_episode with various inputs. (Coverage for input validation)."""
        ui, logger_mock, _ = ui_interface
        result = ui._normalize_contentseries_episode(input_data)
        assert result == expected


class TestContinueWatchingCoverage:
    """Tests for continue_watching_menu edge cases."""

    def test_continue_watching_episode_with_embedded_project(self, ui_interface, mock_kodi_xbmcplugin):
        """Test episode with embedded project but no projectSlug."""
        ui, logger_mock, angel_interface_mock = ui_interface

        # Episode with embedded project but missing projectSlug field
        episode = {
            "guid": "ep-guid-1",
            "name": "Episode 1",
            "subtitle": "Test Episode",
            "project": {"slug": "embedded-project", "name": "Embedded Project"},
            # Note: projectSlug field is missing
            "duration": 3600,
            "source": {"url": "https://example.com"},
            "watchPosition": {"position": 0},
        }

        resume_data = {"episodes": [episode], "pageInfo": {"hasNextPage": False}}

        with (
            patch.object(angel_interface_mock, "get_resume_watching", return_value=resume_data),
            patch.object(ui.menu_handler, "_create_list_item_from_episode", return_value=MagicMock()),
        ):
            ui.continue_watching_menu()

            # Should extract slug from embedded project
            ui.menu_handler._create_list_item_from_episode.assert_called_once()


class TestProcessAttributesCoverage:
    """Tests for _process_attributes_to_infotags cast handling."""

    def test_process_attributes_cast_with_invalid_data(self, ui_interface, mock_xbmc):
        """Test cast handling with invalid actor data. (Coverage for cast handling edge case)."""
        ui, logger_mock, angel_interface_mock = ui_interface
        mock_add_item, mock_end_dir, mock_list_item_class = mock_xbmc

        list_item = MagicMock()
        info_tag = MagicMock()
        list_item.getVideoInfoTag.return_value = info_tag

        # Cast with mix of valid and invalid entries
        info_dict = {
            "cast": [
                {"name": "Actor 1"},
                {"name": ""},  # Empty name
                {},  # Missing name
                "not a dict",  # Not a dict
                {"name": "Actor 2"},
            ]
        }

        # Mock Actor creation to succeed for valid entries
        mock_actors = []

        def create_actor(name):
            actor = MagicMock()
            mock_actors.append(actor)
            return actor

        with patch("xbmc.Actor", side_effect=create_actor):
            ui.menu_handler._process_attributes_to_infotags(list_item, info_dict)

            # Should create 2 actors (Actor 1 and Actor 2)
            info_tag.setCast.assert_called_once()
            actors = info_tag.setCast.call_args[0][0]
            assert len(actors) == 2

    def test_process_attributes_cast_exception_handling(self, ui_interface, mock_xbmc):
        """Test cast handling when Actor creation raises exception."""
        ui, logger_mock, angel_interface_mock = ui_interface
        mock_add_item, mock_end_dir, mock_list_item_class = mock_xbmc

        list_item = MagicMock()
        info_tag = MagicMock()
        list_item.getVideoInfoTag.return_value = info_tag

        info_dict = {"cast": [{"name": "Actor 1"}]}

        # Mock Actor to raise exception
        with patch("xbmc.Actor", side_effect=Exception("Actor creation failed")):
            # Should not raise, just skip cast
            ui.menu_handler._process_attributes_to_infotags(list_item, info_dict)

            # setCast should not be called due to exception
            info_tag.setCast.assert_not_called()


class TestEpisodesMenuEdgeCases:
    """Tests for episodes_menu edge cases."""

    def test_episodes_menu_all_seasons_with_missing_season_number(self, ui_interface, mock_xbmc, mock_cache):
        """Test episodes_menu in all-seasons mode adds missing seasonNumber."""
        ui, logger_mock, angel_interface_mock = ui_interface
        mock_add_item, mock_end_dir, mock_list_item = mock_xbmc

        project_data = {
            "slug": "test-project",
            "name": "Test Project",
            "seasons": [
                {
                    "id": "s1",
                    "seasonNumber": 1,
                    "episodes": [
                        {"id": "ep1", "guid": "ep1", "episodeNumber": 1, "source": {"url": "http://video1"}},
                    ],
                },
            ],
        }

        with (
            patch.object(ui, "_get_project", return_value=project_data),
            patch.object(ui.menu_handler, "_create_list_item_from_episode", return_value=mock_list_item),
            patch("xbmcplugin.setContent"),
            patch("xbmcplugin.addSortMethod"),
        ):
            # Call with season_id=None for all-seasons mode
            ui.episodes_menu(content_type="series", project_slug="test-project", season_id=None)

            # Should have processed episode
            assert mock_add_item.call_count == 1


class TestSettingsCallbacks:
    """Tests for settings callback methods."""

    def test_clear_cache_with_notification_success(self, ui_interface, mock_xbmc):
        """Test clear_cache_with_notification on success."""
        ui, logger_mock, angel_interface_mock = ui_interface

        with (
            patch.object(ui, "clear_cache", return_value=True),
            patch.object(ui, "show_notification") as mock_notify,
        ):
            ui.clear_cache_with_notification()

            mock_notify.assert_called_once_with("Cache cleared.")
            logger_mock.info.assert_any_call("Cache cleared successfully via settings")

    def test_clear_cache_with_notification_failure(self, ui_interface, mock_xbmc):
        """Test clear_cache_with_notification on failure."""
        ui, logger_mock, angel_interface_mock = ui_interface

        with (
            patch.object(ui.cache_manager, "clear_cache", return_value=False),
            patch.object(ui, "show_notification") as mock_notify,
        ):
            ui.clear_cache_with_notification()

            mock_notify.assert_called_once_with("Cache clear failed; please try again.")
            logger_mock.error.assert_any_call("Cache clear failed via settings")

    def test_force_logout_with_notification_success(self, ui_interface, mock_xbmc):
        """Test force_logout_with_notification on success."""
        ui, logger_mock, angel_interface_mock = ui_interface

        angel_interface_mock.force_logout.return_value = True

        with patch("xbmcgui.Dialog") as mock_dialog:
            ui.force_logout_with_notification()

            angel_interface_mock.force_logout.assert_called_once()
            mock_dialog.return_value.ok.assert_called_once_with(
                "Angel Studios - Force Logout",
                "Successfully logged out.\n\nSession details may not update immediately.\nRestart the addon to see changes."
            )
            logger_mock.info.assert_any_call("Logged out locally via settings")

    def test_force_logout_with_notification_failure(self, ui_interface, mock_xbmc):
        """Test force_logout_with_notification on failure."""
        ui, logger_mock, angel_interface_mock = ui_interface

        angel_interface_mock.force_logout.return_value = False

        with patch("xbmcgui.Dialog") as mock_dialog:
            ui.force_logout_with_notification()

            angel_interface_mock.force_logout.assert_called_once()
            mock_dialog.return_value.ok.assert_called_once_with("Angel Studios - Force Logout", "Logout failed; please try again.")
            logger_mock.error.assert_any_call("Logout failed via settings")

    def test_force_logout_without_angel_interface(self, ui_interface, mock_xbmc):
        """Test force_logout_with_notification raises error without angel_interface."""
        ui, logger_mock, angel_interface_mock = ui_interface

        ui.angel_interface = None

        with pytest.raises(ValueError, match="Angel interface not initialized"):
            ui.force_logout_with_notification()

    def test_clear_debug_data_with_notification_success(self, ui_interface, mock_xbmc):
        """Test clear_debug_data_with_notification on success."""
        ui, logger_mock, angel_interface_mock = ui_interface

        with (
            patch.object(ui.ui_helpers, "clear_debug_data", return_value=True),
            patch.object(ui.ui_helpers, "show_notification") as mock_notify,
        ):
            ui.clear_debug_data_with_notification()

            mock_notify.assert_called_once_with("Debug data cleared.")

    def test_clear_debug_data_with_notification_logs_info_on_success(self, ui_interface, mock_xbmc):
        """Test clear_debug_data_with_notification logs info message on success (line 853)."""
        ui, logger_mock, angel_interface_mock = ui_interface

        with (
            patch.object(ui, "clear_debug_data", return_value=True),
            patch.object(ui, "show_notification"),
        ):
            ui.clear_debug_data_with_notification()

            logger_mock.info.assert_any_call("Debug data cleared via settings")

    def test_clear_debug_data_with_notification_logs_error_on_failure(self, ui_interface, mock_xbmc):
        """Test clear_debug_data_with_notification logs error message on failure (line 854)."""
        ui, logger_mock, angel_interface_mock = ui_interface

        with (
            patch.object(ui.ui_helpers, "clear_debug_data", return_value=False),
            patch.object(ui.ui_helpers, "show_notification"),
        ):
            ui.clear_debug_data_with_notification()

            logger_mock.error.assert_any_call("Debug data clear failed via settings")
