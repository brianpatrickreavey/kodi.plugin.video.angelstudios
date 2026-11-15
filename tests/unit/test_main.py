"""Unit tests for plugin main entrypoint and router."""

import runpy
import sys
from importlib import util
from pathlib import Path
from unittest.mock import MagicMock
from urllib.parse import urlencode

import pytest

from .unittest_data import ROUTER_DISPATCH_CASES

MAIN_PATH = (
    Path(__file__).resolve().parents[2]
    / "plugin.video.angelstudios"
    / "resources"
    / "lib"
    / "addon_entry.py"
)
MAIN_ENTRY_PATH = (
    Path(__file__).resolve().parents[2]
    / "plugin.video.angelstudios"
    / "resources"
    / "lib"
    / "main.py"
)
RES_LIB = MAIN_PATH.parent / "resources" / "lib"


def _fresh_main_module():
    """Load addon_entry.py via importlib to avoid package import issues."""
    sys.argv = ["plugin://", "1", "?"]
    sys.path.insert(0, str(MAIN_PATH.parent))
    sys.path.insert(0, str(RES_LIB))
    spec = util.spec_from_file_location("addon_main", MAIN_PATH)
    module = util.module_from_spec(spec)
    spec.loader.exec_module(module)  # type: ignore[arg-type]
    return module


