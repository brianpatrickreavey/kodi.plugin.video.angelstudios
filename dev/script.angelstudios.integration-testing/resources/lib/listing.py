"""Read a plugin directory and describe its rows.

These helpers do not decide whether a check passed. The check modules do that.
Nothing here imports xbmc, so the row helpers can be tested without Kodi.
"""

from urllib.parse import parse_qsl, urlencode, urlsplit

PLUGIN = "plugin.video.angelstudios"
ROOT = "plugin://plugin.video.angelstudios/"

_TAG_PROPERTIES = ("title", "genre", "mpaa", "plot", "rating", "year", "duration")


def plugin_url(**params):
    """Return a plugin URL. Empty values are left out."""
    clean = {}
    for key, value in params.items():
        if value is None or value == "":
            continue
        clean[key] = value
    return ROOT + "?" + urlencode(clean)


def video_addon():
    """Return the running video addon."""
    import xbmcaddon  # type: ignore

    return xbmcaddon.Addon(PLUGIN)


def directory(kodi, url, properties=None):
    """Return (files, error). error is empty when Kodi opened the directory."""
    params = {"directory": url, "media": "video"}
    if properties:
        params["properties"] = list(properties)
    try:
        result = kodi.rpc("Files.GetDirectory", params)
    except RuntimeError as exc:
        return None, public_error(exc)
    if not isinstance(result, dict):
        return None, "Kodi did not return a directory."
    files = result.get("files")
    if not isinstance(files, list):
        return None, "Kodi did not return the directory items."
    return files, ""


def tag_properties():
    """Properties that carry watch-page title tags."""
    return list(_TAG_PROPERTIES)


def rows(files):
    """Return the label, action, URL, and raw item for each directory row."""
    parsed = []
    for item in files or []:
        if not isinstance(item, dict):
            continue
        file_url = item.get("file")
        if not isinstance(file_url, str):
            file_url = ""
        params = dict(parse_qsl(urlsplit(file_url).query))
        label = item.get("label")
        parsed.append(
            {
                "label": label if isinstance(label, str) else "",
                "action": params.get("action", ""),
                "file": file_url,
                "params": params,
                "item": item,
            }
        )
    return parsed


def has_entry(parsed, label, action):
    """Return True when one row has this label and action."""
    for row in parsed:
        if row["label"] == label and row["action"] == action:
            return True
    return False


def tag_summary(item):
    """Return the watch-page tags Kodi put on one row, or an empty string."""
    if not isinstance(item, dict):
        return ""
    parts = []
    plot = item.get("plot")
    if isinstance(plot, str) and plot.strip():
        parts.append("plot")
    mpaa = item.get("mpaa")
    if isinstance(mpaa, str) and mpaa.strip():
        parts.append(mpaa.strip())
    genre = item.get("genre")
    names = []
    if isinstance(genre, list):
        names = [name.strip() for name in genre if isinstance(name, str) and name.strip()]
    elif isinstance(genre, str) and genre.strip():
        names = [genre.strip()]
    if names:
        parts.append(" ".join(names))
    rating = item.get("rating")
    if isinstance(rating, (int, float)) and not isinstance(rating, bool) and rating > 0:
        parts.append(f"rating {rating}")
    return " ".join(parts)


def public_error(exc):
    """Return a sentence that does not include a URL, token, or password."""
    text = str(exc)
    lowered = text.lower()
    if "://" in text or "eyj" in lowered or "password" in lowered or "token" in lowered or "bearer" in lowered:
        return f"Kodi check failed ({type(exc).__name__})."
    return f"Kodi check failed ({type(exc).__name__}): {text}"
