"""Open Movies, Series, and Dry Bar Comedy Specials.

Each check opens the folder, then opens the first title. Nothing is played.
"""

from listing import directory, plugin_url, public_error, rows
from runner import register

_FOLDERS = (
    ("catalog-movies", "movies_menu", "Movies"),
    ("catalog-series", "series_menu", "Series"),
    ("catalog-specials", "specials_menu", "Dry Bar Comedy Specials"),
)


def _register_folder(name, action, label):
    def check(kodi):
        _open_folder(kodi, name, action, label)

    check.__name__ = name.replace("-", "_")
    return register(name)(check)


for _name, _action, _label in _FOLDERS:
    _register_folder(_name, _action, _label)


def _open_folder(kodi, name, action, label):
    """The folder lists titles, and the first title opens."""
    try:
        files, error = directory(kodi, plugin_url(action=action))
        if error:
            kodi.check(name, False, f"Kodi did not open {label}. " + error)
            return
        parsed = rows(files)
        title = next((row for row in parsed if row["action"] == "seasons_menu" and row["file"]), None)
        if title is None:
            kodi.check(name, False, f"{label} did not list a title.")
            return
        opened, error = directory(kodi, title["file"])
        if error:
            kodi.check(name, False, f"Kodi did not open {title['label']}. " + error)
            return
        if not rows(opened):
            kodi.check(name, False, f"{title['label']} opened and had no rows.")
            return
        kodi.check(name, True, f"{label} listed {len(parsed)} rows. Opened {title['label']}.")
    except Exception as exc:
        kodi.check(name, False, public_error(exc))
