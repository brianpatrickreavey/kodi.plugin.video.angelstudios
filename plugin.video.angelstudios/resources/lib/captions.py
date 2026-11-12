"""Turn on the caption track that matches Kodi's subtitle settings.

Angel's HLS playlist lists the caption tracks and marks each one default off.
Kodi then leaves them off, including when Preferred subtitle language is a
real language. This module applies that preference once, when playback starts.
A change the viewer makes after that is left alone.

Original language and the interface language stay with Kodi. Those two choices
depend on flags this playlist does not set the way Kodi expects.
"""

import json

# How long to wait for InputStream Adaptive to list the caption tracks.
_CAPTION_WAIT_SECONDS = 5
_CAPTION_POLL_SECONDS = 0.2

# Stored values of Settings > Player > Language > Preferred subtitle language.
_LEAVE_TO_KODI = {"original", "default"}
_PREFERENCE_NONE = "none"
_PREFERENCE_FORCED = "forced_only"

# Kodi's player reports many tracks as ISO 639-2. The preference is ISO 639-1.
# convertLanguage covers the rest. These names cover the tracks Angel labels
# in English when that conversion returns nothing.
_FALLBACK_LANGUAGE = {
    "eng": "en",
    "english": "en",
    "spa": "es",
    "spanish": "es",
    "por": "pt",
    "portuguese": "pt",
}


def kodi_convert_language(value):
    """Return an ISO 639-1 code for a Kodi language value, or an empty string."""
    if not isinstance(value, str):
        return ""
    text = value.strip()
    if not text:
        return ""
    converted = ""
    try:
        import xbmc  # type: ignore

        result = xbmc.convertLanguage(text, xbmc.ISO_639_1)
        if isinstance(result, str):
            converted = result.strip().lower()
    except Exception:
        converted = ""
    if converted:
        return converted
    primary = text.split("-", 1)[0].strip().lower()
    if len(primary) == 2 and primary.isalpha():
        return primary
    return _FALLBACK_LANGUAGE.get(primary, "")


def language_keys(value, convert_language):
    """Return the comparable forms of a language code or a track name."""
    if not isinstance(value, str):
        return set()
    text = value.strip()
    if not text:
        return set()
    keys = set()
    lowered = text.lower()
    primary = lowered.split("-", 1)[0].strip()
    name = lowered.split("(", 1)[0].strip()
    for candidate in (lowered, primary, name):
        if candidate:
            keys.add(candidate)
        converted = _converted(candidate, convert_language)
        if converted:
            keys.add(converted)
    return keys


def choose_caption_track(preference, tracks, prefer_hearing_impaired, audio_language, convert_language):
    """Return the caption action for the start of playback.

    None means leave Kodi's choice in place.
    {"wait": True} means the track list is not ready.
    {"enable": False} means captions off.
    {"enable": True, "index": n} means that track on.
    """
    if not isinstance(preference, str):
        return None
    preference = preference.strip().lower()
    if not preference or preference in _LEAVE_TO_KODI:
        return None

    usable = _usable_tracks(tracks)
    if preference == _PREFERENCE_NONE:
        if not usable:
            return {"wait": True}
        return {"enable": False}
    if preference == _PREFERENCE_FORCED:
        if not usable or not isinstance(audio_language, str) or not audio_language.strip():
            return {"wait": True}
        matches = [
            track
            for track in usable
            if track.get("isforced") is True and _same_language(audio_language, track, convert_language)
        ]
        if not matches:
            return {"enable": False}
        return {"enable": True, "index": _pick(matches, prefer_hearing_impaired)["index"]}

    if not usable:
        return {"wait": True}
    matches = [
        track
        for track in usable
        if track.get("isforced") is not True and _same_language(preference, track, convert_language)
    ]
    if not matches:
        return {"enable": False}
    return {"enable": True, "index": _pick(matches, prefer_hearing_impaired)["index"]}


def apply_playback_captions(rpc, monitor, log, convert_language, stopped):
    """Apply the caption preference once. A failure leaves playback running."""
    try:
        preference = _setting_value(rpc, "locale.subtitlelanguage")
        hearing = _setting_value(rpc, "accessibility.subhearing") is True
    except Exception as exc:
        log.warning(f"Could not read the preferred subtitle language: {exc}")
        return
    if not isinstance(preference, str) or not preference.strip():
        log.warning("Could not read the preferred subtitle language")
        return

    stored = preference.strip().lower()
    if stored in _LEAVE_TO_KODI:
        log.info(f"Preferred subtitle language is {stored}; Kodi chooses the caption track")
        return

    playerid = None
    logged_tracks = False
    polls = int(_CAPTION_WAIT_SECONDS / _CAPTION_POLL_SECONDS)
    for _ in range(polls):
        if _stop_requested(monitor, stopped):
            return
        try:
            state = _player_captions(rpc)
        except Exception as exc:
            log.warning(f"Could not read the caption tracks: {exc}")
            return
        if state["playerid"] is not None:
            playerid = state["playerid"]
        tracks = state["tracks"]
        if tracks and not logged_tracks:
            log.info("Caption tracks: " + _describe(tracks))
            logged_tracks = True
        choice = choose_caption_track(
            stored,
            tracks,
            hearing,
            state["audio_language"],
            convert_language,
        )
        if choice is None or choice.get("wait"):
            if _stop_requested(monitor, stopped):
                return
            if monitor.waitForAbort(_CAPTION_POLL_SECONDS) is True:
                return
            continue
        _send_choice(rpc, playerid, choice, tracks, log)
        return

    if stored in (_PREFERENCE_NONE, _PREFERENCE_FORCED) and playerid is not None:
        _send_choice(rpc, playerid, {"enable": False}, [], log)
        return
    log.info("No caption tracks in this stream")


