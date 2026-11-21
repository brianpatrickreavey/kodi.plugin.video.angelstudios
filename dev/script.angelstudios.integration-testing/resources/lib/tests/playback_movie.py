"""Play Kensuke's Kingdom from the start and stop it.

The playlist gate is the same one the no-captions check uses. A dialog,
including a Widevine install question, fails the check. The check does not
answer the dialog. Playback stops either way.
"""

from playback import start_without_tracks
from playlist import confirm_playlist, kensuke_case
from runner import register
from tests.kensuke import _GUID, _PLAY_URL, _SLUG

_LOOK_SECONDS = 20


@register("playback-movie")
def playback_movie(kodi):
    """The movie starts. Kodi does not ask to install Widevine."""
    if not kodi.gate(
        "kensuke-playlist",
        lambda: confirm_playlist(kodi, "kensuke-playlist", _SLUG, _GUID, kensuke_case),
    ):
        return
    saved = kodi.setting("locale.subtitlelanguage")
    try:
        state = start_without_tracks(kodi, _PLAY_URL, "none", empty_seconds=3)
        if kodi.blocking_dialog():
            kodi.check("playback-movie", False, "Kensuke's Kingdom opened a dialog. Playback was stopped.")
            return
        if state is None or not state.get("playing"):
            kodi.check("playback-movie", False, "Kensuke's Kingdom did not start playing.")
            return
        if kodi.wants_look():
            kodi.hold(
                "playback-movie",
                "Look at the picture and listen. Kodi should not ask to install Widevine.",
                _LOOK_SECONDS,
            )
            kodi.check(
                "playback-movie-look",
                True,
                "Needs a person to confirm the picture and the audio.",
                needs_human=True,
            )
        kodi.check(
            "playback-movie",
            True,
            "Kensuke's Kingdom is playing. Kodi did not ask to install Widevine.",
        )
    except Exception as exc:
        kodi.check("playback-movie", False, f"Playback failed ({type(exc).__name__}).")
    finally:
        _restore(kodi, saved)
        try:
            kodi.stop()
        except Exception as exc:
            kodi.check("playback-movie-stop", False, f"Could not stop playback ({type(exc).__name__}).")


def _restore(kodi, language):
    try:
        kodi.set_setting("locale.subtitlelanguage", language)
    except Exception as exc:
        kodi.check(
            "playback-movie-subtitles", False, f"Could not put the subtitle language back ({type(exc).__name__})."
        )
