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

        logger = kodi_utils.KodiLogger(uncategorized_promotion=True)

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

        # Mock currentframe to return None (edge case)
        monkeypatch.setattr(kodi_utils.inspect, "currentframe", MagicMock(return_value=None))

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

        # Create mock frames for the stack walking
        # Frame structure: xbmclog -> _get_caller_info -> caller_frame
        caller_frame = SimpleNamespace(
            f_code=SimpleNamespace(co_filename="test.py", co_name="target"), f_lineno=42, f_locals={"self": Dummy()}
        )

        # Mock currentframe to return a frame that walks to caller_frame
        mock_frame = SimpleNamespace(
            f_back=SimpleNamespace(f_back=caller_frame)  # xbmclog -> _get_caller_info -> caller_frame
        )
        monkeypatch.setattr(kodi_utils.inspect, "currentframe", MagicMock(return_value=mock_frame))

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


class TestKodiLoggerInitialization:
    """Test KodiLogger initialization with different parameters."""

    def test_init_default_values(self):
        """Test default initialization values."""
        logger = kodi_utils.KodiLogger()
        assert logger.promote_all_debug is False
        assert logger.category_promotions == {}
        assert logger.uncategorized_promotion is False
        assert logger.miscategorized_promotion is False
        assert logger._caller_cache == {}

    def test_init_with_parameters(self):
        """Test initialization with custom parameters."""
        category_promotions = {"api": True, "cache": False}
        logger = kodi_utils.KodiLogger(
            promote_all_debug=True,
            category_promotions=category_promotions,
            uncategorized_promotion=True,
            miscategorized_promotion=True,
        )
        assert logger.promote_all_debug is True
        assert logger.category_promotions == category_promotions
        assert logger.uncategorized_promotion is True
        assert logger.miscategorized_promotion is True
        assert logger._caller_cache == {}

    def test_debug_with_promote_all_debug(self):
        """Test debug method with promote_all_debug enabled."""
        xbmc = sys.modules["xbmc"]
        xbmc.log.reset_mock()

        logger = kodi_utils.KodiLogger(promote_all_debug=True)
        logger.debug("test message")

        xbmc.log.assert_called_once()
        assert xbmc.log.call_args[0][1] == xbmc.LOGINFO
        assert "(all-debug) test message" in xbmc.log.call_args[0][0]

    def test_debug_with_category_promotion(self):
        """Test debug method with category-based promotion."""
        xbmc = sys.modules["xbmc"]
        xbmc.log.reset_mock()

        logger = kodi_utils.KodiLogger(category_promotions={"api": True})
        logger.debug("test message", category="api")

        xbmc.log.assert_called_once()
        assert xbmc.log.call_args[0][1] == xbmc.LOGINFO
        assert "(api-debug) test message" in xbmc.log.call_args[0][0]

    def test_debug_with_miscategorized_promotion(self):
        """Test debug method with unknown category and miscategorized promotion."""
        xbmc = sys.modules["xbmc"]
        xbmc.log.reset_mock()

        logger = kodi_utils.KodiLogger(miscategorized_promotion=True)
        logger.debug("test message", category="unknown")

        # Should have two calls: one for the unknown category warning, one for the promoted debug
        assert xbmc.log.call_count == 2
        # Check that the promoted debug message was logged
        debug_calls = [call for call in xbmc.log.call_args_list if "misc-debug" in str(call[0][0])]
        assert len(debug_calls) == 1
        assert debug_calls[0][0][1] == xbmc.LOGINFO

    def test_debug_no_promotion(self):
        """Test debug method without promotion."""
        xbmc = sys.modules["xbmc"]
        xbmc.log.reset_mock()

        logger = kodi_utils.KodiLogger()
        logger.debug("test message")

        xbmc.log.assert_called_once()
        assert xbmc.log.call_args[0][1] == xbmc.LOGDEBUG
        assert "test message" in xbmc.log.call_args[0][0]


