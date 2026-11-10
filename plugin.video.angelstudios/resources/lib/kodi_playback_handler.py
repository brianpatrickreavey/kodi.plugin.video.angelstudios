"""
Kodi Playback Handler for Angel Studios addon.
Handles all Kodi-specific playback operations and stream resolution.
"""

import json
import queue
import sys
import threading
import time

import xbmc  # type: ignore
import xbmcgui  # type: ignore
import xbmcplugin  # type: ignore

from next_episode import UNAVAILABLE_MESSAGE, NextEpisodeSession, next_play_command
from next_episode_overlay import NextEpisodeOverlay
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

    def play_episode(self, episode_guid, project_slug, content_type="", resume=False, from_beginning=False):
        """Play an episode using cached project data (no separate API call)."""
        if from_beginning:
            resume = False
        try:
            # First, check if episode is cached (e.g., from Continue Watching)
            episode = self.parent.cache_manager._get_episode(episode_guid)
            if episode:
                self.log.info(f"Using cached episode data for: {episode_guid}")
                # Check for playable source
                source = episode.get("source")
                if not source or not source.get("url"):
                    self.parent.show_error(self._unplayable_message(from_beginning))
                    self.log.error(f"No stream URL for cached episode: {episode_guid}")
                    return

                episode_name = episode.get("subtitle") or episode.get("name", "Unknown")
                project_name = episode.get("projectSlug", "Unknown")
                self.log.info(f"Playing cached episode: {episode_name} from project: {project_name}")

                # Play using cached episode data
                project = episode.get("project", {"name": episode.get("name", "Unknown")})
                self._start_playback(episode, project, content_type, resume, from_beginning)
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
                self.parent.show_error(self._unplayable_message(from_beginning))
                self.log.error(f"No stream URL for episode: {episode_guid} in project: {project_slug}")
                return

            episode_name = episode.get("subtitle") or episode.get("name", "Unknown")
            project_name = project.get("name", "Unknown")
            self.log.info(f"Playing episode: {episode_name} from project: {project_name}")

            # Play using existing episode data
            self._start_playback(episode, project, content_type, resume, from_beginning)

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

    def _unplayable_message(self, from_beginning):
        """The next title uses the public unavailable line. A normal play keeps its own."""
        if from_beginning:
            return UNAVAILABLE_MESSAGE
        return "No playable stream URL found for this episode"

    def _start_playback(self, episode, project, content_type, resume, from_beginning=False):
        """Resolve the stream, then report progress for this title."""
        saved = self._lookup_saved_position(episode)
        self.play_video(
            episode_data={"episode": episode, "project": project},
            resume_at=None if from_beginning else self._seek_target(content_type, saved, resume),
            saved_position=saved,
            clear_kodi_stop=bool(from_beginning) or content_type in _RESUME_CONTENT_TYPES,
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
        self, stream_url=None, episode_data=None, resume_at=None, saved_position=None, clear_kodi_stop=False
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
        episode = None
        episode_for_next = None

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
                self.log.info(f"Playing enhanced video: {episode_name} from project: {project_name}")
            elif stream_url:
                # Basic playback (fallback for play_content)
                list_item = xbmcgui.ListItem(offscreen=True)
                list_item.setPath(stream_url)
                list_item.setIsFolder(False)
                list_item.setProperty("IsPlayable", "true")
                list_item.addStreamInfo("video", {"codec": "h264"})

                self.log.info(f"Playing basic video from URL: {stream_url}")

            if episode_data and isinstance(episode, dict):
                guid = episode.get("guid") or None
                episode_for_next = episode
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
            self.log.info(f"Playing stream: {list_item.getPath()}")

        except Exception as e:
            self.parent.show_error(f"Error playing video: {e}")
            self.log.error(f"Error playing video: {e}")
            return

        if not guid:
            return
        try:
            self._monitor_watch_progress(guid, saved_position, resume_at, project_slug, player, episode_for_next)
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

    def _send_watch_position(self, guid, position, session, project_slug=None, event_type="heartbeat"):
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
        remember = getattr(cache_manager, "remember_watch_position", None) if cache_manager else None
        if not callable(remember):
            return
        try:
            remember(project_slug, guid, position)
        except Exception as exc:
            self.log.warning(f"Could not update the cached resume time for {guid}: {exc}")

    def _setting_enabled(self, setting_id):
        """True only for a real True. A missing setting or a test double stays off."""
        addon = getattr(self.parent, "addon", None)
        getter = getattr(addon, "getSettingBool", None) if addon is not None else None
        if not callable(getter):
            return False
        try:
            return getter(setting_id) is True
        except Exception as exc:
            self.log.warning(f"Could not read setting {setting_id}: {exc}")
            return False

    def _load_next_session(self, episode):
        """Read the next title after this episode is actually playing.

        The offer has to be on, and the episode has to be the one we started.
        A slow or failed read must not stop playback or the watch-progress save.
        """
        if not isinstance(episode, dict) or not self._setting_enabled("offer_next_episode"):
            return None
        guid = episode.get("guid")
        if not isinstance(guid, str) or not guid:
            return None
        interface = getattr(self.parent, "angel_interface", None)
        getter = getattr(interface, "get_next_content", None) if interface is not None else None
        if not callable(getter):
            return None
        try:
            content = getter(guid)
            session = NextEpisodeSession(
                episode,
                content,
                offer_enabled=True,
                autostart_enabled=self._setting_enabled("autostart_next_episode"),
            )
        except Exception as exc:
            self.log.warning(f"Could not load the next episode for {guid}: {exc}")
            return None
        if session.target is None:
            self.log.info(f"No next episode for {guid}")
            return None
        self.log.info(f"Next episode is {session.title}")
        return session

    def _open_next_overlay(self, player, next_session):
        """Build the offer. A broken dialog still leaves auto-start able to run."""
        if next_session is None:
            return None
        try:
            return NextEpisodeOverlay(getattr(self.parent, "addon", None), player, self.log)
        except Exception as exc:
            self.log.warning(f"Next Episode offer could not be shown: {exc}")
            return None

    def _close_next_overlay(self, overlay):
        try:
            overlay.close()
        except Exception as exc:
            self.log.warning(f"Next Episode offer could not be closed: {exc}")

    def _start_next_episode(self, target):
        """Open the next title at the beginning. The current episode has already stopped."""
        command = next_play_command(target)
        if not command:
            self.parent.show_error(UNAVAILABLE_MESSAGE)
            return
        self.log.info(f"Starting next episode: {command}")
        try:
            xbmc.executebuiltin(command)
        except Exception as exc:
            self.log.warning(f"Could not start the next episode: {exc}")
            self.parent.show_error(UNAVAILABLE_MESSAGE)

    def _monitor_watch_progress(self, guid, saved_position, resume_at, project_slug=None, player=None, episode=None):
        """Report the playhead once a minute, and again on pause or stop.

        This stays on the plugin thread until playback ends. setResolvedUrl has
        already returned the stream to Kodi, so the directory wait is finished.
        The player is created before that resolve when this play has a guid.
        The next title is loaded after the resume seek, and started only after
        the final watch position has been sent.
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
        next_session = None
        overlay = None
        chosen = False
        aborting = False

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

            next_session = self._load_next_session(episode)
            overlay = self._open_next_overlay(player, next_session)

            while True:
                if monitor.abortRequested() is True:
                    aborting = True
                    break
                if player.stopped is True:
                    break
                if not _is_this_playback(player, accepted_files):
                    break
                try:
                    position = player.getTime()
                except Exception:
                    position = session.last_position
                if overlay is not None and next_session is not None:
                    try:
                        overlay.update(next_session.view_at(position))
                    except Exception as exc:
                        self.log.warning(f"Next Episode offer could not be shown: {exc}")
                        if overlay.chosen is True:
                            chosen = True
                        self._close_next_overlay(overlay)
                        overlay = None
                due = session.observe(position, time.monotonic(), paused=player.paused is True)
                if due is not None:
                    sender.submit(due, "heartbeat")
                if monitor.waitForAbort(1) is True:
                    aborting = True
                    break

            # The heartbeat request has to finish before the stop is chosen.
            # Otherwise a slow save could still be the position Angel keeps.
            sender.flush()
            ending = getattr(player, "stop_position", None)
            sample = session.on_pause_or_stop(ending if ending is not None else session.last_position)
            if sample is not None:
                # The website uses complete when the video finishes, and stop_exit when the player closes.
                event_type = "complete" if player.ended is True else "stop_exit"
                sender.submit(sample, event_type)
        finally:
            if overlay is not None:
                if overlay.chosen is True:
                    chosen = True
                self._close_next_overlay(overlay)
            sender.close()

        # A shutdown, a stop, or a different file must not open another title.
        # Choosing Next Episode is a stop plus an explicit start. Auto-start
        # runs only when the episode itself ends.
        if aborting or next_session is None:
            return
        if next_session.should_start(player.ended is True, chosen):
            player.on_pause = None
            self._start_next_episode(next_session.target)

    def _ensure_isa_available(self, manifest_type: str = "hls") -> bool:
        """Check if InputStream Adaptive is available (and installed/enabled)."""
        has_helper = xbmc.getCondVisibility("System.HasAddon(script.module.inputstreamhelper)")
        has_isa = xbmc.getCondVisibility("System.HasAddon(inputstream.adaptive)")

        if not has_helper:
            if has_isa:
                self.log.info("inputstreamhelper not installed; inputstream.adaptive present via System.HasAddon")
            else:
                self.log.info("inputstreamhelper not installed; inputstream.adaptive not detected; skipping ISA setup")
            return has_isa

        try:
            from inputstreamhelper import Helper  # type: ignore
        except Exception as exc:  # pragma: no cover - defensive
            self.log.warning(f"inputstreamhelper present but import failed: {exc}")
            return has_isa

        try:
            is_helper = Helper(manifest_type)
            result = bool(is_helper.check_inputstream())
            if not result:
                self.log.info("inputstreamhelper check_inputstream returned False; ISA unavailable")
            return result
        except Exception as exc:  # pragma: no cover - defensive
            self.log.warning(f"inputstreamhelper check failed: {exc}")
            return has_isa

    def _get_quality_pref(self):
        """Return dict with 'mode' and 'target_height'. mode in {'auto','fixed','manual'}."""
        try:
            addon = self.parent.addon
            getter = getattr(addon, "getSettingString", None)
            quality_value = getter("video_quality") if callable(getter) else addon.getSetting("video_quality")
        except Exception:
            quality_value = "auto"

        quality_value = (quality_value or "auto").lower() if isinstance(quality_value, str) else "auto"
        mapping = {
            "1080p": {"mode": "fixed", "target_height": 1080},
            "720p": {"mode": "fixed", "target_height": 720},
            "480p": {"mode": "fixed", "target_height": 480},
            "360p": {"mode": "fixed", "target_height": 360},
            "manual": {"mode": "manual", "target_height": None},
            "auto": {"mode": "auto", "target_height": None},
        }
        return mapping.get(quality_value, {"mode": "auto", "target_height": None})
