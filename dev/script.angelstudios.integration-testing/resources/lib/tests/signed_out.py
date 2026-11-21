"""Sign out, read the main menu, then sign back in.

Force Logout opens an OK dialog. The person has to press OK. The username
and password are written to a recovery file before the logout and deleted
after sign-in works again. The file is not written into the result.
This check is not part of make kodi-test-guild. That run signs in first.
"""

import json
import os

from listing import directory, has_entry, public_error, rows, video_addon
from recovery_file import write_recovery
from runner import register
from tests.sign_in import _refresh

_ROOT = "plugin://plugin.video.angelstudios/"
_RECOVERY = "/tmp/plugin.video.angelstudios.login-recovery.json"


@register("signed-out")
def signed_out(kodi):
    """Guild Voting is absent after logout. Settings is still there."""
    addon = video_addon()
    username = addon.getSettingString("username")
    password = addon.getSettingString("password")
    if (not username or not password) and os.path.exists(_RECOVERY):
        _restore_file(addon)
        kodi.check(
            "signed-out",
            False,
            "The saved login was empty. It was put back from the recovery file. Run this check again.",
        )
        return
    if not username or not password:
        kodi.check("signed-out", False, "There is no saved username and password to sign back in with.")
        return
    _write_recovery(username, password)
    try:
        kodi.notify("Force Logout", "Press OK on Force Logout.", 15000)
        import xbmc  # type: ignore

        xbmc.executebuiltin("RunPlugin(plugin://plugin.video.angelstudios/?action=force_logout)", True)
        if addon.getSettingString("username") or addon.getSettingString("jwt_token"):
            kodi.check("signed-out", False, "Force Logout did not clear the saved login.")
            return
        files, error = directory(kodi, _ROOT)
        if error:
            kodi.check("signed-out", False, "Kodi did not open the main menu after logout. " + error)
            return
        parsed = rows(files)
        if has_entry(parsed, "Guild Voting", "guild_voting_menu"):
            kodi.check("signed-out", False, "Guild Voting was still on the main menu after logout.")
            return
        if not has_entry(parsed, "Settings", "settings"):
            kodi.check("signed-out", False, "Settings was missing after logout.")
            return
        kodi.check("signed-out", True, "Guild Voting was absent. Settings was still there.")
    except Exception as exc:
        kodi.check("signed-out", False, public_error(exc))
    finally:
        _sign_back_in(kodi, addon, username, password)


def _sign_back_in(kodi, addon, username, password):
    restored = False
    try:
        addon.setSettingString("username", username)
        addon.setSettingString("password", password)
        ready, _refreshed = _refresh()
        restored = bool(ready)
    except Exception as exc:
        kodi.check("signed-out-restore", False, public_error(exc))
        return
    if not restored:
        kodi.check("signed-out-restore", False, f"Sign-in was not restored. The recovery file is still {_RECOVERY}.")
        return
    try:
        os.remove(_RECOVERY)
    except OSError:
        pass
    files, error = directory(kodi, _ROOT)
    if error:
        kodi.check("signed-out-restore", False, "Sign-in returned but the main menu did not open. " + error)
        return
    if not has_entry(rows(files), "Guild Voting", "guild_voting_menu"):
        kodi.check("signed-out-restore", False, "Sign-in returned but Guild Voting was still absent.")
        return
    kodi.check("signed-out-restore", True, "Guild Voting is back.")


def _write_recovery(username, password):
    write_recovery(_RECOVERY, username, password)


def _restore_file(addon):
    try:
        with open(_RECOVERY, "r", encoding="utf-8") as handle:
            saved = json.load(handle)
    except (OSError, json.JSONDecodeError):
        return
    if not isinstance(saved, dict):
        return
    username = saved.get("username")
    password = saved.get("password")
    if isinstance(username, str) and username:
        addon.setSettingString("username", username)
    if isinstance(password, str) and password:
        addon.setSettingString("password", password)
