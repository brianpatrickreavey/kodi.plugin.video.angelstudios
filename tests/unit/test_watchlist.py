"""Watchlist menu, context commands, and the Angel watchlist calls."""

import base64
import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from kodi_ui_interface import KodiUIInterface
from resources.lib.angel_interface import AngelStudiosInterface, _watchlist_items
from resources.lib.kodi_menu_handler import KodiMenuHandler
from resources.lib.menu_projects import ProjectsMenu, projects_need_title_ids, title_content_id

ADDON_ROOT = Path(__file__).resolve().parents[2] / "plugin.video.angelstudios"
GRAPHQL_DIR = ADDON_ROOT / "resources" / "lib" / "angel_graphql"
STRINGS_PO = ADDON_ROOT / "resources" / "language" / "resource.language.en_gb" / "strings.po"

FAILURE = "We ran into an issue while updating your watchlist. Please try again later."

SPY = {
    "content_id": "spy-id",
    "name": "The Spy Next Door",
    "description": "A man is called to baby-sit his neighbor's children.",
    "project_slug": "the-spy-next-door",
    "menu_content_type": "movies",
    "poster_path": "spy-poster",
    "landscape_path": "spy-landscape",
}
TUTTLE = {
    "content_id": "tuttle-id",
    "name": "Tuttle Twins",
    "description": "Ethan and Emily Tuttle go on adventures through time.",
    "project_slug": "tuttle-twins",
    "menu_content_type": "series",
    "poster_path": None,
    "landscape_path": None,
}


def _edge(typename, content_id, slug, name, project=True):
    content = {
        "__typename": typename,
        "id": content_id,
        "name": name,
        "description": "About " + name,
        "imagePortrait": {"cloudinaryPath": "portrait-" + name},
        "imageLandscape": None,
    }
    if project:
        content["project"] = {"slug": slug}
    return {"node": {"id": "row-" + str(content_id), "content": content}}


def _watchlist_payload(*edges):
    return {"getMyDefaultWatchList": {"id": "list-id", "items": {"edges": list(edges)}}}


@pytest.fixture
def angel_interface():
    auth = MagicMock()
    auth.session_store.get_token.return_value = "token"
    with patch("requests.Session", return_value=MagicMock()):
        interface = AngelStudiosInterface(auth_core=auth, logger=MagicMock())
        yield interface


