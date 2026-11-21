"""Clear the saved token and open Movies.

The username and password stay. The movie menu signs in again before it
builds. The new token is left in place. A failure puts the old token back.
"""

from listing import directory, plugin_url, public_error, video_addon
from runner import register


@register("auth-refresh")
def auth_refresh(kodi):
    """A missing token signs in again before Movies is built."""
    addon = video_addon()
    old = addon.getSettingString("jwt_token")
    try:
        addon.setSettingString("jwt_token", "")
        files, error = directory(kodi, plugin_url(action="movies_menu"))
        new = addon.getSettingString("jwt_token")
        if error:
            kodi.check("auth-refresh", False, "Kodi did not open Movies after the token was cleared. " + error)
            return
        if not isinstance(files, list) or not files:
            kodi.check("auth-refresh", False, "Movies opened with no titles after the token was cleared.")
            return
        if not new or new == old:
            kodi.check("auth-refresh", False, "Movies opened but the cleared token was not replaced.")
            return
        kodi.check("auth-refresh", True, "A cleared token was signed in again before Movies opened.")
    except Exception as exc:
        kodi.check("auth-refresh", False, public_error(exc))
    finally:
        if not addon.getSettingString("jwt_token") and old:
            addon.setSettingString("jwt_token", old)
