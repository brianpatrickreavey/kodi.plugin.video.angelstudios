"""
Unit tests for menus from Kodi UI Interface class.
"""

import pytest
import unittest
from unittest.mock import MagicMock, patch

import copy

from datetime import timedelta

# from kodi_ui_interface import KodiUIInterface

from .unittest_data import (
    MOCK_PROJECTS_DATA,
    MOCK_PROJECT_DATA,
    # MOCK_SEASON_DATA,
    MOCK_EPISODE_DATA,
)

parameterized_project_types = pytest.mark.parametrize(
    "content_type,expected_project_type",
    [("movies", "movie"), ("series", "series"), ("specials", "special")],
)

episodes_menu_cases = [
    (project_key, season["id"])
    for project_key, project in MOCK_PROJECT_DATA.items()
    for season in project["seasons"]
]


class TestMainMenu:
    def test_main_menu_new(self, ui_interface, mock_xbmc):
        """Test that main_menu adds directory items via xbmcplugin."""
        ui, logger_mock, angel_interface_mock = ui_interface
        mock_add_item, mock_end_dir, mock_list_item = mock_xbmc

        ui.main_menu()

        # Assert addDirectoryItem was called for each menu item
        assert mock_add_item.call_count == len(ui.menu_items)

        # Verify each call matches the expected menu item
        for i, item in enumerate(ui.menu_items):
            expected_url = ui.create_plugin_url(
                base_url=ui.kodi_url,
                action=item["action"],
                content_type=item["content_type"],
            )

            call_args = mock_add_item.call_args_list[i]

            args = call_args[0]  # Positional args tuple
            kwargs = call_args[1]  # Keyword args dict

            assert args[0] == ui.handle  # handle
            assert args[1] == expected_url  # url
            assert args[2] is mock_list_item.return_value  # listitem
            assert args[3] == True  # isFolder

            # Check that ListItem was created with the correct label
            list_item_call = mock_list_item.call_args_list[i]
            assert list_item_call[1]["label"] == item["label"]

        mock_end_dir.assert_called_once_with(1)


def projects_menu_logic_helper(
    ui_interface, mock_xbmc, mock_cache, cache_hit, content_type, expected_project_type
):
    """Shared logic for projects_menu cache miss/hit."""
    ui, logger_mock, angel_interface_mock = ui_interface
    mock_add_item, mock_end_dir, mock_list_item = mock_xbmc

    # Set up mock data
    projects_data = MOCK_PROJECTS_DATA[content_type]

    # Set up the mock cache behavior
    ui.cache.get.return_value = projects_data if cache_hit else None
    angel_interface_mock.get_projects.return_value = projects_data

    # Call the method
    ui.projects_menu(content_type=content_type)

    # Assertions
    ui.cache.get.assert_called_once()
    if cache_hit:
        angel_interface_mock.get_projects.assert_not_called()
        ui.cache.set.assert_not_called()
    else:
        angel_interface_mock.get_projects.assert_called_once_with(
            project_type=expected_project_type
        )
        cache_key = f"projects_{content_type}"
        ui.cache.set.assert_called_once_with(
            cache_key, projects_data, expiration=timedelta(hours=4)
        )

    # Directory item assertions
    assert mock_add_item.call_count == len(projects_data)
    for i, project in enumerate(projects_data):
        call_args = mock_add_item.call_args_list[i]
        args = call_args[0]  # Positional args
        assert args[0] == 1  # handle
        assert project["slug"] in args[1]  # url
        assert args[2] is mock_list_item.return_value  # listitem
        assert args[3] == True  # isFolder

        list_item_call = mock_list_item.call_args_list[i]
        assert list_item_call[1]["label"] == project["name"]

    mock_end_dir.assert_called_once_with(1)