class TestWatchlistApi:
    def test_list_keeps_angel_order_and_title_ids(self, angel_interface):
        angel_interface._graphql_query = MagicMock(
            return_value=_watchlist_payload(
                _edge("ContentMovie", "spy-id", "the-spy-next-door", "The Spy Next Door"),
                _edge("ContentSeries", "tuttle-id", "tuttle-twins", "Tuttle Twins"),
                _edge("ContentSpecial", "special-id", "dry-bar", "A Special"),
            )
        )

        items = angel_interface.get_default_watchlist()

        assert [item["name"] for item in items] == ["The Spy Next Door", "Tuttle Twins", "A Special"]
        assert [item["content_id"] for item in items] == ["spy-id", "tuttle-id", "special-id"]
        assert [item["menu_content_type"] for item in items] == ["movies", "series", "specials"]
        assert items[0]["project_slug"] == "the-spy-next-door"
        assert items[0]["poster_path"] == "portrait-The Spy Next Door"
        assert items[0]["landscape_path"] is None
        assert items[1]["description"] == "About Tuttle Twins"
        angel_interface._graphql_query.assert_called_once_with("getMyDefaultWatchList", variables={})

    def test_list_skips_rows_that_cannot_be_opened(self, angel_interface):
        angel_interface._graphql_query = MagicMock(
            return_value=_watchlist_payload(
                "not-an-edge",
                {"node": "bad"},
                {"node": {"content": "bad"}},
                _edge("ContentEpisode", "episode-id", "tuttle-twins", "Episode"),
                _edge("ContentMovie", "no-slug", "", "No Slug", project=False),
                _edge("ContentMovie", "", "has-slug", "No Id"),
                _edge("ContentMovie", "spy-id", "the-spy-next-door", ""),
            )
        )

        items = angel_interface.get_default_watchlist()

        assert len(items) == 1
        assert items[0]["content_id"] == "spy-id"
        assert items[0]["name"] == "Unknown"

    def test_blank_artwork_is_omitted(self, angel_interface):
        edge = _edge("ContentMovie", "spy-id", "the-spy-next-door", "The Spy Next Door")
        edge["node"]["content"]["imagePortrait"] = {"cloudinaryPath": ""}
        edge["node"]["content"]["imageLandscape"] = {"cloudinaryPath": None}
        angel_interface._graphql_query = MagicMock(return_value=_watchlist_payload(edge))

        items = angel_interface.get_default_watchlist()

        assert items[0]["poster_path"] is None
        assert items[0]["landscape_path"] is None

    def test_parser_skips_a_node_that_is_not_a_title(self):
        assert _watchlist_items(["nope"]) == []

    def test_empty_list_is_not_a_failure(self, angel_interface):
        angel_interface._graphql_query = MagicMock(return_value=_watchlist_payload())

        assert angel_interface.get_default_watchlist() == []

    def test_failed_read_is_none(self, angel_interface):
        angel_interface._graphql_query = MagicMock(side_effect=Exception("No viewer profile id provided"))
        assert angel_interface.get_default_watchlist() is None

        angel_interface._graphql_query = MagicMock(return_value=[])
        assert angel_interface.get_default_watchlist() is None

        angel_interface._graphql_query = MagicMock(return_value={"getMyDefaultWatchList": None})
        assert angel_interface.get_default_watchlist() is None

    @pytest.mark.parametrize(
        "method,operation",
        [("add_to_watchlist", "addToWatchList"), ("remove_from_watchlist", "deleteFromWatchList")],
    )
    def test_update_sends_the_title_id(self, angel_interface, method, operation):
        angel_interface._graphql_query = MagicMock(return_value={operation: {"id": "list-id"}})

        assert getattr(angel_interface, method)("spy-id") is True

        angel_interface._graphql_query.assert_called_once_with(operation, variables={"contentId": "spy-id"})

    @pytest.mark.parametrize("method", ["add_to_watchlist", "remove_from_watchlist"])
    def test_update_failure_returns_false(self, angel_interface, method):
        angel_interface._graphql_query = MagicMock(side_effect=Exception("down"))
        assert getattr(angel_interface, method)("spy-id") is False

        angel_interface._graphql_query = MagicMock(return_value={"addToWatchList": None, "deleteFromWatchList": None})
        assert getattr(angel_interface, method)("spy-id") is False

        angel_interface._graphql_query = MagicMock(return_value=[])
        assert getattr(angel_interface, method)("spy-id") is False

        angel_interface._graphql_query = MagicMock(return_value={"addToWatchList": {}, "deleteFromWatchList": {}})
        assert getattr(angel_interface, method)("spy-id") is False

        angel_interface._graphql_query = MagicMock()
        assert getattr(angel_interface, method)("") is False
        angel_interface._graphql_query.assert_not_called()


def _signed_token(profile_id):
    """A JWT whose payload is only the sub claim. The signature is not checked."""
    payload = base64.urlsafe_b64encode(json.dumps({"sub": profile_id}).encode()).decode().rstrip("=")
    return "eyJhbGciOiJub25lIn0." + payload + ".sig"


def _interface_with_token(token):
    auth = MagicMock()
    auth.session_store.get_token.return_value = token
    session = MagicMock()
    session.headers = {}
    with patch("requests.Session", return_value=session):
        interface = AngelStudiosInterface(auth_core=auth, logger=MagicMock())
    return interface, session


class TestViewerProfileHeader:
    def test_session_sends_the_jwt_sub_as_the_viewer_profile(self):
        _interface, session = _interface_with_token(_signed_token("profile-1"))

        assert session.headers["Authorization"] == "Bearer " + _signed_token("profile-1")
        assert session.headers["x-viewer-profile-id"] == "profile-1"

    def test_a_token_without_a_profile_id_does_not_keep_a_stale_one(self):
        interface, session = _interface_with_token("not-a-jwt")

        assert session.headers["Authorization"] == "Bearer not-a-jwt"
        assert "x-viewer-profile-id" not in session.headers

        session.headers["x-viewer-profile-id"] = "stale"
        interface._apply_auth_headers("not-a-jwt")
        interface._apply_auth_headers(_signed_token(""))

        assert "x-viewer-profile-id" not in session.headers

    def test_a_refreshed_token_replaces_the_profile_id(self):
        interface, session = _interface_with_token(_signed_token("first"))
        interface.auth_core.session_store.get_token.return_value = _signed_token("second")
        with patch.object(interface, "_load_query", return_value="query { x }"), patch.object(session, "post") as post:
            post.return_value.json.return_value = {"data": {"ok": True}}
            interface._graphql_query("getMyDefaultWatchList")

        assert session.headers["x-viewer-profile-id"] == "second"

    def test_logout_clears_the_viewer_profile(self):
        interface, session = _interface_with_token(_signed_token("profile-1"))
        with patch("resources.lib.angel_interface.requests.get") as get:
            get.return_value.status_code = 302
            assert interface.force_logout() is True

        assert "Authorization" not in session.headers
        assert "x-viewer-profile-id" not in session.headers


