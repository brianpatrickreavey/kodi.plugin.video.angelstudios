"""Read caption tracks from an Angel HLS playlist.

A check calls this before playback. The title is played only when the playlist
still matches the case. Signed stream addresses are not included in check text.
"""

import json
import re
from urllib.parse import urljoin
from urllib.request import Request, urlopen

_GRAPHQL = "https://api.angelstudios.com/graphql"
_HI_MARKERS = (
    "transcribes-spoken-dialog",
    "describes-music-and-sound",
    "describes-video",
)
_PROJECT_QUERY = """
query ($slug: String!) {
  project(slug: $slug) {
    seasons {
      episodes {
        guid
        source { url(input: {segmentFormat: TS}) }
      }
    }
  }
}
"""


def subtitle_tracks(text, page_url):
    """Return subtitle media tags and variant playlist addresses from one playlist page."""
    tracks = []
    variants = []
    waiting_for_variant = False
    for raw in text.splitlines():
        line = raw.strip()
        if line.startswith("#EXT-X-MEDIA:") and "TYPE=SUBTITLES" in line:
            tracks.append(_attrs(line))
            waiting_for_variant = False
        elif line.startswith("#EXT-X-STREAM-INF:"):
            waiting_for_variant = True
        elif waiting_for_variant and line and not line.startswith("#"):
            variants.append(urljoin(page_url, line))
            waiting_for_variant = False
        else:
            waiting_for_variant = False
    return tracks, variants


def load_subtitle_tracks(url, fetch):
    """Return subtitle tracks from the master playlist, or from a video rendition."""
    text = fetch(url)
    tracks, variants = subtitle_tracks(text, url)
    if tracks:
        return tracks
    found = []
    for variant in variants[:3]:
        more, _ignored = subtitle_tracks(fetch(variant), variant)
        found.extend(more)
    return found


def source_url(project, guid):
    """Return the stream address for one episode guid, or an empty string."""
    for season in project.get("seasons") or []:
        if not isinstance(season, dict):
            continue
        for episode in season.get("episodes") or []:
            if not isinstance(episode, dict) or episode.get("guid") != guid:
                continue
            source = episode.get("source") or {}
            url = source.get("url") if isinstance(source, dict) else ""
            return url if isinstance(url, str) else ""
    return ""


def tracks_for_episode(slug, guid):
    """Read the live playlist for one Angel episode. Raises RuntimeError with safe text."""
    caught = None
    for _attempt in range(2):
        try:
            project = _project(slug)
            url = source_url(project, guid)
            if not url:
                raise RuntimeError("The title has no playable stream")
            return load_subtitle_tracks(url, _fetch_text)
        except RuntimeError as exc:
            if str(exc) == "The title has no playable stream":
                raise
            caught = exc
        except Exception as exc:
            caught = RuntimeError(f"Could not read the playlist ({type(exc).__name__}).")
    if isinstance(caught, RuntimeError):
        raise caught
    raise RuntimeError("Could not read the playlist.")


def is_impaired(track):
    characteristics = track.get("characteristics") or ""
    return any(marker in characteristics for marker in _HI_MARKERS)


def is_forced(track):
    return (track.get("forced") or "").upper() == "YES"


def language_is(track, code):
    language = (track.get("language") or "").lower()
    return language == code or language.startswith(code + "-")


def has_regular_and_impaired(tracks, code):
    """A regular track and a hearing-impaired track in one language."""
    group = [track for track in tracks if language_is(track, code)]
    regular = [track for track in group if not is_impaired(track) and not is_forced(track)]
    impaired = [track for track in group if is_impaired(track)]
    return bool(regular and impaired)


def has_language(tracks, code):
    return any(language_is(track, code) for track in tracks)


def describe(tracks):
    if not tracks:
        return "No caption tracks."
    parts = []
    for track in tracks:
        label = track.get("name") or track.get("language") or "untitled"
        language = track.get("language") or ""
        flags = []
        if is_impaired(track):
            flags.append("hearing-impaired")
        if is_forced(track):
            flags.append("forced")
        suffix = " " + " ".join(flags) if flags else ""
        parts.append(f"{label} [{language}]{suffix}")
    return "Tracks: " + ", ".join(parts)


def tuttle_case(tracks):
    """Tuttle Twins is the non-forced language case. A forced track changes that case."""
    detail = describe(tracks)
    if any(is_forced(track) for track in tracks):
        return False, "Tuttle Twins now has a forced caption track. " + detail
    missing = [
        name
        for code, name in (("en", "English"), ("es", "Spanish"), ("pt", "Portuguese"))
        if not has_language(tracks, code)
    ]
    if missing:
        return False, "Tuttle Twins is missing " + " and ".join(missing) + ". " + detail
    return True, "Playlist still has English, Spanish, and Portuguese. " + detail


def young_washington_case(tracks):
    detail = describe(tracks)
    if has_regular_and_impaired(tracks, "en"):
        return True, "Playlist still has regular English and English closed captions. " + detail
    return False, (
        "Young Washington no longer has both a regular English track and a hearing-impaired English track. " + detail
    )


def kensuke_case(tracks):
    if tracks:
        return False, "Kensuke's Kingdom now has caption tracks. " + describe(tracks)
    return True, "Playlist still has no caption tracks."


def confirm_playlist(kodi, name, slug, guid, accept):
    """Record the playlist check. Return True when this title is still the right case."""
    try:
        tracks = tracks_for_episode(slug, guid)
    except RuntimeError as exc:
        message = str(exc)
        if "://" in message:
            message = "Could not read the playlist."
        kodi.check(name, False, message)
        return False
    passed, detail = accept(tracks)
    kodi.check(name, passed, detail)
    return passed


def _attrs(line):
    body = line.split(":", 1)[1]
    found = {}
    for match in re.finditer(r'([A-Z0-9-]+)=("[^"]*"|[^,]*)', body):
        value = match.group(2)
        if value.startswith('"') and value.endswith('"'):
            value = value[1:-1]
        found[match.group(1).lower()] = value
    return found


def _fetch_text(url):
    request = Request(url, headers={"User-Agent": "angel-integration"})
    with urlopen(request, timeout=30) as response:
        return response.read().decode("utf-8", errors="replace")


def _project(slug):
    import xbmcaddon  # type: ignore

    token = xbmcaddon.Addon("plugin.video.angelstudios").getSetting("jwt_token")
    if not token:
        raise RuntimeError("Angel is not signed in")
    body = json.dumps({"query": _PROJECT_QUERY, "variables": {"slug": slug}}).encode("utf-8")
    request = Request(
        _GRAPHQL,
        data=body,
        headers={"Content-Type": "application/json", "Authorization": "Bearer " + token},
    )
    with urlopen(request, timeout=30) as response:
        payload = json.loads(response.read().decode("utf-8"))
    if not isinstance(payload, dict) or payload.get("errors"):
        raise RuntimeError("Angel did not return the project")
    project = (payload.get("data") or {}).get("project")
    if not isinstance(project, dict):
        raise RuntimeError("Angel did not return the project")
    return project