class TestProjectsMenu:
    @pytest.mark.parametrize("cache_hit", [False, True])
    @parameterized_project_types
    def test_projects_menu(
        self,
        ui_interface,
        mock_xbmc,
        mock_cache,
        cache_hit,
        content_type,
        expected_project_type,
    ):

        projects_menu_logic_helper(
            ui_interface,
            mock_xbmc,
            mock_cache,
            cache_hit,
            content_type,
            expected_project_type,
        )

    @parameterized_project_types
    def test_projects_menu_no_projects(
        self, ui_interface, mock_xbmc, mock_cache, content_type, expected_project_type
    ):
        """Test projects_menu shows error when no projects are found."""
        ui, logger_mock, angel_interface_mock = ui_interface
        mock_add_item, mock_end_dir, mock_list_item = mock_xbmc

        ui.cache.get.return_value = None
        angel_interface_mock.get_projects.return_value = []  # No projects

        with patch.object(ui, "show_error") as mock_show_error:
            ui.projects_menu(content_type=content_type)

            # Ensure cache was checked
            ui.cache.get.assert_called_once()

            # Ensure get_projects was called
            angel_interface_mock.get_projects.assert_called_once_with(
                project_type=expected_project_type
            )

            # Ensure show_error was called with the correct message
            mock_show_error.assert_called_once_with(
                f"No projects found for content type: {content_type}"
            )

            # Ensure no directory items were added
            mock_add_item.assert_not_called()
            mock_end_dir.assert_not_called()

    @parameterized_project_types
    def test_projects_menu_exception(
        self, ui_interface, mock_xbmc, mock_cache, content_type, expected_project_type
    ):
        """Test projects_menu handles exceptions during project fetching."""
        ui, logger_mock, angel_interface_mock = ui_interface
        mock_add_item, mock_end_dir, mock_list_item = mock_xbmc
        angel_interface_mock.get_projects.side_effect = Exception(
            f"Test exception for {content_type}"
        )

        # Set up exception on get_projects
        angel_interface_mock.get_projects.side_effect = Exception(
            f"Test exception for {content_type}"
        )
        ui.cache.get.return_value = None  # Cache miss

        with patch.object(ui, "show_error") as mock_show_error:
            # Expect the exception to be raised
            with pytest.raises(Exception, match=f"Test exception for {content_type}"):
                ui.projects_menu(content_type=content_type)

            # Ensure cache was checked
            ui.cache.get.assert_called_once()

            # Ensure get_projects was called
            angel_interface_mock.get_projects.assert_called_once_with(
                project_type=expected_project_type
            )

            # Ensure error was logged and shown
            mock_show_error.assert_called_once_with(
                f"Failed to load {expected_project_type}: Test exception for {content_type}"
            )


def seasons_menu_logic_helper(ui_interface, mock_xbmc, mock_cache, cache_hit, project_data):
    # Shared logic for cache miss/hit
    ui, logger_mock, angel_interface_mock = ui_interface
    mock_add_item, mock_end_dir, mock_list_item = mock_xbmc

    # Set up mocks
    ui.cache.get.return_value = project_data if cache_hit else None
    angel_interface_mock.get_project.return_value = project_data if not cache_hit else None
    mock_list_item.return_value = MagicMock()


    with (
        patch.object(ui, "_process_attributes_to_infotags") as mock_process_attrs,
        patch.object(ui, "episodes_menu") as mock_episodes_menu
    ):

        # Call method
        result = ui.seasons_menu(content_type=project_data["projectType"], project_slug=project_data["slug"])
        assert result is True

        if cache_hit:
            angel_interface_mock.get_project.assert_not_called()
            ui.cache.set.assert_not_called()
        else:
            angel_interface_mock.get_project.assert_any_call(
                project_data["slug"]
            )
            cache_key = f"project_{project_data['slug']}"
            ui.cache.set.assert_any_call(
                cache_key, project_data, expiration=timedelta(hours=4)
            )

        # Ensure cache was checked
        ui.cache.get.assert_any_call(
            f"project_{project_data['slug']}"
        )

        seasons_data = project_data["seasons"]

        # If we have multiple seasons, items should be added
        if len(seasons_data) > 1:
            assert mock_add_item.call_count == len(seasons_data)
            for i, season in enumerate(seasons_data):
                call_args = mock_add_item.call_args_list[i]
                kwargs = call_args[0]  # Positional args
            assert kwargs[0] == 1  # handle
            assert "episodes_menu" in kwargs[1]  # url contains action
            assert str(season["id"]) in kwargs[1]  # url contains season_id
            assert kwargs[2] is mock_list_item.return_value  # listitem
            assert kwargs[3] == True  # isFolder

            # Check ListItem creation
            list_item_call = mock_list_item.call_args_list[i]
            assert list_item_call[1]["label"] == season["name"]

            # Check _process_attributes_to_infotags was called with season data
            mock_process_attrs.assert_any_call(mock_list_item.return_value, season)
            mock_end_dir.assert_called_once_with(1)
        else:
            # Single season: episodes_menu should be called, no directory items
            mock_episodes_menu.assert_called_once_with(
                project_data["projectType"],
                project_data["slug"],
                season_id=project_data["seasons"][0]["id"],
            )
            mock_add_item.assert_not_called()
            mock_end_dir.assert_not_called()
            mock_process_attrs.assert_not_called()
            logger_mock.info.assert_called_with(
                f"Single season found: {project_data['seasons'][0]['name']}"
            )

