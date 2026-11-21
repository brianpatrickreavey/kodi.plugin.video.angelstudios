"""Clear the cache and the debug data.

Both actions report success in the Kodi log. Neither signs out.
The cache is empty afterward. The next catalog read fills it again.
"""

from listing import PLUGIN, public_error
from runner import register

_CACHE_LINE = "Cache cleared successfully via settings"
_DEBUG_LINE = "Debug data cleared via settings"


@register("clear-cache")
def clear_cache(kodi):
    """Clear cache reports success."""
    _run_action(kodi, "clear-cache", "clear_cache", _CACHE_LINE, "Cache cleared.")


@register("clear-debug")
def clear_debug(kodi):
    """Clear debug data reports success."""
    _run_action(kodi, "clear-debug", "clear_debug_data", _DEBUG_LINE, "Debug data cleared.")


def _run_action(kodi, name, action, phrase, detail):
    try:
        import xbmc  # type: ignore

        before = _log_size()
        xbmc.executebuiltin(f"RunPlugin(plugin://{PLUGIN}/?action={action})", True)
        found = kodi.wait(lambda: phrase in _log_tail(before), 20)
        if kodi.blocking_dialog():
            kodi.check(name, False, "A dialog stayed open after " + detail)
            return
        if not found:
            kodi.check(name, False, "The log did not report success.")
            return
        kodi.check(name, True, detail)
    except Exception as exc:
        kodi.check(name, False, public_error(exc))


def _log_size():
    import os

    import xbmcvfs  # type: ignore

    path = xbmcvfs.translatePath("special://logpath/kodi.log")
    try:
        return os.path.getsize(path)
    except OSError:
        return 0


def _log_tail(before):
    import xbmcvfs  # type: ignore

    path = xbmcvfs.translatePath("special://logpath/kodi.log")
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as handle:
            handle.seek(before)
            return handle.read()
    except OSError:
        return ""