def _converted(candidate, convert_language):
    if not candidate:
        return ""
    try:
        converted = convert_language(candidate)
    except Exception:
        return ""
    if isinstance(converted, str):
        return converted.strip().lower()
    return ""


def _usable_tracks(tracks):
    usable = []
    for track in tracks or []:
        if not isinstance(track, dict):
            continue
        index = track.get("index")
        if isinstance(index, bool) or not isinstance(index, int):
            continue
        usable.append(track)
    return usable


def _same_language(wanted, track, convert_language):
    wanted_keys = language_keys(wanted, convert_language)
    track_keys = language_keys(track.get("language"), convert_language)
    name = track.get("name")
    if isinstance(name, str):
        track_keys |= language_keys(name.split("(", 1)[0], convert_language)
    return bool(wanted_keys & track_keys)


def _pick(tracks, prefer_hearing_impaired):
    """Choose one track. A forced track is not the regular track."""
    if prefer_hearing_impaired:
        impaired = [track for track in tracks if track.get("isimpaired") is True]
        if impaired:
            return impaired[0]
    regular = [track for track in tracks if track.get("isimpaired") is not True and track.get("isforced") is not True]
    if regular:
        return regular[0]
    unforced = [track for track in tracks if track.get("isforced") is not True]
    if unforced:
        return unforced[0]
    # forced_only is the caller that still passes forced tracks in.
    return tracks[0]


def _setting_value(rpc, setting):
    result = _rpc(rpc, "Settings.GetSettingValue", {"setting": setting})
    if not isinstance(result, dict) or "value" not in result:
        raise ValueError(setting)
    return result["value"]


def _player_captions(rpc):
    """Return the active video player's caption tracks, or an empty player."""
    players = _rpc(rpc, "Player.GetActivePlayers", {})
    playerid = None
    if isinstance(players, list):
        for player in players:
            if isinstance(player, dict) and player.get("type") == "video":
                playerid = player.get("playerid")
                break
    if not isinstance(playerid, int):
        return {"playerid": None, "tracks": [], "audio_language": ""}
    result = _rpc(
        rpc,
        "Player.GetProperties",
        {"playerid": playerid, "properties": ["subtitles", "currentaudiostream"]},
    )
    if not isinstance(result, dict):
        raise ValueError("Player.GetProperties")
    tracks = result.get("subtitles")
    if not isinstance(tracks, list):
        tracks = []
    audio = result.get("currentaudiostream")
    audio_language = ""
    if isinstance(audio, dict) and isinstance(audio.get("language"), str):
        audio_language = audio["language"]
    return {"playerid": playerid, "tracks": tracks, "audio_language": audio_language}


def _send_choice(rpc, playerid, choice, tracks, log):
    if not isinstance(playerid, int):
        log.warning("Could not set the caption track: the player is not ready")
        return
    if choice.get("enable") is True:
        index = choice["index"]
        params = {"playerid": playerid, "subtitle": index, "enable": True}
        name = _track_name(tracks, index)
        message = f"Captions on: {name}"
    else:
        params = {"playerid": playerid, "subtitle": "off"}
        message = "Captions off"
    try:
        result = _rpc(rpc, "Player.SetSubtitle", params)
    except Exception as exc:
        log.warning(f"Could not set the caption track: {exc}")
        return
    if result != "OK":
        log.warning(f"Could not set the caption track: {result}")
        return
    log.info(message)


def _track_name(tracks, index):
    for track in tracks:
        if isinstance(track, dict) and track.get("index") == index:
            name = track.get("name")
            if isinstance(name, str) and name.strip():
                return name
    return str(index)


def _describe(tracks):
    parts = []
    for track in _usable_tracks(tracks):
        name = track.get("name") if isinstance(track.get("name"), str) else ""
        language = track.get("language") if isinstance(track.get("language"), str) else ""
        label = name.strip() or "Untitled"
        if language.strip():
            label = f"{label} [{language.strip()}]"
        parts.append(label)
    return ", ".join(parts)


def _rpc(rpc, method, params):
    raw = rpc(json.dumps({"jsonrpc": "2.0", "id": 1, "method": method, "params": params}))
    if not isinstance(raw, str):
        raise TypeError("JSON-RPC did not return text")
    payload = json.loads(raw)
    if not isinstance(payload, dict):
        raise ValueError(method)
    if payload.get("error"):
        raise ValueError(payload["error"])
    return payload.get("result")


def _stop_requested(monitor, stopped):
    if monitor.abortRequested() is True:
        return True
    try:
        return stopped() is True
    except Exception:
        return False
