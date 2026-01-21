import xbmc  # type: ignore
import xbmcaddon  # type: ignore
import xbmcvfs  # type: ignore
import os
import inspect
import time


class KodiLogger:
    """Simple logger class to log messages to Kodi log with category-based debug promotion"""

    def __init__(self, promote_all_debug=False, category_promotions=None, uncategorized_promotion=False, miscategorized_promotion=False):
        self.promote_all_debug = promote_all_debug
        self.category_promotions = category_promotions or {}
        self.uncategorized_promotion = uncategorized_promotion
        self.miscategorized_promotion = miscategorized_promotion

    def debug(self, message, category=None):
        """Log debug message with optional category-based promotion to INFO level."""
        # Check promote_all_debug first - overrides everything
        if self.promote_all_debug:
            self.xbmclog(f"(all-debug) {message}", xbmc.LOGINFO)
            return

        # Determine promotion based on category
        if category:
            if category in self.category_promotions:
                is_promoted = self.category_promotions[category]
                prefix = f"({category}-debug)"
            else:
                # Unknown category - use miscategorized promotion
                is_promoted = self.miscategorized_promotion
                prefix = "(misc-debug)"
                self.xbmclog(f"Unknown debug category '{category}' - consider adding setting", xbmc.LOGINFO)
        else:
            # No category - use uncategorized promotion
            is_promoted = self.uncategorized_promotion
            prefix = "(debug)"

        if is_promoted:
            promoted_message = f"{prefix} {message}"
            self.xbmclog(promoted_message, xbmc.LOGINFO)
        else:
            self.xbmclog(message, xbmc.LOGDEBUG)

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


def timed(context_func=None, metrics_func=None):
    """Decorator to time function execution and log if performance logging is enabled.

    Args:
        context_func: Optional function that takes (args, kwargs) and returns a string
                     to append to the log message for additional context.
        metrics_func: Optional function that takes (result, elapsed_ms, args, kwargs)
                     and returns a dict of additional metrics to log.
    """

    def decorator(func):
        def wrapper(*args, **kwargs):
            addon = xbmcaddon.Addon()
            if addon.getSettingBool("enable_performance_logging"):
                start = time.perf_counter()
                result = func(*args, **kwargs)
                elapsed = (time.perf_counter() - start) * 1000  # ms

                context = ""
                if context_func:
                    try:
                        context = f" ({context_func(*args, **kwargs)})"
                    except Exception:
                        context = " (context_error)"

                metrics = ""
                if metrics_func:
                    try:
                        metrics_dict = metrics_func(result, elapsed, *args, **kwargs)
                        if metrics_dict:
                            metrics_parts = []
                            for key, value in metrics_dict.items():
                                if isinstance(value, float):
                                    metrics_parts.append(f"{key}={value:.1f}")
                                else:
                                    metrics_parts.append(f"{key}={value}")
                            metrics = f" ({', '.join(metrics_parts)})"
                    except Exception as e:
                        metrics = f" (metrics_error: {e})"

                xbmc.log(f"[PERF] {func.__name__}{context}{metrics}: {elapsed:.2f}ms", xbmc.LOGINFO)
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
        if addon.getSettingBool("enable_performance_logging"):
            self.start = time.perf_counter()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.start is not None:
            elapsed = (time.perf_counter() - self.start) * 1000  # ms
            xbmc.log(f"[PERF] {self.name}: {elapsed:.2f}ms", xbmc.LOGINFO)
