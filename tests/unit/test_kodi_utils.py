"""Unit tests for kodi_utils module utilities and logging."""

import sys
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import resources.lib.kodi_utils as kodi_utils


class TestKodiLogger:
    """KodiLogger log level delegation and stack handling."""

    def test_level_methods_delegate_to_xbmclog(self, monkeypatch):
        """Each helper method forwards message and level to xbmclog."""
        logger = kodi_utils.KodiLogger()
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
        xbmc = sys.modules["xbmc"]
        xbmc.log.reset_mock()

        logger = kodi_utils.KodiLogger(debug_promotion=True)

        frame = SimpleNamespace(f_locals={"self": object()})
        stack = [SimpleNamespace(function="outer", frame=frame), SimpleNamespace(function="inner", frame=frame)]
        monkeypatch.setattr(kodi_utils.inspect, "stack", MagicMock(return_value=stack))

        logger.debug("msg")

        assert xbmc.log.call_args[0][1] == xbmc.LOGINFO
        assert "(debug) msg" in xbmc.log.call_args[0][0]

    def test_xbmclog_short_stack_uses_fallback_handler(self, monkeypatch):
        """When stack lacks self, handler defaults to Unknown Handler."""
        xbmc = sys.modules["xbmc"]
        xbmc.log.reset_mock()

        logger = kodi_utils.KodiLogger()

        frame = SimpleNamespace(f_locals={})
        stack = [SimpleNamespace(function="f1", frame=frame), SimpleNamespace(function="f2", frame=frame)]
        monkeypatch.setattr(kodi_utils.inspect, "stack", MagicMock(return_value=stack))

        logger.xbmclog("msg", xbmc.LOGINFO)

        assert any("Handler: Unknown Handler" in str(call.args[0]) for call in xbmc.log.call_args_list)
        assert any("Angel Studios" in str(call.args[0]) for call in xbmc.log.call_args_list)

    def test_xbmclog_with_self_in_stack_reports_handler(self, monkeypatch):
        """Stack with self should log class and function name."""
        xbmc = sys.modules["xbmc"]
        xbmc.log.reset_mock()

        logger = kodi_utils.KodiLogger()

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
        monkeypatch.setattr(kodi_utils.inspect, "stack", MagicMock(return_value=stack))

        logger.xbmclog("msg", xbmc.LOGWARNING)

        assert any("Dummy.target" in str(call.args[0]) for call in xbmc.log.call_args_list)
        assert xbmc.log.call_args_list[-1].args[1] == xbmc.LOGWARNING


class TestSessionHelpers:
    """Session file utilities coverage."""

    def test_get_session_file_creates_dir(self, monkeypatch):
        """Creates cache directory when missing and returns session path."""
        xbmcvfs = sys.modules["xbmcvfs"]
        xbmcvfs.exists.return_value = False
        xbmcvfs.translatePath.return_value = "/tmp/cache/"
        xbmcvfs.mkdirs.reset_mock()

        addon = MagicMock()
        addon.getAddonInfo.return_value = "plugin.id"
        monkeypatch.setattr(sys.modules["xbmcaddon"], "Addon", MagicMock(return_value=addon))

        path = kodi_utils.get_session_file()

        xbmcvfs.mkdirs.assert_called_once_with("/tmp/cache/")
        assert path.endswith("angel_session.pkl")

    def test_get_session_file_existing_dir(self, monkeypatch):
        """Reuses existing cache directory without creating it."""
        xbmcvfs = sys.modules["xbmcvfs"]
        xbmcvfs.exists.return_value = True
        xbmcvfs.translatePath.return_value = "/tmp/cache/"
        xbmcvfs.mkdirs.reset_mock()

        addon = MagicMock()
        addon.getAddonInfo.return_value = "plugin.id"
        monkeypatch.setattr(sys.modules["xbmcaddon"], "Addon", MagicMock(return_value=addon))

        path = kodi_utils.get_session_file()

        xbmcvfs.mkdirs.assert_not_called()
        assert path == "/tmp/cache/angel_session.pkl"
