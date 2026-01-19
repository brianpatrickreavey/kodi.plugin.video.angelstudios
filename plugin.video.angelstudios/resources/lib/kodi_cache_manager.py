"""
Kodi Cache Manager for Angel Studios addon.
Handles all caching operations and cache management.
"""

from datetime import timedelta

from simplecache import SimpleCache  # type: ignore


class KodiCacheManager:
    """Handles caching operations and cache management for Kodi UI."""

    def __init__(self, parent):
        """
        Initialize the Kodi Cache Manager.
        Takes the parent KodiUIInterface instance for shared state.
        """
        self.parent = parent
        self.cache = SimpleCache()  # Initialize cache
        self.log = parent.log
        self.addon = parent.addon

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

    def _set_episode(self, guid, episode):
        """Cache an episode by guid."""
        if self._cache_enabled():
            self.cache.set(f"episode_{guid}", episode, expiration=self._episode_cache_ttl())

    def _get_episode(self, guid):
        """Get cached episode by guid."""
        if self._cache_enabled():
            return self.cache.get(f"episode_{guid}")
        return None

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
            project = self.parent.angel_interface.get_project(project_slug)
            if project and cache_enabled:
                self.cache.set(cache_key, project, expiration=self._cache_ttl())
        else:
            self.log.info(f"Using cached project data for: {project_slug}")
        return project

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

    def clear_cache_with_notification(self):
        """Clear cache and notify user with outcome."""
        result = self.clear_cache()
        if result:
            self.parent.show_notification("Cache cleared.")
            self.log.info("Cache cleared successfully via settings")
        else:
            self.parent.show_notification("Cache clear failed; please try again.")
            self.log.error("Cache clear failed via settings")

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
                    proj = self.parent.angel_interface.get_project(slug)
                except Exception:
                    self.log.debug("API error; abandoning prefetch")
                    break
                if not proj:
                    continue
                if self._cache_enabled():
                    self.cache.set(f"project_{slug}", proj, expiration=self._cache_ttl())
        except Exception as exc:
            self.log.error(f"Project prefetch failed: {exc}")