class TestKodiLoggerCallerInfo:
    """Test caller info caching and computation."""

    def test_get_caller_info_caching(self, monkeypatch):
        """Test that caller info is cached to improve performance."""
        logger = kodi_utils.KodiLogger()

        # Mock frames
        caller_frame = SimpleNamespace(
            f_code=SimpleNamespace(co_filename="test.py", co_name="test_func"), f_lineno=42, f_locals={"self": self}
        )
        mock_frame = SimpleNamespace(f_back=SimpleNamespace(f_back=caller_frame))

        monkeypatch.setattr(kodi_utils.inspect, "currentframe", MagicMock(return_value=mock_frame))

        # First call should compute and cache
        result1 = logger._get_caller_info()
        assert len(logger._caller_cache) == 1

        # Second call should use cache
        result2 = logger._get_caller_info()
        assert result1 == result2
        assert len(logger._caller_cache) == 1  # Still only one entry

    def test_get_caller_info_cache_limit(self, monkeypatch):
        """Test that cache is limited to prevent memory leaks."""
        logger = kodi_utils.KodiLogger()

        # Fill cache to near limit
        for i in range(999):
            cache_key = f"file{i}.py:{i}"
            logger._caller_cache[cache_key] = f"handler{i}"

        # Mock frames for a new call
        caller_frame = SimpleNamespace(
            f_code=SimpleNamespace(co_filename="new.py", co_name="new_func"), f_lineno=1000, f_locals={"self": self}
        )
        mock_frame = SimpleNamespace(f_back=SimpleNamespace(f_back=caller_frame))

        monkeypatch.setattr(kodi_utils.inspect, "currentframe", MagicMock(return_value=mock_frame))

        # This call should add to cache since we're under limit
        result = logger._get_caller_info()
        assert len(logger._caller_cache) == 1000

        # Add one more to hit the limit
        caller_frame2 = SimpleNamespace(
            f_code=SimpleNamespace(co_filename="new2.py", co_name="new_func2"), f_lineno=1001, f_locals={"self": self}
        )
        mock_frame2 = SimpleNamespace(f_back=SimpleNamespace(f_back=caller_frame2))

        monkeypatch.setattr(kodi_utils.inspect, "currentframe", MagicMock(return_value=mock_frame2))

        result2 = logger._get_caller_info()
        # Cache should still be at limit (not add new entry)
        assert len(logger._caller_cache) == 1000


