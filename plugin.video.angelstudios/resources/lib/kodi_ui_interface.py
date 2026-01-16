"""
Kodi UI helper functions for Angel Studios addon.
Handles all Kodi-specific UI operations and list item creation.
"""

import json
import os
import time
from datetime import timedelta
from urllib.parse import urlencode

import xbmc  # type: ignore
import xbmcaddon  # type: ignore
import xbmcgui  # type: ignore
import xbmcplugin  # type: ignore
import xbmcvfs  # type: ignore

from simplecache import SimpleCache  # type: ignore

REDACTED = "<redacted>"

# Cache TTL defaults (in seconds)
# Note: Current implementation uses addon settings via _cache_ttl(); these constants
# exist for clarity and future use without changing runtime behavior.
DEFAULT_CACHE_TTL_PROJECTS_MENU = 3600  # 1 hour (projects menu)
DEFAULT_CACHE_TTL_EPISODES = 86400 * 3  # 72 hours (episodes data)
DEFAULT_CACHE_TTL_INDIVIDUAL_PROJECT = 28800  # 8 hours (individual project)

angel_menu_content_mapper = {
    "movies": "movie",
    "series": "series",
    "specials": "special",
}

# Map Angel Studios content types to Kodi content types
kodi_content_mapper = {
    "movies": "movies",
    "series": "tvshows",
    "special": "videos",  # Specials are treated as generic videos
    "podcast": "videos",  # Podcasts are also generic videos
    "livestream": "videos",  # Livestreams are generic videos
}


