"""Compare the Kodi watchlist directory with the Angel response.

The Kodi check reads the directory. These functions decide whether that
directory is the same list Angel returned. They do not call Angel or Kodi.
"""

from urllib.parse import parse_qsl, urlsplit

_MENU_TYPES = {
    "ContentMovie": "movies",
    "ContentSeries": "series",
    "ContentSpecial": "specials",
}


def parse_watchlist(payload):
    """Return the saved titles, or None when the response has no list.

    An empty list is a real empty watchlist. None means the read failed.
    """
    if not isinstance(payload, dict):
        return None
    watchlist = payload.get("getMyDefaultWatchList")
    if not isinstance(watchlist, dict):
        return None
    items = watchlist.get("items")
    edges = items.get("edges") if isinstance(items, dict) else None
    if not isinstance(edges, list):
        edges = []
    saved = []
    for edge in edges:
        row = _title(edge)
        if row is not None:
            saved.append(row)
    return saved


def _title(edge):
    if not isinstance(edge, dict):
        return None
    node = edge.get("node")
    if not isinstance(node, dict):
        return None
    content = node.get("content")
    if not isinstance(content, dict):
        return None
    menu_type = _MENU_TYPES.get(content.get("__typename"))
    project = content.get("project")
    slug = project.get("slug") if isinstance(project, dict) else None
    content_id = content.get("id")
    if not menu_type or not isinstance(slug, str) or not slug:
        return None
    if not isinstance(content_id, str) or not content_id:
        return None
    name = content.get("name")
    if not isinstance(name, str) or not name:
        name = "Unknown"
    return {
        "content_id": content_id,
        "name": name,
        "project_slug": slug,
        "menu_content_type": menu_type,
    }


def directory_rows(files):
    """Return the label and query fields for each Kodi directory item."""
    rows = []
    for item in files or []:
        if not isinstance(item, dict):
            continue
        file_url = item.get("file")
        if not isinstance(file_url, str):
            file_url = ""
        params = dict(parse_qsl(urlsplit(file_url).query))
        label = item.get("label")
        rows.append(
            {
                "label": label if isinstance(label, str) else "",
                "action": params.get("action", ""),
                "content_type": params.get("content_type", ""),
                "project_slug": params.get("project_slug", ""),
                "file": file_url,
            }
        )
    return rows


def watchlist_menu_rows(files):
    """Return main-menu rows whose action is the watchlist."""
    return [row for row in directory_rows(files) if row["action"] == "watchlist_menu"]


def list_difference(rows, expected):
    """Return a sentence when the directory is not Angel's list.

    An empty string means the directory matches. The order is Angel's order.
    """
    if len(rows) != len(expected):
        return f"Kodi listed {len(rows)} titles. Angel returned {len(expected)}."
    for index, (row, item) in enumerate(zip(rows, expected), start=1):
        if row["label"] != item["name"]:
            return f"Title {index} is {row['label']!r}. Angel returned {item['name']!r}."
        if row["action"] != "seasons_menu":
            opened = row["action"] or "nothing"
            return f"Title {index} opens {opened} instead of the title page."
        if row["content_type"] != item["menu_content_type"] or row["project_slug"] != item["project_slug"]:
            shown = f"{row['content_type']}/{row['project_slug']}"
            wanted = f"{item['menu_content_type']}/{item['project_slug']}"
            return f"Title {index} opens {shown}. Angel returned {wanted}."
        if "remove_from_watchlist" in row["file"] or "add_to_watchlist" in row["file"]:
            return f"Opening title {index} would change the watchlist."
    return ""
