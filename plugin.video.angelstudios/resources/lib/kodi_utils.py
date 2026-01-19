import xbmc  # type: ignore
import xbmcaddon  # type: ignore
import xbmcvfs  # type: ignore
import os
import inspect
import time


class KodiLogger:
    """Simple logger class to log messages to Kodi log"""

    def __init__(self, debug_promotion=False):
        self.debug_promotion = debug_promotion

    def debug(self, message):
        promoted_message = f"(debug) {message}" if self.debug_promotion else message
        level = xbmc.LOGINFO if self.debug_promotion else xbmc.LOGDEBUG
        self.xbmclog(promoted_message, level)

    def info(self, message):
        self.xbmclog(message, xbmc.LOGINFO)

    def warning(self, message):
        self.xbmclog(message, xbmc.LOGWARNING)

    def error(self, message):
        self.xbmclog(message, xbmc.LOGERROR)

    def critical(self, message):
        self.xbmclog(message, xbmc.LOGFATAL)

    def xbmclog(self, message, level):
        """Log a message to Kodi's log with the specified level"""
        stack = inspect.stack(context=0)
        handler = "Unknown Handler"

        for frame_info in stack[1:]:  # skip xbmclog itself
            module = inspect.getmodule(frame_info.frame)
            module_name = module.__name__ if module else None

            # Skip frames from this helpers module to find the caller
            if module_name and module_name.startswith(__name__):
                continue

            self_obj = frame_info.frame.f_locals.get("self")
            if not self_obj:
                continue

            class_name = self_obj.__class__.__name__
            function_name = frame_info.function

            parts = []
            if module_name:
                parts.append(module_name)
            if class_name:
                parts.append(class_name)
            if function_name:
                parts.append(function_name)

            if parts:
                handler = ".".join(parts)
            break

        xbmc.log(f"Angel Studios: Handler: {handler}: {message}", level)


def get_session_file():
    """Load the session for Angel Studios authentication"""
    addon = xbmcaddon.Addon()
    addon_id = addon.getAddonInfo("id")
    cache_dir = xbmcvfs.translatePath(f"special://profile/addon_data/{addon_id}/")
    if not xbmcvfs.exists(cache_dir):
        xbmcvfs.mkdirs(cache_dir)
    return os.path.join(cache_dir, "angel_session.pkl")


def timed(context_func=None):
    """Decorator to time function execution and log if performance logging is enabled.
    
    Args:
        context_func: Optional function that takes (args, kwargs) and returns a string
                     to append to the log message for additional context.
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            addon = xbmcaddon.Addon()
            if addon.getSettingBool('enable_performance_logging'):
                start = time.perf_counter()
                result = func(*args, **kwargs)
                elapsed = (time.perf_counter() - start) * 1000  # ms
                
                context = ""
                if context_func:
                    try:
                        context = f" ({context_func(*args, **kwargs)})"
                    except Exception:
                        context = " (context_error)"
                
                xbmc.log(f'[PERF] {func.__name__}{context}: {elapsed:.2f}ms', xbmc.LOGINFO)
                return result
            return func(*args, **kwargs)
        return wrapper
    return decorator


class TimedBlock:
    """Context manager to time code blocks and log if performance logging is enabled."""
    def __init__(self, name):
        self.name = name
        self.start = None

    def __enter__(self):
        addon = xbmcaddon.Addon()
        if addon.getSettingBool('enable_performance_logging'):
            self.start = time.perf_counter()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.start is not None:
            elapsed = (time.perf_counter() - self.start) * 1000  # ms
            xbmc.log(f'[PERF] {self.name}: {elapsed:.2f}ms', xbmc.LOGINFO)
