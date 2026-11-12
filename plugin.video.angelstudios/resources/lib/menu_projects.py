"""
Projects Menu Handler for Angel Studios Kodi addon.
Handles all project listing and related operations.
"""

import json
from urllib.parse import urlencode

import xbmcplugin  # type: ignore

from kodi_utils import TimedBlock
from menu_utils import MenuUtils, watch_page_facts

# Movies, series, and specials can be saved. Episodes, seasons, and trailers cannot.
_WATCHLIST_CONTENT_TYPES = ("movies", "series", "specials")
_TITLE_PROJECT_TYPES = ("movie", "series", "special")


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

        # A catalog cached before title ids were requested cannot add or remove.
        # Read it again once. Membership itself is not taken from this cache.
        if projects and content_type in _WATCHLIST_CONTENT_TYPES and projects_need_title_ids(projects):
            self.log.info("Cached projects are missing title ids; fetching the catalog again")
            projects = None
            was_cached = False

        if projects:
            self.log.info(f"Using cached projects for content type: {content_type}")
        else:
            self.log.info(f"Fetching projects from AngelStudiosInterface for content type: {content_type}")
            with TimedBlock("projects_api_fetch"):
                projects = self.parent.angel_interface.get_projects(
                    project_type=self._get_angel_project_type(content_type)
                )
            # Cache will be set deferred after UI rendering
        try:
            projects_json = json.dumps(projects, indent=2)
            self.log.info("Projects: %s", projects_json)
        except TypeError:
            type_name = type(projects).__name__
            self.log.info(f"Projects: <non-serializable type {type_name}>")

        if not projects:
            self.parent.show_error(f"No projects found for content type: {content_type}")
            return None, False

        # Store metrics for performance logging
        self._perf_metrics["projects_count"] = len(projects)

        return projects, was_cached

    def _render_projects_menu(self, projects, content_type):
        """Render the projects menu UI."""
        # Set content type for the plugin
        kodi_content_type = (
            "movies" if content_type == "movies" else "tvshows" if content_type == "series" else "videos"
        )
        xbmcplugin.setContent(self.kodi_handle, kodi_content_type)
        saved_ids = self._saved_watchlist_ids() if content_type in _WATCHLIST_CONTENT_TYPES else set()

        for project in projects:
            self.log.info(f"Processing project: {project['name']}")
            self.log.debug(f"Project dictionary: {json.dumps(project, indent=2)}")

            # Create list item using unified builder.
            # A movie, series, or special already has its watch-page media type.
            # The mapper below is the directory type, and it would replace movie with video.
            list_item = self._build_list_item_for_content(project, "project")
            if watch_page_facts(project) is None:
                info_tag = list_item.getVideoInfoTag()
                info_tag.setMediaType(self._get_kodi_content_type(project["projectType"]))

            # Create URL for seasons listing
            url = self.create_plugin_url(
                base_url=self.kodi_url,
                action="seasons_menu",
                content_type=content_type,
                project_slug=project["slug"],
            )

            if content_type in _WATCHLIST_CONTENT_TYPES:
                content_id = title_content_id(project)
                if content_id:
                    list_item.addContextMenuItems([self.watchlist_context_item(content_id, content_id in saved_ids)])

            # Add to directory
            xbmcplugin.addDirectoryItem(self.kodi_handle, url, list_item, True)

        xbmcplugin.addSortMethod(self.kodi_handle, xbmcplugin.SORT_METHOD_LABEL)
        xbmcplugin.endOfDirectory(self.kodi_handle)

    def _defer_cache_operations(self, projects, content_type):
        """Deferred cache operations after UI rendering."""
        cache_key = f"projects_{content_type or 'all'}"
        # Note: We don't check if already cached since we just fetched it
        with TimedBlock("projects_deferred_cache_write"):
            self.parent.cache_manager.cache.set(cache_key, projects, expiration=self.parent._cache_ttl())

    def _defer_prefetch_operations(self, projects):
        """Deferred prefetch operations after UI rendering."""
        try:
            enable_prefetch = self.parent.addon.getSettingBool("enable_prefetch")
            if enable_prefetch:
                with TimedBlock("projects_prefetch"):
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
        count = self._perf_metrics.get("projects_count", 0)
        if count > 0:
            per_record = elapsed_ms / count
            return {"records": count, "per_record": per_record}
        return {}

    def create_plugin_url(self, **kwargs):
        """Create a URL for calling the plugin recursively"""
        return f"{self.kodi_url}?{urlencode(kwargs)}"

    def _saved_watchlist_ids(self):
        """Title ids on the watchlist. An unread list leaves every title as Add."""
        getter = getattr(self.parent.angel_interface, "get_default_watchlist", None)
        if not callable(getter):
            return set()
        try:
            items = getter()
        except Exception as exc:
            self.log.warning(f"Could not read the watchlist: {exc}")
            return set()
        if not isinstance(items, list):
            return set()
        saved = set()
        for item in items:
            if isinstance(item, dict) and item.get("content_id"):
                saved.add(item["content_id"])
        return saved


def title_content_id(project):
    """Return the movie, series, or special id Angel uses for the watchlist."""
    if not isinstance(project, dict):
        return None
    title = project.get("title")
    if not isinstance(title, dict):
        return None
    content_id = title.get("id")
    if isinstance(content_id, str) and content_id:
        return content_id
    return None


def projects_need_title_ids(projects):
    """True when this catalog was stored before title ids were requested.

    A title that is present and includes an id key is a current response, even
    when that id is empty. Fetching that catalog again would not add the key.
    """
    if not isinstance(projects, list):
        return False
    for project in projects:
        if not isinstance(project, dict):
            continue
        if project.get("projectType") not in _TITLE_PROJECT_TYPES:
            continue
        if "title" not in project:
            return True
        title = project.get("title")
        if isinstance(title, dict) and "id" not in title:
            return True
    return False
