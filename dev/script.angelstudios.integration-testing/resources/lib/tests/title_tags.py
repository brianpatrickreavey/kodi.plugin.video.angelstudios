"""Read the watch-page tags Kodi puts on movies, series, and specials.

Nothing is played. A row counts when Kodi returns a plot, a rating label, or a genre.
"""

from listing import directory, plugin_url, public_error, rows, tag_properties, tag_summary
from runner import register

_FOLDERS = (
    ("movies_menu", "Movies"),
    ("series_menu", "Series"),
    ("specials_menu", "Dry Bar Comedy Specials"),
)


@register("title-tags")
def title_tags(kodi):
    """One movie, one series, and one special carry watch-page tags."""
    try:
        found = []
        missing = []
        for action, label in _FOLDERS:
            summary, title = _first_tagged(kodi, action)
            if summary:
                found.append(f"{label}: {title} ({summary})")
            else:
                missing.append(label)
        if missing:
            kodi.check("title-tags", False, "Kodi did not return watch-page tags for " + " ".join(missing) + ".")
            return
        kodi.check("title-tags", True, " ".join(found))
    except Exception as exc:
        kodi.check("title-tags", False, public_error(exc))


def _first_tagged(kodi, action):
    files, error = directory(kodi, plugin_url(action=action), properties=tag_properties())
    if error:
        raise RuntimeError(error)
    for row in rows(files):
        summary = tag_summary(row["item"])
        if summary:
            return summary, row["label"] or "Untitled"
    return "", ""
