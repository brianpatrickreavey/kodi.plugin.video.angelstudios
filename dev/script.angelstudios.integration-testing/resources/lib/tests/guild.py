"""Open Guild Voting in Kodi.

guild-menu reads the main menu. guild-list reads the torch folder only when
Angel has at least one torch. Neither check opens a torch or sends a vote.
Angel can name a different torch for a category on the next read, so the
folder check does not compare titles with that read. An empty ballot list
still opens, and its first item is Already voted on. Playback and a real
ballot are in docs/dev/manual-tests.md.
"""

import os
from urllib.parse import urlencode

from guild_expect import directory_rows, folder_problem, menu_problem, parse_member, parse_torches
from runner import register

_PLUGIN = "plugin.video.angelstudios"
_ROOT = "plugin://plugin.video.angelstudios/"
_GUILD_URL = _ROOT + "?" + urlencode({"action": "guild_voting_menu"})
_GRAPHQL = "https://api.angelstudios.com/graphql"


@register("guild-menu")
def guild_menu(kodi):
    """The main menu shows Guild Voting directly above Settings."""
    files, error = _directory(kodi, _ROOT)
    if error:
        kodi.check("guild-menu", False, "Kodi did not open the main menu. " + error)
        return
    problem = menu_problem(directory_rows(files))
    if problem:
        kodi.check("guild-menu", False, problem)
        return
    kodi.check("guild-menu", True, "Guild Voting is directly above Settings.")


@register("guild-list")
def guild_list(kodi):
    """The Guild Voting folder lists torch links and does not open one."""
    addon = _addon()
    try:
        member, error = _member(addon)
        if error:
            kodi.check("guild-list", False, error)
            return
        if member is None:
            kodi.check("guild-list", False, "Angel did not say whether this account is a Guild member.")
            return
        if member is not True:
            kodi.check(
                "guild-list",
                False,
                "This account is not a Guild member. The torch list was not opened.",
            )
            return
        expected, error = _torches(addon)
        if error:
            kodi.check("guild-list", False, error)
            return
        files, error = _directory(kodi, _GUILD_URL)
        if error:
            kodi.check("guild-list", False, "Kodi did not open Guild Voting. " + error)
            return
        rows = directory_rows(files)
        problem = folder_problem(rows)
        if problem:
            kodi.check("guild-list", False, problem)
            return
        if not expected:
            kodi.check(
                "guild-list",
                True,
                "Angel has no torches right now. Guild Voting shows Already voted on.",
            )
            return
        listed = sum(1 for row in rows if row["action"] == "play_torch")
        kodi.check("guild-list", True, f"Guild Voting listed {listed} torches. None were opened.")
    except Exception as exc:
        kodi.check("guild-list", False, _public(exc))


def _addon():
    import xbmcaddon  # type: ignore

    return xbmcaddon.Addon(_PLUGIN)


def _directory(kodi, url):
    """Return (files, error). error is empty when Kodi opened the directory."""
    try:
        result = kodi.rpc("Files.GetDirectory", {"directory": url, "media": "video"})
    except RuntimeError as exc:
        return None, _public(exc)
    if not isinstance(result, dict):
        return None, "Kodi did not return a directory."
    files = result.get("files")
    if not isinstance(files, list):
        return None, "Kodi did not return the directory items."
    return files, ""


def _member(addon):
    """Return (member, error). member is True, False, or None."""
    data, error = _read(addon, "query_guildMemberStatus.graphql")
    if error:
        return None, error
    return parse_member(data), ""


def _torches(addon):
    """Return (torches, error). torches is None only with an error."""
    data, error = _read(addon, "query_getGuildVotingCategories.graphql")
    if error:
        return None, error
    torches = parse_torches(data)
    if torches is None:
        return None, "Angel did not return the Guild Voting list."
    return torches, ""


def _read(addon, filename):
    token, profile = _token_and_profile(addon)
    if not token or not profile:
        return None, "Angel sign-in did not produce a usable token."
    try:
        data = _post(token, profile, _query(addon, filename))
    except Exception as exc:
        return None, _public(exc)
    return data, ""


def _token_and_profile(addon):
    import sys

    import xbmcvfs  # type: ignore

    root = xbmcvfs.translatePath(addon.getAddonInfo("path"))
    lib = os.path.join(root, "resources", "lib")
    if lib not in sys.path:
        sys.path.insert(0, lib)
    from angel_authentication import KodiSessionStore, decode_jwt_payload

    token = KodiSessionStore(addon).get_token()
    if not isinstance(token, str) or not token:
        return None, None
    try:
        payload = decode_jwt_payload(token)
    except Exception:
        return token, None
    profile = payload.get("sub") if isinstance(payload, dict) else None
    if not isinstance(profile, str) or not profile:
        return token, None
    return token, profile


def _query(addon, filename):
    import xbmcvfs  # type: ignore

    root = xbmcvfs.translatePath(addon.getAddonInfo("path"))
    path = os.path.join(root, "resources", "lib", "angel_graphql", filename)
    with open(path, "r", encoding="utf-8") as handle:
        return handle.read()


def _post(token, profile, query):
    import requests

    response = requests.post(
        _GRAPHQL,
        json={"operationName": _operation_name(query), "query": query, "variables": {}},
        headers={
            "Authorization": "Bearer " + token,
            "Content-Type": "application/json",
            "x-viewer-profile-id": profile,
        },
        timeout=30,
    )
    response.raise_for_status()
    body = response.json()
    errors = body.get("errors") if isinstance(body, dict) else None
    if errors:
        message = ""
        if isinstance(errors, list) and errors and isinstance(errors[0], dict):
            message = str(errors[0].get("message") or "")
        raise RuntimeError(message or "Angel returned an error")
    data = body.get("data") if isinstance(body, dict) else None
    if not isinstance(data, dict):
        raise RuntimeError("Angel did not return data")
    return data


def _operation_name(query):
    parts = query.split()
    for index, word in enumerate(parts):
        if word == "query" and index + 1 < len(parts):
            return parts[index + 1].split("(")[0]
    return "getGuildVotingCategories"


def _public(exc):
    text = str(exc)
    lowered = text.lower()
    if "://" in text or "eyj" in lowered or "password" in lowered or "token" in lowered or "bearer" in lowered:
        return f"Guild check failed ({type(exc).__name__})."
    return f"Guild check failed ({type(exc).__name__}): {text}"
