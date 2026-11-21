"""Show and hide each folder setting, then put the settings back.

Other Content is turned on as well. It does not add a main-menu row.
Top Picks is not opened. That dialog is in docs/dev/manual-tests.md.
"""

from listing import directory, has_entry, public_error, rows, video_addon
from runner import register

_ROOT = "plugin://plugin.video.angelstudios/"
_TOGGLES = (
    ("show_movies", "Movies", "movies_menu"),
    ("show_series", "Series", "series_menu"),
    ("show_specials", "Dry Bar Comedy Specials", "specials_menu"),
    ("show_podcasts", "Podcasts", "podcast_menu"),
    ("show_livestreams", "Livestreams", "livestream_menu"),
    ("show_continue_watching", "Continue Watching", "continue_watching_menu"),
    ("show_top_picks", "Top Picks For You", "top_picks_menu"),
    ("show_watchlist", "Watchlist", "watchlist_menu"),
)


@register("folders-toggles")
def folders_toggles(kodi):
    """Each folder setting shows its row, then hides it."""
    addon = video_addon()
    saved = {}
    for setting, _label, _action in _TOGGLES:
        saved[setting] = addon.getSettingBool(setting)
    saved["show_other_content"] = addon.getSettingBool("show_other_content")
    problems = []
    try:
        for setting, label, action in _TOGGLES:
            problem = _expect(kodi, addon, setting, label, action, True)
            if problem:
                problems.append(problem)
            problem = _expect(kodi, addon, setting, label, action, False)
            if problem:
                problems.append(problem)
        addon.setSettingBool("show_other_content", True)
        parsed, error = _menu(kodi)
        if error:
            problems.append("Kodi did not open the main menu while Other Content was on. " + error)
        elif has_entry(parsed, "Other Content", "") or any(row["label"] == "Other Content" for row in parsed):
            problems.append("Other Content appeared on the main menu.")
    except Exception as exc:
        problems.append(public_error(exc))
    finally:
        for setting, value in saved.items():
            try:
                addon.setSettingBool(setting, bool(value))
            except Exception as exc:
                problems.append(f"Could not put {setting} back. " + public_error(exc))
    if problems:
        kodi.check("folders-toggles", False, " ".join(problems))
        return
    kodi.check(
        "folders-toggles",
        True,
        "Each folder setting showed its row and then hid it. Other Content did not add a row.",
    )


def _expect(kodi, addon, setting, label, action, enabled):
    addon.setSettingBool(setting, enabled)
    parsed, error = _menu(kodi)
    if error:
        state = "on" if enabled else "off"
        return f"Kodi did not open the main menu while {label} was {state}. " + error
    present = has_entry(parsed, label, action)
    if enabled and not present:
        return f"{label} was hidden while {setting} was on."
    if not enabled and present:
        return f"{label} was shown while {setting} was off."
    return ""


def _menu(kodi):
    files, error = directory(kodi, _ROOT)
    if error:
        return None, error
    return rows(files), ""
