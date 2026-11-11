"""Play Kensuke's Kingdom when its playlist still has no caption tracks.

If captions are added later, the playlist check fails and the movie is not played.
"""

from urllib.parse import urlencode

from playback import move_past_opening, start_without_tracks
from playlist import confirm_playlist, kensuke_case
from runner import register

_GUID = "cfab1162-43bf-40c3-9cb6-6da0f24f083f"
_SLUG = "kensukes-kingdom"
_LOOK_SECONDS = 20
_PLAY_URL = "plugin://plugin.video.angelstudios/?" + urlencode(
    {
        "action": "play_episode",
        "content_type": "movies",
        "project_slug": _SLUG,
        "episode_guid": _GUID,
    }
)


@register("no-captions")
def no_captions(kodi):
    if not kodi.gate(
        "kensuke-playlist", lambda: confirm_playlist(kodi, "kensuke-playlist", _SLUG, _GUID, kensuke_case)
    ):
        return
    saved = kodi.setting("locale.subtitlelanguage")
    try:
        state = start_without_tracks(kodi, _PLAY_URL, "en")
        if state is None:
            kodi.check("no-captions", False, "Playback did not start")
            return
        if not move_past_opening(kodi):
            kodi.check("no-captions", False, "Playback stayed on the opening, so there was no dialog to watch.")
            return
        state = kodi.player()
        tracks = [track for track in (state.get("subtitles") or []) if _named(track)]
        passed = state.get("playing") is True and not tracks
        if passed:
            detail = "The player listed no caption tracks."
        else:
            names = [f"{track.get('name') or ''} [{track.get('language') or ''}]" for track in tracks]
            detail = "The player listed caption tracks. Tracks: " + ", ".join(names)
        kodi.check("no-captions", passed, detail)
        if state.get("playing"):
            kodi.hold("no-captions", "No captions. This movie should offer no caption choice.", _LOOK_SECONDS)
    finally:
        try:
            kodi.set_setting("locale.subtitlelanguage", saved)
        except Exception as exc:
            kodi.check("kensuke-restore", False, f"Could not put the subtitle language back: {exc}")
        try:
            kodi.stop()
        except Exception as exc:
            kodi.check("kensuke-stop", False, f"Could not stop playback: {exc}")


def _named(track):
    return isinstance(track, dict) and bool(track.get("name") or track.get("language"))