class TestTimedDecorator:
    """Test the timed decorator functionality."""

    def test_timed_decorator_performance_logging_disabled(self, monkeypatch):
        """Test timed decorator when performance logging is disabled."""
        addon = MagicMock()
        addon.getSettingBool.return_value = False
        monkeypatch.setattr(sys.modules["xbmcaddon"], "Addon", MagicMock(return_value=addon))

        xbmc = sys.modules["xbmc"]
        xbmc.log.reset_mock()

        @kodi_utils.timed()
        def test_func():
            return "result"

        result = test_func()

        assert result == "result"
        xbmc.log.assert_not_called()

    def test_timed_decorator_performance_logging_enabled(self, monkeypatch):
        """Test timed decorator when performance logging is enabled."""
        addon = MagicMock()
        addon.getSettingBool.return_value = True
        monkeypatch.setattr(sys.modules["xbmcaddon"], "Addon", MagicMock(return_value=addon))

        xbmc = sys.modules["xbmc"]
        xbmc.log.reset_mock()

        @kodi_utils.timed()
        def test_func():
            return "result"

        result = test_func()

        assert result == "result"
        xbmc.log.assert_called_once()
        log_message = xbmc.log.call_args[0][0]
        assert "[PERF] test_func:" in log_message
        assert "ms" in log_message

    def test_timed_decorator_with_context_func(self, monkeypatch):
        """Test timed decorator with context function."""
        addon = MagicMock()
        addon.getSettingBool.return_value = True
        monkeypatch.setattr(sys.modules["xbmcaddon"], "Addon", MagicMock(return_value=addon))

        xbmc = sys.modules["xbmc"]
        xbmc.log.reset_mock()

        def context_func(*args, **kwargs):
            return f"context_{args[0] if args else 'none'}"

        @kodi_utils.timed(context_func=context_func)
        def test_func(value):
            return f"result_{value}"

        result = test_func("test")

        assert result == "result_test"
        xbmc.log.assert_called_once()
        log_message = xbmc.log.call_args[0][0]
        assert "[PERF] test_func (context_test):" in log_message

    def test_timed_decorator_with_metrics_func(self, monkeypatch):
        """Test timed decorator with metrics function."""
        addon = MagicMock()
        addon.getSettingBool.return_value = True
        monkeypatch.setattr(sys.modules["xbmcaddon"], "Addon", MagicMock(return_value=addon))

        xbmc = sys.modules["xbmc"]
        xbmc.log.reset_mock()

        def metrics_func(result, elapsed_ms, *args, **kwargs):
            return {"result_len": len(result), "elapsed": elapsed_ms}

        @kodi_utils.timed(metrics_func=metrics_func)
        def test_func():
            return "result"

        result = test_func()

        assert result == "result"
        xbmc.log.assert_called_once()
        log_message = xbmc.log.call_args[0][0]
        assert "[PERF] test_func" in log_message
        assert "result_len=6" in log_message
        assert "elapsed=" in log_message

    def test_timed_decorator_context_func_error(self, monkeypatch):
        """Test timed decorator handles context function errors gracefully."""
        addon = MagicMock()
        addon.getSettingBool.return_value = True
        monkeypatch.setattr(sys.modules["xbmcaddon"], "Addon", MagicMock(return_value=addon))

        xbmc = sys.modules["xbmc"]
        xbmc.log.reset_mock()

        def failing_context_func(*args, **kwargs):
            raise Exception("context error")

        @kodi_utils.timed(context_func=failing_context_func)
        def test_func():
            return "result"

        result = test_func()

        assert result == "result"
        xbmc.log.assert_called_once()
        log_message = xbmc.log.call_args[0][0]
        assert "(context_error)" in log_message

    def test_timed_decorator_metrics_func_error(self, monkeypatch):
        """Test timed decorator handles metrics function errors gracefully."""
        addon = MagicMock()
        addon.getSettingBool.return_value = True
        monkeypatch.setattr(sys.modules["xbmcaddon"], "Addon", MagicMock(return_value=addon))

        xbmc = sys.modules["xbmc"]
        xbmc.log.reset_mock()

        def failing_metrics_func(result, elapsed_ms, *args, **kwargs):
            raise Exception("metrics error")

        @kodi_utils.timed(metrics_func=failing_metrics_func)
        def test_func():
            return "result"

        result = test_func()

        assert result == "result"
        xbmc.log.assert_called_once()
        log_message = xbmc.log.call_args[0][0]
        assert "metrics_error:" in log_message


class TestTimedBlock:
    """Test the TimedBlock context manager."""

    def test_timed_block_performance_logging_disabled(self, monkeypatch):
        """Test TimedBlock when performance logging is disabled."""
        addon = MagicMock()
        addon.getSettingBool.return_value = False
        monkeypatch.setattr(sys.modules["xbmcaddon"], "Addon", MagicMock(return_value=addon))

        xbmc = sys.modules["xbmc"]
        xbmc.log.reset_mock()

        with kodi_utils.TimedBlock("test_block"):
            pass

        xbmc.log.assert_not_called()

    def test_timed_block_performance_logging_enabled(self, monkeypatch):
        """Test TimedBlock when performance logging is enabled."""
        addon = MagicMock()
        addon.getSettingBool.return_value = True
        monkeypatch.setattr(sys.modules["xbmcaddon"], "Addon", MagicMock(return_value=addon))

        xbmc = sys.modules["xbmc"]
        xbmc.log.reset_mock()

        with kodi_utils.TimedBlock("test_block"):
            pass

        xbmc.log.assert_called_once()
        log_message = xbmc.log.call_args[0][0]
        assert "[PERF] test_block:" in log_message
        assert "ms" in log_message
