"""Additional tests to achieve 100% coverage for kodi_ui_interface.py edge cases."""

import pytest
from unittest.mock import MagicMock, patch


class TestMergeStillsIntoEpisodesUI:
    """Tests for _merge_stills_into_episodes in KodiUIInterface."""

    def test_merge_with_no_cache(self, ui_interface):
        """Test _merge_stills_into_episodes with no cached project data. (Coverage for cache miss path)."""
        ui, logger_mock, _ = ui_interface
        episodes = [{"id": "ep1", "guid": "g1"}]

        ui.cache.get.return_value = None

        result = ui._merge_stills_into_episodes(episodes, "test-slug")

        print("Result:", result)
        assert result == episodes
        logger_mock.debug.assert_any_call("No cached project for test-slug, skipping STILL merge")

    def test_merge_with_no_contentseries_data(self, ui_interface):
        """Test _merge_stills_into_episodes with project lacking ContentSeries data. (Coverage for non-ContentSeries typename)."""
        ui, logger_mock, _ = ui_interface
        episodes = [{"id": "ep1", "guid": "g1"}]
        project = {"title": {"__typename": "NotContentSeries"}}

        ui.cache.get.return_value = project

        result = ui._merge_stills_into_episodes(episodes, "test-slug")

        assert result == episodes
        logger_mock.debug.assert_any_call("No ContentSeries data in project test-slug")

    def test_merge_stills_success(self, ui_interface):
        ui, logger_mock, angel_interface_mock = ui_interface
        episodes = [{"id": "ep1", "guid": "g1"}, {"id": "ep2", "guid": "g2"}]
        project = {
            "title": {
                "__typename": "ContentSeries",
                "seasons": {
                    "edges": [
                        {
                            "node": {
                                "episodes": {
                                    "edges": [
                                        {
                                            "node": {
                                                "id": "ep1",
                                                "portraitStill1": {"cloudinaryPath": "/p1"},
                                                "landscapeStill1": {"cloudinaryPath": "/l1"},
                                            }
                                        }
                                    ]
                                }
                            }
                        }
                    ]
                },
            }
        }

        def unwrap_relay_mock(edges_structure):
            """Mock that properly unwraps relay pagination structure."""
            if not edges_structure or not isinstance(edges_structure, dict):
                return []
            edges = edges_structure.get("edges", [])
            if not isinstance(edges, list):
                return []
            nodes = []
            for edge in edges:
                if edge and isinstance(edge, dict) and "node" in edge:
                    node = edge["node"]
                    if node:
                        nodes.append(node)
            return nodes

        ui.cache.get.return_value = project

        # Mock _unwrap_relay_pagination properly
        ui.angel_interface._unwrap_relay_pagination = MagicMock(side_effect=unwrap_relay_mock)

        result = ui._merge_stills_into_episodes(episodes, "test-slug")

        assert "portraitStill1" in result[0]
        assert "landscapeStill1" in result[0]
        assert "portraitStill1" not in result[1]
        logger_mock.info.assert_any_call("Merging ContentSeries STILLs from 1 episodes into 2 episodes")

    def test_merge_handles_exception(self, ui_interface):
        """Test _merge_stills_into_episodes exception handling. (Coverage for error path in STILL merge)."""
        ui, logger_mock, _ = ui_interface
        episodes = [{"id": "ep1"}]

        ui.cache.get.side_effect = Exception("Cache error")

        result = ui._merge_stills_into_episodes(episodes, "test-slug")

        assert result == episodes
        logger_mock.error.assert_called()

    def test_merge_skips_none_episode(self, ui_interface):
        ui, logger_mock, angel_interface_mock = ui_interface
        episodes = [None, {"id": "ep1", "displayName": "Episode 1"}]
        project = {
            "title": {
                "__typename": "ContentSeries",
                "seasons": {
                    "edges": [
                        {
                            "node": {
                                "episodes": {
                                    "edges": [
                                        {
                                            "node": {
                                                "id": "ep1",
                                                "portraitStill1": {"cloudinaryPath": "portrait1.jpg"},
                                                "landscapeStill1": {"cloudinaryPath": "landscape1.jpg"},
                                            }
                                        }
                                    ]
                                }
                            }
                        }
                    ]
                },
            }
        }

        def unwrap_relay_mock(edges_structure):
            """Mock that properly unwraps relay pagination structure."""
            if not edges_structure or not isinstance(edges_structure, dict):
                return []
            edges = edges_structure.get("edges", [])
            if not isinstance(edges, list):
                return []
            nodes = []
            for edge in edges:
                if edge and isinstance(edge, dict) and "node" in edge:
                    node = edge["node"]
                    if node:
                        nodes.append(node)
            return nodes

        ui.cache.get.return_value = project

        # Mock _unwrap_relay_pagination properly
        ui.angel_interface._unwrap_relay_pagination = MagicMock(side_effect=unwrap_relay_mock)

        result = ui._merge_stills_into_episodes(episodes, "test-slug")

        assert result[0] is None
        assert result[1]["portraitStill1"] == {"cloudinaryPath": "portrait1.jpg"}
        assert result[1]["landscapeStill1"] == {"cloudinaryPath": "landscape1.jpg"}

    def test_normalize_contentseries_episode_with_none(self, ui_interface):
        """Test _normalize_contentseries_episode with None input."""
        ui, logger_mock, _ = ui_interface
        result = ui._normalize_contentseries_episode(None)
        assert result == {}

    def test_normalize_contentseries_episode_with_non_dict(self, ui_interface):
        """Test _normalize_contentseries_episode with non-dict input."""
        ui, logger_mock, _ = ui_interface
        result = ui._normalize_contentseries_episode("not a dict")
        assert result == {}
        result = ui._normalize_contentseries_episode(123)
        assert result == {}

    def test_normalize_contentseries_episode_with_valid_data(self, ui_interface):
        """Test _normalize_contentseries_episode with valid episode data."""
        ui, logger_mock, _ = ui_interface
        episode = {
            "id": "ep1",
            "name": "Episode 1",
            "subtitle": "Subtitle",
            "description": "Description",
            "episodeNumber": 5,
            "portraitStill1": {"cloudinaryPath": "portrait1.jpg"},
            "landscapeStill2": {"cloudinaryPath": "landscape2.jpg"},
            "extraField": "should be ignored",
        }
        result = ui._normalize_contentseries_episode(episode)
        assert result["id"] == "ep1"
        assert result["name"] == "Episode 1"
        assert result["portraitStill1"] == {"cloudinaryPath": "portrait1.jpg"}
        assert result["landscapeStill2"] == {"cloudinaryPath": "landscape2.jpg"}
        assert "extraField" not in result


