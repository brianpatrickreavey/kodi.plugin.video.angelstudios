"""Play Tuttle Twins episode 1 and read the caption tracks Kodi reports.

Preferred subtitle language is put back when the check ends. Prefer subtitles
for the hearing impaired is left as it is. This episode has no hearing-impaired
track to compare.
"""

from urllib.parse import urlencode

from playback import start_playback
from playlist import confirm_playlist, tuttle_case
from runner import register

# Tuttle Twins season 1 episode 1. The stream has English, Spanish (Latam),
# and Portuguese captions, none of them marked default or forced.
_EPISODE_GUID = "2f3d0382-ea82-4cdc-958e-84fbadadc710"
_PROJECT_SLUG = "tuttle-twins"
_PLAY_URL = "plugin://plugin.video.angelstudios/?" + urlencode(
    {
        "action": "play_episode",
        "content_type": "series",
        "project_slug": _PROJECT_SLUG,
        "episode_guid": _EPISODE_GUID,
    }
)
_START_SECONDS = 45
_TRACK_SECONDS = 15
_OFF_SECONDS = 3
_LOOK_SECONDS = 60
_LOOK_STEP_SECONDS = 20


def _name(track):
    if not isinstance(track, dict):
        return ""
    name = track.get("name")
    return name.lower() if isinstance(name, str) else ""


def _language(track):
    if not isinstance(track, dict):
        return ""
    language = track.get("language")
    return language.lower() if isinstance(language, str) else ""


def _is_english(track):
    language = _language(track)
    return _name(track).startswith("english") or language in {"en", "eng"} or language.startswith("en-")


def _is_spanish(track):
    language = _language(track)
    return "spanish" in _name(track) or language in {"es", "spa"} or language.startswith("es")


def _is_portuguese(track):
    language = _language(track)
    return "portuguese" in _name(track) or language in {"pt", "por"} or language.startswith("pt")


def _describe(tracks):
    parts = []
    for track in tracks:
        name = track.get("name") if isinstance(track, dict) else ""
        language = track.get("language") if isinstance(track, dict) else ""
        label = name.strip() if isinstance(name, str) and name.strip() else "Untitled"
        if isinstance(language, str) and language.strip():
            label = f"{label} [{language.strip()}]"
        parts.append(label)
    return ", ".join(parts) if parts else "none"


def _play(kodi, preference):
    """Start the episode and return the player once caption tracks are listed."""
    return start_playback(
        kodi,
        _PLAY_URL,
        preference,
        start_seconds=_START_SECONDS,
        track_seconds=_TRACK_SECONDS,
    )


def _tracks_detail(state):
    return "Tracks: " + _describe(state.get("subtitles") or [])


def _tuttle(kodi, body):
    """Play Tuttle Twins for one condition, then put the subtitle language back."""
    if not kodi.gate(
        "tuttle-playlist",
        lambda: confirm_playlist(kodi, "tuttle-playlist", _PROJECT_SLUG, _EPISODE_GUID, tuttle_case),
    ):
        return
    saved = kodi.setting("locale.subtitlelanguage")
    try:
        body()
    finally:
        try:
            kodi.set_setting("locale.subtitlelanguage", saved)
        except Exception as exc:
            kodi.check("restore", False, f"Could not put the subtitle language back: {exc}")
        try:
            kodi.stop()
        except Exception as exc:
            kodi.check("stop", False, f"Could not stop playback: {exc}")


@register("captions-english")
def captions_english(kodi):
    def body():
        state = _started(kodi, "en", "captions-english")
        if state is None:
            return
        on, detail = _english_on(state)
        kodi.check("captions-english", on, detail)
        if kodi.wants_look():
            _ask_for_a_look(kodi, on and state.get("playing"))

    _tuttle(kodi, body)


@register("captions-off")
def captions_off(kodi):
    def body():
        state = _started(kodi, "en", "captions-off")
        if state is None:
            return
        on, detail = _english_on(state)
        if not on or not state.get("playing"):
            kodi.check("captions-off", False, "English was not on, so captions could not be turned off. " + detail)
            return
        kodi.announce("captions-off", "Captions now turn off. Leave the video playing.", 5000)
        try:
            kodi.set_subtitle_off()
        except Exception as exc:
            kodi.check("captions-off", False, f"Could not turn captions off: {exc}")
            return
        stayed = _stays_off(kodi)
        kodi.check("captions-off", stayed, "Captions stayed off" if stayed else "Captions did not stay off")

    _tuttle(kodi, body)


@register("captions-none")
def captions_none(kodi):
    _preference(kodi, "none", "captions-none", enabled=False, words="None. Captions should stay off.")


@register("captions-spanish")
def captions_spanish(kodi):
    _preference(
        kodi,
        "es",
        "captions-spanish",
        enabled=True,
        match=_is_spanish,
        words="Spanish. Spanish captions should be on.",
    )


@register("captions-forced-only")
def captions_forced_only(kodi):
    _preference(
        kodi,
        "forced_only",
        "captions-forced-only",
        enabled=False,
        words="Forced only. Captions should stay off.",
    )


def _started(kodi, preference, name):
    state = _play(kodi, preference)
    if state is None:
        kodi.check(name, False, "Playback did not start, or the stream listed no caption tracks")
    return state


def _english_on(state):
    tracks = state["subtitles"]
    listed = _has_three(tracks)
    on = state["enabled"] and _is_english(state.get("current")) and listed
    detail = _tracks_detail(state)
    if on:
        detail = "English is on. " + detail
    elif not listed:
        detail = "The three caption tracks were not all listed. " + detail
    else:
        detail = "English was not on. " + detail
    return on, detail


def _ask_for_a_look(kodi, showing):
    """Leave English captions on so a person can watch. The script cannot see the words."""
    if showing:
        kodi.hold("captions-english", "Look at the captions. Do the words follow the speech?", _LOOK_SECONDS)
        detail = "Needs a person to confirm the words follow the speech and use Kodi's subtitle font."
    else:
        detail = "English captions were not on, so the picture could not be confirmed."
    kodi.check("on-screen", False, detail, needs_human=True)


def _stays_off(kodi):
    """Return True when captions turn off and stay off."""
    turned_off = kodi.wait(lambda: _is_off(kodi.player()), 5)
    if not turned_off:
        return False
    polls = int(_OFF_SECONDS / 0.5)
    for _ in range(polls):
        state = kodi.player()
        if not state.get("playing") or state.get("enabled") is True:
            return False
        if kodi.monitor.waitForAbort(0.5):
            return False
    return True


def _is_off(state):
    if state.get("playing") and state.get("enabled") is False:
        return state
    return None


def _has_three(tracks):
    return all(any(predicate(track) for track in tracks) for predicate in (_is_english, _is_spanish, _is_portuguese))


def _preference(kodi, preference, name, enabled, match=None, words=""):
    def body():
        state = _started(kodi, preference, name)
        if state is None:
            return
        tracks = state["subtitles"]
        listed = _has_three(tracks)
        current_ok = True if match is None else (state["enabled"] and match(state.get("current")))
        enabled_ok = state["enabled"] is enabled
        passed = listed and enabled_ok and current_ok
        detail = _tracks_detail(state)
        if not listed:
            detail = "The three caption tracks were not all listed. " + detail
        elif not enabled_ok:
            detail = ("Captions were on. " if state["enabled"] else "Captions were off. ") + detail
        elif not current_ok:
            detail = "The current track did not match. " + detail
        kodi.check(name, passed, detail)
        if state.get("playing"):
            kodi.hold(name, words, _LOOK_STEP_SECONDS)

    _tuttle(kodi, body)
