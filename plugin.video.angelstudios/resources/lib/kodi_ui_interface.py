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

import kodi_menu_handler
import kodi_playback_handler
import kodi_cache_manager

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

        self.addon = xbmcaddon.Addon()
        addon_path = xbmcvfs.translatePath(self.addon.getAddonInfo("path"))
        self.default_icon = os.path.join(addon_path, "resources", "images", "icons", "Angel_Studios_Logo.png")
        self.default_settings_icon = "DefaultAddonService.png"

        # Initialize handlers
        self.menu_handler = kodi_menu_handler.KodiMenuHandler(self)
        self.playback_handler = kodi_playback_handler.KodiPlaybackHandler(self)
        self.cache_manager = kodi_cache_manager.KodiCacheManager(self)

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

        # Initialize handlers
        self.menu_handler = kodi_menu_handler.KodiMenuHandler(self)
        self.playback_handler = kodi_playback_handler.KodiPlaybackHandler(self)

    def main_menu(self):
        """Show the main menu with content type options"""
        return self.menu_handler.main_menu()

    def projects_menu(self, content_type=""):
        """Display a menu of projects based on content type, with persistent caching."""
        return self.menu_handler.projects_menu(content_type)

    def seasons_menu(self, content_type, project_slug):
        """Display a menu of seasons for a specific project, with persistent caching."""
        return self.menu_handler.seasons_menu(content_type, project_slug)

    def episodes_menu(self, content_type, project_slug, season_id=None):
        """Display a menu of episodes for a specific season, with persistent caching."""
        return self.menu_handler.episodes_menu(content_type, project_slug, season_id)

    def watchlist_menu(self):
        """Placeholder for user watchlist until API support is added."""
        return self.menu_handler.watchlist_menu()

    def continue_watching_menu(self, after=None):
        """Display continue watching menu with pagination."""
        return self.menu_handler.continue_watching_menu(after)

    def top_picks_menu(self):
        """Placeholder for top picks until API support is added."""
        return self.menu_handler.top_picks_menu()

    def play_episode(self, episode_guid, project_slug):
        """Play an episode using cached project data (no separate API call)."""
        return self.playback_handler.play_episode(episode_guid, project_slug)

    def play_video(self, stream_url=None, episode_data=None):
        """Play a video stream with optional enhanced metadata"""
        return self.playback_handler.play_video(stream_url, episode_data)

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
        """Return timedelta for current cache expiration setting."""
        return self.cache_manager._cache_ttl()

    def _project_cache_ttl(self):
        """Return timedelta for project cache expiration."""
        return self.cache_manager._project_cache_ttl()

    def _episode_cache_ttl(self):
        """Return timedelta for episode cache expiration."""
        return self.cache_manager._episode_cache_ttl()

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
            self.log.warning(f"disable_cache returned non-bool; assuming cache enabled: {exc}")
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
        return self.cache_manager.clear_cache()

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
        """Helper function to handle fetching and caching project data."""
        return self.cache_manager._get_project(project_slug)

    def _get_quality_pref(self):
        """Return dict with 'mode' and 'target_height'. mode in {'auto','fixed','manual'}."""
        try:
            addon = self.addon
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
        return self.cache_manager._deferred_prefetch_project(project_slugs, max_count)

    def clear_cache_with_notification(self):
        """Clear cache and notify user with outcome."""
        return self.cache_manager.clear_cache_with_notification()

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
