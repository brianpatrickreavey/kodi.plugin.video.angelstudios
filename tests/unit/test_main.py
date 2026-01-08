"""Unit tests for plugin main entrypoint and router."""

import os
import runpy
import sys
from importlib import util
from pathlib import Path
from unittest.mock import MagicMock, patch
from urllib.parse import urlencode

import pytest

from .unittest_data import ROUTER_DISPATCH_CASES

MAIN_PATH = Path(__file__).resolve().parents[2] / "plugin.video.angelstudios" / "main.py"
RES_LIB = MAIN_PATH.parent / "resources" / "lib"


def _fresh_main_module():
	"""Load main.py via importlib to avoid package import issues."""
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
		monkeypatch.setattr(main, "ui_interface", ui_mock)

		main.router("")

		ui_mock.main_menu.assert_called_once()

	@pytest.mark.parametrize("action,method,extra", ROUTER_DISPATCH_CASES)
	def test_router_dispatch(self, monkeypatch, action, method, extra):
		"""Dispatch actions to correct UI methods; ensure no-op on all_content_menu."""
		main = _fresh_main_module()
		ui_mock = MagicMock()
		monkeypatch.setattr(main, "ui_interface", ui_mock)
		paramstring = urlencode({"action": action, **extra})

		main.router(paramstring)

		if method:
			getattr(ui_mock, method).assert_called_once()
		else:
			ui_mock.projects_menu.assert_not_called()
			ui_mock.main_menu.assert_not_called()

	def test_router_info_action(self, monkeypatch):
		"""Info action surfaces message via show_error."""
		main = _fresh_main_module()
		ui_mock = MagicMock()
		monkeypatch.setattr(main, "ui_interface", ui_mock)

		main.router(urlencode({"action": "info", "message": "hi"}))

		ui_mock.show_error.assert_called_once_with("hi")

	def test_router_unknown_action(self, monkeypatch):
		"""Unknown action is reported via show_error."""
		main = _fresh_main_module()
		ui_mock = MagicMock()
		monkeypatch.setattr(main, "ui_interface", ui_mock)

		main.router(urlencode({"action": "bad"}))

		ui_mock.show_error.assert_called_once()
		assert "Invalid action" in ui_mock.show_error.call_args[0][0]

	def test_router_clear_cache(self, monkeypatch):
		"""clear_cache triggers cache clear and notification."""
		main = _fresh_main_module()
		ui_mock = MagicMock()
		ui_mock.clear_cache.return_value = True
		monkeypatch.setattr(main, "ui_interface", ui_mock)

		main.router(urlencode({"action": "clear_cache"}))

		ui_mock.clear_cache.assert_called_once()
		ui_mock.show_notification.assert_called_once()

	def test_router_clear_cache_failure(self, monkeypatch):
		"""clear_cache failure surfaces failure notification."""
		main = _fresh_main_module()
		ui_mock = MagicMock()
		ui_mock.clear_cache.return_value = False
		monkeypatch.setattr(main, "ui_interface", ui_mock)

		main.router(urlencode({"action": "clear_cache"}))

		ui_mock.show_notification.assert_called_once()
		assert "failed" in ui_mock.show_notification.call_args[0][0].lower()

	def test_router_clear_debug_data(self, monkeypatch):
		"""clear_debug_data triggers cleanup and notification messaging."""
		main = _fresh_main_module()
		ui_mock = MagicMock()
		ui_mock.clear_debug_data.return_value = True
		monkeypatch.setattr(main, "ui_interface", ui_mock)

		main.router(urlencode({"action": "clear_debug_data"}))

		ui_mock.clear_debug_data.assert_called_once()
		ui_mock.show_notification.assert_called_once_with("Debug data cleared.")

	def test_router_clear_debug_data_failure(self, monkeypatch):
		"""clear_debug_data failure surfaces failure notification."""
		main = _fresh_main_module()
		ui_mock = MagicMock()
		ui_mock.clear_debug_data.return_value = False
		monkeypatch.setattr(main, "ui_interface", ui_mock)

		main.router(urlencode({"action": "clear_debug_data"}))

		ui_mock.clear_debug_data.assert_called_once()
		ui_mock.show_notification.assert_called_once_with("Debug data clear failed; please try again.")

	def test_router_force_logout(self, monkeypatch):
		"""force_logout triggers interface logout and notification."""
		main = _fresh_main_module()
		ui_mock = MagicMock()
		iface = MagicMock()
		iface.force_logout.return_value = True
		ui_mock.angel_interface = iface
		monkeypatch.setattr(main, "ui_interface", ui_mock)

		main.router(urlencode({"action": "force_logout"}))

		iface.force_logout.assert_called_once()
		ui_mock.show_notification.assert_called_once()

	def test_router_force_logout_failure(self, monkeypatch):
		"""force_logout failure surfaces failure notification."""
		main = _fresh_main_module()
		ui_mock = MagicMock()
		iface = MagicMock()
		iface.force_logout.return_value = False
		ui_mock.angel_interface = iface
		monkeypatch.setattr(main, "ui_interface", ui_mock)

		main.router(urlencode({"action": "force_logout"}))

		ui_mock.show_notification.assert_called_once()
		assert "failed" in ui_mock.show_notification.call_args[0][0].lower()

	def test_router_force_logout_missing_interface(self, monkeypatch):
		"""Missing interface raises and is caught as navigation error."""
		main = _fresh_main_module()
		ui_mock = MagicMock()
		ui_mock.angel_interface = None
		monkeypatch.setattr(main, "ui_interface", ui_mock)

		main.router(urlencode({"action": "force_logout"}))

		ui_mock.show_error.assert_called_once()
		assert "navigation error" in ui_mock.show_error.call_args[0][0].lower()

	def test_router_show_information(self, monkeypatch):
		"""show_information action calls auth details dialog."""
		main = _fresh_main_module()
		ui_mock = MagicMock()
		monkeypatch.setattr(main, "ui_interface", ui_mock)

		main.router(urlencode({"action": "show_information"}))

		ui_mock.show_auth_details_dialog.assert_called_once()

	def test_router_settings_opens_settings(self, monkeypatch):
		"""settings action opens addon settings."""
		main = _fresh_main_module()
		ui_mock = MagicMock()
		monkeypatch.setattr(main, "ui_interface", ui_mock)
		addon_mock = MagicMock()
		monkeypatch.setattr(main, "ADDON", addon_mock)

		main.router(urlencode({"action": "settings"}))

		addon_mock.openSettings.assert_called_once()

	def test_router_missing_param(self, monkeypatch):
		"""Missing required params triggers error handling."""
		main = _fresh_main_module()
		ui_mock = MagicMock()
		monkeypatch.setattr(main, "ui_interface", ui_mock)

		main.router(urlencode({"action": "seasons_menu", "content_type": "series"}))

		ui_mock.show_error.assert_called_once()
		assert "project_slug" in ui_mock.show_error.call_args[0][0]

	def test_main_guard_shows_dialog_on_missing_credentials(self, monkeypatch):
		"""__main__ guard shows dialog when credentials are absent."""
		addon = MagicMock()
		addon.getSetting.side_effect = ["", ""]
		addon.getAddonInfo.return_value = "/addon"
		monkeypatch.setattr(sys.modules["xbmcaddon"], "Addon", MagicMock(return_value=addon))

		dialog = MagicMock()
		monkeypatch.setattr(sys.modules["xbmcgui"], "Dialog", MagicMock(return_value=dialog))
		monkeypatch.setattr(sys.modules["xbmcvfs"], "translatePath", MagicMock(side_effect=lambda p: p))

		sys.argv = ["plugin://", "1", "?"]

		kodi_ui_mock = MagicMock()
		monkeypatch.setitem(sys.modules, "kodi_ui_interface", MagicMock(KodiUIInterface=MagicMock(return_value=kodi_ui_mock)))
		monkeypatch.setitem(sys.modules, "angel_interface", MagicMock(AngelStudiosInterface=MagicMock()))

		sys.path.insert(0, str(MAIN_PATH.parent))
		sys.path.insert(0, str(RES_LIB))
		runpy.run_path(str(MAIN_PATH), run_name="__main__")

		dialog.ok.assert_called_once()

	def test_main_guard_calls_router_with_credentials(self, monkeypatch):
		"""__main__ guard initializes interfaces and routes when creds exist."""
		addon = MagicMock()
		addon.getSetting.side_effect = ["user", "pass"]
		addon.getAddonInfo.return_value = "/addon"
		monkeypatch.setattr(sys.modules["xbmcaddon"], "Addon", MagicMock(return_value=addon))

		monkeypatch.setattr(sys.modules["xbmcvfs"], "translatePath", MagicMock(side_effect=lambda p: p))
		monkeypatch.setattr(sys.modules["xbmcvfs"], "exists", MagicMock(return_value=True))

		asi = MagicMock()
		monkeypatch.setitem(sys.modules, "angel_interface", MagicMock(AngelStudiosInterface=MagicMock(return_value=asi)))
		ui_mock = MagicMock()
		monkeypatch.setitem(sys.modules, "kodi_ui_interface", MagicMock(KodiUIInterface=MagicMock(return_value=ui_mock)))

		sys.argv = ["plugin://", "1", "?action=movies_menu"]

		sys.path.insert(0, str(MAIN_PATH.parent))
		sys.path.insert(0, str(RES_LIB))
		runpy.run_path(str(MAIN_PATH), run_name="__main__")

		ui_mock.setAngelInterface.assert_called_once_with(asi)
		ui_mock.projects_menu.assert_called_once_with(content_type="movies")

	def test_main_guard_logs_on_exception(self, monkeypatch):
		"""__main__ guard surfaces initialization failures via show_error."""
		addon = MagicMock()
		addon.getSetting.side_effect = ["user", "pass"]
		addon.getAddonInfo.return_value = "/addon"
		monkeypatch.setattr(sys.modules["xbmcaddon"], "Addon", MagicMock(return_value=addon))

		monkeypatch.setattr(sys.modules["xbmcvfs"], "translatePath", MagicMock(side_effect=lambda p: p))
		monkeypatch.setattr(sys.modules["xbmcvfs"], "exists", MagicMock(return_value=True))

		monkeypatch.setitem(sys.modules, "angel_interface", MagicMock(AngelStudiosInterface=MagicMock(side_effect=RuntimeError("boom"))))
		ui_mock = MagicMock()
		monkeypatch.setitem(sys.modules, "kodi_ui_interface", MagicMock(KodiUIInterface=MagicMock(return_value=ui_mock)))

		sys.argv = ["plugin://", "1", "?action=movies_menu"]

		sys.path.insert(0, str(MAIN_PATH.parent))
		sys.path.insert(0, str(RES_LIB))
		runpy.run_path(str(MAIN_PATH), run_name="__main__")

		ui_mock.show_error.assert_called_once()

	def test_show_auth_details_dialog_with_session(self, monkeypatch, ui_interface):
		"""Dialog shows details when session data is available."""
		ui, _logger, _angel_iface = ui_interface
		dialog = MagicMock()
		monkeypatch.setattr("kodi_ui_interface.xbmcgui.Dialog", MagicMock(return_value=dialog))

		session = MagicMock()
		session.get_session_details.return_value = {
			"login_email": "user@example.com",
			"account_id": "uuid-123",
			"authenticated": True,
			"expires_at_local": "2026-01-05 10:00:00 PST",
			"expires_at_utc": "2026-01-05 18:00:00 UTC",
			"expires_in_human": "1 day, 2:03:04",
			"expires_in_seconds": 93784,
			"issued_at_local": "2026-01-04 10:00:00 PST",
			"issued_at_utc": "2026-01-04 18:00:00 UTC",
			"cookie_names": ["angel_jwt", "other"],
			"session_file": "/tmp/session.pkl",
		}
		ui.angel_interface = MagicMock(angel_studios_session=session)

		ui.show_auth_details_dialog()

		session.get_session_details.assert_called_once()
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

		session = MagicMock()
		session.get_session_details.side_effect = RuntimeError("boom")
		ui.angel_interface = MagicMock(angel_studios_session=session)

		ui.show_auth_details_dialog()

		dialog.ok.assert_called_once()

	def test_show_auth_details_dialog_non_int_remaining(self, monkeypatch, ui_interface):
		"""Non-int remaining uses fallback formatting branch."""
		ui, _logger, _angel_iface = ui_interface
		dialog = MagicMock()
		monkeypatch.setattr("kodi_ui_interface.xbmcgui.Dialog", MagicMock(return_value=dialog))

		session = MagicMock()
		session.get_session_details.return_value = {
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
		ui.angel_interface = MagicMock(angel_studios_session=session)

		ui.show_auth_details_dialog()

		dialog.textviewer.assert_called_once()
		content = dialog.textviewer.call_args[0][1]
		assert "unknown" in content