class TestWatchlistMenu:
    def test_empty_watchlist_has_no_titles_and_no_error(self, ui_interface, mock_xbmc):
        ui, _logger, angel = ui_interface
        _add_item, end_dir, _list_item = mock_xbmc
        angel.get_default_watchlist.return_value = []

        with (
            patch.object(ui, "show_error") as show_error,
            patch.object(ui, "show_notification") as show_notification,
        ):
            assert ui.watchlist_menu() is True

        show_error.assert_not_called()
        show_notification.assert_not_called()
        _add_item.assert_not_called()
        end_dir.assert_called_once_with(1)
        assert "Watchlist is not available yet." not in str(show_error.call_args_list)

    def test_titles_stay_in_angel_order_and_open_the_catalog_screen(self, ui_interface, mock_xbmc):
        ui, _logger, angel = ui_interface
        add_item, end_dir, list_item = mock_xbmc
        angel.get_default_watchlist.return_value = [SPY, TUTTLE]

        with patch("xbmcplugin.addSortMethod") as sort_method:
            assert ui.watchlist_menu() is True
            sort_method.assert_not_called()

        spy_url = ui.create_plugin_url(
            base_url=ui.kodi_url,
            action="seasons_menu",
            content_type="movies",
            project_slug="the-spy-next-door",
        )
        tuttle_url = ui.create_plugin_url(
            base_url=ui.kodi_url,
            action="seasons_menu",
            content_type="series",
            project_slug="tuttle-twins",
        )
        assert add_item.call_args_list[0][0][1] == spy_url
        assert add_item.call_args_list[1][0][1] == tuttle_url
        assert "remove_from_watchlist" not in spy_url
        assert add_item.call_args_list[0][0][3] is True
        end_dir.assert_called_once_with(1)

        contexts = list_item.return_value.addContextMenuItems.call_args_list
        assert contexts[0][0][0][0][0] == "Remove from Watchlist"
        assert "content_id=spy-id" in contexts[0][0][0][0][1]
        assert contexts[1][0][0][0][0] == "Remove from Watchlist"
        assert "content_id=tuttle-id" in contexts[1][0][0][0][1]

        media_types = [
            call.args[0] for call in list_item.return_value.getVideoInfoTag.return_value.setMediaType.call_args_list
        ]
        assert "movie" in media_types
        assert media_types[-1] == "tvshow"

    def test_failed_load_shows_an_error(self, ui_interface, mock_xbmc):
        ui, _logger, angel = ui_interface
        _add_item, end_dir, _list_item = mock_xbmc
        angel.get_default_watchlist.return_value = None

        with patch.object(ui, "show_error") as show_error:
            assert ui.watchlist_menu() is False

        show_error.assert_called_once_with("Failed to load Watchlist")
        end_dir.assert_not_called()
        assert "Watchlist is not available yet." not in show_error.call_args[0][0]

        angel.get_default_watchlist.side_effect = Exception("down")
        with patch.object(ui, "show_error") as show_error:
            assert ui.watchlist_menu() is False
        show_error.assert_called_once_with("Failed to load Watchlist")

    def test_add_and_remove_notices(self, ui_interface):
        ui, _logger, angel = ui_interface
        angel.add_to_watchlist.return_value = True
        with (
            patch.object(ui, "show_notification") as show_notification,
            patch("xbmc.executebuiltin") as refresh,
        ):
            assert ui.add_to_watchlist("spy-id") is True
        show_notification.assert_called_once_with("Added to Watchlist.")
        refresh.assert_called_once_with("Container.Refresh")
        angel.add_to_watchlist.assert_called_once_with("spy-id")

        angel.remove_from_watchlist.return_value = True
        with (
            patch.object(ui, "show_notification") as show_notification,
            patch("xbmc.executebuiltin") as refresh,
        ):
            assert ui.remove_from_watchlist("tuttle-id") is True
        show_notification.assert_called_once_with("Removed from Watchlist.")
        refresh.assert_called_once_with("Container.Refresh")

    def test_failed_update_leaves_the_list_alone(self, ui_interface):
        ui, _logger, angel = ui_interface
        angel.remove_from_watchlist.return_value = False
        with (
            patch.object(ui, "show_notification") as show_notification,
            patch("xbmc.executebuiltin") as refresh,
        ):
            assert ui.remove_from_watchlist("spy-id") is False
        show_notification.assert_called_once_with(FAILURE)
        refresh.assert_not_called()

        angel.add_to_watchlist.side_effect = Exception("down")
        with (
            patch.object(ui, "show_notification") as show_notification,
            patch("xbmc.executebuiltin") as refresh,
        ):
            assert ui.add_to_watchlist("spy-id") is False
        show_notification.assert_called_once_with(FAILURE)
        refresh.assert_not_called()

        with (
            patch.object(ui, "show_notification") as show_notification,
            patch("xbmc.executebuiltin") as refresh,
        ):
            assert ui.add_to_watchlist("") is False
        angel.add_to_watchlist.assert_called_once_with("spy-id")
        show_notification.assert_called_once_with(FAILURE)
        refresh.assert_not_called()


