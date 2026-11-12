"""Open the watchlist in Kodi and compare it with Angel.

This does not play video. watchlist-add-remove saves one title that is not
already on the list, then removes that same title. The other checks only read.
The Folders setting is put back when a check that changes it ends.
"""

import os
from urllib.parse import urlencode

from runner import register
from watchlist_expect import directory_rows, list_difference, parse_watchlist, watchlist_menu_rows

_PLUGIN = "plugin.video.angelstudios"
_ROOT = "plugin://plugin.video.angelstudios/"
_WATCHLIST_URL = _ROOT + "?" + urlencode({"action": "watchlist_menu"})
_GRAPHQL = "https://api.angelstudios.com/graphql"
# Tried in this order. A title that is already saved is left alone.
_CANDIDATES = (
    "kensukes-kingdom",
    "young-washington",
    "spy-next-door",
    "tuttle-twins",
)
_PROJECT_QUERY = """
query projectTitle($slug: String!) {
  project(slug: $slug) {
    name
    title {
      __typename
      ... on ContentMovie { id }
      ... on ContentSeries { id }
      ... on ContentSpecial { id }
    }
  }
}
"""


@register("watchlist-hidden")
def watchlist_hidden(kodi):
    """The main menu omits Watchlist while the Folders setting is off."""
    addon = _addon()
    previous = addon.getSettingBool("show_watchlist")
    try:
        addon.setSettingBool("show_watchlist", False)
        files, error = _directory(kodi, _ROOT)
        if error:
            kodi.check("watchlist-hidden", False, "Kodi did not open the main menu. " + error)
            return
        hits = watchlist_menu_rows(files)
        if hits:
            kodi.check("watchlist-hidden", False, "The main menu showed Watchlist while the setting was off.")
            return
        kodi.check("watchlist-hidden", True, "The main menu hid Watchlist.")
    finally:
        addon.setSettingBool("show_watchlist", previous)


@register("watchlist-shown")
def watchlist_shown(kodi):
    """The main menu shows one Watchlist item while the Folders setting is on."""
    addon = _addon()
    previous = addon.getSettingBool("show_watchlist")
    try:
        addon.setSettingBool("show_watchlist", True)
        files, error = _directory(kodi, _ROOT)
        if error:
            kodi.check("watchlist-shown", False, "Kodi did not open the main menu. " + error)
            return
        hits = watchlist_menu_rows(files)
        if len(hits) != 1 or hits[0]["label"] != "Watchlist":
            kodi.check("watchlist-shown", False, f"The main menu showed {len(hits)} Watchlist items.")
            return
        kodi.check("watchlist-shown", True, "The main menu showed Watchlist.")
    finally:
        addon.setSettingBool("show_watchlist", previous)


@register("watchlist-matches")
def watchlist_matches(kodi):
    """The Watchlist folder lists Angel's saved titles, in Angel's order."""
    addon = _addon()
    try:
        expected, error = _saved(addon)
        if error:
            kodi.check("watchlist-matches", False, error)
            return
        files, error = _directory(kodi, _WATCHLIST_URL)
        if error:
            kodi.check("watchlist-matches", False, "Kodi did not open Watchlist. " + error)
            return
        difference = list_difference(directory_rows(files), expected)
        if difference:
            kodi.check("watchlist-matches", False, difference)
            return
        count = len(expected)
        detail = "Watchlist is empty." if count == 0 else f"Watchlist listed {count} titles in Angel's order."
        kodi.check("watchlist-matches", True, detail)
    except Exception as exc:
        kodi.check("watchlist-matches", False, _public(exc))


@register("watchlist-open")
def watchlist_open(kodi):
    """Opening the first saved title leaves the watchlist as it was."""
    addon = _addon()
    try:
        before, error = _saved(addon)
        if error:
            kodi.check("watchlist-open", False, error)
            return
        if not before:
            kodi.check("watchlist-open", True, "The watchlist is empty. There is no title to open.")
            return
        files, error = _directory(kodi, _WATCHLIST_URL)
        if error:
            kodi.check("watchlist-open", False, "Kodi did not open Watchlist. " + error)
            return
        rows = directory_rows(files)
        difference = list_difference(rows, before)
        if difference:
            kodi.check("watchlist-open", False, difference)
            return
        _opened, error = _directory(kodi, rows[0]["file"])
        if error:
            kodi.check("watchlist-open", False, "Kodi did not open the first saved title. " + error)
            return
        after, error = _saved(addon)
        if error:
            kodi.check("watchlist-open", False, error)
            return
        before_ids = [item["content_id"] for item in before]
        after_ids = [item["content_id"] for item in after]
        name = before[0]["name"]
        if after_ids != before_ids:
            kodi.check("watchlist-open", False, f"Opening {name} changed the watchlist.")
            return
        kodi.check("watchlist-open", True, f"Opened {name}. The watchlist stayed the same.")
    except Exception as exc:
        kodi.check("watchlist-open", False, _public(exc))


