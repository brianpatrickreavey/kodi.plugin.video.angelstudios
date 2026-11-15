"""
Kodi Playback Handler for Angel Studios addon.
Handles all Kodi-specific playback operations and stream resolution.
"""

import base64
import json
import queue
import re
import sys
import threading
import time
import urllib.request
from urllib.parse import parse_qs, urlparse

import xbmc  # type: ignore
import xbmcgui  # type: ignore
import xbmcplugin  # type: ignore

from captions import apply_playback_captions, kodi_convert_language
from watch_progress import (
    REPORT_INTERVAL_SECONDS,
    coerce_seconds,
    position_from_episode,
    WatchProgressSession,
)

# Catalog plays ask Resume or Play from beginning. Continue Watching leaves this empty.
_RESUME_CONTENT_TYPES = {"movies", "series", "specials"}

# How long to wait for the stream to start before giving up on progress reports.
_PLAYBACK_START_TIMEOUT = 30
_PLAYBACK_START_POLL = 0.2


# InputStream Adaptive accepts these caps, as width x height. A row is included
# only when both dimensions fit. 360p is not one of them.
_WIDEVINE_CAPS = (
    ("480p", 640, 480),
    ("640p", 960, 640),
    ("720p", 1280, 720),
    ("1080p", 1920, 1080),
)
_RESOLUTION = re.compile(r"RESOLUTION=(\d+)x(\d+)")
_TRACK_TYPE = re.compile(r"[?&]drm_track_type=([^&\s]+)")


def _torch_viewer_quality(addon) -> bool:
    """True when the viewer chose their quality setting for a torch."""
    try:
        return addon.getSettingBool("torch_viewer_quality") is True
    except Exception:
        return False


def _json_segment(token: str):
    parts = token.split(".")
    if len(parts) < 2:
        return None
    segment = parts[1] + "=" * (-len(parts[1]) % 4)
    try:
        data = json.loads(base64.urlsafe_b64decode(segment))
    except Exception:
        return None
    return data if isinstance(data, dict) else None


def _software_track_types(license_url: str) -> set[str]:
    """Playlist track types whose key policy is SW_SECURE_CRYPTO.

    The license URL already carries this. An empty set means the token could
    not be read, so the caller keeps the 720p cap.
    """
    query = parse_qs(urlparse(license_url).query)
    token = (query.get("AxDrmMessage") or [None])[0]
    if not isinstance(token, str):
        return set()
    claims = _json_segment(token)
    if not isinstance(claims, dict):
        return set()
    message = claims.get("message")
    if isinstance(message, str):
        try:
            message = json.loads(message)
        except Exception:
            return set()
    if not isinstance(message, dict):
        return set()
    policies = message.get("content_key_usage_policies")
    if not isinstance(policies, list):
        return set()
    names = set()
    for policy in policies:
        if not isinstance(policy, dict):
            continue
        widevine = policy.get("widevine")
        if not isinstance(widevine, dict):
            continue
        if widevine.get("device_security_level") != "SW_SECURE_CRYPTO":
            continue
        name = policy.get("name")
        if isinstance(name, str) and name.lower().startswith("policy_"):
            names.add(name[7:].lower())
    return names


def _playlist_text(url: str) -> str:
    """The master playlist. Empty when it cannot be read."""
    if not isinstance(url, str) or not url.startswith("https://"):
        return ""
    try:
        with urllib.request.urlopen(url, timeout=10) as response:
            raw = response.read(1_000_001)
    except Exception:
        return ""
    if len(raw) > 1_000_000:
        return ""
    return raw.decode("utf-8", errors="replace")


def _playlist_rows(text: str) -> list[tuple[int, int, str]]:
    """Width, height, and drm_track_type for each HLS video row."""
    rows = []
    pending = None
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("#EXT-X-STREAM-INF"):
            match = _RESOLUTION.search(line)
            pending = (int(match.group(1)), int(match.group(2))) if match else None
            continue
        if pending and line and not line.startswith("#"):
            track = _TRACK_TYPE.search(line)
            rows.append((pending[0], pending[1], track.group(1) if track else ""))
            pending = None
    return rows