class TestSeasonsMenu:
    @pytest.mark.parametrize("cache_hit", [False, True])
    @pytest.mark.parametrize("project_data", [
        MOCK_PROJECT_DATA["single_season_project"],
        MOCK_PROJECT_DATA["multi_season_project"],
    ])
    def test_seasons_menu(self, ui_interface, mock_xbmc, mock_cache, cache_hit, project_data):
        seasons_menu_logic_helper(ui_interface, mock_xbmc, mock_cache, cache_hit, project_data)


    @parameterized_project_types
    def test_seasons_menu_project_not_found(
        self, ui_interface, mock_xbmc, mock_cache, content_type, expected_project_type
    ):
        """Test seasons_menu shows error when project is not found."""
        ui, logger_mock, angel_interface_mock = ui_interface
        mock_add_item, mock_end_dir, mock_list_item = mock_xbmc

        # Set up mocks for project not found
        ui.cache.get.return_value = None  # Cache miss
        angel_interface_mock.get_project.return_value = None  # Project not found

        with (
            patch.object(ui, "show_error") as mock_show_error,
            patch("xbmcplugin.setContent") as mock_set_content,
        ):

            result = ui.seasons_menu(
                content_type=expected_project_type, project_slug="nonexistent-project"
            )
            assert result is None

            # Ensure cache was checked
            ui.cache.get.assert_any_call(
                f"project_nonexistent-project"
            )

            # Ensure get_project was called
            angel_interface_mock.get_project.assert_called_once_with(
                "nonexistent-project"
            )

            # Ensure show_error was called
            mock_show_error.assert_called_once_with(
                "Project not found: nonexistent-project"
            )

            # Ensure no directory items or content setting occurred
            mock_set_content.assert_not_called()
            mock_add_item.assert_not_called()
            mock_end_dir.assert_not_called()


    @parameterized_project_types
    def test_seasons_menu_exception(
        self, ui_interface, mock_xbmc, mock_cache, content_type, expected_project_type,
    ):
        """Test seasons_menu handles exceptions during project fetching."""
        ui, logger_mock, angel_interface_mock = ui_interface
        mock_add_item, mock_end_dir, mock_list_item = mock_xbmc

        # Set up exception
        angel_interface_mock.get_project.side_effect = Exception("Test exception")

        with (
            patch.object(ui, "show_error") as mock_show_error,
            patch.object(ui.cache, "get", return_value=None) as mock_cache_get,
        ):

            result = ui.seasons_menu(
                content_type=expected_project_type, project_slug="test-project"
            )

            # Ensure cache was checked
            mock_cache_get.assert_called_once()

            # Ensure get_project was called
            angel_interface_mock.get_project.assert_called_once_with("test-project")

            # Ensure error was logged and shown
            mock_show_error.assert_called_once_with(
                "Error fetching project test-project: Test exception"
            )

            # Ensure the method returns False on exception
            assert result is False




def episodes_menu_logic_helper(ui_interface, mock_xbmc, mock_cache, cache_hit, project_data, season_id):
    """Shared logic for episodes_menu cache miss/hit."""
    ui, logger_mock, angel_interface_mock = ui_interface
    mock_add_item, mock_end_dir, mock_list_item = mock_xbmc

    # Set up mocks
    ui.cache.get.return_value = project_data if cache_hit else None
    angel_interface_mock.get_project.return_value = project_data if not cache_hit else None

    # Find the season for assertions
    season = next((s for s in project_data["seasons"] if s["id"] == season_id), None)
    episodes_data = season["episodes"] if season else []

    with (
        patch.object(ui, "_create_list_item_from_episode") as mock_create_item,
        patch("xbmcplugin.setContent") as mock_set_content,
        patch("xbmcplugin.addSortMethod") as mock_add_sort,
        patch("xbmcplugin.SORT_METHOD_EPISODE") as mock_episode_sort,
        patch("xbmcplugin.SORT_METHOD_VIDEO_SORT_TITLE") as mock_title_sort,
        patch("xbmcplugin.SORT_METHOD_LABEL") as mock_label_sort,
    ):
        # Call method
        ui.episodes_menu(content_type="series", project_slug=project_data["slug"], season_id=season_id)

        # Conditional assertions for cache behavior
        ui.cache.get.assert_called_once_with(f"project_{project_data['slug']}")
        if cache_hit:
            angel_interface_mock.get_project.assert_not_called()
            ui.cache.set.assert_not_called()
        else:
            angel_interface_mock.get_project.assert_called_once_with(project_data["slug"])
            ui.cache.set.assert_called_once_with(f"project_{project_data['slug']}", project_data, expiration=timedelta(hours=4))

        # Content and sorting assertions
        mock_set_content.assert_called_once_with(1, "tvshows")
        if episodes_data and episodes_data[0].get("seasonNumber", 0) > 0:
            mock_add_sort.assert_any_call(1, mock_episode_sort)
        else:
            mock_add_sort.assert_any_call(1, mock_title_sort)
        mock_add_sort.assert_called_with(1, mock_label_sort)

        # Episode item assertions
        assert mock_add_item.call_count == len(episodes_data)
        for i, episode in enumerate(episodes_data):
            call_args = mock_add_item.call_args_list[i]
            args = call_args[0]
            assert args[0] == 1  # handle
            assert episode["guid"] in args[1]  # url
            if episode.get("source"):
                assert "play_episode" in args[1]
            else:
                assert "info" in args[1]
            assert args[2] is mock_create_item.return_value  # listitem
            assert args[3] == False  # isFolder

            # Check _create_list_item_from_episode calls
            mock_create_item.assert_any_call(
                episode,
                project=None,
                content_type="series",
                stream_url=None,
                is_playback=False,
            )

        mock_end_dir.assert_called_once_with(1)