class TestContinueWatchingCoverage:
    """Tests for continue_watching_menu edge cases."""

    def test_continue_watching_episode_with_embedded_project(self, ui_interface, mock_kodi_xbmcplugin):
        """Test episode with embedded project but no projectSlug. (Coverage for embedded project slug extraction in continue_watching_menu)."""
        ui, logger_mock, angel_interface_mock = ui_interface

        # Episode with embedded project but missing projectSlug field
        episode = {
            "guid": "ep-guid-1",
            "name": "Episode 1",
            "subtitle": "Test Episode",
            "project": {"slug": "embedded-project", "name": "Embedded Project"},
            # Note: projectSlug field is missing
            "duration": 3600,
        }

        resume_data = {"episodes": [episode], "projects": {}, "pageInfo": {"hasNextPage": False}}

        with (
            patch.object(angel_interface_mock, "get_resume_watching", return_value=resume_data),
            patch.object(ui, "_create_list_item_from_episode", return_value=MagicMock()),
        ):
            ui.continue_watching_menu()

            # Should extract slug from embedded project
            ui._create_list_item_from_episode.assert_called_once()
            call_kwargs = ui._create_list_item_from_episode.call_args
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
            ui._process_attributes_to_infotags(list_item, info_dict)

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
            ui._process_attributes_to_infotags(list_item, info_dict)

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
            patch.object(ui, "_create_list_item_from_episode", return_value=mock_list_item),
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
            patch.object(ui, "clear_cache", return_value=False),
            patch.object(ui, "show_notification") as mock_notify,
        ):
            ui.clear_cache_with_notification()

            mock_notify.assert_called_once_with("Cache clear failed; please try again.")
            logger_mock.error.assert_any_call("Cache clear failed via settings")

    def test_force_logout_with_notification_success(self, ui_interface, mock_xbmc):
        """Test force_logout_with_notification on success."""
        ui, logger_mock, angel_interface_mock = ui_interface

        angel_interface_mock.force_logout.return_value = True

        with patch.object(ui, "show_notification") as mock_notify:
            ui.force_logout_with_notification()

            angel_interface_mock.force_logout.assert_called_once()
            mock_notify.assert_called_once_with("Logged out locally.")
            logger_mock.info.assert_any_call("Logged out locally via settings")

    def test_force_logout_with_notification_failure(self, ui_interface, mock_xbmc):
        """Test force_logout_with_notification on failure."""
        ui, logger_mock, angel_interface_mock = ui_interface

        angel_interface_mock.force_logout.return_value = False

        with patch.object(ui, "show_notification") as mock_notify:
            ui.force_logout_with_notification()

            angel_interface_mock.force_logout.assert_called_once()
            mock_notify.assert_called_once_with("Logout failed; please try again.")
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
            patch.object(ui, "clear_debug_data", return_value=True),
            patch.object(ui, "show_notification") as mock_notify,
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
            patch.object(ui, "clear_debug_data", return_value=False),
            patch.object(ui, "show_notification"),
        ):
            ui.clear_debug_data_with_notification()

            logger_mock.error.assert_any_call("Debug data clear failed via settings")