def _fits(width: int, height: int, cap_width: int, cap_height: int) -> bool:
    return width <= cap_width and height <= cap_height


def _cap_for_rows(rows, software_tracks, target_height) -> str | None:
    """Chooser value for the highest software row that fits a known cap.

    A fixed quality below that row is kept when a software row still fits it.
    """
    software = [
        (width, height)
        for width, height, track in rows
        if width > 0 and height > 0 and track.lower() in software_tracks
    ]
    if not software:
        return None
    best_width, best_height = max(software, key=lambda row: (row[1], row[0]))
    best_index = None
    for index, (_name, cap_width, cap_height) in enumerate(_WIDEVINE_CAPS):
        if _fits(best_width, best_height, cap_width, cap_height):
            best_index = index
            break
    if best_index is None:
        return None
    chosen = best_index
    if isinstance(target_height, int) and target_height > 0:
        for index, (_name, cap_width, cap_height) in enumerate(_WIDEVINE_CAPS):
            if cap_height > target_height or index > best_index:
                break
            if any(_fits(width, height, cap_width, cap_height) for width, height in software):
                chosen = index
    return _WIDEVINE_CAPS[chosen][0]


def _fallback_widevine_cap(target_height) -> str:
    """720p, or the viewer's lower choice, when the playlist cannot be read."""
    if isinstance(target_height, int) and 0 < target_height < 720:
        return "480p"
    return "720p"


def _software_widevine_cap(license_url: str, stream_url, target_height) -> str:
    """Chooser value for a software CDM. 720p when the ladder cannot be read."""
    tracks = _software_track_types(license_url)
    text = _playlist_text(stream_url) if tracks else ""
    cap = _cap_for_rows(_playlist_rows(text), tracks, target_height) if text else None
    if cap:
        return cap
    return _fallback_widevine_cap(target_height)


def _widevine_license_url(widevine):
    """A license URL that can sit in an InputStream Adaptive property."""
    if not isinstance(widevine, dict):
        return None
    url = widevine.get("license_url")
    if not isinstance(url, str) or not url or "|" in url:
        return None
    return url


def _widevine_certificate_b64(body):
    """The certificate InputStream Adaptive expects, as base64 text."""
    if not isinstance(body, (bytes, bytearray)) or not body:
        return None
    try:
        text = body.decode("ascii")
    except UnicodeDecodeError:
        text = ""
    begin = "-----BEGIN CERTIFICATE-----"
    end = "-----END CERTIFICATE-----"
    if begin in text and end in text:
        inner = text.split(begin, 1)[1].split(end, 1)[0]
        extracted = "".join(inner.split())
        return extracted or None
    return base64.b64encode(bytes(body)).decode("ascii")


def _plugin_play_url():
    """Return the plugin URL Kodi stored for this play.

    argv[0] is plugin://plugin.video.angelstudios/ and argv[2] is the query.
    Kodi stores that full string as the video filename.
    """
    if len(sys.argv) < 3:
        return None
    plugin = sys.argv[0]
    query = sys.argv[2]
    if not isinstance(plugin, str) or not plugin.startswith("plugin://"):
        return None
    if not isinstance(query, str) or not query.startswith("?"):
        return None
    return plugin + query


def _kodi_player_type():
    """Return xbmc.Player when Kodi provides that class.

    Tests replace xbmc with MagicMock. A MagicMock cannot be a base class,
    so the pause and stop callbacks use a small stand-in there.
    """
    player_type = getattr(xbmc, "Player", None)
    if isinstance(player_type, type):
        return player_type

    class _Player:
        def isPlayingVideo(self):
            return False

        def getTime(self):
            return 0

        def seekTime(self, seconds):
            return None

    return _Player


