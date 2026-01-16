"""
Unit tests for menus from Kodi UI Interface class.
"""

import os
import tempfile
import copy

import pytest
from datetime import timedelta
from unittest.mock import MagicMock, patch

from kodi_ui_interface import KodiUIInterface

from .unittest_data import (
    MOCK_PROJECTS_DATA,
    MOCK_PROJECT_DATA,
    TEST_EXCEPTION_MESSAGE,
)

parameterized_project_types = pytest.mark.parametrize(
    "content_type,expected_project_type",
    [("movies", "movie"), ("series", "series"), ("specials", "special")],
)

episodes_menu_cases = [
    (project_key, season["id"]) for project_key, project in MOCK_PROJECT_DATA.items() for season in project["seasons"]
] + [
    # All-episodes mode for multi-season projects
    ("multi_season_project", None),
]


class TestMainMenu:
    def test_main_menu_new(self, ui_interface, mock_xbmc):
        """Test that main_menu adds directory items via xbmcplugin."""
        ui, logger_mock, angel_interface_mock = ui_interface
        mock_add_item, mock_end_dir, mock_list_item = mock_xbmc

        # Ensure menu rebuild uses current settings
        ui.addon.getSettingBool.return_value = True

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
            kwargs = call_args[1]  # Keyword args dict  # noqa: F841

            assert args[0] == ui.handle  # handle
            assert args[1] == expected_url  # url
            assert args[2] is mock_list_item.return_value  # listitem
            assert args[3] is True  # isFolder

            # Check that ListItem was created with the correct label
            list_item_call = mock_list_item.call_args_list[i]
            assert list_item_call[1]["label"] == item["label"]

        mock_end_dir.assert_called_once_with(1)

    def test_watchlist_menu_placeholder(self, ui_interface):
        ui, logger_mock, angel_interface_mock = ui_interface

        with patch.object(ui, "show_error") as mock_show_error:
            ui.watchlist_menu()

        mock_show_error.assert_called_once_with("Watchlist is not available yet.")
        logger_mock.info.assert_any_call("Watchlist menu requested, but not yet implemented.")

    def test_top_picks_menu_placeholder(self, ui_interface):
        ui, logger_mock, angel_interface_mock = ui_interface

        with patch.object(ui, "show_error") as mock_show_error:
            ui.top_picks_menu()

        mock_show_error.assert_called_once_with("Top Picks is not available yet.")
        logger_mock.info.assert_any_call("Top picks menu requested, but not yet implemented.")

    def test_main_menu_settings_error_defaults_enabled(self, mock_xbmc):
        """If settings read fails, menu defaults stay enabled."""
        import xbmcaddon

        addon = xbmcaddon.Addon.return_value
        original_side_effect = addon.getSettingBool.side_effect
        addon.getSettingBool.side_effect = Exception("settings failure")

        ui = KodiUIInterface(
            handle=1,
            url="plugin://plugin.video.angelstudios/",
            logger=MagicMock(),
            angel_interface=MagicMock(),
        )

        mock_add_item, mock_end_dir, mock_list_item = mock_xbmc

        ui.main_menu()

        addon.getSettingBool.side_effect = original_side_effect

        # Fallback to defaults shows only enabled defaults plus Settings
        assert len(ui.menu_items) == 4
        mock_add_item.assert_called()
        assert mock_add_item.call_count == len(ui.menu_items)
        mock_end_dir.assert_called_once_with(1)

    def test_main_menu_non_bool_setting_falls_back_to_default(self, mock_xbmc):
        """Non-boolean setting values fall back to defaults."""
        import xbmcaddon

        addon = xbmcaddon.Addon.return_value
        original_side_effect = addon.getSettingBool.side_effect

        def fake_get_setting_bool(key):
            if key == "show_podcasts":
                return "yes"  # force non-bool path
            return original_side_effect(key)

        addon.getSettingBool.side_effect = fake_get_setting_bool

        ui = KodiUIInterface(
            handle=1,
            url="plugin://plugin.video.angelstudios/",
            logger=MagicMock(),
            angel_interface=MagicMock(),
        )

        # Rebuild menu and ensure non-bool falls back to default (podcasts stays hidden)
        ui.main_menu()

        addon.getSettingBool.side_effect = original_side_effect

        labels = [item["label"] for item in ui.menu_items]
        assert "Podcasts" not in labels
        assert labels.count("Movies") == 1
        assert labels.count("Series") == 1
        assert labels.count("Dry Bar Comedy Specials") == 1
        assert labels.count("Settings") == 1

    def test_main_menu_respects_setting_toggle_off(self, mock_xbmc):
        """Menu rebuild should hide items when settings are false."""
        import xbmcaddon

        addon = xbmcaddon.Addon.return_value
        original_side_effect = addon.getSettingBool.side_effect
        addon.getSettingBool.side_effect = lambda key: False if key == "show_series" else True

        ui = KodiUIInterface(
            handle=1,
            url="plugin://plugin.video.angelstudios/",
            logger=MagicMock(),
            angel_interface=MagicMock(),
        )

        # Rebuild menu using current settings
        ui.main_menu()

        addon.getSettingBool.side_effect = original_side_effect

        labels = [item["label"] for item in ui.menu_items]
        assert "Series" not in labels
        assert "Movies" in labels
        assert "Dry Bar Comedy Specials" in labels
        assert "Settings" in labels

    def test_cache_ttl_uses_setting_int(self):
        import xbmcaddon

        addon = xbmcaddon.Addon.return_value
        addon.getSettingInt.return_value = 5

        ui = KodiUIInterface(
            handle=1,
            url="plugin://plugin.video.angelstudios/",
            logger=MagicMock(),
            angel_interface=MagicMock(),
        )

        ttl = ui._cache_ttl()
        assert ttl == timedelta(hours=5)

        addon.getSettingInt.return_value = 12

    @pytest.mark.parametrize("hours", [1, 12, 168])
    def test_cache_ttl_respects_slider_range(self, hours):
        import xbmcaddon

        addon = xbmcaddon.Addon.return_value
        addon.getSettingInt.return_value = hours

        ui = KodiUIInterface(
            handle=1,
            url="plugin://plugin.video.angelstudios/",
            logger=MagicMock(),
            angel_interface=MagicMock(),
        )

        ttl = ui._cache_ttl()
        assert ttl == timedelta(hours=hours)

        addon.getSettingInt.return_value = 12

    def test_cache_ttl_falsy_defaults_to_12(self):
        import xbmcaddon

        addon = xbmcaddon.Addon.return_value
        addon.getSettingInt.return_value = 0

        ui = KodiUIInterface(
            handle=1,
            url="plugin://plugin.video.angelstudios/",
            logger=MagicMock(),
            angel_interface=MagicMock(),
        )

        ttl = ui._cache_ttl()
        assert ttl == timedelta(hours=12)

        addon.getSettingInt.return_value = 12

    def test_cache_ttl_falls_back_on_exception(self):
        import xbmcaddon

        addon = xbmcaddon.Addon.return_value
        addon.getSettingInt.side_effect = Exception("fail int")

        ui = KodiUIInterface(
            handle=1,
            url="plugin://plugin.video.angelstudios/",
            logger=MagicMock(),
            angel_interface=MagicMock(),
        )

        ttl = ui._cache_ttl()
        assert ttl == timedelta(hours=12)

        addon.getSettingInt.side_effect = None
        addon.getSettingInt.return_value = 12

    def test_cache_ttl_getsetting_fallback_exception(self):
        import xbmcaddon

        addon = xbmcaddon.Addon.return_value
        addon.getSettingInt = None  # force non-callable path
        addon.getSetting.side_effect = Exception("boom")

        ui = KodiUIInterface(
            handle=1,
            url="plugin://plugin.video.angelstudios/",
            logger=MagicMock(),
            angel_interface=MagicMock(),
        )

        ttl = ui._cache_ttl()
        assert ttl == timedelta(hours=12)

        addon.getSetting = MagicMock(return_value="12")
        addon.getSettingInt = MagicMock(return_value=12)

    def test_cache_disabled_bypasses_get_set(self, ui_interface):

        ui, logger_mock, angel_interface_mock = ui_interface

        # Fresh addon scoped to this test to avoid leaking disable_cache to other tests
        fresh_addon = MagicMock()
        fresh_addon.getSettingBool.side_effect = lambda key: True if key == "disable_cache" else False
        fresh_addon.getSettingString.return_value = "off"
        fresh_addon.getSettingInt.return_value = 12

        ui.addon = fresh_addon
        ui.cache.get.reset_mock()
        ui.cache.set.reset_mock()
        angel_interface_mock.get_projects.return_value = []

        with (
            patch("xbmcaddon.Addon", return_value=fresh_addon),
            patch.object(ui, "show_error"),
        ):
            ui.projects_menu(content_type="movies")

        ui.cache.get.assert_not_called()
        ui.cache.set.assert_not_called()

    def test_trace_writer_redacts_and_stores(self):
        import xbmcaddon

        addon = xbmcaddon.Addon.return_value
        addon.getSettingString.return_value = "trace"

        ui = KodiUIInterface(
            handle=1,
            url="plugin://plugin.video.angelstudios/",
            logger=MagicMock(),
            angel_interface=MagicMock(),
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            ui.trace_dir = tmpdir
            tracer = ui.get_trace_callback()
            payload = {
                "operation": "op",
                "request": {"headers": {"Authorization": "secret", "X": "ok"}, "body": {"password": "pw"}},
                "response": {"token": "abc", "value": 1},
            }
            tracer(payload)

            files = os.listdir(tmpdir)
            assert len(files) == 1
            with open(os.path.join(tmpdir, files[0]), "r", encoding="utf-8") as fp:
                content = fp.read()
                assert "secret" not in content
                assert "pw" not in content
                assert "abc" not in content
                assert "<redacted>" in content

        addon.getSettingString.return_value = "off"


def projects_menu_logic_helper(ui_interface, mock_xbmc, mock_cache, cache_hit, content_type, expected_project_type):
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
        angel_interface_mock.get_projects.assert_called_once_with(project_type=expected_project_type)
        cache_key = f"projects_{content_type}"
        ui.cache.set.assert_called_once_with(cache_key, projects_data, expiration=timedelta(hours=12))

    # Directory item assertions
    assert mock_add_item.call_count == len(projects_data)
    for i, project in enumerate(projects_data):
        call_args = mock_add_item.call_args_list[i]
        args = call_args[0]  # Positional args
        assert args[0] == 1  # handle
        assert project["slug"] in args[1]  # url
        assert args[2] is mock_list_item.return_value  # listitem
        assert args[3] is True  # isFolder

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
    def test_projects_menu_no_projects(self, ui_interface, mock_xbmc, mock_cache, content_type, expected_project_type):
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
            angel_interface_mock.get_projects.assert_called_once_with(project_type=expected_project_type)

            # Ensure show_error was called with the correct message
            mock_show_error.assert_called_once_with(f"No projects found for content type: {content_type}")

            # Ensure no directory items were added
            mock_add_item.assert_not_called()
            mock_end_dir.assert_not_called()

    @parameterized_project_types
    def test_projects_menu_exception(self, ui_interface, mock_xbmc, mock_cache, content_type, expected_project_type):
        """Test projects_menu handles exceptions during project fetching."""
        ui, logger_mock, angel_interface_mock = ui_interface
        mock_add_item, mock_end_dir, mock_list_item = mock_xbmc
        angel_interface_mock.get_projects.side_effect = Exception(f"{TEST_EXCEPTION_MESSAGE} for {content_type}")

        # Set up exception on get_projects
        angel_interface_mock.get_projects.side_effect = Exception(f"{TEST_EXCEPTION_MESSAGE} for {content_type}")
        ui.cache.get.return_value = None  # Cache miss

        with patch.object(ui, "show_error") as mock_show_error:
            # Expect the exception to be raised
            with pytest.raises(Exception, match=f"{TEST_EXCEPTION_MESSAGE} for {content_type}"):
                ui.projects_menu(content_type=content_type)

            # Ensure cache was checked
            ui.cache.get.assert_called_once()

            # Ensure get_projects was called
            angel_interface_mock.get_projects.assert_called_once_with(project_type=expected_project_type)

            # Ensure error was logged and shown
            mock_show_error.assert_called_once_with(
                f"Failed to load {expected_project_type}: {TEST_EXCEPTION_MESSAGE} for {content_type}"
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
        patch.object(ui, "episodes_menu") as mock_episodes_menu,
    ):

        # Call method
        result = ui.seasons_menu(content_type=project_data["projectType"], project_slug=project_data["slug"])
        assert result is True

        if cache_hit:
            angel_interface_mock.get_project.assert_not_called()
            ui.cache.set.assert_not_called()
        else:
            angel_interface_mock.get_project.assert_any_call(project_data["slug"])
            cache_key = f"project_{project_data['slug']}"
            ui.cache.set.assert_any_call(cache_key, project_data, expiration=timedelta(hours=12))

        # Ensure cache was checked
        ui.cache.get.assert_any_call(f"project_{project_data['slug']}")

        seasons_data = project_data["seasons"]

# If we have multiple seasons, items should be added (seasons + All Episodes)
        if len(seasons_data) > 1:
            assert mock_add_item.call_count == len(seasons_data) + 1
            for i, season in enumerate(seasons_data):
                call_args = mock_add_item.call_args_list[i]
                kwargs = call_args[0]  # Positional args
                assert kwargs[0] == 1  # handle
                assert "episodes_menu" in kwargs[1]  # url contains action
                assert str(season["id"]) in kwargs[1]  # url contains season_id
                assert kwargs[2] is mock_list_item.return_value  # listitem
                assert kwargs[3] is True  # isFolder

                # Check ListItem creation
                list_item_call = mock_list_item.call_args_list[i]
                assert list_item_call[1]["label"] == season["name"]

                # Check _process_attributes_to_infotags was called with season data
                mock_process_attrs.assert_any_call(mock_list_item.return_value, season)

            # Check "All Episodes" item
            all_episodes_call = mock_add_item.call_args_list[-1]
            kwargs = all_episodes_call[0]
            assert kwargs[0] == 1  # handle
            assert "episodes_menu" in kwargs[1]  # url contains action
            assert "season_id=" not in kwargs[1]  # url does not contain season_id
            assert kwargs[2] is mock_list_item.return_value  # listitem
            assert kwargs[3] is True  # isFolder

            # Check ListItem creation for "All Episodes"
            all_episodes_list_item_call = mock_list_item.call_args_list[-1]
            assert all_episodes_list_item_call[1]["label"] == "[All Episodes]"

            mock_end_dir.assert_called_once_with(1)
        else:
            # Single season: episodes_menu should be called with season_id=None, no directory items
            mock_episodes_menu.assert_called_once_with(
                project_data["projectType"],
                project_data["slug"],
            )
            mock_add_item.assert_not_called()
            mock_end_dir.assert_not_called()
            mock_process_attrs.assert_not_called()
            logger_mock.info.assert_called_with(f"Single season found: {project_data['seasons'][0]['name']}, using all-episodes mode")


class TestSeasonsMenu:
    @pytest.mark.parametrize("cache_hit", [False, True])
    @pytest.mark.parametrize(
        "project_data",
        [
            MOCK_PROJECT_DATA["single_season_project"],
            MOCK_PROJECT_DATA["multi_season_project"],
        ],
    )
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

            result = ui.seasons_menu(content_type=expected_project_type, project_slug="nonexistent-project")
            assert result is None

            # Ensure cache was checked
            ui.cache.get.assert_any_call("project_nonexistent-project")

            # Ensure get_project was called
            angel_interface_mock.get_project.assert_called_once_with("nonexistent-project")

            # Ensure show_error was called
            mock_show_error.assert_called_once_with("Project not found: nonexistent-project")

            # Ensure no directory items or content setting occurred
            mock_set_content.assert_not_called()
            mock_add_item.assert_not_called()
            mock_end_dir.assert_not_called()

    @parameterized_project_types
    def test_seasons_menu_exception(
        self,
        ui_interface,
        mock_xbmc,
        mock_cache,
        content_type,
        expected_project_type,
    ):
        """Test seasons_menu handles exceptions during project fetching."""
        ui, logger_mock, angel_interface_mock = ui_interface
        mock_add_item, mock_end_dir, mock_list_item = mock_xbmc

        # Set up exception
        angel_interface_mock.get_project.side_effect = Exception(TEST_EXCEPTION_MESSAGE)

        with (
            patch.object(ui, "show_error") as mock_show_error,
            patch.object(ui.cache, "get", return_value=None) as mock_cache_get,
        ):

            result = ui.seasons_menu(content_type=expected_project_type, project_slug="test-project")

            # Ensure cache was checked
            mock_cache_get.assert_called_once()

            # Ensure get_project was called
            angel_interface_mock.get_project.assert_called_once_with("test-project")

            # Ensure error was logged and shown
            mock_show_error.assert_called_once_with(f"Error fetching project test-project: {TEST_EXCEPTION_MESSAGE}")

            # Ensure the method returns False on exception
            assert result is False


def episodes_menu_logic_helper(ui_interface, mock_xbmc, mock_cache, cache_hit, project_data, season_id):
    """Shared logic for episodes_menu cache miss/hit."""
    ui, logger_mock, angel_interface_mock = ui_interface
    mock_add_item, mock_end_dir, mock_list_item = mock_xbmc

    # Set up mocks
    ui.cache.get.return_value = project_data if cache_hit else None
    angel_interface_mock.get_project.return_value = project_data if not cache_hit else None

    # Find the season for assertions or aggregate for all-episodes
    if season_id is None:
        # All-episodes mode: aggregate and sort
        all_episodes = []
        for s in project_data["seasons"]:
            for ep in s["episodes"]:
                all_episodes.append(ep)
        all_episodes.sort(key=lambda e: (e.get("seasonNumber", 0), e.get("episodeNumber", 0)))
        episodes_data = all_episodes
        sort_episodic = True
    else:
        season = next((s for s in project_data["seasons"] if s["id"] == season_id), None)
        episodes_data = season["episodes"] if season else []
        sort_episodic = episodes_data and episodes_data[0].get("seasonNumber", 0) > 0

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
            ui.cache.set.assert_called_once_with(
                f"project_{project_data['slug']}", project_data, expiration=timedelta(hours=12)
            )

        # Content and sorting assertions
        mock_set_content.assert_called_once_with(1, "tvshows")
        if sort_episodic:
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
            assert args[3] is False  # isFolder

            # Check _create_list_item_from_episode calls
            mock_create_item.assert_any_call(
                episode,
                project=project_data,
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

        angel_interface_mock.get_project.side_effect = Exception(TEST_EXCEPTION_MESSAGE)
        ui.cache.get.return_value = None

        with patch.object(ui, "show_error") as mock_show_error:
            result = ui.episodes_menu(content_type="series", project_slug="test-project", season_id=1)

            ui.cache.get.assert_called_once_with("project_test-project")
            angel_interface_mock.get_project.assert_called_once_with("test-project")
            mock_show_error.assert_called_once_with(f"Error fetching season 1: {TEST_EXCEPTION_MESSAGE}")
            assert result is None

    def test_episodes_menu_handles_unavailable_episodes(self, ui_interface, mock_xbmc, mock_cache):
        """Episodes with source: None (unavailable) should be rendered but marked unavailable."""
        import copy

        ui, logger_mock, angel_interface_mock = ui_interface
        mock_add_item, mock_end_dir, mock_list_item = mock_xbmc

        # Prepare project with a season where episodes include both available and unavailable
        project_data = copy.deepcopy(MOCK_PROJECT_DATA["single_season_project"])
        season = project_data["seasons"][0]
        available_episode = copy.deepcopy(season["episodes"][0])
        unavailable_episode = copy.deepcopy(season["episodes"][0])
        unavailable_episode["guid"] = "unavailable-guid"
        unavailable_episode["source"] = None  # Unavailable episode

        season["episodes"] = [unavailable_episode, available_episode]

        ui.cache.get.return_value = project_data
        angel_interface_mock.get_project.return_value = project_data

        with (
            patch.object(ui, "_create_list_item_from_episode") as mock_create_item,  # noqa: F841
            patch("xbmcplugin.setContent") as mock_set_content,  # noqa: F841
            patch("xbmcplugin.addSortMethod") as mock_add_sort,
            patch("xbmcplugin.SORT_METHOD_EPISODE") as mock_episode_sort,  # noqa: F841
            patch("xbmcplugin.SORT_METHOD_VIDEO_SORT_TITLE") as mock_title_sort,  # noqa: F841
            patch("xbmcplugin.SORT_METHOD_LABEL") as mock_label_sort,
        ):
            ui.episodes_menu(content_type="series", project_slug=project_data["slug"], season_id=season["id"])

            # Both episodes should be added (unavailable and available)
            assert mock_add_item.call_count == 2

            # Check first call (unavailable episode)
            first_call_args = mock_add_item.call_args_list[0][0]
            assert "unavailable-guid" in first_call_args[1]
            assert first_call_args[3] is False  # Non-playable

            # Check second call (available episode)
            second_call_args = mock_add_item.call_args_list[1][0]
            assert available_episode["guid"] in second_call_args[1]
            assert second_call_args[3] is False  # Still non-playable in menu

            # Sorting still applied safely
            mock_add_sort.assert_any_call(1, mock_label_sort)
            mock_end_dir.assert_called_once_with(1)

    def test_episodes_menu_applies_progress_bars(self, ui_interface, mock_xbmc, mock_cache):
        """Test episodes_menu applies progress bars to episodes with watch position."""
        ui, logger_mock, angel_interface_mock = ui_interface
        mock_add_item, mock_end_dir, mock_list_item = mock_xbmc

        # Create project with episodes that have watch position
        project_data = copy.deepcopy(MOCK_PROJECT_DATA["multi_season_project"])
        season = project_data["seasons"][0]

        # Add watchPosition to episodes
        for episode in season["episodes"]:
            episode["watchPosition"] = {"position": 30.0}  # 30 seconds watched
            episode["source"] = {"url": "http://example.com/video.mp4", "duration": 3600}  # 1 hour

        ui.cache.get.return_value = project_data
        angel_interface_mock.get_project.return_value = None

        with (
            patch.object(ui, "_create_list_item_from_episode") as mock_create_item,
            patch.object(ui, "_apply_progress_bar") as mock_progress_bar,
            patch("xbmcplugin.setContent"),
            patch("xbmcplugin.addSortMethod"),
        ):
            mock_created_item = MagicMock()
            mock_create_item.return_value = mock_created_item

            ui.episodes_menu(content_type="series", project_slug=project_data["slug"], season_id=season["id"])

            # Verify _apply_progress_bar was called for each episode
            assert mock_progress_bar.call_count == len(season["episodes"])

            # Verify the calls with correct parameters
            for i, episode in enumerate(season["episodes"]):
                call_args = mock_progress_bar.call_args_list[i]
                assert call_args[0][0] is mock_created_item  # list_item
                assert call_args[0][1] == 30.0  # watch_position
                assert call_args[0][2] == 3600  # duration


class TestContinueWatchingMenu:
    def test_continue_watching_menu_success(self, ui_interface, mock_xbmc):
        """Test continue_watching_menu displays items successfully."""
        ui, logger_mock, angel_interface_mock = ui_interface
        mock_add_item, mock_end_dir, mock_list_item = mock_xbmc

        resume_data = {
            "guids": ["resume-guid-1", "resume-guid-2"],
            "positions": {"resume-guid-1": 1200, "resume-guid-2": 600},
            "pageInfo": {"hasNextPage": True, "endCursor": "cursor-2"},
        }

        episodes_data = {
            "episode_resume-guid-1": {
                "guid": "resume-guid-1",
                "name": "Episode 1",
                "projectSlug": "project-1",
                "duration": 3600,
            },
            "episode_resume-guid-2": {
                "guid": "resume-guid-2",
                "name": "Episode 2",
                "projectSlug": "project-2",
                "duration": 2400,
            },
        }

        projects_data = {
            "project-1": {"name": "Test Show 1", "id": "proj-1"},
            "project-2": {"name": "Test Show 2", "id": "proj-2"},
        }

        angel_interface_mock.get_resume_watching.return_value = resume_data
        angel_interface_mock.get_episodes_for_guids.return_value = episodes_data
        angel_interface_mock.get_projects_by_slugs.return_value = projects_data

        with (
            patch.object(ui, "_create_list_item_from_episode", return_value=mock_list_item) as mock_create,
            patch.object(ui, "_apply_progress_bar") as mock_progress,
        ):
            ui.continue_watching_menu(after=None)

            # Verify API called correctly
            angel_interface_mock.get_resume_watching.assert_called_once_with(first=10, after=None)
            angel_interface_mock.get_episodes_for_guids.assert_called_once_with(["resume-guid-1", "resume-guid-2"])
            # Verify projects batch called with both project slugs
            projects_call = angel_interface_mock.get_projects_by_slugs.call_args[0][0]
            assert set(projects_call) == {"project-1", "project-2"}

            # Verify items created (2 episodes + 1 load more)
            assert mock_add_item.call_count == 3

            # Verify episode list items created
            assert mock_create.call_count == 2
            assert mock_progress.call_count == 2

            # Verify "Load More" pagination item added with correct cursor
            pagination_calls = [call for call in mock_add_item.call_args_list if "after=cursor-2" in str(call)]
            assert len(pagination_calls) == 1

            mock_end_dir.assert_called_once()

    def test_continue_watching_menu_with_pagination_cursor(self, ui_interface, mock_xbmc):
        """Test continue_watching_menu with after cursor."""
        ui, logger_mock, angel_interface_mock = ui_interface
        mock_add_item, mock_end_dir, mock_list_item = mock_xbmc

        resume_data = {"guids": [], "positions": {}, "pageInfo": {"hasNextPage": False, "endCursor": None}}
        angel_interface_mock.get_resume_watching.return_value = resume_data

        with patch.object(ui, "show_notification") as mock_notify:
            ui.continue_watching_menu(after="cursor-abc")

            angel_interface_mock.get_resume_watching.assert_called_once_with(first=10, after="cursor-abc")
            mock_notify.assert_called_once_with("No items in Continue Watching")

    def test_continue_watching_menu_empty_items(self, ui_interface, mock_xbmc):
        """Test continue_watching_menu with no items."""
        ui, logger_mock, angel_interface_mock = ui_interface
        mock_add_item, mock_end_dir, mock_list_item = mock_xbmc

        angel_interface_mock.get_resume_watching.return_value = {
            "guids": [],
            "positions": {},
            "pageInfo": {"hasNextPage": False},
        }

        with patch.object(ui, "show_notification") as mock_notify:
            ui.continue_watching_menu()

            mock_notify.assert_called_once_with("No items in Continue Watching")
            mock_add_item.assert_not_called()
            mock_end_dir.assert_not_called()

    def test_continue_watching_menu_no_pagination(self, ui_interface, mock_xbmc):
        """Test continue_watching_menu without next page."""
        ui, logger_mock, angel_interface_mock = ui_interface
        mock_add_item, mock_end_dir, mock_list_item = mock_xbmc

        resume_data = {
            "guids": ["resume-guid-1"],
            "positions": {"resume-guid-1": 1200},
            "pageInfo": {"hasNextPage": False, "endCursor": None},
        }

        episodes_data = {
            "episode_resume-guid-1": {
                "guid": "resume-guid-1",
                "name": "Episode 1",
                "projectSlug": "project-1",
                "duration": 3600,
            }
        }

        projects_data = {
            "project-1": {"name": "Test Show 1", "id": "proj-1"},
        }

        angel_interface_mock.get_resume_watching.return_value = resume_data
        angel_interface_mock.get_episodes_for_guids.return_value = episodes_data
        angel_interface_mock.get_projects_by_slugs.return_value = projects_data

        with (
            patch.object(ui, "_create_list_item_from_episode", return_value=mock_list_item),
            patch.object(ui, "_apply_progress_bar"),
        ):
            ui.continue_watching_menu()

            # Only 1 episode item, no "Load More"
            assert mock_add_item.call_count == 1
            mock_end_dir.assert_called_once()

    def test_continue_watching_menu_failed_api_call(self, ui_interface, mock_xbmc):
        """Test continue_watching_menu when API returns empty dict."""
        ui, logger_mock, angel_interface_mock = ui_interface
        mock_add_item, mock_end_dir, mock_list_item = mock_xbmc

        angel_interface_mock.get_resume_watching.return_value = {}

        with patch.object(ui, "show_error") as mock_error:
            ui.continue_watching_menu()

            mock_error.assert_called_once_with("Failed to load Continue Watching")
            mock_add_item.assert_not_called()

    def test_continue_watching_menu_exception(self, ui_interface, mock_xbmc):
        """Test continue_watching_menu handles exceptions."""
        ui, logger_mock, angel_interface_mock = ui_interface
        mock_add_item, mock_end_dir, mock_list_item = mock_xbmc

        angel_interface_mock.get_resume_watching.side_effect = Exception("API error")

        with patch.object(ui, "show_error") as mock_error:
            ui.continue_watching_menu()

            mock_error.assert_called_once()
            assert "Failed to load Continue Watching" in str(mock_error.call_args)

    def test_continue_watching_menu_applies_progress_bars(self, ui_interface, mock_xbmc):
        """Test continue_watching_menu applies progress bars correctly."""
        ui, logger_mock, angel_interface_mock = ui_interface
        mock_add_item, mock_end_dir, mock_list_item = mock_xbmc

        resume_data = {
            "guids": ["resume-guid-1"],
            "positions": {"resume-guid-1": 1200},
            "pageInfo": {"hasNextPage": False},
        }

        episodes_data = {
            "episode_resume-guid-1": {
                "guid": "resume-guid-1",
                "name": "Episode 1",
                "projectSlug": "project-1",
                "duration": 3600,
            }
        }

        projects_data = {
            "project-1": {"name": "Test Show 1", "id": "proj-1"},
        }

        angel_interface_mock.get_resume_watching.return_value = resume_data
        angel_interface_mock.get_episodes_for_guids.return_value = episodes_data
        angel_interface_mock.get_projects_by_slugs.return_value = projects_data

        mock_created_item = MagicMock()

        with (
            patch.object(ui, "_create_list_item_from_episode", return_value=mock_created_item),
            patch.object(ui, "_apply_progress_bar") as mock_progress,
        ):
            ui.continue_watching_menu()

            # Verify progress bar called with correct values
            mock_progress.assert_called_once_with(mock_created_item, 1200, 3600)

    def test_continue_watching_menu_skips_progress_when_missing_watchposition(self, ui_interface, mock_xbmc):
        """Test continue_watching_menu skips progress bar when watchPosition is missing."""
        ui, logger_mock, angel_interface_mock = ui_interface
        mock_add_item, mock_end_dir, mock_list_item = mock_xbmc

        resume_data = {
            "guids": ["guid-1"],
            "positions": {},  # No position for guid-1
            "pageInfo": {"hasNextPage": False},
        }

        episodes_data = {
            "episode_guid-1": {
                "guid": "guid-1",
                "name": "Episode 1",
                "projectSlug": "project-1",
                "duration": 3600,
            }
        }

        projects_data = {
            "project-1": {"name": "Test Show", "id": "proj-1"},
        }

        angel_interface_mock.get_resume_watching.return_value = resume_data
        angel_interface_mock.get_episodes_for_guids.return_value = episodes_data
        angel_interface_mock.get_projects_by_slugs.return_value = projects_data

        with (
            patch.object(ui, "_create_list_item_from_episode", return_value=mock_list_item),
            patch.object(ui, "_apply_progress_bar") as mock_progress,
        ):
            ui.continue_watching_menu()

            # Progress bar should not be called since position is missing
            mock_progress.assert_not_called()

    def test_continue_watching_menu_skips_malformed_items(self, ui_interface, mock_xbmc):
        """Test continue_watching_menu skips items not returned from batch query."""
        ui, logger_mock, angel_interface_mock = ui_interface
        mock_add_item, mock_end_dir, mock_list_item = mock_xbmc

        resume_data = {
            "guids": ["guid-1", "guid-2", "guid-3"],
            "positions": {"guid-1": 100, "guid-2": 200, "guid-3": 300},
            "pageInfo": {"hasNextPage": False},
        }

        # Only 2 of 3 episodes returned from batch (guid-3 missing)
        episodes_data = {
            "episode_guid-1": {"guid": "guid-1", "name": "Episode 1", "projectSlug": "project-1"},
            "episode_guid-2": {"guid": "guid-2", "name": "Episode 2", "projectSlug": "project-1"},
        }

        projects_data = {
            "project-1": {"name": "Test Show", "id": "proj-1"},
        }

        angel_interface_mock.get_resume_watching.return_value = resume_data
        angel_interface_mock.get_episodes_for_guids.return_value = episodes_data
        angel_interface_mock.get_projects_by_slugs.return_value = projects_data

        with (
            patch.object(ui, "_create_list_item_from_episode", return_value=mock_list_item) as mock_create,
            patch.object(ui, "_apply_progress_bar"),
        ):
            ui.continue_watching_menu()

            # Only 2 items added (guid-3 skipped because not in batch response)
            assert mock_add_item.call_count == 2
            assert mock_create.call_count == 2
            mock_end_dir.assert_called_once()

    def test_continue_watching_menu_failed_episodes_batch(self, ui_interface, mock_xbmc):
        """Test continue_watching_menu when batch episodes fetch fails."""
        ui, logger_mock, angel_interface_mock = ui_interface
        mock_add_item, mock_end_dir, mock_list_item = mock_xbmc

        # Resume watching returns data, but batch episodes returns empty
        angel_interface_mock.get_resume_watching.return_value = {
            "guids": ["guid-1", "guid-2"],
            "positions": {"guid-1": 0.5, "guid-2": 0.3},
            "pageInfo": {"endCursor": None, "hasNextPage": False},
        }
        angel_interface_mock.get_episodes_for_guids.return_value = {}

        with patch.object(ui, "show_error") as mock_error:
            ui.continue_watching_menu()

            mock_error.assert_called_once_with("Failed to load episode details")
            mock_add_item.assert_not_called()
