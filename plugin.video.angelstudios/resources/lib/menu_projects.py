"""
Projects Menu Handler for Angel Studios Kodi addon.
Handles all project listing and related operations.
"""

import json
from urllib.parse import urlencode

import xbmc       # type: ignore
import xbmcgui    # type: ignore
import xbmcplugin # type: ignore

from kodi_utils import timed, TimedBlock
from menu_utils import MenuUtils


class ProjectsMenu(MenuUtils):
    """Handles project menu operations with granular performance tracking."""

    def __init__(self, parent):
        """
        Initialize Projects Menu Handler.
        Takes the parent KodiUIInterface instance for shared state.
        """
        # super().__init__(parent)
        self.parent = parent
        self.kodi_handle = parent.handle
        self.kodi_url = parent.kodi_url
        self.log = parent.log

        # Performance metrics storage for enhanced logging
        self._perf_metrics = {}

    def handle(self, content_type=""):
        """Display a menu of projects based on content type, with persistent caching."""
        # Clear previous metrics
        self._perf_metrics.clear()

        try:
            projects, was_cached = self._fetch_projects_data(content_type)
            if projects is None:
                return True
            self._render_projects_menu(projects, content_type)
            if not was_cached:
                self._defer_cache_operations(projects, content_type)
            self._defer_prefetch_operations(projects)

        except Exception as e:
            self.log.error(f"Error listing {content_type}: {e}")
            self.parent.show_error(f"Failed to load {self._get_angel_project_type(content_type)}: {str(e)}")

        return True

    def _fetch_projects_data(self, content_type):
        """Fetch projects data with caching."""
        cache_key = f"projects_{content_type or 'all'}"
        cache_enabled = self.parent._cache_enabled()
        projects = None
        was_cached = False
        if cache_enabled:
            projects = self.parent.cache_manager.cache.get(cache_key)
            if projects:
                self.log.debug(f"Cache hit for {cache_key}")
                was_cached = True
            else:
                self.log.debug(f"Cache miss for {cache_key}")
        else:
            self.log.debug("Cache disabled; bypassing projects cache")

        if projects:
            self.log.info(f"Using cached projects for content type: {content_type}")
        else:
            self.log.info(f"Fetching projects from AngelStudiosInterface for content type: {content_type}")
            with TimedBlock('projects_api_fetch'):
                projects = self.parent.angel_interface.get_projects(project_type=self._get_angel_project_type(content_type))
            # Cache will be set deferred after UI rendering
        try:
            self.log.info(f"Projects: {json.dumps(projects, indent=2)}")
        except TypeError:
            self.log.info(f"Projects: <non-serializable type {type(projects).__name__}>")

        if not projects:
            self.parent.show_error(f"No projects found for content type: {content_type}")
            return None, False

        # Store metrics for performance logging
        self._perf_metrics['projects_count'] = len(projects)

        return projects, was_cached

    def _render_projects_menu(self, projects, content_type):
        """Render the projects menu UI."""
        # Set content type for the plugin
        kodi_content_type = (
            "movies" if content_type == "movies" else "tvshows" if content_type == "series" else "videos"
        )
        xbmcplugin.setContent(self.kodi_handle, kodi_content_type)

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
            xbmcplugin.addDirectoryItem(self.kodi_handle, url, list_item, True)

        xbmcplugin.addSortMethod(self.kodi_handle, xbmcplugin.SORT_METHOD_LABEL)
        xbmcplugin.endOfDirectory(self.kodi_handle)

    def _defer_cache_operations(self, projects, content_type):
        """Deferred cache operations after UI rendering."""
        cache_key = f"projects_{content_type or 'all'}"
        # Note: We don't check if already cached since we just fetched it
        with TimedBlock('projects_deferred_cache_write'):
            self.parent.cache_manager.cache.set(cache_key, projects, expiration=self.parent._cache_ttl())

    def _defer_prefetch_operations(self, projects):
        """Deferred prefetch operations after UI rendering."""
        try:
            enable_prefetch = self.parent.addon.getSettingBool("enable_prefetch")
            if enable_prefetch:
                with TimedBlock('projects_prefetch'):
                    max_count = self.parent.addon.getSettingInt("prefetch_project_count") or 5
                    if max_count <= 0:
                        self.log.warning(f"prefetch_project_count was {max_count}; defaulting to 5")
                        max_count = 5
                    slugs = [p.get("slug") for p in projects if p.get("slug")]
                    self.parent._deferred_prefetch_project(slugs, max_count)
        except Exception as exc:
            self.log.warning(f"prefetch settings read failed; skipping prefetch: {exc}")

    def _get_projects_metrics(self, result, elapsed_ms, *args, **kwargs):
        """Extract performance metrics for projects_menu function."""
        count = self._perf_metrics.get('projects_count', 0)
        if count > 0:
            per_record = elapsed_ms / count
            return {
                'records': count,
                'per_record': per_record
            }
        return {}

    def create_plugin_url(self, **kwargs):
        """Create a URL for calling the plugin recursively"""
        return f"{self.kodi_url}?{urlencode(kwargs)}"