def _accepted_playback_files(player):
    """Return the plugin URL and the resolved stream URL for this play."""
    files = []
    for value in (getattr(player, "expected_file", None), getattr(player, "stream_file", None)):
        if isinstance(value, str) and value and value not in files:
            files.append(value)
    return files


def _is_this_playback(player, accepted_files):
    """Return True when the player is showing the episode this playback requested.

    isPlayingVideo() is already true when another video has not stopped yet.
    After the addon resolves the episode, Kodi may report the plugin URL or the
    stream URL. Either one means this episode is playing.
    """
    if player.isPlayingVideo() is not True:
        return False
    if not accepted_files:
        return True
    getter = getattr(player, "getPlayingFile", None)
    if not callable(getter):
        return False
    try:
        current = getter()
    except Exception:
        return False
    return current in accepted_files


class _OrderedPositionSender:
    """Send watch positions one at a time, in the order they were submitted.

    The playback loop only queues a position. A slow request cannot hold the
    playhead sample, and a stop queued while a heartbeat is in flight is sent
    after that heartbeat, never before it.
    """

    def __init__(self, send):
        self._send = send
        self._queue = queue.Queue()
        self._lock = threading.Lock()
        self._idle = threading.Condition(self._lock)
        self._closed = False
        self._started = False
        self._pending = 0
        self._thread = threading.Thread(target=self._run, name="watch-progress", daemon=True)

    def submit(self, position, event_type):
        with self._lock:
            if self._closed:
                return
            if not self._started:
                self._started = True
                self._thread.start()
            self._pending += 1
            self._queue.put((position, event_type))

    def flush(self):
        """Wait until every position submitted so far has been sent."""
        with self._idle:
            while self._pending:
                self._idle.wait()

    def close(self):
        with self._lock:
            if self._closed:
                started = self._started
            else:
                self._closed = True
                started = self._started
                if started:
                    self._pending += 1
                    self._queue.put(None)
        if started:
            self._thread.join()

    def _run(self):
        while True:
            item = self._queue.get()
            try:
                if item is None:
                    return
                position, event_type = item
                self._send(position, event_type)
            finally:
                with self._idle:
                    self._pending -= 1
                    self._idle.notify_all()


class _WatchProgressPlayer(_kodi_player_type()):
    """Player callbacks for pause and stop. The monitor loop sends the stop position."""

    def __init__(self):
        super().__init__()
        self.stopped = False
        self.ended = False
        self.paused = False
        self.on_pause = None
        self.expected_file = None
        self.stream_file = None
        self.seen_target = False
        self.stop_position = None

    def _ignore_until_this_episode(self):
        """A stop before this episode is seen belongs to the previous video."""
        return bool(_accepted_playback_files(self)) and not self.seen_target

    def onPlayBackPaused(self):
        if self._ignore_until_this_episode():
            return
        self.paused = True
        if self.on_pause is None:
            return
        try:
            position = self.getTime()
        except Exception:
            position = None
        self.on_pause(position)

    def onPlayBackResumed(self):
        self.paused = False

    def _finish(self, ended):
        """Record the playhead, then end the watch. Ignore the previous video's stop."""
        if self._ignore_until_this_episode():
            return
        try:
            self.stop_position = self.getTime()
        except Exception:
            pass
        if ended:
            self.ended = True
        self.stopped = True

    def onPlayBackStopped(self):
        self._finish(False)

    def onPlayBackEnded(self):
        self._finish(True)

    def onPlayBackError(self):
        self._finish(False)