@register("watchlist-add-remove")
def watchlist_add_remove(kodi):
    """Save one title that is not already saved, then remove that same title."""
    addon = _addon()
    try:
        before, error = _saved(addon)
        if error:
            kodi.check("watchlist-add-remove", False, error)
            return
        saved = {item["content_id"] for item in before}
        candidate, error = _candidate(addon, saved)
        if error:
            kodi.check("watchlist-add-remove", False, error)
            return
        if candidate is None:
            kodi.check(
                "watchlist-add-remove",
                True,
                "Every candidate title is already saved. This run did not change the watchlist.",
            )
            return
    except Exception as exc:
        kodi.check("watchlist-add-remove", False, _public(exc))
        return

    content_id = candidate["content_id"]
    name = candidate["name"]
    issued = False
    try:
        _run_plugin("add_to_watchlist", content_id)
        issued = True
        if not kodi.wait(lambda: _has(addon, content_id), 30):
            kodi.check("watchlist-add-remove", False, f"Kodi did not add {name}.")
            return
        _run_plugin("remove_from_watchlist", content_id)
        if not kodi.wait(lambda: _lacks(addon, content_id), 30):
            kodi.check("watchlist-add-remove", False, f"Kodi did not remove {name}.")
            return
        kodi.check("watchlist-add-remove", True, f"Added {name} and then removed it.")
    finally:
        if issued:
            try:
                still_there = _has(addon, content_id)
            except Exception:
                still_there = True
            if still_there:
                _run_plugin("remove_from_watchlist", content_id)
                if not kodi.wait(lambda: _lacks(addon, content_id), 30):
                    kodi.check("watchlist-add-remove", False, f"{name} is still on the watchlist.")


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


def _saved(addon):
    """Return (titles, error) from Angel. titles is None only with an error."""
    token, profile = _token_and_profile(addon)
    if not token or not profile:
        return None, "Angel sign-in did not produce a usable token."
    data = _post(token, profile, _watchlist_query(addon))
    saved = parse_watchlist(data)
    if saved is None:
        return None, "Angel did not return the watchlist."
    return saved, ""


def _has(addon, content_id):
    saved, error = _saved(addon)
    if error or saved is None:
        return False
    return any(item["content_id"] == content_id for item in saved)


def _lacks(addon, content_id):
    saved, error = _saved(addon)
    if error or saved is None:
        return False
    return all(item["content_id"] != content_id for item in saved)


def _candidate(addon, saved_ids):
    """Return ({content_id, name}, error). None means every candidate is saved."""
    token, profile = _token_and_profile(addon)
    if not token or not profile:
        return None, "Angel sign-in did not produce a usable token."
    for slug in _CANDIDATES:
        data = _post(token, profile, _PROJECT_QUERY, {"slug": slug})
        project = data.get("project") if isinstance(data, dict) else None
        title = project.get("title") if isinstance(project, dict) else None
        content_id = title.get("id") if isinstance(title, dict) else None
        if not isinstance(content_id, str) or not content_id or content_id in saved_ids:
            continue
        name = project.get("name") if isinstance(project, dict) else ""
        if not isinstance(name, str) or not name:
            name = slug
        return {"content_id": content_id, "name": name}, ""
    return None, ""


def _run_plugin(action, content_id):
    import xbmc  # type: ignore

    url = _ROOT + "?" + urlencode({"action": action, "content_id": content_id})
    xbmc.executebuiltin("RunPlugin(" + url + ")")


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


def _watchlist_query(addon):
    import xbmcvfs  # type: ignore

    root = xbmcvfs.translatePath(addon.getAddonInfo("path"))
    path = os.path.join(root, "resources", "lib", "angel_graphql", "query_getMyDefaultWatchList.graphql")
    with open(path, "r", encoding="utf-8") as handle:
        return handle.read()


def _post(token, profile, query, variables=None):
    import requests

    response = requests.post(
        _GRAPHQL,
        json={"operationName": _operation_name(query), "query": query, "variables": variables or {}},
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
    for word in query.split():
        if word in ("getMyDefaultWatchList", "projectTitle"):
            return word
    return "projectTitle"


def _public(exc):
    text = str(exc)
    lowered = text.lower()
    if "://" in text or "eyj" in lowered or "password" in lowered or "token" in lowered or "bearer" in lowered:
        return f"Watchlist check failed ({type(exc).__name__})."
    return f"Watchlist check failed ({type(exc).__name__}): {text}"
