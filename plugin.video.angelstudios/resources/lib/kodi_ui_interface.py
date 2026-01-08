"""
Kodi UI helper functions for Angel Studios addon.
Handles all Kodi-specific UI operations and list item creation.
"""

import json
import os
import time
from datetime import timedelta
from urllib.parse import urlencode, urljoin

import xbmc  # type: ignore
import xbmcaddon  # type: ignore
import xbmcgui  # type: ignore
import xbmcplugin  # type: ignore
import xbmcvfs  # type: ignore

from simplecache import SimpleCache  # type: ignore

REDACTED = '<redacted>'

angel_menu_content_mapper = {
    'movies': 'movie',
    'series': 'series',
    'specials': 'special'
}

# Map Angel Studios content types to Kodi content types
kodi_content_mapper = {
    'movies': 'movies',
    'series': 'tvshows',
    'special': 'videos',    # Specials are treated as generic videos
    'podcast': 'videos',    # Podcasts are also generic videos
    'livestream': 'videos'  # Livestreams are generic videos
}

class KodiUIInterface:
    """Helper class for Kodi UI operations"""

    def __init__(self, handle, url, logger, angel_interface):
        '''
        Initialize the Kodi UI interface.
        '''
        self.handle = handle
        self.kodi_url = url
        self.log = logger
        self.angel_interface = angel_interface
        self.cache = SimpleCache()  # Initialize cache

        self.addon = xbmcaddon.Addon()
        addon_path = xbmcvfs.translatePath(self.addon.getAddonInfo('path'))
        self.default_icon = os.path.join(addon_path, 'resources', 'images', 'icons', 'Angel_Studios_Logo.png')
        self.default_settings_icon = 'DefaultAddonService.png'
        profile_path = xbmcvfs.translatePath(self.addon.getAddonInfo('profile'))
        self.trace_dir = os.path.join(profile_path, 'temp')

        # Log initialization
        self.log.info("KodiUIInterface initialized")
        self.log.debug(f"{self.handle=}, {self.kodi_url=}")

        # Default state for menu toggles
        self.default_menu_enabled = {
            'show_movies': True,
            'show_series': True,
            'show_specials': True,
            'show_podcasts': False,
            'show_livestreams': False,
            'show_continue_watching': False,
            'show_top_picks': False,
            'show_other_content': False,
        }

        # Static menu definitions (settings are applied when rendering)
        self.menu_defs = {
            'show_movies': {
                'label': 'Movies',
                'content_type': 'movie',
                'action': 'movies_menu',
                'description': 'Browse standalone movies and films',
                'icon': 'DefaultMovies.png',
            },
            'show_series': {
                'label': 'Series',
                'content_type': 'tvshow',
                'action': 'series_menu',
                'description': 'Browse series with multiple episodes',
                'icon': 'DefaultTVShows.png',
            },
            # Kodi uses 'specials' for Dry Bar Comedy Specials
            # If this changes in the future, update accordingly
            'show_specials': {
                'label': 'Dry Bar Comedy Specials',
                'content_type': 'video',
                'action': 'specials_menu',
                'description': 'Browse Dry Bar Comedy Specials',
                'icon': 'DefaultAddonLyrics.png',  # Microphone icon, best we could do
            },
            'show_podcasts': {
                'label': 'Podcasts',
                'content_type': 'video',
                'action': 'podcast_menu',
                'description': 'Browse Podcast content',
                'icon': 'DefaultMusicSources.png',
            },
            'show_livestreams': {
                'label': 'Livestreams',
                'content_type': 'video',
                'action': 'livestream_menu',
                'description': 'Browse Livestream content',
                'icon': 'DefaultPVRGuide.png',
            },
            'show_continue_watching': {
                'label': 'Continue Watching',
                'content_type': 'video',
                'action': 'continue_watching_menu',
                'description': 'Continue watching your in-progress content',
                'icon': 'DefaultInProgressShows.png',
            },
            'show_watchlist': {
                'label': 'Watchlist',
                'content_type': 'video',
                'action': 'watchlist_menu',
                'description': 'Browse your saved watchlist items',
                'icon': 'DefaultVideoPlaylists.png',
            },
            'show_top_picks': {
                'label': 'Top Picks For You',
                'content_type': 'video',
                'action': 'top_picks_menu',
                'description': 'Browse top picks for you',
                'icon': 'DefaultMusicTop100.png',
            },
            'show_other_content': {
                'label': 'Other Content',
                'content_type': 'video',
                'action': 'other_content_menu',
                'description': 'Other content types not categorized above',
            },
        }

        self.menu_items = []

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
        '''Set the Angel Studios interface for this UI helper'''
        self.angel_interface = angel_interface

    def create_plugin_url(self, **kwargs):
        """Create a URL for calling the plugin recursively"""
        return f'{self.kodi_url}?{urlencode(kwargs)}'

    def _cache_ttl(self):
        """Return timedelta for current cache expiration setting."""
        try:
            hours = self.addon.getSettingInt('cache_expiration_hours')
            if not hours:
                self.log.warning(f"cache_expiration_hours was falsy ({hours!r}); defaulting to 12")
                hours = 12
        except Exception as exc:
            self.log.warning(f"Failed to read cache_expiration_hours; defaulting to 12: {exc}")
            hours = 12

        return timedelta(hours=hours)

    def _get_debug_mode(self):
        """Return debug mode string in {'off','debug','trace'}"""
        try:
            value = self.addon.getSettingString('debug_mode')
        except Exception as exc:
            self.log.warning(f"debug_mode read failed; defaulting to off: {exc}")
            value = 'off'

        value = (value or 'off').lower()
        return value if value in {'off', 'debug', 'trace'} else 'off'

    def _is_debug(self):
        """Return True if debug or trace mode is enabled."""
        mode = self._get_debug_mode()
        return mode in {'debug', 'trace'}

    def _is_trace(self):
        """Return True only when trace mode is enabled."""
        return self._get_debug_mode() == 'trace'

    def _cache_enabled(self):
        """Return True if cache is enabled based on addon settings.

        Interprets `disable_cache` as a boolean; defaults to enabled when
        the setting is missing, unreadable, or a non-bool value.
        """
        try:
            disabled_val = self.addon.getSettingBool('disable_cache')
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
                if any(secret in key_lower for secret in ('password', 'authorization', 'cookie', 'token')):
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
        ts = time.strftime('%Y%m%dT%H%M%S')
        fname = f"trace_{ts}_{int(time.time()*1000)%1000}.json"
        path = os.path.join(self.trace_dir, fname)
        try:
            with open(path, 'w', encoding='utf-8') as fp:
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
        self.menu_items.append({
            'label': 'Settings',
            'content_type': 'video',
            'action': 'settings',
            'description': 'Open addon settings',
            'icon': self.default_settings_icon
        })

    def main_menu(self):
        """Show the main menu with content type options"""

        # Rebuild menu items to reflect current settings
        self._load_menu_items()

        # Create directory items for each menu option
        for item in self.menu_items:
            # Create list item
            list_item = xbmcgui.ListItem(label=item['label'])

            if item.get('icon'):
                list_item.setArt({'icon': item['icon'], 'thumb': item['icon']})

            # Set info tags
            info_tag = list_item.getVideoInfoTag()
            info_tag.setPlot(item['description'])

            # Create URL
            self.log.debug(f"Creating URL for action: {item['action']}, content_type: {item['content_type']}")
            url = self.create_plugin_url(base_url=self.kodi_url, action=item['action'], content_type=item['content_type'])

            # Add to directory
            xbmcplugin.addDirectoryItem(self.handle, url, list_item, True)

        # Finish directory
        xbmcplugin.endOfDirectory(self.handle)

    def watchlist_menu(self):
        """Placeholder for user watchlist until API support is added."""
        self.log.info("Watchlist menu requested, but not yet implemented.")
        self.show_error("Watchlist is not available yet.")

    def continue_watching_menu(self):
        """Placeholder for continue watching until API support is added."""
        self.log.info("Continue watching menu requested, but not yet implemented.")
        self.show_error("Continue Watching is not available yet.")

    def top_picks_menu(self):
        """Placeholder for top picks until API support is added."""
        self.log.info("Top picks menu requested, but not yet implemented.")
        self.show_error("Top Picks is not available yet.")

    def other_content_menu(self):
        """Placeholder for other content until API support is added."""
        self.log.info("Other content menu requested, but not yet implemented.")
        self.show_error("Other Content is not available yet.")

    def projects_menu(self, content_type=None):
        """Display a menu of projects based on content type, with persistent caching."""
        try:
            self.log.info("Fetching projects from AngelStudiosInterface...")
            angel_menu_content_mapper = {
                'movies': 'movie',
                'series': 'series',
                'specials': 'special'
            }
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
                    project_type=angel_menu_content_mapper.get(content_type, 'videos'))
                if cache_enabled:
                    self.cache.set(cache_key, projects, expiration=self._cache_ttl())
            try:
                self.log.info(f"Projects: {json.dumps(projects, indent=2)}")
            except TypeError:
                self.log.info(f"Projects: <non-serializable type {type(projects).__name__}>")

            if not projects:
                self.show_error(f"No projects found for content type: {content_type}")
                return

            self.log.info(f"Processing {len(projects)} \'{content_type if content_type else 'all content type'}\' projects")

            # Set content type for the plugin
            kodi_content_type = 'movies' if content_type == 'movies' else 'tvshows' if content_type == 'series' else 'videos'
            xbmcplugin.setContent(self.handle, kodi_content_type)
            # Create list items for each project
            for project in projects:
                self.log.info(f"Processing project: {project['name']}")
                self.log.debug(f"Project dictionary: {json.dumps(project, indent=2)}")

                # Create list item
                list_item = xbmcgui.ListItem(label=project['name'])
                info_tag = list_item.getVideoInfoTag()
                info_tag.setMediaType(kodi_content_mapper.get(project['projectType'], 'video'))
                self._process_attributes_to_infotags(list_item, project)

                # Create URL for seasons listing
                url = self.create_plugin_url(
                    base_url=self.kodi_url,
                    action='seasons_menu',
                    content_type=content_type,
                    project_slug=project['slug']
                )

                # Add to directory
                xbmcplugin.addDirectoryItem(self.handle, url, list_item, True)

            xbmcplugin.addSortMethod(self.handle, xbmcplugin.SORT_METHOD_LABEL)
            xbmcplugin.endOfDirectory(self.handle)

        except Exception as e:
            self.log.error(f"Error listing {content_type}: {e}")
            self.show_error(f"Failed to load {angel_menu_content_mapper.get(content_type)}: {str(e)}")
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
            kodi_content_type = 'movies' if content_type == 'movies' else 'tvshows' if content_type == 'series' else 'videos'
            self.log.info(f"Setting content type for Kodi: {content_type} ({kodi_content_type})")
            xbmcplugin.setContent(self.handle, kodi_content_type)

            if len(project.get('seasons', [])) == 1:
                self.log.info(f"Single season found: {project['seasons'][0]['name']}")
                self.episodes_menu(content_type, project['slug'], season_id=project['seasons'][0]['id'])
            else:
                for season in project.get('seasons', []):
                    self.log.info(f"Processing season: {season['name']}")
                    self.log.debug(f"Season dictionary: {json.dumps(season, indent=2)}")
                    # Create list item
                    list_item = xbmcgui.ListItem(label=season['name'])
                    info_tag = list_item.getVideoInfoTag()
                    info_tag.setMediaType(kodi_content_mapper.get(content_type, 'video'))
                    self._process_attributes_to_infotags(list_item, season)


                    # Create URL for seasons listing
                    url = self.create_plugin_url(
                        base_url=self.kodi_url,
                        action='episodes_menu',
                        content_type=content_type,
                        project_slug=project_slug,
                        season_id=season['id']
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

            season = next((s for s in project.get('seasons', []) if s.get('id') == season_id), None)
            if not season:
                self.log.error(f"Season not found: {season_id}")
                self.show_error(f"Season not found: {season_id}")
                return

            self.log.info(f"Processing {len(season.get('episodes', []))} episodes for project: {project_slug}, season: {season_id}")
            kodi_content_type = 'movies' if content_type == 'movies' else 'tvshows' if content_type == 'series' else 'videos'
            self.log.info(f"Setting content type for Kodi: {content_type} ({kodi_content_type})")
            xbmcplugin.setContent(self.handle, kodi_content_type)

            episodes_list = season.get('episodes', [])
            for idx, episode in enumerate(episodes_list):
                episode_available = bool(episode.get('source'))
                list_item = self._create_list_item_from_episode(
                    episode,
                    project=None,
                    content_type=content_type,
                    stream_url=None,
                    is_playback=False
                )

                # Create URL for seasons listing
                url = self.create_plugin_url(
                    base_url=self.kodi_url,
                    action='play_episode' if episode_available else 'info',
                    content_type=content_type,
                    project_slug=project_slug,
                    season_id=season['id'],
                    episode_id=episode['id'],
                    episode_guid=episode.get('guid', '')
                )

                xbmcplugin.addDirectoryItem(self.handle, url, list_item, False)

            if season['episodes'][0].get('seasonNumber', 0) > 0:
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

    def play_episode(self, episode_guid, project_slug):
        """Play an episode with enhanced metadata, with persistent caching."""
        try:
            cache_key = f"episode_data_{episode_guid}_{project_slug}"
            data = None
            if self._cache_enabled():
                data = self.cache.get(cache_key)
                if data:
                    self.log.debug(f"Cache hit for {cache_key}")
                else:
                    self.log.debug(f"Cache miss for {cache_key}")
            else:
                self.log.debug("Cache disabled; bypassing episode cache")

            if data is None:
                data = self.angel_interface.get_episode_data(episode_guid, project_slug)
                if self._cache_enabled():
                    self.cache.set(cache_key, data, expiration=self._cache_ttl())
            if not data:
                self.log.info(f"No data: {data}")
                self.log.info(f"Episode not found: {episode_guid}")
                self.show_error(f"Episode not found: {episode_guid}")
                return
        except Exception as e:
            self.log.error(f"Error playing episode {episode_guid}: {e}")
            self.show_error(f"Failed to play episode: {str(e)}")
            return

        # Extract stream URL and metadata
        source = data.get('episode', {}).get('source')
        if not source or not source.get('url'):
            self.show_error("No playable stream URL found for this episode")
            self.log.error(f"No stream URL for episode: {episode_guid} in project: {project_slug}")
            print("No stream URL found")
            print(f"Data: {data}")
            return

        stream_url = source['url']
        self.log.info(f"Playing episode: {data['episode']['name']} from project: {project_slug}")
        self.play_video(episode_data=data)

    def play_video(self, stream_url=None, episode_data=None):
        """Play a video stream with optional enhanced metadata"""
        if stream_url and episode_data:
            raise ValueError("Provide only stream_url or episode_data, not both")
        if not stream_url and not episode_data:
            raise ValueError("Must provide either stream_url or episode_data to play video")
        try:
            if episode_data:
                # Enhanced playback with metadata
                episode = episode_data.get('episode', {})
                project = episode_data.get('project', {})

                # Create ListItem with metadata using helper
                list_item = self._create_list_item_from_episode(
                    episode=episode,
                    project=project,
                    content_type=None,
                    is_playback=True
                )

                self.log.info(f"Playing enhanced video: {episode.get('subtitle', 'Unknown')} from project: {project.get('name', 'Unknown')}")
            elif stream_url:
                # Basic playback (fallback for play_content)
                list_item = xbmcgui.ListItem(offscreen=True)
                list_item.setPath(stream_url)
                list_item.setIsFolder(False)
                list_item.setProperty('IsPlayable', 'true')
                list_item.addStreamInfo('video', {'codec': 'h264'})

                self.log.info(f"Playing basic video from URL: {stream_url}")

            # Resolve and play
            xbmcplugin.setResolvedUrl(self.handle, True, listitem=list_item)
            self.log.info(f"Playing stream: {list_item.getPath()}")

        except Exception as e:
            self.show_error(f"Error playing video: {e}")
            self.log.error(f"Error playing video: {e}")

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
        if not self.angel_interface or not getattr(self.angel_interface, 'angel_studios_session', None):
            xbmcgui.Dialog().ok("Angel Studios Session Details", "No session available.")
            return

        try:
            details = self.angel_interface.angel_studios_session.get_session_details()
        except Exception:
            xbmcgui.Dialog().ok("Angel Studios Session Details", "Unable to read session details.")
            return

        login_email = details.get('login_email', 'Unknown')
        account_id = details.get('account_id', 'Unknown')
        lines = [f"{'Login email:':<18} {login_email}"]
        if account_id:
            lines.append(f"{'Account ID:':<18} {account_id}")

        lines.append(f"{'Authenticated:':<18} {details.get('authenticated', False)}")

        expires_at_local = details.get('expires_at_local', 'Unknown')
        expires_at_utc = details.get('expires_at_utc', 'Unknown')
        expires_in_td = details.get('expires_in_human', 'Unknown')
        expires_in_seconds = details.get('expires_in_seconds')
        issued_at_local = details.get('issued_at_local', 'Unknown')
        issued_at_utc = details.get('issued_at_utc', 'Unknown')

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

        if details.get('cookie_names'):
            lines.append("Cookies:")
            for cookie_name in details['cookie_names']:
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

    def _create_list_item_from_episode(self, episode, project=None, content_type=None, stream_url=None, is_playback=False):
        """
        Unified helper to create a ListItem from an episode dict.
        - episode: Raw episode dict.
        - project: Optional project dict (for playback metadata).
        - content_type: For directory media type.
        - stream_url: If provided, enables playback mode.
        - is_playback: True for playback mode (sets offscreen, path, etc.).
        """
        self.log.info(f"Creating ListItem for episode: {episode.get('name', 'Unknown Episode')}, is_playback={is_playback}")
        episode_available = bool(episode.get('source'))
        episode_subtitle = episode.get('subtitle', episode.get('name', 'Unknown Episode'))

        # If the episode is not available (no source), indicate that in the subtitle with italics.
        if not episode_available:
            episode_subtitle = f"[I] {episode_subtitle} (Unavailable)[/I]"

        # Both directory items and playback items must be set to IsPlayable true
        # if the episode is available.
        list_item = xbmcgui.ListItem(label=episode_subtitle, offscreen=is_playback)
        list_item.setProperty('IsPlayable', 'true' if episode_available else 'false')

        # Create ListItem
        if is_playback:
            quality_pref = self._get_quality_pref()
            quality_mode = quality_pref['mode']
            target_height = quality_pref['target_height']
            manifest_url = (episode.get('source') or {}).get('url', stream_url)
            selected_url = manifest_url

            list_item.setIsFolder(False)

            if manifest_url:
                self.log.info(f"Loading Manifest: {manifest_url}")

            use_isa = xbmcaddon.Addon().getSettingBool('use_isa')
            isa_ready = False
            stream_selection_type = None

            if use_isa:
                isa_ready = self._ensure_isa_available('hls')
                if not isa_ready:
                    isa_ready = xbmc.getCondVisibility('System.HasAddon(inputstream.adaptive)')
                    if isa_ready:
                        self.log.info("ISA detected via System.HasAddon; proceeding without inputstreamhelper")

                if isa_ready:
                    if quality_mode == 'manual':
                        stream_selection_type = 'ask-quality'
                    elif quality_mode == 'fixed':
                        stream_selection_type = 'fixed-res'
                    else:
                        stream_selection_type = 'adaptive'

                    if manifest_url:
                        list_item.setPath(manifest_url)
                    list_item.setProperty('inputstream', 'inputstream.adaptive')
                    list_item.setProperty('inputstream.adaptive.manifest_type', 'hls')
                    if stream_selection_type:
                        list_item.setProperty('inputstream.adaptive.stream_selection_type', stream_selection_type)
                    if target_height and quality_mode != 'manual':
                        chooser_map = {
                            1080: '1080p',
                            720: '720p',
                            480: '480p',
                            360: '360p'
                        }
                        chooser_value = chooser_map.get(target_height)
                        if chooser_value:
                            list_item.setProperty('inputstream.adaptive.chooser_resolution_max', chooser_value)
                            list_item.setProperty('inputstream.adaptive.chooser_resolution_secure_max', chooser_value)
                    list_item.setMimeType('application/vnd.apple.mpegurl')
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
            video_stream_detail.setCodec('h264')
            video_stream_detail.setWidth(1920)
            video_stream_detail.setHeight(1080)
            info_tag = list_item.getVideoInfoTag()
            info_tag.addVideoStream(video_stream_detail)

            # Resume
            if episode.get('watch_position'):
                info_tag.setResumePoint(episode['watch_position'])
        else:
            list_item.setIsFolder(True)

        # Set common metadata
        self._process_attributes_to_infotags(list_item, episode)

        # Set media type and additional metadata
        info_tag = list_item.getVideoInfoTag()
        if episode_available:
            info_tag.setDuration(episode.get('source').get('duration', 0))
        if is_playback:
            info_tag.setMediaType('video')
            # Additional playback metadata from project
            if project:
                info_tag.setTvShowTitle(project.get('name'))
        else:
            info_tag.setMediaType(kodi_content_mapper.get(content_type, 'video'))
            info_tag.setTitle(episode_subtitle)

        return list_item

    def _get_quality_pref(self):
        """Return dict with 'mode' and 'target_height'. mode in {'auto','fixed','manual'}."""
        try:
            addon = xbmcaddon.Addon()
            getter = getattr(addon, 'getSettingString', None)
            quality_value = getter('video_quality') if callable(getter) else addon.getSetting('video_quality')
        except Exception:
            quality_value = 'auto'

        quality_value = (quality_value or 'auto').lower()
        mapping = {
            '1080p': {'mode': 'fixed', 'target_height': 1080},
            '720p': {'mode': 'fixed', 'target_height': 720},
            '480p': {'mode': 'fixed', 'target_height': 480},
            '360p': {'mode': 'fixed', 'target_height': 360},
            'manual': {'mode': 'manual', 'target_height': None},
            'auto': {'mode': 'auto', 'target_height': None},
        }
        return mapping.get(quality_value, {'mode': 'auto', 'target_height': None})

    def _process_attributes_to_infotags(self, list_item, info_dict):
        """
        Set VideoInfoTag attributes from a dictionary using known setters.
        Only sets attributes present in the info_dict.
        """
        self.log.info(f"Processing attributes for list item: {list_item.getLabel()}")
        self.log.debug(f"Attribute dict: {info_dict}")
        info_tag = list_item.getVideoInfoTag()
        mapping = {
            'media_type': info_tag.setMediaType,
            'name': info_tag.setTitle,
            'theaterDescription': info_tag.setPlot,
            'description': info_tag.setPlot,
            'year': info_tag.setYear,
            'genres': info_tag.setGenres,
            'contentRating': info_tag.setMpaa,
            'original_title': info_tag.setOriginalTitle,
            'sort_title': info_tag.setSortTitle,
            'tagline': info_tag.setTagLine,
            'duration': info_tag.setDuration,
            'cast': info_tag.setCast,
            'episode': info_tag.setEpisode,
            'episodeNumber': info_tag.setEpisode,
            'season': info_tag.setSeason,
            'seasonNumber': info_tag.setSeason,
            'tvshowtitle': info_tag.setTvShowTitle,
            'premiered': info_tag.setPremiered,
            'rating': info_tag.setRating,
            'votes': info_tag.setVotes,
            'trailer': info_tag.setTrailer,
            'playcount': info_tag.setPlaycount,
            'unique_ids': info_tag.setUniqueIDs,
            'imdbnumber': info_tag.setIMDBNumber,
            'dateadded': info_tag.setDateAdded
        }
        art_dict = {}

        for key, value in info_dict.items():
            self.log.debug(f"Processing key: {key} with value: \'{value}\'")
            # Handle metadata keys that have setters
            if key == 'metadata':
                for meta_key, meta_value in value.items():
                    if meta_key in mapping and meta_value:
                        mapping[meta_key](meta_value)
            # Handle artwork
            elif 'Cloudinary' in key and value:
                if key in ['discoveryPosterCloudinaryPath', 'posterCloudinaryPath']:
                    art_dict['poster'] = self.angel_interface.get_cloudinary_url(value)
                elif key in ['discoveryPosterLandscapeCloudinaryPath', 'posterLandscapeCloudinaryPath']:
                    art_dict['landscape'] = self.angel_interface.get_cloudinary_url(value)
                    art_dict['fanart'] = self.angel_interface.get_cloudinary_url(value)
                elif key == 'logoCloudinaryPath':
                    art_dict['logo'] = self.angel_interface.get_cloudinary_url(value)
                    art_dict['clearlogo'] = self.angel_interface.get_cloudinary_url(value)
                    art_dict['icon'] = self.angel_interface.get_cloudinary_url(value)
                else:
                    self.log.info(f"Unknown Cloudinary key: {key}, skipping")
            elif key == 'seasonNumber' and value == 0:
                self.log.info("Season is 0, skipping season info")
            elif key in mapping:
                mapping[key](value)
            else:
                self.log.debug(f"No known processor for key: {key}, skipping")

        # Set artwork if available
        if art_dict:
            self.log.debug(f"Setting artwork: {art_dict}")
            list_item.setArt(art_dict)
        return