class KodiPlaybackHandler:
    """Handles playback operations and stream resolution for Kodi UI."""

    def __init__(self, parent):
        """
        Initialize the Kodi Playback Handler.
        Takes the parent KodiUIInterface instance for shared state.
        """
        self.parent = parent
        self.handle = parent.handle
        self.kodi_url = parent.kodi_url
        self.log = parent.log

    def play_episode(self, episode_guid, project_slug, content_type="", resume=False):
        """Play an episode using cached project data (no separate API call)."""
        try:
            # First, check if episode is cached (e.g., from Continue Watching)
            episode = self.parent.cache_manager._get_episode(episode_guid)
            if episode:
                self.log.info(f"Using cached episode data for: {episode_guid}")
                # Check for playable source
                source = episode.get("source")
                if not source or not source.get("url"):
                    self.parent.show_error("No playable stream URL found for this episode")
                    self.log.error(f"No stream URL for cached episode: {episode_guid}")
                    return

                episode_name = episode.get("subtitle") or episode.get("name", "Unknown")
                project_name = episode.get("projectSlug", "Unknown")
                self.log.info(
                    f"Playing cached episode: {episode_name} from project: {project_name}"
                )

                # Play using cached episode data
                project = episode.get("project", {"name": episode.get("name", "Unknown")})
                self._start_playback(episode, project, content_type, resume)
                return

            # Fallback: Fetch project data and find episode in it
            project = self.parent._get_project(project_slug)
            if not project:
                self.log.error(f"Project not found: {project_slug}")
                self.parent.show_error(f"Project not found: {project_slug}")
                return

            # Find episode in project seasons
            episode = None
            for season in project.get("seasons", []):
                for ep in season.get("episodes", []):
                    if ep.get("guid") == episode_guid:
                        episode = ep
                        break
                if episode:
                    break

            if not episode:
                self.log.error(f"Episode {episode_guid} not found in project {project_slug}")
                self.parent.show_error(f"Episode not found: {episode_guid}")
                return

            # Check for playable source
            source = episode.get("source")
            if not source or not source.get("url"):
                self.parent.show_error("No playable stream URL found for this episode")
                self.log.error(
                    f"No stream URL for episode: {episode_guid} in project: {project_slug}"
                )
                return

            episode_name = episode.get("subtitle") or episode.get("name", "Unknown")
            project_name = project.get("name", "Unknown")
            self.log.info(f"Playing episode: {episode_name} from project: {project_name}")

            # Play using existing episode data
            self._start_playback(episode, project, content_type, resume)

        except Exception as e:
            self.log.error(f"Error playing episode {episode_guid}: {e}")
            self.parent.show_error(f"Failed to play episode: {str(e)}")

    def _lookup_saved_position(self, episode):
        """Return Angel's saved seconds. A fresh read wins over the copy on the episode."""
        guid = episode.get("guid") if isinstance(episode, dict) else None
        interface = getattr(self.parent, "angel_interface", None)
        getter = getattr(interface, "get_watch_position", None) if interface else None
        if guid and callable(getter):
            try:
                fresh = coerce_seconds(getter(guid))
            except Exception as exc:
                self.log.warning(f"Could not read watch position for {guid}: {exc}")
                fresh = None
            if fresh is not None:
                return fresh
        return position_from_episode(episode)

    def _seek_target(self, content_type, saved_position, resume):
        """Return the seconds to seek to after Kodi's resume dialog.

        resume is true only when that dialog, or the player setting, chose
        Resume. Continue Watching does not seek. Cancel never reaches here.
        """
        if not resume or content_type not in _RESUME_CONTENT_TYPES:
            return None
        if saved_position is None or saved_position < 1:
            return None
        return saved_position

    def _start_playback(self, episode, project, content_type, resume):
        """Resolve the stream, then report progress for this title."""
        saved = self._lookup_saved_position(episode)
        self.play_video(
            episode_data={"episode": episode, "project": project},
            resume_at=self._seek_target(content_type, saved, resume),
            saved_position=saved,
            clear_kodi_stop=content_type in _RESUME_CONTENT_TYPES,
        )

    def _clear_kodi_resume_bookmark(self):
        """Drop the stop Kodi stored for this plugin URL.

        Angel's seconds are the resume time. Kodi also keeps its own stop and
        seeks to that a few seconds after playback starts. This runs before
        setResolvedUrl returns, which is when Kodi reads that stop.
        A failure is logged and playback still starts.
        """
        play_url = _plugin_play_url()
        if not play_url:
            self.log.warning("Could not clear Kodi's stored stop: play URL is missing")
            return
        request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "Files.SetFileDetails",
            "params": {
                "file": play_url,
                "media": "video",
                "resume": {"position": 0, "total": 0},
            },
        }
        try:
            raw = xbmc.executeJSONRPC(json.dumps(request))
            response = json.loads(raw) if isinstance(raw, str) else None
        except Exception as exc:
            self.log.warning(f"Could not clear Kodi's stored stop: {exc}")
            return
        if isinstance(response, dict) and response.get("result") == "OK":
            self.log.info("Cleared Kodi's stored stop")
            return
        self.log.warning(f"Could not clear Kodi's stored stop: {raw}")

    def play_video(
        self,
        stream_url=None,
        episode_data=None,
        resume_at=None,
        saved_position=None,
        clear_kodi_stop=False,
        manifest_type=None,
        widevine=None,
    ):
        """Play a video stream with optional enhanced metadata"""
        if stream_url and episode_data:
            raise ValueError("Provide only stream_url or episode_data, not both")
        if not stream_url and not episode_data:
            raise ValueError("Must provide either stream_url or episode_data to play video")

        list_item = xbmcgui.ListItem(offscreen=True)
        project_slug = None
        guid = None
        player = None

        try:
            if episode_data:
                # Enhanced playback with metadata
                episode = episode_data.get("episode", {})
                project = episode_data.get("project", {})
                project_slug = self._project_slug(project, episode)

                # Create ListItem with metadata using helper
                list_item = self.parent.menu_handler._create_list_item_from_episode(
                    episode=episode, project=project, content_type="", is_playback=True
                )

                episode_name = episode.get("subtitle", "Unknown")
                project_name = project.get("name", "Unknown")
                self.log.info(
                    f"Playing enhanced video: {episode_name} from project: {project_name}"
                )
            elif stream_url:
                # Basic playback (fallback for play_content)
                list_item = xbmcgui.ListItem(offscreen=True)
                list_item.setPath(stream_url)
                list_item.setIsFolder(False)
                list_item.setProperty("IsPlayable", "true")
                list_item.addStreamInfo("video", {"codec": "h264"})
                if manifest_type in ("hls", "mpd"):
                    self._apply_adaptive_manifest(
                        list_item, manifest_type, widevine=widevine, stream_url=stream_url
                    )

                self.log.info("Playing basic video")

            if episode_data and isinstance(episode, dict):
                guid = episode.get("guid") or None
            # Register before Resolve so a video that is already playing is not
            # mistaken for this episode. Its stop must not end the new watch.
            if guid:
                player = _WatchProgressPlayer()
                player.expected_file = _plugin_play_url()
                stream_path = list_item.getPath()
                if isinstance(stream_path, str) and stream_path:
                    player.stream_file = stream_path

            # Drop Kodi's stored stop before Resolve. Kodi reads that bookmark
            # after setResolvedUrl returns and seeks to it a few seconds later.
            if clear_kodi_stop:
                self._clear_kodi_resume_bookmark()

            # Resolve and play
            xbmcplugin.setResolvedUrl(self.handle, True, listitem=list_item)
            if widevine:
                self.log.info("Playing protected stream")
            else:
                self.log.info(f"Playing stream: {list_item.getPath()}")

        except Exception as e:
            self.parent.show_error(f"Error playing video: {e}")
            self.log.error(f"Error playing video: {e}")
            return False

        if not guid:
            return True
        try:
            self._monitor_watch_progress(guid, saved_position, resume_at, project_slug, player)
        except Exception as exc:
            self.log.warning(f"Watch progress stopped for {guid}: {exc}")

    def _project_slug(self, project, episode):
        """Return the slug for the cached project, when this playback has one."""
        slug = project.get("slug") if isinstance(project, dict) else None
        if slug or not isinstance(episode, dict):
            return slug or None
        slug = episode.get("projectSlug")
        if slug:
            return slug
        nested = episode.get("project")
        if isinstance(nested, dict):
            return nested.get("slug") or None
        return None

    def _send_watch_position(
        self, guid, position, session, project_slug=None, event_type="heartbeat"
    ):
        """Send one position. A failure is logged and playback continues."""
        interface = getattr(self.parent, "angel_interface", None)
        sender = getattr(interface, "upsert_watch_position", None) if interface else None
        if not callable(sender):
            self.log.warning(f"Watch position was not saved for {guid}")
            return
        try:
            saved = sender(guid, position, event_type=event_type)
        except Exception as exc:
            self.log.warning(f"Could not save watch position for {guid}: {exc}")
            return
        if saved:
            session.note_saved(position)
            self._remember_saved_position(project_slug, guid, position)

    def _remember_saved_position(self, project_slug, guid, position):
        """Keep the episode-list cache aligned with a position Angel accepted."""
        cache_manager = getattr(self.parent, "cache_manager", None)
        remember = (
            getattr(cache_manager, "remember_watch_position", None) if cache_manager else None
        )
        if not callable(remember):
            return
        try:
            remember(project_slug, guid, position)
        except Exception as exc:
            self.log.warning(f"Could not update the cached resume time for {guid}: {exc}")

    def _apply_captions(self, player, monitor):
        """Turn on the preferred caption track once. Playback continues either way."""
        try:
            apply_playback_captions(
                xbmc.executeJSONRPC,
                monitor,
                self.log,
                kodi_convert_language,
                stopped=lambda: player.stopped is True or player.ended is True,
            )
        except Exception as exc:
            self.log.warning(f"Could not apply the caption preference: {exc}")

    def _monitor_watch_progress(
        self, guid, saved_position, resume_at, project_slug=None, player=None
    ):
        """Report the playhead once a minute, and again on pause or stop.

        This stays on the plugin thread until playback ends. setResolvedUrl has
        already returned the stream to Kodi, so the directory wait is finished.
        The player is created before that resolve when this play has a guid.
        """
        if player is None:
            player = _WatchProgressPlayer()
        monitor = xbmc.Monitor()
        session = WatchProgressSession(saved_position, interval=REPORT_INTERVAL_SECONDS)
        sender = _OrderedPositionSender(
            lambda position, event_type: self._send_watch_position(
                guid, position, session, project_slug, event_type=event_type
            )
        )

        def report_pause(position):
            sample = session.on_pause_or_stop(position)
            if sample is not None:
                sender.submit(sample, "pause")

        player.on_pause = report_pause
        accepted_files = _accepted_playback_files(player)

        try:
            polls = int(_PLAYBACK_START_TIMEOUT / _PLAYBACK_START_POLL)
            started = False
            for _ in range(polls):
                if monitor.abortRequested() is True:
                    return
                if _is_this_playback(player, accepted_files):
                    started = True
                    break
                if monitor.waitForAbort(_PLAYBACK_START_POLL) is True:
                    return
            if not started:
                self.log.info("Playback did not start; watch position was not updated")
                return

            player.seen_target = True
            session.start(time.monotonic())
            if resume_at is not None and resume_at >= 1:
                try:
                    player.seekTime(float(resume_at))
                except Exception as exc:
                    self.log.warning(f"Could not resume at {resume_at}s: {exc}")

            self._apply_captions(player, monitor)

            while True:
                if monitor.abortRequested() is True or player.stopped is True:
                    break
                if not _is_this_playback(player, accepted_files):
                    break
                try:
                    position = player.getTime()
                except Exception:
                    position = session.last_position
                due = session.observe(position, time.monotonic(), paused=player.paused is True)
                if due is not None:
                    sender.submit(due, "heartbeat")
                if monitor.waitForAbort(1) is True:
                    break

            # The heartbeat request has to finish before the stop is chosen.
            # Otherwise a slow save could still be the position Angel keeps.
            sender.flush()
            ending = getattr(player, "stop_position", None)
            sample = session.on_pause_or_stop(
                ending if ending is not None else session.last_position
            )
            if sample is not None:
                # The website uses complete when the video finishes, and stop_exit when the player closes.
                event_type = "complete" if player.ended is True else "stop_exit"
                sender.submit(sample, event_type)
        finally:
            sender.close()

    def _apply_adaptive_manifest(
        self, list_item, manifest_type: str, widevine=None, stream_url=None
    ):
        """Mark a direct stream as HLS or DASH when InputStream Adaptive is on.

        A DRM torch uses InputStream Adaptive even when that setting is off.
        """
        license_url = _widevine_license_url(widevine)
        if license_url is None:
            try:
                use_isa = self.parent.addon.getSettingBool("use_isa") is True
            except Exception:
                use_isa = False
            if not use_isa:
                return
        drm = "widevine" if license_url else None
        isa_ready = self._ensure_isa_available(manifest_type, drm=drm)
        # The addon alone cannot decrypt. A failed Widevine check must not fall through.
        if not isa_ready and not license_url:
            isa_ready = xbmc.getCondVisibility("System.HasAddon(inputstream.adaptive)")
        if not isa_ready:
            return
        quality_pref = self._get_quality_pref()
        quality_mode = quality_pref["mode"]
        target_height = quality_pref["target_height"]
        software_cap = None
        if license_url and not _torch_viewer_quality(self.parent.addon):
            software_cap = _software_widevine_cap(license_url, stream_url, target_height)
            viewer_value = {1080: "1080p", 720: "720p", 480: "480p", 360: "360p"}.get(target_height)
            if quality_mode != "fixed" or viewer_value != software_cap:
                self.log.info(
                    f"Playing this torch at {software_cap}. "
                    "A higher row needs a hardware key."
                )
            quality_mode = "fixed"
        if quality_mode == "manual":
            stream_selection_type = "ask-quality"
        elif quality_mode == "fixed":
            stream_selection_type = "fixed-res"
        else:
            stream_selection_type = "adaptive"
        list_item.setProperty("inputstream", "inputstream.adaptive")
        list_item.setProperty("inputstream.adaptive.manifest_type", manifest_type)
        list_item.setProperty("inputstream.adaptive.stream_selection_type", stream_selection_type)
        if software_cap:
            list_item.setProperty("inputstream.adaptive.chooser_resolution_max", software_cap)
            list_item.setProperty(
                "inputstream.adaptive.chooser_resolution_secure_max", software_cap
            )
        elif isinstance(target_height, int) and quality_mode != "manual":
            chooser_map = {1080: "1080p", 720: "720p", 480: "480p", 360: "360p"}
            chooser_value = chooser_map.get(target_height)
            if chooser_value:
                list_item.setProperty("inputstream.adaptive.chooser_resolution_max", chooser_value)
                list_item.setProperty(
                    "inputstream.adaptive.chooser_resolution_secure_max", chooser_value
                )
        if manifest_type == "hls":
            list_item.setMimeType("application/vnd.apple.mpegurl")
        else:
            list_item.setMimeType("application/dash+xml")
        list_item.setContentLookup(False)
        if license_url:
            list_item.setProperty("inputstream.adaptive.license_type", "com.widevine.alpha")
            # The last field must be R. An empty one leaves the CDM with no key.
            list_item.setProperty(
                "inputstream.adaptive.license_key",
                license_url + "|Content-Type=application%2Foctet-stream|R{SSM}|R",
            )
            certificate = None
            if isinstance(widevine, dict):
                certificate = widevine.get("server_certificate")
            if isinstance(certificate, str) and certificate:
                list_item.setProperty("inputstream.adaptive.server_certificate", certificate)

    def widevine_ready(self, manifest_type: str = "hls") -> bool:
        """True when Widevine can decrypt. Kodi prompts to install it when it is missing."""
        return self._ensure_isa_available(manifest_type, drm="widevine")

    def widevine_certificate(self, url):
        """Base64 certificate for InputStream Adaptive. None when it cannot be read."""
        if not isinstance(url, str) or not url:
            return None
        encoded = None
        try:
            import requests

            response = requests.get(url, timeout=15)
            response.raise_for_status()
            encoded = _widevine_certificate_b64(response.content)
        except Exception:
            encoded = None
        if not encoded:
            self.log.warning("Could not read the Widevine certificate")
            return None
        return encoded

    def install_widevine(self):
        """Settings action. A cancel leaves Kodi's own dialog as the only message."""
        has_helper = xbmc.getCondVisibility("System.HasAddon(script.module.inputstreamhelper)")
        if not has_helper:
            self.parent.show_error("InputStream Helper is not installed.")
            return
        if self.widevine_ready("hls"):
            self.parent.show_notification("Widevine is installed.")

    def _ensure_isa_available(self, manifest_type: str = "hls", drm=None) -> bool:
        """Check if InputStream Adaptive is available (and installed/enabled).

        drm='widevine' asks the helper to install the Widevine library when it is missing.
        """
        has_helper = xbmc.getCondVisibility("System.HasAddon(script.module.inputstreamhelper)")
        has_isa = xbmc.getCondVisibility("System.HasAddon(inputstream.adaptive)")

        if not has_helper:
            if drm == "widevine":
                self.log.info("inputstreamhelper not installed; Widevine cannot be installed")
                return False
            if has_isa:
                self.log.info(
                    "inputstreamhelper not installed; inputstream.adaptive present via System.HasAddon"
                )
            else:
                self.log.info(
                    "inputstreamhelper not installed; inputstream.adaptive not detected; skipping ISA setup"
                )
            return has_isa

        try:
            from inputstreamhelper import Helper  # type: ignore
        except Exception as exc:  # pragma: no cover - defensive
            self.log.warning(f"inputstreamhelper present but import failed: {exc}")
            if drm == "widevine":
                return False
            return has_isa

        try:
            if drm:
                is_helper = Helper(manifest_type, drm=drm)
            else:
                is_helper = Helper(manifest_type)
            result = bool(is_helper.check_inputstream())
            if not result:
                self.log.info("inputstreamhelper check_inputstream returned False; ISA unavailable")
            return result
        except Exception as exc:  # pragma: no cover - defensive
            self.log.warning(f"inputstreamhelper check failed: {exc}")
            if drm == "widevine":
                return False
            return has_isa

    def _get_quality_pref(self):
        """Return dict with 'mode' and 'target_height'. mode in {'auto','fixed','manual'}."""
        try:
            addon = self.parent.addon
            getter = getattr(addon, "getSettingString", None)
            quality_value = (
                getter("video_quality") if callable(getter) else addon.getSetting("video_quality")
            )
        except Exception:
            quality_value = "auto"

        quality_value = (
            (quality_value or "auto").lower() if isinstance(quality_value, str) else "auto"
        )
        mapping = {
            "1080p": {"mode": "fixed", "target_height": 1080},
            "720p": {"mode": "fixed", "target_height": 720},
            "480p": {"mode": "fixed", "target_height": 480},
            "360p": {"mode": "fixed", "target_height": 360},
            "manual": {"mode": "manual", "target_height": None},
            "auto": {"mode": "auto", "target_height": None},
        }
        return mapping.get(quality_value, {"mode": "auto", "target_height": None})
