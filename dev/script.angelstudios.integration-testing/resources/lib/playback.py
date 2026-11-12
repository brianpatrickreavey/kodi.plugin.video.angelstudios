"""Start one plugin URL and wait until Kodi is playing it."""

_DIALOG_SECONDS = 180


def start_playback(kodi, url, preference, start_seconds=45, track_seconds=15):
    """Return the player once caption tracks are listed."""
    kodi.set_setting("locale.subtitlelanguage", preference)
    kodi.stop()
    kodi.wait(lambda: None, 1)
    kodi.open_video(url)
    started = kodi.wait(lambda: kodi.player()["playing"], start_seconds)
    if not started:
        return None
    appeared = kodi.wait(lambda: _with_tracks(kodi.player()), track_seconds)
    if not appeared:
        return None
    kodi.wait(lambda: None, 2)
    state = kodi.player()
    if state.get("playing") and state.get("subtitles"):
        return state
    return None


def start_without_tracks(kodi, url, preference, start_seconds=45, empty_seconds=6):
    """Return the player after it has had time to list captions."""
    kodi.set_setting("locale.subtitlelanguage", preference)
    kodi.stop()
    kodi.wait(lambda: None, 1)
    kodi.open_video(url)
    started = kodi.wait(lambda: kodi.player()["playing"], start_seconds)
    if not started:
        return None
    kodi.wait(lambda: None, empty_seconds)
    state = kodi.player()
    if not state.get("playing"):
        return None
    return state


def move_past_opening(kodi, seconds=_DIALOG_SECONDS):
    """Jump past the logos so the picture has dialog. Return False when it stays at the start."""
    if not kodi.seek(seconds):
        return False
    kodi.wait(lambda: None, 2)
    clock = kodi.play_time()
    if clock is None or clock < seconds - 30:
        return False
    return kodi.player().get("playing") is True


def _with_tracks(state):
    if state.get("playing") and state.get("subtitles"):
        return state
    return None
