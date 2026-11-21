"""Read one Angel GraphQL query with the saved token.

The check modules use this. It does not import the video addon as a plugin.
"""

import os

from listing import PLUGIN, public_error

_GRAPHQL = "https://api.angelstudios.com/graphql"


def graphql(query, variables):
    """Return (data, error). error is empty when Angel returned data."""
    try:
        token, profile = _token_and_profile()
    except Exception as exc:
        return None, public_error(exc)
    if not token or not profile:
        return None, "Angel sign-in did not produce a usable token."
    try:
        data = _post(token, profile, query, variables)
    except Exception as exc:
        return None, public_error(exc)
    return data, ""


def _token_and_profile():
    import sys

    import xbmcaddon  # type: ignore
    import xbmcvfs  # type: ignore

    addon = xbmcaddon.Addon(PLUGIN)
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


def _post(token, profile, query, variables):
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
    parts = query.split()
    for index, word in enumerate(parts):
        if word == "query" and index + 1 < len(parts):
            return parts[index + 1].split("(")[0]
    return "query"