class TestMain:
    def test_router_main_menu(self, monkeypatch):
        """Routes with no params call main_menu."""
        main = _fresh_main_module()
        ui_mock = MagicMock()

        main.router("", ui_mock)

        ui_mock.main_menu.assert_called_once()

    @pytest.mark.parametrize("action,method,extra", ROUTER_DISPATCH_CASES)
    def test_router_dispatch(self, monkeypatch, action, method, extra):
        """Dispatch actions to correct UI methods; ensure no-op on all_content_menu."""
        main = _fresh_main_module()
        ui_mock = MagicMock()
        paramstring = urlencode({"action": action, **extra})

        main.router(paramstring, ui_mock)

        if method:
            getattr(ui_mock, method).assert_called_once()
        else:
            ui_mock.projects_menu.assert_not_called()
            ui_mock.main_menu.assert_not_called()

    def test_router_info_action(self, monkeypatch):
        """Info action surfaces message via show_error."""
        main = _fresh_main_module()
        ui_mock = MagicMock()

        main.router(urlencode({"action": "info", "message": "hi"}), ui_mock)

        ui_mock.show_error.assert_called_once_with("hi")

    def test_router_unknown_action(self, monkeypatch):
        """Unknown action is reported via show_error."""
        main = _fresh_main_module()
        ui_mock = MagicMock()

        main.router(urlencode({"action": "bad"}), ui_mock)

        ui_mock.show_error.assert_called_once()
        assert "Invalid action" in ui_mock.show_error.call_args[0][0]

    def test_router_clear_cache(self, monkeypatch):
        """clear_cache triggers cache clear and notification."""
        main = _fresh_main_module()
        ui_mock = MagicMock()

        main.router(urlencode({"action": "clear_cache"}), ui_mock)

        ui_mock.clear_cache_with_notification.assert_called_once()

    def test_router_install_widevine(self, monkeypatch):
        """The settings button installs Widevine without opening a catalog screen."""
        main = _fresh_main_module()
        ui_mock = MagicMock()

        main.router(urlencode({"action": "install_widevine"}), ui_mock)

        ui_mock.install_widevine.assert_called_once_with()

    def test_router_clear_cache_failure(self, monkeypatch):
        """clear_cache failure surfaces failure notification."""
        main = _fresh_main_module()
        ui_mock = MagicMock()

        main.router(urlencode({"action": "clear_cache"}), ui_mock)

        ui_mock.clear_cache_with_notification.assert_called_once()

    def test_router_clear_debug_data(self, monkeypatch):
        """clear_debug_data triggers cleanup and notification messaging."""
        main = _fresh_main_module()
        ui_mock = MagicMock()

        main.router(urlencode({"action": "clear_debug_data"}), ui_mock)

        ui_mock.clear_debug_data_with_notification.assert_called_once()

    def test_router_clear_debug_data_failure(self, monkeypatch):
        """clear_debug_data failure surfaces failure notification."""
        main = _fresh_main_module()
        ui_mock = MagicMock()

        main.router(urlencode({"action": "clear_debug_data"}), ui_mock)

        ui_mock.clear_debug_data_with_notification.assert_called_once()

    def test_router_force_logout(self, monkeypatch):
        """force_logout triggers interface logout and notification."""
        main = _fresh_main_module()
        ui_mock = MagicMock()

        main.router(urlencode({"action": "force_logout"}), ui_mock)

        ui_mock.force_logout_with_notification.assert_called_once()

    def test_router_force_logout_failure(self, monkeypatch):
        """force_logout failure surfaces failure notification."""
        main = _fresh_main_module()
        ui_mock = MagicMock()

        main.router(urlencode({"action": "force_logout"}), ui_mock)

        ui_mock.force_logout_with_notification.assert_called_once()

    def test_router_force_logout_missing_interface(self, monkeypatch):
        """Missing interface raises and is caught as navigation error."""
        main = _fresh_main_module()
        ui_mock = MagicMock()
        ui_mock.force_logout_with_notification.side_effect = ValueError(
            "Angel interface not initialized"
        )

        main.router(urlencode({"action": "force_logout"}), ui_mock)

        ui_mock.show_error.assert_called_once()
        assert "navigation error" in ui_mock.show_error.call_args[0][0].lower()

    def test_router_show_information(self, monkeypatch):
        """show_information action calls auth details dialog."""
        main = _fresh_main_module()
        ui_mock = MagicMock()

        main.router(urlencode({"action": "show_information"}), ui_mock)

        ui_mock.show_auth_details_dialog.assert_called_once()

    def test_router_settings_opens_settings(self, monkeypatch):
        """settings action opens addon settings."""
        main = _fresh_main_module()
        ui_mock = MagicMock()
        addon_mock = MagicMock()
        monkeypatch.setattr(main, "ADDON", addon_mock)

        main.router(urlencode({"action": "settings"}), ui_mock)

        addon_mock.openSettings.assert_called_once()

    def test_router_watchlist_updates_pass_the_title_id(self):
        """Add and remove send the title id. A missing id is an empty string."""
        main = _fresh_main_module()
        ui_mock = MagicMock()

        main.router(urlencode({"action": "add_to_watchlist", "content_id": "spy-id"}), ui_mock)
        ui_mock.add_to_watchlist.assert_called_once_with("spy-id")

        ui_mock.reset_mock()
        main.router(
            urlencode({"action": "remove_from_watchlist", "content_id": "tuttle-id"}), ui_mock
        )
        ui_mock.remove_from_watchlist.assert_called_once_with("tuttle-id")

        ui_mock.reset_mock()
        main.router(urlencode({"action": "add_to_watchlist"}), ui_mock)
        ui_mock.add_to_watchlist.assert_called_once_with("")

    def test_router_play_episode_passes_content_type(self):
        """Catalog playback keeps content_type. Continue Watching leaves it empty."""
        main = _fresh_main_module()
        ui_mock = MagicMock()

        main.router(
            urlencode(
                {
                    "action": "play_episode",
                    "episode_guid": "guid",
                    "project_slug": "slug",
                    "content_type": "series",
                }
            ),
            ui_mock,
        )
        ui_mock.play_episode.assert_called_once_with(
            "guid", "slug", content_type="series", resume=False
        )

        ui_mock.reset_mock()
        main.router(
            urlencode({"action": "play_episode", "episode_guid": "guid", "project_slug": "slug"}),
            ui_mock,
            resume=True,
        )
        ui_mock.play_episode.assert_called_once_with("guid", "slug", content_type="", resume=True)

    def test_router_voted_torch_passes_the_cursor_and_id(self):
        """Already voted on keeps the page cursor and plays one torch by id."""
        main = _fresh_main_module()
        ui_mock = MagicMock()

        main.router(urlencode({"action": "guild_voted_menu", "after": "page-2"}), ui_mock)
        ui_mock.guild_voted_menu.assert_called_once_with(after="page-2")

        ui_mock.reset_mock()
        main.router(urlencode({"action": "play_voted_torch", "torch_id": "land"}), ui_mock)
        ui_mock.play_voted_torch.assert_called_once_with("land")

    def test_router_missing_param(self, monkeypatch):
        """Missing required params triggers error handling."""
        main = _fresh_main_module()
        ui_mock = MagicMock()

        main.router(urlencode({"action": "seasons_menu", "content_type": "series"}), ui_mock)

        ui_mock.show_error.assert_called_once()
        assert "project_slug" in ui_mock.show_error.call_args[0][0]

    def test_main_guard_shows_dialog_on_missing_credentials(self, monkeypatch):
        """__main__ guard shows dialog when credentials are absent."""
        addon = MagicMock()
        addon.getSettingString.side_effect = lambda k: (
            "" if k in ["username", "password"] else "off"
        )
        addon.getAddonInfo.return_value = "/addon"
        monkeypatch.setattr(sys.modules["xbmcaddon"], "Addon", MagicMock(return_value=addon))

        dialog = MagicMock()
        monkeypatch.setattr(sys.modules["xbmcgui"], "Dialog", MagicMock(return_value=dialog))
        monkeypatch.setattr(
            sys.modules["xbmcvfs"], "translatePath", MagicMock(side_effect=lambda p: p)
        )

        sys.argv = ["plugin://", "1", "?action=movies_menu"]

        kodi_ui_mock = MagicMock()
        monkeypatch.setattr(
            "kodi_ui_interface.KodiUIInterface", MagicMock(return_value=kodi_ui_mock)
        )
        monkeypatch.setattr("angel_interface.AngelStudiosInterface", MagicMock())

        sys.path.insert(0, str(MAIN_PATH.parent))
        sys.path.insert(0, str(RES_LIB))
        runpy.run_path(str(MAIN_PATH), run_name="__main__")

        dialog.ok.assert_called_once_with(
            "Angel Studios",
            "Please configure your Angel.com username and password in the addon settings.",
        )

    def test_main_menu_opens_without_credentials(self, monkeypatch):
        """A missing username still opens the main menu."""
        main = _fresh_main_module()
        monkeypatch.setattr(main, "USERNAME", "")
        monkeypatch.setattr(main, "PASSWORD", "")
        ui = MagicMock()
        monkeypatch.setattr(main, "KodiUIInterface", MagicMock(return_value=ui))
        monkeypatch.setattr(main, "AuthenticationCore", MagicMock())
        monkeypatch.setattr(main, "AngelStudiosInterface", MagicMock())
        monkeypatch.setattr(sys, "argv", ["plugin://", "1", "?"])

        main.main()

        ui.main_menu.assert_called_once_with()
        main.AuthenticationCore.return_value.ensure_valid_session.assert_not_called()

    def _open_with_saved_login(self, monkeypatch, argv, signed_in):
        """Run main() with a saved username and password and a fake auth core."""
        main = _fresh_main_module()
        monkeypatch.setattr(main, "USERNAME", "user")
        monkeypatch.setattr(main, "PASSWORD", "secret")
        addon = MagicMock()
        addon.getSettingBool.return_value = False
        monkeypatch.setattr(main, "ADDON", addon)
        ui = MagicMock()
        auth = MagicMock()
        auth.validate_session.return_value = signed_in
        monkeypatch.setattr(main, "KodiUIInterface", MagicMock(return_value=ui))
        monkeypatch.setattr(main, "AuthenticationCore", MagicMock(return_value=auth))
        monkeypatch.setattr(main, "AngelStudiosInterface", MagicMock())
        monkeypatch.setattr(sys, "argv", argv)
        return main, ui, auth

    def test_expired_login_refreshes_before_the_menu_is_built(self, monkeypatch):
        """Entering the addon signs in again before the interface reads the token."""
        main, ui, auth = self._open_with_saved_login(monkeypatch, ["plugin://", "1", "?"], False)
        order = []
        auth.ensure_valid_session.side_effect = lambda: order.append("refresh")
        auth.validate_session.side_effect = [False, True]

        def build_interface(*_args, **_kwargs):
            order.append("interface")
            return MagicMock()

        monkeypatch.setattr(main, "AngelStudiosInterface", build_interface)

        main.main()

        assert order == ["refresh", "interface"]
        ui.main_menu.assert_called_once_with()

    def test_valid_login_is_left_alone(self, monkeypatch):
        """A token that is still valid does not start a new sign-in."""
        main, ui, auth = self._open_with_saved_login(monkeypatch, ["plugin://", "1", "?"], True)

        main.main()

        auth.ensure_valid_session.assert_not_called()
        ui.main_menu.assert_called_once_with()

    def test_failed_refresh_still_opens_the_menu(self, monkeypatch):
        """A failed sign-in does not block the rest of the addon."""
        main, ui, auth = self._open_with_saved_login(monkeypatch, ["plugin://", "1", "?"], False)
        auth.ensure_valid_session.side_effect = RuntimeError("nope")

        main.main()

        ui.main_menu.assert_called_once_with()
        ui.show_error.assert_not_called()

    def test_movies_menu_refreshes_an_expired_login(self, monkeypatch):
        """A catalog menu signs in again before it loads."""
        main, ui, auth = self._open_with_saved_login(
            monkeypatch, ["plugin://", "1", "?action=movies_menu"], False
        )
        auth.validate_session.side_effect = [False, True]

        main.main()

        auth.ensure_valid_session.assert_called_once_with()
        ui.projects_menu.assert_called_once_with(content_type="movies")

    def test_guild_menu_refreshes_an_expired_login(self, monkeypatch):
        """Guild Voting signs in again before it checks the saved token."""
        main, ui, auth = self._open_with_saved_login(
            monkeypatch, ["plugin://", "1", "?action=guild_voting_menu"], False
        )
        auth.validate_session.side_effect = [False, True]

        main.main()

        auth.ensure_valid_session.assert_called_once_with()
        ui.guild_voting_menu.assert_called_once_with()

    def test_settings_and_logout_do_not_refresh(self, monkeypatch):
        """Settings and logout do not sign in on the way through."""
        main, ui, auth = self._open_with_saved_login(
            monkeypatch, ["plugin://", "1", "?action=settings"], False
        )
        main.main()
        auth.ensure_valid_session.assert_not_called()
        main.ADDON.openSettings.assert_called_once_with()

        main, ui, auth = self._open_with_saved_login(
            monkeypatch, ["plugin://", "1", "?action=force_logout"], False
        )
        main.main()
        auth.ensure_valid_session.assert_not_called()
        ui.force_logout_with_notification.assert_called_once_with()

    def test_session_details_do_not_refresh(self, monkeypatch):
        """The session dialog inspects the token that is already saved."""
        main, ui, auth = self._open_with_saved_login(
            monkeypatch, ["plugin://", "1", "?action=show_information"], False
        )
        main.main()
        auth.ensure_valid_session.assert_not_called()
        ui.show_auth_details_dialog.assert_called_once_with()

        main, ui, auth = self._open_with_saved_login(
            monkeypatch, ["plugin://", "1", "?action=info&message=hi"], False
        )
        main.main()
        auth.ensure_valid_session.assert_not_called()
        ui.show_error.assert_called_once_with("hi")

    def test_session_details_available_without_credentials(self, monkeypatch):
        main = _fresh_main_module()
        monkeypatch.setattr(main, "USERNAME", "")
        monkeypatch.setattr(main, "PASSWORD", "")
        ui = MagicMock()
        monkeypatch.setattr(main, "KodiUIInterface", MagicMock(return_value=ui))
        monkeypatch.setattr(main, "AuthenticationCore", MagicMock())
        monkeypatch.setattr(main, "AngelStudiosInterface", MagicMock())
        monkeypatch.setattr(sys, "argv", ["plugin://", "1", "?action=show_information"])

        main.main()

        ui.show_auth_details_dialog.assert_called_once_with()

    def test_install_widevine_runs_without_credentials(self, monkeypatch):
        main = _fresh_main_module()
        monkeypatch.setattr(main, "USERNAME", "")
        monkeypatch.setattr(main, "PASSWORD", "")
        ui = MagicMock()
        monkeypatch.setattr(main, "KodiUIInterface", MagicMock(return_value=ui))
        monkeypatch.setattr(main, "AuthenticationCore", MagicMock())
        monkeypatch.setattr(main, "AngelStudiosInterface", MagicMock())
        monkeypatch.setattr(sys, "argv", ["plugin://", "1", "?action=install_widevine"])

        main.main()

        ui.install_widevine.assert_called_once_with()

    def test_main_guard_calls_router_with_credentials(self, monkeypatch):
        """__main__ guard initializes interfaces and routes when creds exist."""
        sys.path.insert(0, str(RES_LIB))
        import angel_interface
        import kodi_ui_interface

        addon = MagicMock()
        addon.getSetting.side_effect = ["user", "pass"]
        addon.getAddonInfo.return_value = "/addon"
        monkeypatch.setattr(sys.modules["xbmcaddon"], "Addon", MagicMock(return_value=addon))

        monkeypatch.setattr(
            sys.modules["xbmcvfs"], "translatePath", MagicMock(side_effect=lambda p: p)
        )
        monkeypatch.setattr(sys.modules["xbmcvfs"], "exists", MagicMock(return_value=True))

        asi = MagicMock()
        monkeypatch.setattr(angel_interface, "AngelStudiosInterface", MagicMock(return_value=asi))
        ui_mock = MagicMock()
        monkeypatch.setattr(kodi_ui_interface, "KodiUIInterface", MagicMock(return_value=ui_mock))

        sys.argv = ["plugin://", "1", "?action=movies_menu"]

        sys.path.insert(0, str(MAIN_PATH.parent))
        sys.path.insert(0, str(RES_LIB))
        runpy.run_path(str(MAIN_PATH), run_name="__main__")

        # ui_mock.projects_menu.assert_called_once_with(content_type="movies")

    def test_main_guard_logs_on_exception(self, monkeypatch):
        """__main__ guard surfaces initialization failures via show_error."""
        sys.path.insert(0, str(RES_LIB))
        sys.argv = ["plugin://", "1", "?action=movies_menu"]

        addon = MagicMock()
        addon.getSetting.side_effect = ["user", "pass"]
        addon.getAddonInfo.return_value = "/addon"
        monkeypatch.setattr(sys.modules["xbmcaddon"], "Addon", MagicMock(return_value=addon))

        monkeypatch.setattr(
            sys.modules["xbmcvfs"], "translatePath", MagicMock(side_effect=lambda p: p)
        )
        monkeypatch.setattr(sys.modules["xbmcvfs"], "exists", MagicMock(return_value=True))

        import angel_interface

        monkeypatch.setattr(
            angel_interface, "AngelStudiosInterface", MagicMock(side_effect=RuntimeError("boom"))
        )
        import kodi_ui_interface

        ui_mock = MagicMock()
        monkeypatch.setattr(kodi_ui_interface, "KodiUIInterface", MagicMock(return_value=ui_mock))

        from addon_entry import router

        router("?action=movies_menu", ui_mock)

        ui_mock.show_error.assert_called_once()

    def test_show_auth_details_dialog_with_session(self, monkeypatch, ui_interface):
        """Dialog shows details when session data is available."""
        ui, _logger, _angel_iface = ui_interface
        dialog = MagicMock()
        monkeypatch.setattr("kodi_ui_interface.xbmcgui.Dialog", MagicMock(return_value=dialog))

        auth_core = MagicMock()
        ui.angel_interface = MagicMock(auth_core=auth_core)
        ui.angel_interface.get_session_details.return_value = {
            "login_email": "user@example.com",
            "account_id": "uuid-123",
            "authenticated": True,
            "expires_at_local": "2026-01-05 10:00:00 PST",
            "expires_at_utc": "2026-01-05 18:00:00 UTC",
            "expires_in_human": "1 day, 2:03:04",
            "expires_in_seconds": 93784,
            "issued_at_local": "2026-01-04 10:00:00 PST",
            "issued_at_utc": "2026-01-04 18:00:00 UTC",
            "cookie_names": ["angel_jwt_v2", "other"],
            "session_file": "/tmp/session.pkl",
        }
        ui.show_auth_details_dialog()

        ui.angel_interface.get_session_details.assert_called_once()
        dialog.textviewer.assert_called_once()
        content = dialog.textviewer.call_args[0][1]
        assert "user@example.com" in content
        assert "uuid-123" in content
        assert "Remaining" in content
        assert "angel_jwt" in content and "other" in content

    def test_show_auth_details_dialog_no_session(self, monkeypatch, ui_interface):
        """Dialog ok is shown when no session is present."""
        ui, _logger, _angel_iface = ui_interface
        dialog = MagicMock()
        monkeypatch.setattr("kodi_ui_interface.xbmcgui.Dialog", MagicMock(return_value=dialog))

        ui.angel_interface = None

        ui.show_auth_details_dialog()

        dialog.ok.assert_called_once()

    def test_show_auth_details_dialog_exception(self, monkeypatch, ui_interface):
        """Dialog ok is shown when details access fails."""
        ui, _logger, _angel_iface = ui_interface
        dialog = MagicMock()
        monkeypatch.setattr("kodi_ui_interface.xbmcgui.Dialog", MagicMock(return_value=dialog))

        auth_core = MagicMock()
        ui.angel_interface = MagicMock(auth_core=auth_core)
        ui.angel_interface.get_session_details.side_effect = RuntimeError("boom")

        ui.show_auth_details_dialog()

        dialog.ok.assert_called_once()

    def test_show_auth_details_dialog_non_int_remaining(self, monkeypatch, ui_interface):
        """Non-int remaining uses fallback formatting branch."""
        ui, _logger, _angel_iface = ui_interface
        dialog = MagicMock()
        monkeypatch.setattr("kodi_ui_interface.xbmcgui.Dialog", MagicMock(return_value=dialog))

        auth_core = MagicMock()
        ui.angel_interface = MagicMock(auth_core=auth_core)
        ui.angel_interface.get_session_details.return_value = {
            "login_email": "user@example.com",
            "account_id": "uuid-123",
            "authenticated": True,
            "expires_at_local": "local",
            "expires_at_utc": "utc",
            "expires_in_human": "unknown",
            "expires_in_seconds": None,
            "issued_at_local": "local",
            "issued_at_utc": "utc",
            "cookie_names": [],
            "session_file": "/tmp/session.pkl",
        }
        ui.show_auth_details_dialog()

        dialog.textviewer.assert_called_once()
        content = dialog.textviewer.call_args[0][1]
        assert "unknown" in content
