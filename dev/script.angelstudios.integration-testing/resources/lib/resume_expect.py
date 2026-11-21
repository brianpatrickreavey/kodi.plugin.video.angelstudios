"""Choose an in-progress title to resume.

This does not call Angel or Kodi. The continue-watching check reads the list.
The resume check plays one title this module picks.
"""

_CONTENT_TYPES = {
    "ContentMovie": "movies",
    "ContentEpisode": "series",
    "ContentSpecial": "specials",
}
# Far enough from the start and the end that a seek is obvious.
_EDGE_SECONDS = 90


def parse_resume(payload):
    """Return the in-progress titles, or None when the response has no list.

    An empty list is a real empty Continue Watching list. None means the read failed.
    """
    if not isinstance(payload, dict):
        return None
    watching = payload.get("resumeWatching")
    if not isinstance(watching, dict):
        return None
    edges = watching.get("edges")
    if not isinstance(edges, list):
        return None
    items = []
    for edge in edges:
        item = _item(edge)
        if item is not None:
            items.append(item)
    return items


def resume_candidate(items):
    """Return the first title a resume seek can prove, or None.

    The position has to be at least 90 seconds in, and at least 90 seconds
    before the end when the duration is known.
    """
    for item in items or []:
        if not isinstance(item, dict):
            continue
        position = item.get("position")
        duration = item.get("duration")
        if not isinstance(position, (int, float)) or isinstance(position, bool):
            continue
        if position < _EDGE_SECONDS:
            continue
        if (
            isinstance(duration, (int, float))
            and not isinstance(duration, bool)
            and position > duration - _EDGE_SECONDS
        ):
            continue
        return item
    return None


def _item(edge):
    if not isinstance(edge, dict):
        return None
    node = edge.get("node")
    if not isinstance(node, dict):
        return None
    content = node.get("content")
    if not isinstance(content, dict):
        return None
    content_type = _CONTENT_TYPES.get(content.get("__typename"))
    project = content.get("project")
    slug = project.get("slug") if isinstance(project, dict) else None
    guid = node.get("watchableGuid")
    position = _seconds(node.get("position"))
    if position is None:
        watch_position = content.get("watchPosition")
        if isinstance(watch_position, dict):
            position = _seconds(watch_position.get("position"))
    if not content_type or not isinstance(slug, str) or not slug:
        return None
    if not isinstance(guid, str) or not guid or position is None:
        return None
    name = content.get("name")
    if not isinstance(name, str) or not name.strip():
        name = project.get("name") if isinstance(project, dict) else ""
    if not isinstance(name, str) or not name.strip():
        name = "Unknown"
    return {
        "guid": guid,
        "name": name.strip(),
        "project_slug": slug,
        "content_type": content_type,
        "position": position,
        "duration": _seconds(content.get("duration")),
    }


def _seconds(value):
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    return None
