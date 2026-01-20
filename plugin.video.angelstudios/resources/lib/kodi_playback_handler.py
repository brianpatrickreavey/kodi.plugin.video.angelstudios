"""
Kodi Playback Handler for Angel Studios addon.
Handles all Kodi-specific playback operations and stream resolution.
"""

import xbmc  # type: ignore
import xbmcgui  # type: ignore
import xbmcplugin  # type: ignore


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

    def play_episode(self, episode_guid, project_slug):
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
                self.log.info(f"Playing cached episode: {episode_name} from project: {project_name}")

                # Play using cached episode data
                project = episode.get("project", {"name": episode.get("name", "Unknown")})
                self.play_video(episode_data={"episode": episode, "project": project})
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
                self.log.error(f"No stream URL for episode: {episode_guid} in project: {project_slug}")
                return

            episode_name = episode.get("subtitle") or episode.get("name", "Unknown")
            project_name = project.get("name", "Unknown")
            self.log.info(f"Playing episode: {episode_name} from project: {project_name}")

            # Play using existing episode data
            self.play_video(episode_data={"episode": episode, "project": project})

        except Exception as e:
            self.log.error(f"Error playing episode {episode_guid}: {e}")
            self.parent.show_error(f"Failed to play episode: {str(e)}")

    def play_video(self, stream_url=None, episode_data=None):
        """Play a video stream with optional enhanced metadata"""
        if stream_url and episode_data:
            raise ValueError("Provide only stream_url or episode_data, not both")
        if not stream_url and not episode_data:
            raise ValueError("Must provide either stream_url or episode_data to play video")

        list_item = xbmcgui.ListItem(offscreen=True)

        try:
            if episode_data:
                # Enhanced playback with metadata
                episode = episode_data.get("episode", {})
                project = episode_data.get("project", {})

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

            # Resolve and play
            xbmcplugin.setResolvedUrl(self.handle, True, listitem=list_item)
            self.log.info(f"Playing stream: {list_item.getPath()}")

        except Exception as e:
            self.parent.show_error(f"Error playing video: {e}")
            self.log.error(f"Error playing video: {e}")

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