class TestWatchlistContext:
    def _render_movies(self, ui, projects, saved):
        ui.cache_manager.cache.get.return_value = None
        ui.angel_interface.get_projects.return_value = projects
        ui.angel_interface.get_default_watchlist.return_value = saved
        with patch.object(ui.cache_manager, "_cache_enabled", return_value=True):
            ui.projects_menu(content_type="movies")

    def test_movie_offers_add_until_it_is_saved(self, ui_interface, mock_xbmc):
        ui, _logger, angel = ui_interface
        _add_item, _end_dir, list_item = mock_xbmc
        project = {
            "slug": "the-spy-next-door",
            "name": "The Spy Next Door",
            "projectType": "movie",
            "title": {"__typename": "ContentMovie", "id": "spy-id"},
        }

        self._render_movies(ui, [project], [])
        label, command = list_item.return_value.addContextMenuItems.call_args[0][0][0]
        assert label == "Add to Watchlist"
        assert "action=add_to_watchlist" in command
        assert "content_id=spy-id" in command

        list_item.return_value.addContextMenuItems.reset_mock()
        self._render_movies(ui, [project], [{"content_id": "spy-id"}])
        label, command = list_item.return_value.addContextMenuItems.call_args[0][0][0]
        assert label == "Remove from Watchlist"
        assert "action=remove_from_watchlist" in command

        angel.get_default_watchlist.assert_called()

    def test_movie_without_a_title_id_has_no_watchlist_command(self, ui_interface, mock_xbmc):
        ui, _logger, _angel = ui_interface
        _add_item, _end_dir, list_item = mock_xbmc
        project = {"slug": "the-spy-next-door", "name": "The Spy Next Door", "projectType": "movie"}

        self._render_movies(ui, [project], [])

        list_item.return_value.addContextMenuItems.assert_not_called()

    def test_podcast_has_no_watchlist_command(self, ui_interface, mock_xbmc):
        ui, _logger, angel = ui_interface
        _add_item, _end_dir, list_item = mock_xbmc
        menu = ProjectsMenu(ui)

        menu._render_projects_menu(
            [{"name": "Podcast", "slug": "pod", "projectType": "podcast"}],
            "podcasts",
        )

        list_item.return_value.addContextMenuItems.assert_not_called()
        angel.get_default_watchlist.assert_not_called()

    def test_unreadable_membership_still_offers_add(self, ui_interface, mock_xbmc):
        ui, _logger, angel = ui_interface
        _add_item, _end_dir, list_item = mock_xbmc
        angel.get_default_watchlist.side_effect = Exception("down")
        project = {
            "slug": "tuttle-twins",
            "name": "Tuttle Twins",
            "projectType": "series",
            "title": {"id": "tuttle-id"},
        }
        ui.cache_manager.cache.get.return_value = None
        angel.get_projects.return_value = [project]
        with patch.object(ui.cache_manager, "_cache_enabled", return_value=True):
            ui.projects_menu(content_type="series")

        label, _command = list_item.return_value.addContextMenuItems.call_args[0][0][0]
        assert label == "Add to Watchlist"

    def test_episode_does_not_offer_the_watchlist(self):
        handler = KodiMenuHandler(MagicMock())
        episode = {
            "name": "When Laws Give You Lemons",
            "subtitle": "When Laws Give You Lemons",
            "description": "The twins visit a town.",
            "source": {"url": "https://example.com/stream.m3u8"},
        }
        with patch("xbmcgui.ListItem") as list_item_cls:
            list_item = MagicMock()
            list_item_cls.return_value = list_item
            list_item.getVideoInfoTag.return_value = MagicMock()
            handler._create_list_item_from_episode(episode, content_type="series")
        list_item.addContextMenuItems.assert_not_called()

    def test_cached_catalog_without_title_ids_is_fetched_again(self, ui_interface, mock_xbmc):
        ui, _logger, angel = ui_interface
        cached = [{"slug": "the-spy-next-door", "name": "The Spy Next Door", "projectType": "movie"}]
        fresh = [dict(cached[0], title={"id": "spy-id", "__typename": "ContentMovie"})]
        ui.cache_manager.cache.get.return_value = cached
        angel.get_projects.return_value = fresh
        angel.get_default_watchlist.return_value = []

        with patch.object(ui.cache_manager, "_cache_enabled", return_value=True):
            ui.projects_menu(content_type="movies")

        angel.get_projects.assert_called_once_with(project_type="movie")
        ui.cache_manager.cache.set.assert_called_once()
        assert ui.cache_manager.cache.set.call_args[0][1] == fresh


