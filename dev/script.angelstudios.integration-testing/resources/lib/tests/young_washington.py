"""Play Young Washington when its playlist still has an English caption pair.

The pair is one regular English track and one hearing-impaired English track.
Prefer subtitles for the hearing impaired is put back when the check ends.
"""

from urllib.parse import urlencode

from playback import move_past_opening, start_playback
from playlist import confirm_playlist, young_washington_case
from runner import register

_GUID = "f15945f0-88be-4237-bea6-9b62ee219009"
_SLUG = "young-washington"
_LOOK_SECONDS = 20
_PLAY_URL = "plugin://plugin.video.angelstudios/?" + urlencode(
    {
        "action": "play_episode",
        "content_type": "movies",
        "project_slug": _SLUG,
        "episode_guid": _GUID,
    }
)


@register("hearing-impaired-on")
def hearing_impaired_on(kodi):
    _run(kodi, True, "hearing-impaired-on", "Hearing impaired on. English closed captions should be on.")


@register("hearing-impaired-off")
def hearing_impaired_off(kodi):
    _run(kodi, False, "hearing-impaired-off", "Hearing impaired off. Regular English captions should be on.")


def _run(kodi, hearing, name, words):
    if not kodi.gate(
        "young-washington-playlist",
        lambda: confirm_playlist(kodi, "young-washington-playlist", _SLUG, _GUID, young_washington_case),
    ):
        return
    language = kodi.setting("locale.subtitlelanguage")
    saved_hearing = kodi.setting("accessibility.subhearing")
    try:
        _expect(kodi, hearing, name, words)
    finally:
        _restore(kodi, "locale.subtitlelanguage", language)
        _restore(kodi, "accessibility.subhearing", saved_hearing)
        try:
            kodi.stop()
        except Exception as exc:
            kodi.check("young-washington-stop", False, f"Could not stop playback: {exc}")


def _expect(kodi, hearing, name, words):
    kodi.set_setting("accessibility.subhearing", hearing)
    state = start_playback(kodi, _PLAY_URL, "en")
    if state is None:
        kodi.check(name, False, "Playback did not start, or the stream listed no caption tracks")
        return
    if not move_past_opening(kodi):
        kodi.check(name, False, "Playback stayed on the opening, so there was no dialog to watch.")
        return
    state = kodi.player()
    current = state.get("current") if isinstance(state.get("current"), dict) else {}
    english = _is_english(current)
    impaired = _is_impaired(current)
    forced = _is_forced(current)
    passed = state.get("enabled") is True and english and impaired is hearing and not (forced and not hearing)
    detail = _detail(state)
    if passed:
        detail = ("English closed captions are on. " if hearing else "Regular English is on. ") + detail
    elif forced and not hearing:
        detail = "English Forced Narrative is on. " + detail
    elif not english:
        detail = "The current track is not English. " + detail
    else:
        detail = ("The hearing-impaired track was not on. " if hearing else "The regular track was not on. ") + detail
    kodi.check(name, passed, detail)
    if state.get("playing"):
        kodi.hold(name, words, _LOOK_SECONDS)


def _detail(state):
    parts = []
    for track in state.get("subtitles") or []:
        if not isinstance(track, dict):
            continue
        name = track.get("name") or ""
        language = track.get("language") or ""
        mark = " hearing-impaired" if track.get("isimpaired") is True else ""
        parts.append(f"{name} [{language}]{mark}")
    return "Tracks: " + ", ".join(parts)


def _is_forced(track):
    if track.get("isforced") is True:
        return True
    name = track.get("name") if isinstance(track.get("name"), str) else ""
    return "forced narrative" in name.lower()


def _is_impaired(track):
    flag = track.get("isimpaired")
    if flag is True or flag is False:
        return flag
    name = track.get("name") if isinstance(track.get("name"), str) else ""
    return "closed captions" in name.lower()


def _is_english(track):
    name = track.get("name") if isinstance(track.get("name"), str) else ""
    language = track.get("language") if isinstance(track.get("language"), str) else ""
    language = language.lower()
    return name.lower().startswith("english") or language in {"en", "eng"} or language.startswith("en-")


def _restore(kodi, setting, value):
    try:
        kodi.set_setting(setting, value)
    except Exception as exc:
        kodi.check("young-washington-restore", False, f"Could not put {setting} back: {exc}")