class KodiUIInterface:
    """Helper class for Kodi UI operations"""

    def __init__(self, handle, url, logger, angel_interface):
        """
        Initialize the Kodi UI interface.
        """
        self.handle = handle
        self.kodi_url = url
        self.log = logger
        self.angel_interface = angel_interface
        self.cache = SimpleCache()  # Initialize cache

        self.addon = xbmcaddon.Addon()
        addon_path = xbmcvfs.translatePath(self.addon.getAddonInfo("path"))
        self.default_icon = os.path.join(addon_path, "resources", "images", "icons", "Angel_Studios_Logo.png")
        self.default_settings_icon = "DefaultAddonService.png"

        # Trace directory setup
        profile_path = xbmcvfs.translatePath(self.addon.getAddonInfo("profile"))
        self.trace_dir = os.path.join(profile_path, "temp")

        # Log initialization
        self.log.info("KodiUIInterface initialized")
        self.log.debug(f"{self.handle=}, {self.kodi_url=}")

        # Default state for menu toggles
        self.default_menu_enabled = {
            "show_movies": True,
            "show_series": True,
            "show_specials": True,
            "show_podcasts": False,
            "show_livestreams": False,
            "show_continue_watching": False,
            "show_top_picks": False,
        }

        # Static menu definitions (settings are applied when rendering)
        self.menu_defs = {
            "show_movies": {
                "label": "Movies",
                "content_type": "movie",
                "action": "movies_menu",
                "description": "Browse standalone movies and films",
                "icon": "DefaultMovies.png",
            },
            "show_series": {
                "label": "Series",
                "content_type": "tvshow",
                "action": "series_menu",
                "description": "Browse series with multiple episodes",
                "icon": "DefaultTVShows.png",
            },
            # Kodi uses 'specials' for Dry Bar Comedy Specials
            # If this changes in the future, update accordingly
            "show_specials": {
                "label": "Dry Bar Comedy Specials",
                "content_type": "video",
                "action": "specials_menu",
                "description": "Browse Dry Bar Comedy Specials",
                "icon": "DefaultAddonLyrics.png",  # Microphone icon, best we could do
            },
            "show_podcasts": {
                "label": "Podcasts",
                "content_type": "video",
                "action": "podcast_menu",
                "description": "Browse Podcast content",
                "icon": "DefaultMusicSources.png",
            },
            "show_livestreams": {
                "label": "Livestreams",
                "content_type": "video",
                "action": "livestream_menu",
                "description": "Browse Livestream content",
                "icon": "DefaultPVRGuide.png",
            },
            "show_continue_watching": {
                "label": "Continue Watching",
                "content_type": "video",
                "action": "continue_watching_menu",
                "description": "Continue watching your in-progress content",
                "icon": "DefaultInProgressShows.png",
            },
            "show_watchlist": {
                "label": "Watchlist",
                "content_type": "video",
                "action": "watchlist_menu",
                "description": "Browse your saved watchlist items",
                "icon": "DefaultVideoPlaylists.png",
            },
            "show_top_picks": {
                "label": "Top Picks For You",
                "content_type": "video",
                "action": "top_picks_menu",
                "description": "Browse top picks for you",
                "icon": "DefaultMusicTop100.png",
            },
        }

        self.menu_items = []

    def main_menu(self):
        """Show the main menu with content type options"""

        # Rebuild menu items to reflect current settings
        self._load_menu_items()

        # Create directory items for each menu option
        for item in self.menu_items:
            # Create list item
            list_item = xbmcgui.ListItem(label=item["label"])

            if item.get("icon"):
                list_item.setArt({"icon": item["icon"], "thumb": item["icon"]})

            # Set info tags
            info_tag = list_item.getVideoInfoTag()
            info_tag.setPlot(item["description"])

            # Create URL
            self.log.debug(f"Creating URL for action: {item['action']}, content_type: {item['content_type']}")
            url = self.create_plugin_url(
                base_url=self.kodi_url,
                action=item["action"],
                content_type=item["content_type"],
            )

            # Add to directory
            xbmcplugin.addDirectoryItem(self.handle, url, list_item, True)

        # Finish directory
        xbmcplugin.endOfDirectory(self.handle)

    def projects_menu(self, content_type=""):
        """Display a menu of projects based on content type, with persistent caching."""
        try:
            self.log.info("Fetching projects from AngelStudiosInterface...")

            cache_key = f"projects_{content_type or 'all'}"
            cache_enabled = self._cache_enabled()
            projects = None
            if cache_enabled:
                projects = self.cache.get(cache_key)
                if projects:
                    self.log.debug(f"Cache hit for {cache_key}")
                else:
                    self.log.debug(f"Cache miss for {cache_key}")
            else:
                self.log.debug("Cache disabled; bypassing projects cache")

            if projects:
                self.log.info(f"Using cached projects for content type: {content_type}")
            else:
                self.log.info(f"Fetching projects from AngelStudiosInterface for content type: {content_type}")
                projects = self.angel_interface.get_projects(
                    project_type=self._get_angel_project_type(content_type)
                )
                if cache_enabled:
                    self.cache.set(cache_key, projects, expiration=self._cache_ttl())
            try:
                self.log.info(f"Projects: {json.dumps(projects, indent=2)}")
            except TypeError:
                self.log.info(f"Projects: <non-serializable type {type(projects).__name__}>")

            if not projects:
                self.show_error(f"No projects found for content type: {content_type}")
                return

            self.log.info(
                f"Processing {len(projects)} '{content_type if content_type else 'all content type'}' projects"
            )

            # Set content type for the plugin
            kodi_content_type = (
                "movies" if content_type == "movies" else "tvshows" if content_type == "series" else "videos"
            )
            xbmcplugin.setContent(self.handle, kodi_content_type)
            # Create list items for each project
            for project in projects:
                self.log.info(f"Processing project: {project['name']}")
                self.log.debug(f"Project dictionary: {json.dumps(project, indent=2)}")

                # Create list item
                list_item = xbmcgui.ListItem(label=project["name"])
                info_tag = list_item.getVideoInfoTag()
                info_tag.setMediaType(self._get_kodi_content_type(project["projectType"]))
                self._process_attributes_to_infotags(list_item, project)

                # Create URL for seasons listing
                url = self.create_plugin_url(
                    base_url=self.kodi_url,
                    action="seasons_menu",
                    content_type=content_type,
                    project_slug=project["slug"],
                )

                # Add to directory
                xbmcplugin.addDirectoryItem(self.handle, url, list_item, True)

            xbmcplugin.addSortMethod(self.handle, xbmcplugin.SORT_METHOD_LABEL)

            try:
                enable_prefetch = self.addon.getSettingBool("enable_prefetch")
                if enable_prefetch:
                    max_count = self.addon.getSettingInt("prefetch_project_count") or 5
                    if max_count <= 0:
                        max_count = 5
                    slugs = [p.get("slug") for p in projects if p.get("slug")]
                    self._deferred_prefetch_project(slugs, max_count)
            except Exception as exc:
                self.log.warning(f"prefetch settings read failed; skipping prefetch: {exc}")

            xbmcplugin.endOfDirectory(self.handle)

        except Exception as e:
            self.log.error(f"Error listing {content_type}: {e}")
            self.show_error(f"Failed to load {self._get_angel_project_type(content_type)}: {str(e)}")
            raise e

    def seasons_menu(self, content_type, project_slug):
        """Display a menu of seasons for a specific project, with persistent caching."""
        self.log.info(f"Fetching seasons for project: {project_slug}")
        try:
            self.log.info(f"Fetching seasons for project: {project_slug}")
            project = self._get_project(project_slug)
            if not project:
                self.log.error(f"Project not found: {project_slug}")
                self.show_error(f"Project not found: {project_slug}")
                return
            self.log.info(f"Project details: {json.dumps(project, indent=2)}")
            self.log.info(f"Processing {len(project.get('seasons', []))} seasons for project: {project_slug}")

            # TODO Map this, this is gross.
            kodi_content_type = (
                "movies" if content_type == "movies" else "tvshows" if content_type == "series" else "videos"
            )
            self.log.info(f"Setting content type for Kodi: {content_type} ({kodi_content_type})")
            xbmcplugin.setContent(self.handle, kodi_content_type)

            if len(project.get("seasons", [])) == 1:
                self.log.info(f"Single season found: {project['seasons'][0]['name']}")
                self.episodes_menu(content_type, project["slug"], season_id=project["seasons"][0]["id"])
            else:
                for season in project.get("seasons", []):
                    self.log.info(f"Processing season: {season['name']}")
                    self.log.debug(f"Season dictionary: {json.dumps(season, indent=2)}")
                    # Create list item
                    list_item = xbmcgui.ListItem(label=season["name"])
                    info_tag = list_item.getVideoInfoTag()
                    info_tag.setMediaType(self._get_kodi_content_type(content_type))
                    self._process_attributes_to_infotags(list_item, season)

                    # Create URL for seasons listing
                    url = self.create_plugin_url(
                        base_url=self.kodi_url,
                        action="episodes_menu",
                        content_type=content_type,
                        project_slug=project_slug,
                        season_id=season["id"],
                    )

                    xbmcplugin.addDirectoryItem(self.handle, url, list_item, True)

                xbmcplugin.addSortMethod(self.handle, xbmcplugin.SORT_METHOD_LABEL)
                xbmcplugin.endOfDirectory(self.handle)

            return True

        except Exception as e:
            self.log.error(f"Error fetching project {project_slug}: {e}")
            self.show_error(f"Error fetching project {project_slug}: {str(e)}")
            return False

    def episodes_menu(self, content_type, project_slug, season_id=None):
        """Display a menu of episodes for a specific season, with persistent caching."""
        self.log.info(f"Fetching episodes for project: {project_slug}, season: {season_id}")
        try:
            project = self._get_project(project_slug)
            if not project:
                self.log.error(f"Project not found: {project_slug}")
                self.show_error(f"Project not found: {project_slug}")
                return

            # If season_id is None, use first season (all-seasons mode)
            # Else find the specified season
            if season_id is None and project.get("seasons"):
                season = project["seasons"][0]
            else:
                season = next(
                    (s for s in project.get("seasons", []) if s.get("id") == season_id),
                    None,
                )
            if not season:
                self.log.error(f"Season not found: {season_id}")
                self.show_error(f"Season not found: {season_id}")
                return

            episode_count = len(season.get("episodes", []))
            self.log.info(f"Processing {episode_count} episodes for project: {project_slug}, season: {season_id}")
            kodi_content_type = (
                "movies" if content_type == "movies" else "tvshows" if content_type == "series" else "videos"
            )
            self.log.info(f"Setting content type for Kodi: {content_type} ({kodi_content_type})")
            xbmcplugin.setContent(self.handle, kodi_content_type)

            episodes_list = season.get("episodes", [])
            for idx, episode in enumerate(episodes_list):
                episode_available = bool(episode.get("source"))
                list_item = self._create_list_item_from_episode(
                    episode,
                    project=project,
                    content_type=content_type,
                    stream_url=None,
                    is_playback=False,
                )

                # Apply progress bar if watch position data is available
                if episode.get("watchPosition"):
                    watch_position = episode["watchPosition"].get("position")
                    duration = (
                        episode.get("source", {}).get("duration") if episode_available else episode.get("duration")
                    )
                    if watch_position is not None and duration is not None:
                        self._apply_progress_bar(list_item, watch_position, duration)

                # Create URL for seasons listing
                url = self.create_plugin_url(
                    base_url=self.kodi_url,
                    action="play_episode" if episode_available else "info",
                    content_type=content_type,
                    project_slug=project_slug,
                    season_id=season["id"],
                    episode_id=episode["id"],
                    episode_guid=episode.get("guid", ""),
                )

                xbmcplugin.addDirectoryItem(self.handle, url, list_item, False)

            if season["episodes"][0].get("seasonNumber", 0) > 0:
                xbmcplugin.addSortMethod(self.handle, xbmcplugin.SORT_METHOD_EPISODE)
            else:
                xbmcplugin.addSortMethod(self.handle, xbmcplugin.SORT_METHOD_VIDEO_SORT_TITLE)
            xbmcplugin.addSortMethod(self.handle, xbmcplugin.SORT_METHOD_LABEL)
            xbmcplugin.endOfDirectory(self.handle)

        except Exception as e:
            # TODO: this needs to handle episodes that are stubs.  Should not fail completely if one episode is bad.
            self.log.error(f"Error fetching season {season_id}: {e}")
            self.show_error(f"Error fetching season {season_id}: {str(e)}")
            return

    def watchlist_menu(self):
        """Placeholder for user watchlist until API support is added."""
        self.log.info("Watchlist menu requested, but not yet implemented.")
        self.show_error("Watchlist is not available yet.")

    def continue_watching_menu(self, after=None):
        """Display continue watching menu with pagination."""
        try:
            self.log.info(f"Fetching continue watching items, after={after}")

            # Step 1: Fetch resume watching guids (lightweight)
            resume_data = self.angel_interface.get_resume_watching(first=10, after=after)

            if not resume_data:
                self.show_error("Failed to load Continue Watching")
                return

            # Fallback: handle legacy shape with 'episodes' list containing embedded project
            if (
                isinstance(resume_data, dict)
                and "episodes" in resume_data
                and isinstance(resume_data["episodes"], list)
            ):
                xbmcplugin.setContent(self.handle, "videos")
                for episode in resume_data["episodes"]:
                    project = episode.get("project") if isinstance(episode, dict) else None
                    list_item = self._create_list_item_from_episode(
                        episode,
                        project=project,
                        content_type="",
                        stream_url=None,
                        is_playback=False,
                    )
                    project_slug = episode.get("projectSlug") or (project or {}).get("slug", "")
                    url = self.create_plugin_url(
                        base_url=self.kodi_url,
                        action="play_episode",
                        content_type="",
                        project_slug=project_slug,
                        episode_guid=episode.get("guid", ""),
                    )
                    xbmcplugin.addDirectoryItem(self.handle, url, list_item, False)
                xbmcplugin.endOfDirectory(self.handle)
                return

            guids = resume_data.get("guids", [])
            positions = resume_data.get("positions", {})
            page_info = resume_data.get("pageInfo", {})

            if not guids:
                self.log.info("No continue watching items found")
                self.show_notification("No items in Continue Watching")
                return

            # Step 2: Batch fetch full episode data for all guids
            self.log.info(f"Batch fetching {len(guids)} episodes")
            episodes_data = self.angel_interface.get_episodes_for_guids(guids)

            if not episodes_data:
                self.log.error("Failed to fetch episode data for continue watching")
                self.show_error("Failed to load episode details")
                return

            # Step 2b: Fetch unique project names for enrichment
            unique_slugs = set()
            for guid in guids:
                episode_key = f"episode_{guid}"
                episode = episodes_data.get(episode_key, {})
                if episode.get("projectSlug"):
                    unique_slugs.add(episode["projectSlug"])

            project_names = {}
            if unique_slugs:
                self.log.info(f"Fetching project names for {len(unique_slugs)} projects")
                project_names = self.angel_interface.get_projects_by_slugs(list(unique_slugs))

            self.log.info(f"Processing {len(guids)} continue watching items")
            xbmcplugin.setContent(self.handle, "videos")

            # Step 3: Render menu in guid order, merging watch positions
            for guid in guids:
                episode_key = f"episode_{guid}"
                episode = episodes_data.get(episode_key)

                if not episode:
                    self.log.warning(f"Episode {guid} not found in batch response, skipping")
                    continue

                # Enrich with project name if available
                project_slug = episode.get("projectSlug")
                project_for_display = None
                if project_slug and project_slug in project_names:
                    project_for_display = project_names[project_slug]

                # Enrich with watch position from resume watching response
                watch_position = positions.get(guid)
                if watch_position is not None and "watchPosition" not in episode:
                    episode["watchPosition"] = {"position": watch_position}

                # Create list item using shared helper
                list_item = self._create_list_item_from_episode(
                    episode,
                    project=project_for_display,
                    content_type="",
                    stream_url=None,
                    is_playback=False,
                )

                # Apply progress bar if available
                if episode.get("watchPosition"):
                    watch_position_val = episode["watchPosition"].get("position")
                    duration = episode.get("duration")
                    if watch_position_val is not None and duration is not None:
                        self._apply_progress_bar(list_item, watch_position_val, duration)

                # Create URL for playback
                project_slug = episode.get("projectSlug", "")

                url = self.create_plugin_url(
                    base_url=self.kodi_url,
                    action="play_episode",
                    content_type="",
                    project_slug=project_slug,
                    episode_guid=guid,
                )

                xbmcplugin.addDirectoryItem(self.handle, url, list_item, False)

            # Add "Load More" if pagination available
            if page_info.get("hasNextPage"):
                end_cursor = page_info.get("endCursor")
                if end_cursor:
                    list_item = xbmcgui.ListItem(label="[Load More...]")
                    url = self.create_plugin_url(
                        base_url=self.kodi_url,
                        action="continue_watching_menu",
                        after=end_cursor,
                    )
                    xbmcplugin.addDirectoryItem(self.handle, url, list_item, True)

            xbmcplugin.endOfDirectory(self.handle)

        except Exception as e:
            self.log.error(f"Error in continue_watching_menu: {e}")
            self.show_error(f"Failed to load Continue Watching: {str(e)}")

    def top_picks_menu(self):
        """Placeholder for top picks until API support is added."""
        self.log.info("Top picks menu requested, but not yet implemented.")
        self.show_error("Top Picks is not available yet.")

    def play_episode(self, episode_guid, project_slug):
        """Play an episode using cached project data (no separate API call)."""
        try:
            # Fetch project data (uses cache if available)
            project = self._get_project(project_slug)
            if not project:
                self.log.error(f"Project not found: {project_slug}")
                self.show_error(f"Project not found: {project_slug}")
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
                self.show_error(f"Episode not found: {episode_guid}")
                return

            # Check for playable source
            source = episode.get("source")
            if not source or not source.get("url"):
                self.show_error("No playable stream URL found for this episode")
                self.log.error(f"No stream URL for episode: {episode_guid} in project: {project_slug}")
                return

            episode_name = episode.get("subtitle") or episode.get("name", "Unknown")
            project_name = project.get("name", "Unknown")
            self.log.info(f"Playing episode: {episode_name} from project: {project_name}")

            # Play using existing episode data
            self.play_video(episode_data={"episode": episode, "project": project})

        except Exception as e:
            self.log.error(f"Error playing episode {episode_guid}: {e}")
            self.show_error(f"Failed to play episode: {str(e)}")

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
                list_item = self._create_list_item_from_episode(
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
            self.show_error(f"Error playing video: {e}")
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

    def setAngelInterface(self, angel_interface):
        """Set the Angel Studios interface for this UI helper"""
        self.angel_interface = angel_interface

    def create_plugin_url(self, **kwargs):
        """Create a URL for calling the plugin recursively"""
        return f"{self.kodi_url}?{urlencode(kwargs)}"

    def _cache_ttl(self):
        """Return timedelta for current cache expiration setting.

        Uses addon setting `cache_expiration_hours`. Module-level TTL constants
        (DEFAULT_CACHE_TTL_PROJECTS_MENU, DEFAULT_CACHE_TTL_EPISODES, DEFAULT_CACHE_TTL_INDIVIDUAL_PROJECT)
        are provided for clarity and future specialization but are not applied here
        to avoid changing existing behavior.
        """
        try:
            hours = self.addon.getSettingInt("cache_expiration_hours")
            if not hours:
                self.log.warning(f"cache_expiration_hours was falsy ({hours!r}); defaulting to 12")
                hours = 12
        except Exception as exc:
            self.log.warning(f"Failed to read cache_expiration_hours; defaulting to 12: {exc}")
            hours = 12

        return timedelta(hours=hours)

    def _project_cache_ttl(self):
        """Return timedelta for project cache expiration.

        Currently uses the same global cache_expiration_hours setting.
        Future: may use separate project_cache_hours setting.
        """
        return self._cache_ttl()

    def _episode_cache_ttl(self):
        """Return timedelta for episode cache expiration.

        Currently uses the same global cache_expiration_hours setting.
        Future: may use separate episode_cache_hours setting.
        """
        return self._cache_ttl()

    def _get_angel_project_type(self, menu_content_type):
        """Map menu content type to Angel Studios project type for API calls."""
        return angel_menu_content_mapper.get(menu_content_type, "videos")

    def _get_kodi_content_type(self, content_type):
        """Map content type to Kodi media type for info tags."""
        return kodi_content_mapper.get(content_type, "video")

    def _get_debug_mode(self):
        """Return debug mode string in {'off','debug','trace'}"""
        try:
            value = self.addon.getSettingString("debug_mode")
        except Exception as exc:
            self.log.warning(f"debug_mode read failed; defaulting to off: {exc}")
            value = "off"

        value = (value or "off").lower()
        return value if value in {"off", "debug", "trace"} else "off"

    def _is_debug(self):
        """Return True if debug or trace mode is enabled."""
        mode = self._get_debug_mode()
        return mode in {"debug", "trace"}

    def _is_trace(self):
        """Return True only when trace mode is enabled."""
        return self._get_debug_mode() == "trace"

    def _cache_enabled(self):
        """Return True if cache is enabled based on addon settings.

        Interprets `disable_cache` as a boolean; defaults to enabled when
        the setting is missing, unreadable, or a non-bool value.
        """
        try:
            disabled_val = self.addon.getSettingBool("disable_cache")
            if isinstance(disabled_val, bool):
                return not disabled_val

            self.log.warning(f"disable_cache returned non-bool {disabled_val!r}; assuming cache enabled")
            return True
        except Exception as exc:
            self.log.warning(f"disable_cache read failed; assuming cache enabled: {exc}")
            return True

    def _ensure_trace_dir(self):
        """Ensure the trace directory exists if trace mode is active.

        Returns True when the directory is present or created successfully,
        else False. No-op when trace mode is off.
        """
        if not self._is_trace():
            return False
        try:
            os.makedirs(self.trace_dir, exist_ok=True)
            return True
        except Exception as exc:
            self.log.error(f"Failed to ensure trace directory {self.trace_dir}: {exc}")
            return False

    def _redact_sensitive(self, data):
        """Recursively redact sensitive keys in dicts/lists."""
        if isinstance(data, dict):
            redacted = {}
            for key, val in data.items():
                key_lower = str(key).lower()
                if any(secret in key_lower for secret in ("password", "authorization", "cookie", "token")):
                    redacted[key] = REDACTED
                else:
                    redacted[key] = self._redact_sensitive(val)
            return redacted
        if isinstance(data, list):
            return [self._redact_sensitive(item) for item in data]
        return data

    def _trim_trace_files(self, max_files=50):
        """Trim old trace files, keeping only the most recent `max_files`.

        Safe to call even if the directory does not exist or file operations fail.
        """
        try:
            files = [
                os.path.join(self.trace_dir, f)
                for f in os.listdir(self.trace_dir)
                if os.path.isfile(os.path.join(self.trace_dir, f))
            ]
            if len(files) <= max_files:
                return
            files.sort(key=lambda p: os.path.getmtime(p))
            for path in files[: len(files) - max_files]:
                try:
                    os.remove(path)
                except Exception:
                    pass
        except Exception as exc:
            self.log.error(f"Failed to trim trace files: {exc}")

    def _trace_callback(self, payload):
        """Trace callback to persist a redacted payload when in trace mode.

        Redacts sensitive fields, writes JSON to the trace directory, and
        trims older entries. No-ops when trace mode or directory setup is off.
        """
        if not self._is_trace():
            return
        if not self._ensure_trace_dir():
            return

        safe_payload = self._redact_sensitive(payload)
        ts = time.strftime("%Y%m%dT%H%M%S")
        fname = f"trace_{ts}_{int(time.time()*1000) % 1000}.json"
        path = os.path.join(self.trace_dir, fname)
        try:
            with open(path, "w", encoding="utf-8") as fp:
                json.dump(safe_payload, fp, indent=2)
            self._trim_trace_files()
        except Exception as exc:
            self.log.error(f"Failed to write trace file {path}: {exc}")

    def get_trace_callback(self):
        """Expose tracer for API layer; safe to use even when trace is off."""
        return self._trace_callback

    def _load_menu_items(self):
        """Load menu items using current settings each time the main menu is rendered."""
        self.menu_items = []
        addon = self.addon

        for setting_id, item in self.menu_defs.items():
            try:
                enabled = addon.getSettingBool(setting_id)
            except Exception as exc:
                self.log.warning(f"Failed to read setting {setting_id}: {exc}; using default")
                enabled = self.default_menu_enabled.get(setting_id, False)

            if not isinstance(enabled, bool):
                enabled = self.default_menu_enabled.get(setting_id, False)

            if enabled:
                self.menu_items.append(item)

        # Settings is always shown
        self.menu_items.append(
            {
                "label": "Settings",
                "content_type": "video",
                "action": "settings",
                "description": "Open addon settings",
                "icon": self.default_settings_icon,
            }
        )

    def show_error(self, message, title="Angel Studios"):
        """Show error dialog to user"""
        xbmcgui.Dialog().ok(title, message)
        xbmc.log(f"Error shown to user: {message}", xbmc.LOGERROR)

    def show_notification(self, message, title="Angel Studios", time=5000):
        """Show notification to user"""
        xbmcgui.Dialog().notification(title, message, time=time)
        xbmc.log(f"Notification: {message}", xbmc.LOGINFO)

    def show_auth_details_dialog(self):
        """Show authentication/session details in a dialog."""
        if not self.angel_interface or not getattr(self.angel_interface, "angel_studios_session", None):
            xbmcgui.Dialog().ok("Angel Studios Session Details", "No session available.")
            return

        try:
            details = self.angel_interface.angel_studios_session.get_session_details()
        except Exception:
            xbmcgui.Dialog().ok("Angel Studios Session Details", "Unable to read session details.")
            return

        login_email = details.get("login_email", "Unknown")
        account_id = details.get("account_id", "Unknown")
        lines = [f"{'Login email:':<18} {login_email}"]
        if account_id:
            lines.append(f"{'Account ID:':<18} {account_id}")

        lines.append(f"{'Authenticated:':<18} {details.get('authenticated', False)}")

        expires_at_local = details.get("expires_at_local", "Unknown")
        expires_at_utc = details.get("expires_at_utc", "Unknown")
        expires_in_td = details.get("expires_in_human", "Unknown")
        expires_in_seconds = details.get("expires_in_seconds")
        issued_at_local = details.get("issued_at_local", "Unknown")
        issued_at_utc = details.get("issued_at_utc", "Unknown")

        lines.append(f"{'Session Issued:':<18} {issued_at_local} ({issued_at_utc})")
        lines.append(f"{'Session Expires:':<18} {expires_at_local} ({expires_at_utc})")

        if isinstance(expires_in_seconds, int):
            days, rem = divmod(expires_in_seconds, 86400)
            hours, rem = divmod(rem, 3600)
            minutes, seconds = divmod(rem, 60)
            parts = []
            if days:
                parts.append(f"{days}d")
            if hours:
                parts.append(f"{hours}h")
            if minutes:
                parts.append(f"{minutes}m")
            if seconds or not parts:
                parts.append(f"{seconds}s")
            human_remaining = " ".join(parts)
            lines.append(f"{'Session Remaining:':<18} {human_remaining} ({expires_in_td})")
        else:
            lines.append(f"{'Session Remaining:':<18} {expires_in_td}")

        if details.get("cookie_names"):
            lines.append("Cookies:")
            for cookie_name in details["cookie_names"]:
                lines.append(f"  - {cookie_name}")

        xbmcgui.Dialog().textviewer("Angel Studios Session Details", "\n".join(lines), usemono=True)

    def clear_cache(self):
        """Clear addon SimpleCache entries."""
        try:
            # SimpleCache has no public clear-all; rely on its private SQL handle and window cache.
            if not hasattr(self.cache, "_execute_sql"):
                self.log.info("SimpleCache before clear: introspection not available")
                return False

            # Query existing ids once
            rows = self.cache._execute_sql("SELECT id FROM simplecache")
            ids = rows.fetchall() if rows else []
            self.log.info(f"SimpleCache before clear: {[row[0] for row in ids]}")

            if len(ids) == 0:
                self.log.info("SimpleCache empty; nothing to clear")
                self.log.info("SimpleCache after clear: []")
                return True

            for (cache_id,) in ids:
                self.cache._execute_sql("DELETE FROM simplecache WHERE id = ?", (cache_id,))

            if hasattr(self.cache, "_win"):
                for (cache_id,) in ids:
                    try:
                        self.cache._win.clearProperty(cache_id)
                    except Exception:
                        pass

            rows_after = self.cache._execute_sql("SELECT id FROM simplecache")
            ids_after = rows_after.fetchall() if rows_after else []
            self.log.info(f"SimpleCache after clear: {[row[0] for row in ids_after]}")
            return True
        except Exception as e:
            self.log.error(f"Failed to clear cache: {e}")
            return False

    def clear_debug_data(self):
        """Remove trace files from the temp directory."""
        try:
            if not os.path.isdir(self.trace_dir):
                self.log.info("Trace directory does not exist; nothing to clear")
                return True
            files = [os.path.join(self.trace_dir, f) for f in os.listdir(self.trace_dir)]
            removed = 0
            for path in files:
                try:
                    if os.path.isfile(path):
                        os.remove(path)
                        removed += 1
                except Exception:
                    pass
            self.log.info(f"Cleared {removed} trace files from {self.trace_dir}")
            return True
        except Exception as e:
            self.log.error(f"Failed to clear debug data: {e}")
            return False

    def _get_project(self, project_slug):
        """
        Helper function to handle fetching and caching project data.
        """
        cache_key = f"project_{project_slug}"
        cache_enabled = self._cache_enabled()
        project = None
        if cache_enabled:
            project = self.cache.get(cache_key)
            if project:
                self.log.debug(f"Cache hit for {cache_key}")
            else:
                self.log.debug(f"Cache miss for {cache_key}")
        else:
            self.log.debug("Cache disabled; bypassing project cache")

        if project is None:
            self.log.info(f"Fetching project data from AngelStudiosInterface for: {project_slug}")
            project = self.angel_interface.get_project(project_slug)
            if project and cache_enabled:
                self.cache.set(cache_key, project, expiration=self._cache_ttl())
        else:
            self.log.info(f"Using cached project data for: {project_slug}")
        return project

    def _apply_progress_bar(self, list_item, watch_position_seconds, duration_seconds):
        """
        Apply native Kodi resume point indicator to a ListItem.

        Args:
            list_item: xbmcgui.ListItem to apply progress to
            watch_position_seconds: Current watch position in seconds (float)
            duration_seconds: Total duration in seconds (float)

        Returns:
            None. Modifies list_item in place.
        """
        if watch_position_seconds is None or duration_seconds is None or duration_seconds == 0:
            self.log.debug(
                f"Skipping progress bar: watch_position={watch_position_seconds}, " f"duration={duration_seconds}"
            )
            return

        try:
            resume_point = float(watch_position_seconds) / float(duration_seconds)
            # Clamp to [0.0, 1.0]
            resume_point = max(0.0, min(1.0, resume_point))

            info_tag = list_item.getVideoInfoTag()
            info_tag.setResumePoint(resume_point)
            self.log.debug(
                f"Applied progress bar: {watch_position_seconds}s / {duration_seconds}s = {resume_point:.2%}"
            )
        except Exception as e:
            self.log.warning(
                f"Failed to apply progress bar: {e}. "
                f"watch_position={watch_position_seconds}, duration={duration_seconds}"
            )

    def _create_list_item_from_episode(
        self, episode, project=None, content_type="", stream_url=None, is_playback=False
    ):
        """
        Unified helper to create a ListItem from an episode dict.
        - episode: Raw episode dict.
        - project: Optional project dict (for playback metadata).
        - content_type: For directory media type.
        - stream_url: If provided, enables playback mode.
        - is_playback: True for playback mode (sets offscreen, path, etc.).
        """
        self.log.info(
            f"Creating ListItem for episode: {episode.get('name', 'Unknown Episode')}, is_playback={is_playback}"
        )
        episode_available = bool(episode.get("source"))
        episode_subtitle = episode.get("subtitle", episode.get("name", "Unknown Episode"))

        # If the episode is not available (no source), indicate that in the subtitle with italics.
        if not episode_available:
            episode_subtitle = f"[I] {episode_subtitle} (Unavailable)[/I]"

        # Both directory items and playback items must be set to IsPlayable true
        # if the episode is available.
        list_item = xbmcgui.ListItem(label=episode_subtitle, offscreen=is_playback)
        list_item.setProperty("IsPlayable", "true" if episode_available else "false")

        # Create ListItem
        if is_playback:
            quality_pref = self._get_quality_pref()
            quality_mode = quality_pref["mode"]
            target_height = quality_pref["target_height"]
            manifest_url = (episode.get("source") or {}).get("url", stream_url)

            list_item.setIsFolder(False)

            if manifest_url:
                self.log.info(f"Loading Manifest: {manifest_url}")

            use_isa = xbmcaddon.Addon().getSettingBool("use_isa")
            isa_ready = False
            stream_selection_type = None

            if use_isa:
                isa_ready = self._ensure_isa_available("hls")
                if not isa_ready:
                    isa_ready = xbmc.getCondVisibility("System.HasAddon(inputstream.adaptive)")
                    if isa_ready:
                        self.log.info("ISA detected via System.HasAddon; proceeding without inputstreamhelper")

                if isa_ready:
                    if quality_mode == "manual":
                        stream_selection_type = "ask-quality"
                    elif quality_mode == "fixed":
                        stream_selection_type = "fixed-res"
                    else:
                        stream_selection_type = "adaptive"

                    if manifest_url:
                        list_item.setPath(manifest_url)
                    list_item.setProperty("inputstream", "inputstream.adaptive")
                    list_item.setProperty("inputstream.adaptive.manifest_type", "hls")
                    if stream_selection_type:
                        list_item.setProperty(
                            "inputstream.adaptive.stream_selection_type",
                            stream_selection_type,
                        )
                    if target_height and quality_mode != "manual":
                        chooser_map = {
                            1080: "1080p",
                            720: "720p",
                            480: "480p",
                            360: "360p",
                        }
                        chooser_value = chooser_map.get(target_height)
                        if chooser_value:
                            list_item.setProperty(
                                "inputstream.adaptive.chooser_resolution_max",
                                chooser_value,
                            )
                            list_item.setProperty(
                                "inputstream.adaptive.chooser_resolution_secure_max",
                                chooser_value,
                            )
                    list_item.setMimeType("application/vnd.apple.mpegurl")
                    list_item.setContentLookup(False)
                else:
                    self.log.info("ISA requested but unavailable; falling back to native playback")
            else:
                self.log.info("ISA disabled via settings; using Kodi builtin HLS handling")

            if not isa_ready:
                if not manifest_url:
                    self.log.warning("No manifest URL available; skipping quality selection")
                else:
                    list_item.setPath(manifest_url)

            # Stream details
            video_stream_detail = xbmc.VideoStreamDetail()
            video_stream_detail.setCodec("h264")
            video_stream_detail.setWidth(1920)
            video_stream_detail.setHeight(1080)
            info_tag = list_item.getVideoInfoTag()
            info_tag.addVideoStream(video_stream_detail)

            # Resume
            if episode.get("watch_position"):
                info_tag.setResumePoint(episode["watch_position"])
        else:
            list_item.setIsFolder(True)

        # Set common metadata (inject project logo if episode lacks one)
        art_info = dict(episode) if isinstance(episode, dict) else {}
        try:
            if project and isinstance(project, dict) and "logoCloudinaryPath" in project:
                if "logoCloudinaryPath" not in art_info:
                    self.log.debug(f"[ART] Injecting project logo into episode: {project['logoCloudinaryPath']}")
                    art_info["logoCloudinaryPath"] = project["logoCloudinaryPath"]
        except Exception:
            pass

        self._process_attributes_to_infotags(list_item, art_info)

        # Set media type and additional metadata
        info_tag = list_item.getVideoInfoTag()
        if episode_available:
            info_tag.setDuration(episode.get("source").get("duration", 0))
        if is_playback:
            info_tag.setMediaType("video")
            # Additional playback metadata from project
            if project:
                info_tag.setTvShowTitle(project.get("name"))
        else:
            info_tag.setMediaType(self._get_kodi_content_type(content_type))
            info_tag.setTitle(episode_subtitle)

        return list_item

    def _get_quality_pref(self):
        """Return dict with 'mode' and 'target_height'. mode in {'auto','fixed','manual'}."""
        try:
            addon = xbmcaddon.Addon()
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

    def _process_attributes_to_infotags(self, list_item, info_dict):
        """
        Set VideoInfoTag attributes from a dictionary using known setters.
        Only sets attributes present in the info_dict.
        """
        self.log.info(f"Processing attributes for list item: {list_item.getLabel()}")
        self.log.debug(f"Attribute dict: {info_dict}")
        info_tag = list_item.getVideoInfoTag()
        mapping = {
            "media_type": info_tag.setMediaType,
            "name": info_tag.setTitle,
            "theaterDescription": info_tag.setPlot,
            "description": info_tag.setPlot,
            "year": info_tag.setYear,
            "genres": info_tag.setGenres,
            "contentRating": info_tag.setMpaa,
            "original_title": info_tag.setOriginalTitle,
            "sort_title": info_tag.setSortTitle,
            "tagline": info_tag.setTagLine,
            "duration": info_tag.setDuration,
            "cast": info_tag.setCast,
            "episode": info_tag.setEpisode,
            "episodeNumber": info_tag.setEpisode,
            "season": info_tag.setSeason,
            "seasonNumber": info_tag.setSeason,
            "tvshowtitle": info_tag.setTvShowTitle,
            "premiered": info_tag.setPremiered,
            "rating": info_tag.setRating,
            "votes": info_tag.setVotes,
            "trailer": info_tag.setTrailer,
            "playcount": info_tag.setPlaycount,
            "unique_ids": info_tag.setUniqueIDs,
            "imdbnumber": info_tag.setIMDBNumber,
            "dateadded": info_tag.setDateAdded,
        }
        art_dict = {}

        for key, value in info_dict.items():
            self.log.debug(f"Processing key: {key} with value: '{value}'")
            # Handle metadata keys that have setters
            if key == "metadata":
                for meta_key, meta_value in value.items():
                    if meta_key in mapping and meta_value:
                        mapping[meta_key](meta_value)
            elif key == "cast" and isinstance(value, list):
                # Validate and filter cast entries
                valid_actors = []
                for actor_entry in value:
                    if not isinstance(actor_entry, dict):
                        continue
                    name = actor_entry.get("name")
                    if name and isinstance(name, str) and name.strip():
                        try:
                            valid_actors.append(xbmc.Actor(name=name.strip()))
                        except Exception:
                            pass
                if valid_actors:
                    info_tag.setCast(valid_actors)
            # Handle artwork
            elif "Cloudinary" in key and value:
                if key in ["discoveryPosterCloudinaryPath", "posterCloudinaryPath"]:
                    art_dict["poster"] = self.angel_interface.get_cloudinary_url(value)
                elif key in [
                    "discoveryPosterLandscapeCloudinaryPath",
                    "posterLandscapeCloudinaryPath",
                ]:
                    art_dict["landscape"] = self.angel_interface.get_cloudinary_url(value)
                    art_dict["fanart"] = self.angel_interface.get_cloudinary_url(value)
                elif key == "logoCloudinaryPath":
                    art_dict["logo"] = self.angel_interface.get_cloudinary_url(value)
                    art_dict["clearlogo"] = self.angel_interface.get_cloudinary_url(value)
                    art_dict["icon"] = self.angel_interface.get_cloudinary_url(value)
                else:
                    self.log.info(f"Unknown Cloudinary key: {key}, skipping")
            elif key in ("portraitStill1", "portraitStill2") and isinstance(value, dict):
                cp = value.get("cloudinaryPath")
                if cp:
                    self.log.debug(f"[ART] Using {key}: {cp}")
                    url = self.angel_interface.get_cloudinary_url(cp)
                    art_dict.setdefault("poster", url)
                    art_dict.setdefault("thumb", url)
            elif key == "portraitTitleImage" and isinstance(value, dict):
                self.log.debug(f"[ART] direct portraitTitleImage: {value}")
                cp = value.get("cloudinaryPath")
                if cp:
                    self.log.debug(f"[ART] Using direct portraitTitleImage: {cp}")
                    url = self.angel_interface.get_cloudinary_url(cp)
                    art_dict.setdefault("poster", url)
                    art_dict.setdefault("thumb", url)
            elif key in ("landscapeStill1", "landscapeStill2") and isinstance(value, dict):
                cp = value.get("cloudinaryPath")
                if cp:
                    url = self.angel_interface.get_cloudinary_url(cp)
                    art_dict.setdefault("landscape", url)
                    art_dict.setdefault("fanart", url)
            elif key == "seasonNumber" and value == 0:
                self.log.info("Season is 0, skipping season info")
            elif key == "season" and isinstance(value, dict):
                # Extract seasonNumber from nested season object
                season_num = value.get("seasonNumber")
                if season_num is not None:
                    info_tag.setSeason(season_num)
            elif key == "source" and isinstance(value, dict):
                # Skip nested source objects (handled separately in playback)
                pass  # pragma: no cover - defensive skip of nested source
            elif key == "watchPosition" and isinstance(value, dict):
                # Skip nested watchPosition objects (handled separately for progress)
                pass  # pragma: no cover - defensive skip of nested watchPosition
            elif key == "cast":
                # Cast handled above; skip here
                pass
            elif key in mapping:
                mapping[key](value)
            else:
                self.log.debug(f"No known processor for key: {key}, skipping")

        # Set artwork if available
        if art_dict:
            self.log.debug(f"Setting artwork: {art_dict}")
            list_item.setArt(art_dict)
        return

    def _merge_stills_into_episodes(self, episodes, project_slug):
        """Merge ContentSeries STILLs into raw episodes list using cached project."""
        try:
            cache_key = f"project_{project_slug}"
            project = self.cache.get(cache_key)
            if not project:
                self.log.debug(f"No cached project for {project_slug}, skipping STILL merge")
                return episodes

            title = project.get("title", {}) if isinstance(project, dict) else {}
            if title.get("__typename") != "ContentSeries":
                self.log.debug(f"No ContentSeries data in project {project_slug}")
                return episodes

            seasons_edges = title.get("seasons", {})
            unwrap = getattr(self.angel_interface, "_unwrap_relay_pagination", None)
            seasons = unwrap(seasons_edges) if callable(unwrap) else []

            stills_by_id = {}
            for season in seasons:
                episodes_edges = (season or {}).get("episodes", {})
                nodes = unwrap(episodes_edges) if callable(unwrap) else []
                for node in nodes:
                    if not isinstance(node, dict):
                        continue
                    eid = node.get("id")
                    if not eid:
                        continue
                    payload = {}
                    if isinstance(node.get("portraitStill1"), dict):
                        payload["portraitStill1"] = node["portraitStill1"]
                    if isinstance(node.get("landscapeStill1"), dict):
                        payload["landscapeStill1"] = node["landscapeStill1"]
                    if payload:
                        stills_by_id[eid] = payload

            self.log.info(
                f"Merging ContentSeries STILLs from {len(stills_by_id)} episodes into {len(episodes)} episodes"
            )

            merged = []
            for ep in episodes:
                if not ep:
                    merged.append(ep)
                    continue
                eid = ep.get("id")
                inject = stills_by_id.get(eid, {})
                if inject:
                    m = dict(ep)
                    m.update(inject)
                    merged.append(m)
                else:
                    merged.append(ep)
            return merged
        except Exception as exc:
            self.log.error(f"Failed to merge STILLs: {exc}")
            return episodes

    def _normalize_contentseries_episode(self, episode):
        """Normalize ContentSeries episode dict to expected keys."""
        if not isinstance(episode, dict):
            return {}
        keys = {
            "id",
            "name",
            "subtitle",
            "description",
            "episodeNumber",
            "portraitStill1",
            "landscapeStill1",
            "landscapeStill2",
        }
        return {k: episode[k] for k in keys if k in episode}

    def _deferred_prefetch_project(self, project_slugs, max_count=None):
        """Prefetch and cache project data for given slugs in the background."""
        try:
            if not project_slugs:
                return

            if not hasattr(self.cache, "_execute_sql"):
                self.log.debug("SimpleCache introspection not available; prefetch skipped")
                return

            rows = self.cache._execute_sql("SELECT id FROM simplecache WHERE id LIKE ?", ("project_%",))
            cached = set()
            for row in rows.fetchall() if rows else []:
                val = row[0]
                if isinstance(val, str) and val.startswith("project_"):
                    cached.add(val.split("project_", 1)[1])

            to_fetch = [s for s in project_slugs if s not in cached]
            if not to_fetch:
                self.log.debug("All requested projects already cached; skipping prefetch")
                return

            if isinstance(max_count, int) and max_count > 0:
                to_fetch = to_fetch[:max_count]

            for slug in to_fetch:
                try:
                    proj = self.angel_interface.get_project(slug)
                except Exception:
                    self.log.debug("API error; abandoning prefetch")
                    break
                if not proj:
                    continue
                if self._cache_enabled():
                    self.cache.set(f"project_{slug}", proj, expiration=self._cache_ttl())
        except Exception as exc:
            self.log.error(f"Project prefetch failed: {exc}")

    def clear_cache_with_notification(self):
        """Clear cache and notify user with outcome."""
        result = self.clear_cache()
        if result:
            self.show_notification("Cache cleared.")
            self.log.info("Cache cleared successfully via settings")
        else:
            self.show_notification("Cache clear failed; please try again.")
            self.log.error("Cache clear failed via settings")

    def force_logout_with_notification(self):
        """Force local logout via angel_interface and notify user."""
        if not self.angel_interface:
            raise ValueError("Angel interface not initialized")
        result = self.angel_interface.force_logout()
        if result:
            self.show_notification("Logged out locally.")
            self.log.info("Logged out locally via settings")
        else:
            self.show_notification("Logout failed; please try again.")
            self.log.error("Logout failed via settings")

    def clear_debug_data_with_notification(self):
        """Clear debug trace files and log outcome; notify on success."""
        result = self.clear_debug_data()
        if result:
            self.show_notification("Debug data cleared.")
            self.log.info("Debug data cleared via settings")
        else:
            self.log.error("Debug data clear failed via settings")