class TestWatchlistSetting:
    def test_watchlist_stays_off_the_main_menu_until_the_setting_is_on(self, mock_xbmc):
        import xbmcaddon

        addon = xbmcaddon.Addon.return_value
        original = addon.getSettingBool.side_effect
        shown = {"show_movies": True, "show_series": True, "show_specials": True}
        try:
            addon.getSettingBool.side_effect = lambda key: shown.get(key, False)
            ui = KodiUIInterface(
                handle=1,
                url="plugin://plugin.video.angelstudios/",
                logger=MagicMock(),
                angel_interface=MagicMock(),
            )
            ui.main_menu()
            labels = [item["label"] for item in ui.menu_handler.menu_items]
            assert "Watchlist" not in labels

            addon.getSettingBool.side_effect = lambda key: key == "show_watchlist" or shown.get(key, False)
            ui.main_menu()
            labels = [item["label"] for item in ui.menu_handler.menu_items]
            assert "Watchlist" in labels
        finally:
            addon.getSettingBool.side_effect = original

    def test_setting_strings(self):
        text = STRINGS_PO.read_text(encoding="utf-8")
        assert 'msgctxt "#30326"\nmsgid "Watchlist"' in text
        assert 'msgctxt "#30327"\nmsgid "Show Watchlist on the main menu"' in text

    def test_queries_use_the_site_operations(self):
        listing = (GRAPHQL_DIR / "query_getMyDefaultWatchList.graphql").read_text(encoding="utf-8")
        assert "query getMyDefaultWatchList" in listing
        assert "items(first: 100)" in listing
        add = (GRAPHQL_DIR / "query_addToWatchList.graphql").read_text(encoding="utf-8")
        assert "mutation addToWatchList($contentId: String!)" in add
        assert "addToWatchList(contentId: $contentId)" in add
        remove = (GRAPHQL_DIR / "query_deleteFromWatchList.graphql").read_text(encoding="utf-8")
        assert "mutation deleteFromWatchList($contentId: String!)" in remove
        assert "deleteFromWatchList(contentId: $contentId)" in remove


class TestTitleIds:
    def test_title_id_helpers(self):
        assert title_content_id("nope") is None
        assert title_content_id({"title": "nope"}) is None
        assert title_content_id({"title": {"id": ""}}) is None
        assert title_content_id({"title": {"id": "spy-id"}}) == "spy-id"

        assert projects_need_title_ids("nope") is False
        assert projects_need_title_ids([{"projectType": "podcast"}]) is False
        assert projects_need_title_ids(["bad", {"projectType": "movie"}]) is True
        assert projects_need_title_ids([{"projectType": "movie", "title": {"contentRatings": []}}]) is True
        assert projects_need_title_ids([{"projectType": "movie", "title": None}]) is False
        assert projects_need_title_ids([{"projectType": "movie", "title": {"id": ""}}]) is False
        assert projects_need_title_ids([{"projectType": "movie", "title": {"id": "spy-id"}}]) is False

    def test_missing_getter_leaves_membership_unknown(self, ui_interface):
        ui, _logger, _angel = ui_interface
        menu = ProjectsMenu(ui)
        ui.angel_interface = object()
        assert menu._saved_watchlist_ids() == set()
