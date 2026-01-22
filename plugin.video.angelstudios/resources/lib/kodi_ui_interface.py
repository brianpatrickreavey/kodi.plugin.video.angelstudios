"""
Kodi UI helper functions for Angel Studios addon.
Handles all Kodi-specific UI operations and list item creation.
"""

import json  # noqa: F401
import os

import xbmcaddon  # type: ignore
import xbmcgui  # type: ignore  # noqa: F401
import xbmcvfs  # type: ignore

import kodi_menu_handler
import kodi_playback_handler
import kodi_cache_manager
import kodi_ui_helpers


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
        self.ui_helpers = kodi_ui_helpers.KodiUIHelpers(self)

        # Log initialization
        self.log.info("KodiUIInterface initialized")
        self.log.debug(f"{self.handle=}, {self.kodi_url=}")

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
        return self.playback_handler._ensure_isa_available(manifest_type)

    def setAngelInterface(self, angel_interface):
        """Set the Angel Studios interface for this UI helper"""
        return self.ui_helpers.setAngelInterface(angel_interface)

    def create_plugin_url(self, **kwargs):
        """Create a URL for calling the plugin recursively"""
        return self.ui_helpers.create_plugin_url(**kwargs)

    def _cache_ttl(self):
        """Return timedelta for current cache expiration setting."""
        return self.cache_manager._cache_ttl()

    def _project_cache_ttl(self):
        """Return timedelta for project cache expiration."""
        return self.cache_manager._project_cache_ttl()

    def _episode_cache_ttl(self):
        """Return timedelta for episode cache expiration."""
        return self.cache_manager._episode_cache_ttl()

    def _resume_watching_cache_ttl(self):
        """Return timedelta for resume watching cache expiration (5 minutes)."""
        from datetime import timedelta
        return timedelta(minutes=5)

    def get_resume_watching(self, first=10, after=None):
        """Get resume watching data with caching (5 minute TTL)."""
        cache_key = f"resume_watching_{first}_{after or 'none'}"
        cache_enabled = self._cache_enabled()

        if cache_enabled:
            cached_data = self.cache_manager.cache.get(cache_key)
            if cached_data is not None:
                self.log.debug(f"Cache hit for {cache_key}", category="cache")
                return cached_data
            else:
                self.log.debug(f"Cache miss for {cache_key}", category="cache")

        # Fetch from API
        self.log.info(f"Fetching resume watching data from AngelStudiosInterface: first={first}, after={after}")
        data = self.angel_interface.get_resume_watching(first=first, after=after)

        # Cache the result
        if data and cache_enabled:
            self.cache_manager.cache.set(cache_key, data, expiration=self._resume_watching_cache_ttl())

        return data

    def _get_angel_project_type(self, menu_content_type):
        """Map menu content type to Angel Studios project type for API calls."""
        return self.ui_helpers._get_angel_project_type(menu_content_type)

    def _get_kodi_content_type(self, content_type):
        """Map content type to Kodi media type for info tags."""
        return self.ui_helpers._get_kodi_content_type(content_type)

    def _get_debug_mode(self):
        """Return debug mode string in {'off','debug','trace'}"""
        return self.ui_helpers._get_debug_mode()

    def _is_debug(self):
        """Return True if debug or trace mode is enabled."""
        return self.ui_helpers._is_debug()

    def _is_trace(self):
        """Return True only when trace mode is enabled."""
        return self.ui_helpers._is_trace()

    def _cache_enabled(self):
        """Return True if cache is enabled based on addon settings.

        Interprets `disable_cache` as a boolean; defaults to enabled when
        the setting is missing, unreadable, or a non-bool value.
        """
        return self.cache_manager._cache_enabled()

    def _ensure_trace_dir(self):
        """Ensure the trace directory exists if trace mode is active.

        Returns True when the directory is present or created successfully,
        else False. No-op when trace mode is off.
        """
        return self.ui_helpers._ensure_trace_dir()

    def _redact_sensitive(self, data):
        """Recursively redact sensitive keys in dicts/lists."""
        return self.ui_helpers._redact_sensitive(data)

    def _trim_trace_files(self, max_files=50):
        """Trim old trace files, keeping only the most recent `max_files`.

        Safe to call even if the directory does not exist or file operations fail.
        """
        return self.ui_helpers._trim_trace_files(max_files)

    def _trace_callback(self, payload):
        """Trace callback to persist a redacted payload when in trace mode.

        Redacts sensitive fields, writes JSON to the trace directory, and
        trims older entries. No-ops when trace mode or directory setup is off.
        """
        return self.ui_helpers._trace_callback(payload)

    def get_trace_callback(self):
        """Expose tracer for API layer; safe to use even when trace is off."""
        return self.ui_helpers.get_trace_callback()

    def show_error(self, message, title="Angel Studios"):
        """Show error dialog to user"""
        return self.ui_helpers.show_error(message, title)

    def show_notification(self, message, title="Angel Studios", time=5000):
        """Show notification to user"""
        return self.ui_helpers.show_notification(message, title, time)

    def show_auth_details_dialog(self):
        """Show authentication/session details in a dialog."""
        return self.ui_helpers.show_auth_details_dialog()

    def clear_cache(self):
        """Clear addon SimpleCache entries."""
        return self.cache_manager.clear_cache()

    def clear_debug_data(self):
        """Remove trace files from the temp directory."""
        return self.ui_helpers.clear_debug_data()

    def _get_project(self, project_slug):
        """Helper function to handle fetching and caching project data."""
        return self.cache_manager._get_project(project_slug)

    def _get_quality_pref(self):
        """Return dict with 'mode' and 'target_height'. mode in {'auto','fixed','manual'}."""
        return self.playback_handler._get_quality_pref()

    def _normalize_contentseries_episode(self, episode):
        """Normalize ContentSeries episode dict to expected keys."""
        return self.ui_helpers._normalize_contentseries_episode(episode)

    def _deferred_prefetch_project(self, project_slugs, max_count=None):
        """Prefetch and cache project data for given slugs in the background."""
        return self.cache_manager._deferred_prefetch_project(project_slugs, max_count)

    def clear_cache_with_notification(self):
        """Clear cache and notify user with outcome."""
        return self.cache_manager.clear_cache_with_notification()

    def force_logout_with_notification(self):
        """Force local logout via angel_interface and notify user."""
        return self.ui_helpers.force_logout_with_notification()

    def clear_debug_data_with_notification(self):
        """Clear debug trace files and log outcome; notify on success."""
        return self.ui_helpers.clear_debug_data_with_notification()
