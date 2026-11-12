"""Refresh Angel sign-in before any play.

Uses the video addon's saved username and password, through the same
AuthenticationCore.ensure_valid_session call the plugin uses on GraphQL.
"""

import base64
import json

from runner import register

_PLUGIN = "plugin.video.angelstudios"


@register("sign-in")
def sign_in(kodi):
    try:
        ready, refreshed = _refresh()
    except Exception as exc:
        kodi.check("sign-in", False, _public(exc))
        return
    if not ready:
        kodi.check("sign-in", False, "Angel sign-in did not produce a usable token.")
        return
    if refreshed:
        kodi.check("sign-in", True, "Angel sign-in was refreshed.")
    else:
        kodi.check("sign-in", True, "Angel sign-in is still valid.")


def _refresh():
    """Return (usable, refreshed). Raises when the plugin cannot sign in."""
    import os
    import sys

    import xbmcaddon  # type: ignore
    import xbmcvfs  # type: ignore

    addon = xbmcaddon.Addon(_PLUGIN)
    root = xbmcvfs.translatePath(addon.getAddonInfo("path"))
    lib = os.path.join(root, "resources", "lib")
    if lib not in sys.path:
        sys.path.insert(0, lib)

    from angel_authentication import AuthenticationCore, Auth0Config, KodiSessionStore

    before = _expiry(KodiSessionStore(addon).get_token())
    core = AuthenticationCore(
        session_store=KodiSessionStore(addon),
        config=Auth0Config(base_url="https://www.angel.com", user_agent=None, request_timeout=30),
        logger=_Log(),
    )
    core.ensure_valid_session()
    token = KodiSessionStore(addon).get_token()
    after = _expiry(token)
    return after is not None, before is None or after > before


def _expiry(token):
    if not isinstance(token, str) or token.count(".") != 2:
        return None
    try:
        payload = token.split(".")[1]
        payload += "=" * (-len(payload) % 4)
        data = json.loads(base64.urlsafe_b64decode(payload))
    except Exception:
        return None
    exp = data.get("exp") if isinstance(data, dict) else None
    if isinstance(exp, bool) or not isinstance(exp, int):
        return None
    return exp


def _public(exc):
    text = str(exc)
    lowered = text.lower()
    if "://" in text or "eyJ" in text or "password" in lowered or "token" in lowered:
        return f"Angel sign-in failed ({type(exc).__name__})."
    return f"Angel sign-in failed ({type(exc).__name__}): {text}"


class _Log:
    """Kodi log that does not record the token or the password."""

    def info(self, message, *args, **kwargs):
        self._write(message)

    def debug(self, message, *args, **kwargs):
        return None

    def warning(self, message, *args, **kwargs):
        self._write(message)

    def error(self, message, *args, **kwargs):
        self._write(message)

    def _write(self, message):
        import xbmc  # type: ignore

        text = str(message)
        lowered = text.lower()
        if "eyJ" in text or "password" in lowered or "://" in text:
            text = "sign-in step"
        xbmc.log("Angel integration " + text, xbmc.LOGINFO)
