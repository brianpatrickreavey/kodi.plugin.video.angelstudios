"""Unit tests for helpers module utilities and logging."""

import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, mock_open, patch

import pytest

PLUGIN_ROOT = Path(__file__).resolve().parents[2] / "plugin.video.angelstudios"
sys.path.insert(0, str(PLUGIN_ROOT))

import helpers


class TestKodiLogger:
	"""KodiLogger log level delegation and stack handling."""

	def _set_levels(self):
		"""Populate xbmc log level constants used by helpers."""
		xbmc = sys.modules["xbmc"]
		xbmc.LOGDEBUG = 0
		xbmc.LOGINFO = 1
		xbmc.LOGWARNING = 2
		xbmc.LOGERROR = 3
		xbmc.LOGFATAL = 4

	def test_level_methods_delegate_to_xbmclog(self, monkeypatch):
		"""Each helper method forwards message and level to xbmclog."""
		self._set_levels()
		logger = helpers.KodiLogger()
		with patch.object(logger, "xbmclog") as mock_log:
			logger.debug("d")
			logger.info("i")
			logger.warning("w")
			logger.error("e")
			logger.critical("c")

			calls = [
				("d", sys.modules["xbmc"].LOGDEBUG),
				("i", sys.modules["xbmc"].LOGINFO),
				("w", sys.modules["xbmc"].LOGWARNING),
				("e", sys.modules["xbmc"].LOGERROR),
				("c", sys.modules["xbmc"].LOGFATAL),
			]
			for (msg, level), call in zip(calls, mock_log.call_args_list):
				assert call.args == (msg, level)

	def test_debug_promotion_routes_to_info_with_prefix(self, monkeypatch):
		"""Debug promotion sends debug messages at INFO with prefix."""
		self._set_levels()
		xbmc = sys.modules["xbmc"]
		xbmc.log = MagicMock()
		logger = helpers.KodiLogger(debug_promotion=True)

		frame = SimpleNamespace(f_locals={"self": object()})
		stack = [SimpleNamespace(function="outer", frame=frame), SimpleNamespace(function="inner", frame=frame)]
		monkeypatch.setattr(helpers.inspect, "stack", MagicMock(return_value=stack))

		logger.debug("msg")

		assert xbmc.log.call_args[0][1] == xbmc.LOGINFO
		assert "(debug) msg" in xbmc.log.call_args[0][0]

	def test_xbmclog_short_stack_uses_fallback_handler(self, monkeypatch):
		"""When stack lacks self, handler defaults to Unknown Handler."""
		self._set_levels()
		xbmc = sys.modules["xbmc"]
		xbmc.log = MagicMock()
		logger = helpers.KodiLogger()

		frame = SimpleNamespace(f_locals={})
		stack = [SimpleNamespace(function="f1", frame=frame), SimpleNamespace(function="f2", frame=frame)]
		monkeypatch.setattr(helpers.inspect, "stack", MagicMock(return_value=stack))

		logger.xbmclog("msg", xbmc.LOGINFO)

		assert any("Handler: Unknown Handler" in str(call.args[0]) for call in xbmc.log.call_args_list)
		assert any("Angel Studios" in str(call.args[0]) for call in xbmc.log.call_args_list)

	def test_xbmclog_with_self_in_stack_reports_handler(self, monkeypatch):
		"""Stack with self should log class and function name."""
		self._set_levels()
		xbmc = sys.modules["xbmc"]
		xbmc.log = MagicMock()
		logger = helpers.KodiLogger()

		class Dummy:
			pass

		frame0 = SimpleNamespace(f_locals={})
		frame1 = SimpleNamespace(f_locals={})
		frame2 = SimpleNamespace(f_locals={"self": Dummy()})
		stack = [
			SimpleNamespace(function="f0", frame=frame0),
			SimpleNamespace(function="f1", frame=frame1),
			SimpleNamespace(function="target", frame=frame2),
		]
		monkeypatch.setattr(helpers.inspect, "stack", MagicMock(return_value=stack))

		logger.xbmclog("msg", xbmc.LOGWARNING)

		assert any("Dummy.target" in str(call.args[0]) for call in xbmc.log.call_args_list)
		assert xbmc.log.call_args_list[-1].args[1] == xbmc.LOGWARNING


class TestSessionHelpers:
	"""Session file utilities and plugin URL helper coverage."""

	def test_get_session_file_creates_dir(self, monkeypatch):
		"""Creates cache directory when missing and returns session path."""
		xbmcvfs = sys.modules["xbmcvfs"]
		xbmcvfs.exists.return_value = False
		xbmcvfs.translatePath.return_value = "/tmp/cache/"
		xbmcvfs.mkdirs = MagicMock()
		addon = MagicMock()
		addon.getAddonInfo.return_value = "plugin.id"
		monkeypatch.setattr(sys.modules["xbmcaddon"], "Addon", MagicMock(return_value=addon))

		path = helpers.get_session_file()

		xbmcvfs.mkdirs.assert_called_once_with("/tmp/cache/")
		assert path.endswith("angel_session.pkl")

	def test_get_session_file_existing_dir(self, monkeypatch):
		"""Reuses existing cache directory without creating it."""
		xbmcvfs = sys.modules["xbmcvfs"]
		xbmcvfs.exists.return_value = True
		xbmcvfs.translatePath.return_value = "/tmp/cache/"
		xbmcvfs.mkdirs = MagicMock()
		addon = MagicMock()
		addon.getAddonInfo.return_value = "plugin.id"
		monkeypatch.setattr(sys.modules["xbmcaddon"], "Addon", MagicMock(return_value=addon))

		path = helpers.get_session_file()

		xbmcvfs.mkdirs.assert_not_called()
		assert path == "/tmp/cache/angel_session.pkl"

	def test_get_session_data_missing_file(self, monkeypatch):
		"""Returns None when no session file exists."""
		monkeypatch.setattr(helpers, "get_session_file", MagicMock(return_value="/tmp/session.pkl"))
		xbmcvfs = sys.modules["xbmcvfs"]
		xbmcvfs.exists.return_value = False

		assert helpers.get_session_data() is None

	def test_get_session_data_reads_pickle(self, monkeypatch):
		"""Loads session data from pickle when file is present."""
		monkeypatch.setattr(helpers, "get_session_file", MagicMock(return_value="/tmp/session.pkl"))
		xbmcvfs = sys.modules["xbmcvfs"]
		xbmcvfs.exists.return_value = True
		with (
			patch("builtins.open", mock_open(read_data=b"data")) as m_open,
			patch("pickle.load", return_value={"k": "v"}) as p_load,
		):
			assert helpers.get_session_data() == {"k": "v"}
			m_open.assert_called_once_with("/tmp/session.pkl", "rb")
			p_load.assert_called_once()

	def test_save_session_data_writes_and_logs(self, monkeypatch):
		"""Writes session pickle and logs path."""
		monkeypatch.setattr(helpers, "get_session_file", MagicMock(return_value="/tmp/session.pkl"))
		xbmc = sys.modules["xbmc"]
		xbmc.log = MagicMock()
		with (
			patch("builtins.open", mock_open()) as m_open,
			patch("pickle.dump") as p_dump,
		):
			helpers.save_session_data({"k": "v"})
			m_open.assert_called_once_with("/tmp/session.pkl", "wb")
			p_dump.assert_called_once()
			assert xbmc.log.called

	def test_create_plugin_url(self):
		"""Formats plugin URL with provided query params."""
		assert helpers.create_plugin_url("base", a=1, b="two") == "base?a=1&b=two"
