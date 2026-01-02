"""Unit tests for plugin main entrypoint and router."""

import os
import runpy
import sys
from importlib import util
from pathlib import Path
from unittest.mock import MagicMock, patch

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
		paramstring = main.urlencode({"action": action, **extra})

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

		main.router(main.urlencode({"action": "info", "message": "hi"}))

		ui_mock.show_error.assert_called_once_with("hi")

	def test_router_unknown_action(self, monkeypatch):
		"""Unknown action is reported via show_error."""
		main = _fresh_main_module()
		ui_mock = MagicMock()
		monkeypatch.setattr(main, "ui_interface", ui_mock)

		main.router(main.urlencode({"action": "bad"}))

		ui_mock.show_error.assert_called_once()
		assert "Invalid action" in ui_mock.show_error.call_args[0][0]

	def test_router_missing_param(self, monkeypatch):
		"""Missing required params triggers error handling."""
		main = _fresh_main_module()
		ui_mock = MagicMock()
		monkeypatch.setattr(main, "ui_interface", ui_mock)

		main.router(main.urlencode({"action": "seasons_menu", "content_type": "series"}))

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