class TestEpisodesMenu:
    @pytest.mark.parametrize("cache_hit", [False, True])
    @pytest.mark.parametrize("project_key,season_id", episodes_menu_cases)
    def test_episodes_menu(self, ui_interface, mock_xbmc, mock_cache, cache_hit, project_key, season_id):
        """Test episodes_menu with cache hit/miss for valid project/season pairs."""
        project_data = copy.deepcopy(MOCK_PROJECT_DATA[project_key])

        episodes_menu_logic_helper(ui_interface, mock_xbmc, mock_cache, cache_hit, project_data, season_id)

    def test_episodes_menu_project_not_found(self, ui_interface, mock_xbmc, mock_cache):
        """Test episodes_menu shows error when project is not found."""
        ui, logger_mock, angel_interface_mock = ui_interface
        mock_add_item, mock_end_dir, mock_list_item = mock_xbmc

        ui.cache.get.return_value = None
        angel_interface_mock.get_project.return_value = None

        with patch.object(ui, "show_error") as mock_show_error:
            ui.episodes_menu(content_type="series", project_slug="nonexistent-project", season_id=1)

            ui.cache.get.assert_called_once_with("project_nonexistent-project")
            angel_interface_mock.get_project.assert_called_once_with("nonexistent-project")
            mock_show_error.assert_called_once_with("Project not found: nonexistent-project")
            mock_add_item.assert_not_called()
            mock_end_dir.assert_not_called()

    def test_episodes_menu_season_not_found(self, ui_interface, mock_xbmc, mock_cache):
        """Test episodes_menu shows error when season is not found."""
        ui, logger_mock, angel_interface_mock = ui_interface
        mock_add_item, mock_end_dir, mock_list_item = mock_xbmc

        project_data = MOCK_PROJECT_DATA["multi_season_project"]
        ui.cache.get.return_value = project_data
        angel_interface_mock.get_project.return_value = project_data

        with patch.object(ui, "show_error") as mock_show_error:
            ui.episodes_menu(content_type="series", project_slug=project_data["slug"], season_id=999)

            ui.cache.get.assert_called_once_with(f"project_{project_data['slug']}")
            angel_interface_mock.get_project.assert_not_called()
            mock_show_error.assert_called_once_with("Season not found: 999")
            mock_add_item.assert_not_called()
            mock_end_dir.assert_not_called()

    def test_episodes_menu_exception(self, ui_interface, mock_xbmc, mock_cache):
        """Test episodes_menu handles exceptions during execution."""
        ui, logger_mock, angel_interface_mock = ui_interface
        mock_add_item, mock_end_dir, mock_list_item = mock_xbmc

        angel_interface_mock.get_project.side_effect = Exception("Test exception")
        ui.cache.get.return_value = None

        with patch.object(ui, "show_error") as mock_show_error:
            result = ui.episodes_menu(content_type="series", project_slug="test-project", season_id=1)

            ui.cache.get.assert_called_once_with("project_test-project")
            angel_interface_mock.get_project.assert_called_once_with("test-project")
            mock_show_error.assert_called_once_with("Error fetching season 1: Test exception")
            assert result is None
