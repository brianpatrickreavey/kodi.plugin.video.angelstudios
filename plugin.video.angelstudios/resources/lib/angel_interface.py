"""angel_studios_interface.py
This module provides an interface for interacting with the Angel Studios website,
specifically for making HTML and GraphQL queries.
The aim is for this module to be KODI agnostic, meaning it should not depend on KODI-specific libraries.
It should be usable in any Python environment, including unit tests.
This module is designed to be used by the KODI UI Interface, which will handle KODI-specific operations.
It provides methods for authentication, making GraphQL queries, and retrieving project data.
"""

import json
import logging
import math
import os
import re
import sys
from datetime import datetime, timezone
from typing import Any, Optional

import angel_authentication
import requests
import angel_utils

# Import Authentication exceptions
AuthenticationRequiredError = angel_authentication.AuthenticationRequiredError
SessionExpiredError = angel_authentication.SessionExpiredError
InvalidCredentialsError = angel_authentication.InvalidCredentialsError

# Library constants
angel_website_url = "https://www.angel.com"
angel_graphql_url = "https://api.angelstudios.com/graphql"
# The website player posts here. The host is the same API origin as GraphQL.
angel_watch_positions_url = "https://api.angelstudios.com/watch-positions"

# Watchlist rows open the same screen as Movies, Series, or Specials.
_WATCHLIST_MENU_TYPES = {
    "ContentMovie": "movies",
    "ContentSeries": "series",
    "ContentSpecial": "specials",
}


def _viewer_profile_id(token: str) -> Optional[str]:
    """The id Angel expects in the x-viewer-profile-id header.

    The website sends the signed-in user id. On the Angel JWT that id is the
    sub claim, and it matches user.viewerProfiles[].id. A catalog call does
    not need the header. The watchlist calls do.
    """
    try:
        payload = angel_authentication.decode_jwt_payload(token)
    except Exception:
        return None
    if not isinstance(payload, dict):
        return None
    profile_id = payload.get("sub")
    if isinstance(profile_id, str) and profile_id:
        return profile_id
    return None


def _cloudinary_path(image: Any) -> Optional[str]:
    if not isinstance(image, dict):
        return None
    path = image.get("cloudinaryPath")
    if isinstance(path, str) and path:
        return path
    return None


def _watchlist_items(nodes: list) -> list:
    """Keep movie, series, and special rows that can be opened and changed."""
    items = []
    for node in nodes:
        if not isinstance(node, dict):
            continue
        content = node.get("content")
        if not isinstance(content, dict):
            continue
        menu_content_type = _WATCHLIST_MENU_TYPES.get(content.get("__typename"))
        project = content.get("project")
        slug = project.get("slug") if isinstance(project, dict) else None
        content_id = content.get("id")
        if not menu_content_type or not isinstance(slug, str) or not slug:
            continue
        if not isinstance(content_id, str) or not content_id:
            continue
        name = content.get("name")
        description = content.get("description")
        items.append(
            {
                "content_id": content_id,
                "name": name if isinstance(name, str) and name else "Unknown",
                "description": description if isinstance(description, str) else "",
                "project_slug": slug,
                "menu_content_type": menu_content_type,
                "poster_path": _cloudinary_path(content.get("imagePortrait")),
                "landscape_path": _cloudinary_path(content.get("imageLandscape")),
            }
        )
    return items


class AngelStudiosInterface:
    """
    Interface for Angel Studios website HTML and GraphQL queries.
    - GraphQL queries are used to fetch project data, seasons, episodes, and more.
    - helpers translate native graphql queries into useable data
    """

    def __init__(
        self,
        auth_core: angel_authentication.AuthenticationCore,
        logger: Optional[Any] = None,
        query_path=None,
        tracer=None,
        timeout=30,
    ):
        # Use the provided logger, or default to the module logger
        if logger is not None:
            self.log = logger
            self.log.info("Custom logger initialized")
        else:
            # Default to the module logger
            logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)
            self.log = logging.getLogger("AngelStudiosInterface")
            self.log.info("STDOUT logger initialized")
        self.log.debug(f"{self.log=}")

        # Store timeout setting
        self.timeout = timeout

        # Set the tracer function provided by the calling function
        self.tracer = tracer

        # Store the authentication core for session validation
        self.auth_core = auth_core

        # Create a requests session for GraphQL calls
        # The auth core handles token management separately
        self.session = requests.Session()

        # Initialize query path and caches
        self.query_path = query_path or "resources/lib/angel_graphql"
        self._query_file_cache = {}
        self._fragment_file_cache = {}

        # Prepare session with authentication
        self._prepare_authenticated_session()

    def _apply_auth_headers(self, token):
        """Set the bearer token and the viewer profile id, or clear both."""
        if not token:
            self.session.headers.pop("Authorization", None)
            self.session.headers.pop("x-viewer-profile-id", None)
            return
        self.session.headers["Authorization"] = f"Bearer {token}"
        profile_id = _viewer_profile_id(token)
        if profile_id:
            self.session.headers["x-viewer-profile-id"] = profile_id
        else:
            self.session.headers.pop("x-viewer-profile-id", None)

    def _prepare_authenticated_session(self):
        """Prepare the requests session with authentication headers"""
        token = self.auth_core.session_store.get_token()
        if token:
            self._apply_auth_headers(token)
            self.log.info("Session prepared with JWT token")
        else:
            self.log.warning("No JWT token available - session may not be authenticated")

    def _debug_log(self, message, category=None):
        """Helper to log debug messages with optional category support."""
        self.log.debug(message, category=category)  # pyright: ignore[reportCallIssue]

    def _load_query(self, operation: str) -> str:
        """Load and cache a GraphQL query file by operation name."""
        if operation in self._query_file_cache:
            return self._query_file_cache[operation]
        query_file = os.path.join(self.query_path, f"query_{operation}.graphql")
        try:
            with open(query_file, "r") as f:
                query = f.read()
                self._query_file_cache[operation] = query
                return query
        except Exception as e:
            self.log.error(f"Error loading query file '{query_file}': {e}")
            return ""

    def _load_fragment(self, fragment_name: str) -> str:
        """Load and cache a GraphQL fragment file by fragment name."""
        if fragment_name in self._fragment_file_cache:
            return self._fragment_file_cache[fragment_name]
        fragment_path = os.path.join(self.query_path, f"fragment_{fragment_name}.graphql")
        try:
            with open(fragment_path, "r") as f:
                fragment = f.read()
                self._fragment_file_cache[fragment_name] = fragment
                return fragment
        except Exception as e:
            self.log.error(f"Error loading fragment '{fragment_name}' from '{fragment_path}': {e}")
            return ""

    def _trace_request(self, operation, query_dict, status=None, response_data=None, error=None):
        """Helper to trace GraphQL requests without breaking main flow."""
        if not callable(self.tracer):
            return
        try:
            safe_headers = {
                k: v for k, v in self.session.headers.items() if k.lower() not in ("authorization", "cookie")
            }
            trace_payload = {
                "operation": operation,
                "url": angel_graphql_url,
                "status": status,
                "request": {
                    "headers": safe_headers,
                    "body": query_dict,
                },
            }
            if response_data is not None:
                trace_payload["response"] = response_data
            if error is not None:
                trace_payload["error"] = error
            self.tracer(trace_payload)
        except Exception:
            # Tracing must never break main flow
            pass

    def _graphql_query(self, operation: str, variables=None, raw_query=None) -> dict:
        """Generalized GraphQL query executor with automatic fragment loading and caching.

        Args:
            operation: Name of the operation (for loading from file) or operation name for raw queries
            variables: Query variables
            raw_query: Raw GraphQL query string (if provided, operation is used as operationName)
        """
        variables = variables or {}

        # Proactive session validation - refresh token if expiring soon
        try:
            self.auth_core.ensure_valid_session()
            # Update session headers in case token was refreshed
            token = self.auth_core.session_store.get_token()
            if token:
                self._apply_auth_headers(token)
        except AuthenticationRequiredError:
            # If proactive validation fails, re-raise for UI layer to handle
            raise

        if raw_query:
            query = raw_query
        else:
            query = self._load_query(operation)

        # Find all fragment references in the query
        # This regex captures fragment names after '...'
        # It excludes 'on' keyword to avoid matching inline fragments
        # Example: "... FragmentName" will match "FragmentName"
        fragment_names = set(re.findall(r"\.\.\.\s*(?!on\b)([A-Za-z0-9_]+)", query))

        # Load and append each fragment only once (cached)
        for fragment in fragment_names:
            query += "\n" + self._load_fragment(fragment)

        query_dict = {
            "operationName": operation,
            "query": query,
            "variables": variables,
        }
        self._debug_log(f"Executing GraphQL query: {operation}", category="api")
        self._debug_log(f"GraphQL query body:\n{query}", category="api")
        self._debug_log(f"GraphQL variables: {variables}", category="api")
        try:
            response = self.session.post(angel_graphql_url, json=query_dict, timeout=self.timeout)
            response.raise_for_status()
            result = response.json()
            self._debug_log(f"GraphQL response data: {json.dumps(result, indent=2)}", category="api")
            if "errors" in result:
                # Log full error details for debugging
                self.log.error(f"GraphQL errors for operation '{operation}':")
                for error in result.get("errors", []):
                    if isinstance(error, dict):
                        self.log.error(f"  - {error.get('message', 'Unknown error')}")
                        if "extensions" in error:
                            self.log.debug(f"    Extensions: {error['extensions']}")
                    else:
                        self.log.error(f"  - {error}")
                self.log.error(f"session headers: {angel_utils.sanitize_headers_for_logging(self.session.headers)}")
                # Instead of auto-reauthenticating, raise an exception for the UI layer to handle
                raise AuthenticationRequiredError("Authentication required - session may have expired")
            else:
                data = result.get("data", {})

            self._trace_request(operation, query_dict, status=response.status_code, response_data=data)
            return data
        except requests.Timeout:
            self.log.error(f"GraphQL request timeout ({self.timeout}s) for operation '{operation}'")
            self._trace_request(operation, query_dict, status=None, error=f"Timeout ({self.timeout}s)")
            raise Exception(f"Request timeout: Unable to connect to Angel Studios (timeout: {self.timeout}s)")
        except requests.RequestException as e:
            self.log.error(f"GraphQL request failed: {e}")
            if hasattr(e, "response") and e.response is not None and hasattr(e.response, "text"):
                self.log.error(f"GraphQL response body: {e.response.text}")
            self._trace_request(
                operation,
                query_dict,
                status=getattr(e.response, "status_code", None),
                error=str(e),
            )
            return {}
        except Exception as e:
            self.log.error(f"Unexpected error during GraphQL query: {e}")
            self._trace_request(operation, query_dict, error=str(e))
            return {}

    def get_projects(self, project_type=None):
        """Get all projects available in the catalog of the matching content type"""
        try:
            self.log.info("Fetching projects using GraphQL...")
            result = self._graphql_query("getProjectsForMenu", variables={})
            projects = []
            for project in result.get("projects", []):
                if project_type and project.get("projectType") != project_type:
                    continue
                projects.append(project)
            return projects
        except Exception as e:
            self.log.error(f"Error fetching projects: {e}")
            return []

    def get_default_watchlist(self) -> Optional[list]:
        """Return the signed-in viewer's watchlist, in Angel's order.

        An empty list means the viewer has no saved titles. None means the
        read failed, which is not the same as an empty list.
        """
        try:
            result = self._graphql_query("getMyDefaultWatchList", variables={})
        except Exception as exc:
            self.log.error(f"Error fetching watchlist: {exc}")
            return None
        if not isinstance(result, dict):
            return None
        watchlist = result.get("getMyDefaultWatchList")
        if not isinstance(watchlist, dict):
            self.log.error("Watchlist response did not include a list")
            return None
        return _watchlist_items(self._unwrap_relay_pagination(watchlist.get("items")))

    def add_to_watchlist(self, content_id: str) -> bool:
        """Save a title. content_id is the movie, series, or special id."""
        return self._update_watchlist("addToWatchList", content_id)

    def remove_from_watchlist(self, content_id: str) -> bool:
        """Remove a title. content_id is the movie, series, or special id."""
        return self._update_watchlist("deleteFromWatchList", content_id)

    def _update_watchlist(self, operation: str, content_id: str) -> bool:
        if not isinstance(content_id, str) or not content_id:
            return False
        try:
            result = self._graphql_query(operation, variables={"contentId": content_id})
        except Exception as exc:
            self.log.error(f"Error updating watchlist with {operation}: {exc}")
            return False
        if not isinstance(result, dict):
            return False
        payload = result.get(operation)
        return isinstance(payload, dict) and bool(payload.get("id"))

    def get_cloudinary_url(self, cloudinary_path=None):
        """Construct a Cloudinary URL for the given path"""
        if not cloudinary_path:
            return None
        return f"https://images.angelstudios.com/image/upload/{cloudinary_path}"

    def get_project(self, project_slug):
        """Get a specific project by its slug"""
        try:
            result = self._graphql_query(
                "getProject",
                variables={
                    "slug": project_slug,
                    "includePrerelease": True,
                    "includeSeasons": True,
                },
            )
            project = result.get("project", {})
            if not project:
                self.log.warning(f"No project found for slug: {project_slug}")
                return None
            # If ContentSeries display data is present, merge into playback episodes
            title = project.get("title") or {}
            self.log.debug(f"Project title: {title.get('__typename')}, has seasons: {'seasons' in title}")
            if isinstance(title, dict) and title.get("__typename") == "ContentSeries":
                self.log.info("ContentSeries detected, merging STILL images")
                # Build a map of display episodes by id from relay-style seasons
                display_map = {}
                seasons = self._unwrap_relay_pagination(title.get("seasons") or {})
                self.log.debug(f"Found {len(seasons)} seasons in ContentSeries")
                for season in seasons:
                    episodes = self._unwrap_relay_pagination(season.get("episodes") or {})
                    self.log.debug(f"Season has {len(episodes)} episodes")
                    for ep_node in episodes:
                        ep_id = ep_node.get("id")
                        if ep_id:
                            normalized = self._normalize_contentseries_episode(ep_node)
                            # Log STILL fields present in ContentSeries
                            still_fields = [
                                k
                                for k in normalized.keys()
                                if (k.startswith("portraitStill") or k.startswith("landscapeStill"))
                                and isinstance(normalized.get(k), dict)
                            ]
                            if still_fields:
                                self.log.debug(f"Episode {ep_id}: Has STILL fields: {still_fields}")
                            else:
                                self.log.warning(f"Episode {ep_id}: No STILL fields found in ContentSeries data")
                            display_map[ep_id] = normalized

                # Merge display data into playback list
                merged_count = 0
                for season in project.get("seasons", []) or []:
                    for idx, playback_ep in enumerate(season.get("episodes", []) or []):
                        ep_id = playback_ep.get("id") or playback_ep.get("guid")
                        display_ep = display_map.get(ep_id)
                        if display_ep:
                            merged = self._merge_episode_data(display_ep, playback_ep)
                            # Count STILL fields in merged result
                            merged_stills = [
                                k
                                for k in merged.keys()
                                if (k.startswith("portraitStill") or k.startswith("landscapeStill"))
                                and isinstance(merged.get(k), dict)
                            ]
                            if merged_stills:
                                self.log.debug(f"Merged episode {ep_id}: Has {len(merged_stills)} STILL fields")
                                merged_count += 1
                            else:
                                # Warn if display had STILLs but merged result doesn't
                                display_stills = [
                                    k
                                    for k in display_ep.keys()
                                    if (k.startswith("portraitStill") or k.startswith("landscapeStill"))
                                    and isinstance(display_ep.get(k), dict)
                                ]
                                if display_stills:
                                    self.log.warning(f"Merged episode {ep_id}: No STILL fields after merge!")
                            season["episodes"][idx] = merged
                        else:
                            # No display data found; continue with playback as-is
                            pass
                self.log.info(f"ContentSeries merge complete: {merged_count} episodes merged with STILL data")

            return project
        except Exception as e:
            self.log.error(f"Error fetching project by slug '{project_slug}': {e}")
            return None

    def get_projects_by_slugs(self, slugs):
        """Fetch multiple projects by slug (minimal data: just name and id for enrichment)"""
        if not slugs:
            return {}

        try:
            self.log.info(f"Batch fetching {len(slugs)} projects by slug")

            # Build dynamic query with aliased queries (sanitizing slug names for GraphQL aliases)
            query = "query getProjectsForSlugs {\n"
            for slug in slugs:
                sanitized_alias = slug.replace("-", "_")
                query += f'  project_{sanitized_alias}: project(slug: "{slug}") {{\n'
                query += "    name\n"
                query += "    id\n"
                query += "    __typename\n"
                query += "  }\n"
            query += "}\n"

            result = self._graphql_query("getProjectsForSlugs", variables={}, raw_query=query)

            # Map responses back from sanitized aliases to original slugs
            data = result
            remapped_data = {}
            for slug in slugs:
                sanitized_key = f"project_{slug.replace('-', '_')}"
                if sanitized_key in data:
                    remapped_data[slug] = data[sanitized_key]

            self.log.info(f"Batch query returned {len(remapped_data)} projects")
            return remapped_data

        except AuthenticationRequiredError:
            # Re-raise auth errors for UI layer
            raise
        except Exception as e:
            self.log.error(f"Error fetching batch projects: {e}")
            # Re-raise timeout exceptions to allow UI to handle them
            if isinstance(e, Exception) and "Request timeout" in str(e):
                raise
            return {}

    def get_episode_data(self, episode_guid, project_slug=None):
        """Get data for a specific episode by its GUID"""
        try:
            result = self._graphql_query(
                "getEpisodeAndUserWatchData",
                variables={
                    "guid": episode_guid,
                    "projectSlug": project_slug or "",
                    "includePrerelease": True,
                    "authenticated": True,
                    "reactionsRollupInterval": 4000,
                },
            )
            return result
        except Exception as e:
            self.log.error(f"Error fetching episode data for GUID '{episode_guid}': {e}")
            return {}

    def get_watch_position(self, watchable_guid):
        """Return the saved position in seconds.

        Zero means the content record has no position. None means the read
        failed, so a cached position must be left alone. This reads the content
        record the website uses for the series-page link.
        """
        try:
            result = self._graphql_query("getContent", variables={"guid": watchable_guid})
        except Exception as e:
            self.log.warning(f"Could not read watch position for {watchable_guid}: {e}")
            return None
        if not isinstance(result, dict):
            return None
        return self._position_from_content(result.get("getContent"))

    def get_watch_positions(self, watchable_guids):
        """Return saved seconds for many titles in one request.

        A title whose record has no position is 0. A title missing from a
        successful response is omitted. None means the read failed, so every
        cached position must be left alone.
        """
        guids = []
        seen = set()
        for guid in watchable_guids or []:
            if isinstance(guid, str) and guid and guid not in seen:
                seen.add(guid)
                guids.append(guid)
        if not guids:
            return {}

        found = {}
        # One alias per title. A long season is split so one timeout is not
        # the whole list, and a failed chunk leaves that chunk cached.
        chunk_size = 25
        for start in range(0, len(guids), chunk_size):
            chunk = guids[start : start + chunk_size]
            part = self._fetch_watch_position_chunk(chunk)
            if part is None:
                if not found:
                    return None
                continue
            found.update(part)
        return found

    def _position_from_content(self, content):
        """Return seconds, 0 when the record has no position, or None when it is not a record."""
        if not isinstance(content, dict):
            return None
        watch_position = content.get("watchPosition") if "watchPosition" in content else None
        if "watchPosition" not in content or not isinstance(watch_position, dict):
            return 0
        if watch_position.get("position") is None:
            return 0
        return watch_position.get("position")

    def _fetch_watch_position_chunk(self, guids):
        """Read one batch of positions. None means this batch failed."""
        variable_defs = []
        fields = []
        variables = {}
        for index, guid in enumerate(guids):
            key = f"id{index}"
            variable_defs.append(f"${key}: ID!")
            variables[key] = guid
            fields.append(
                f"  item_{index}: getContent(id: ${key}) {{\n"
                "    ... on ContentWatchable { watchPosition { position } }\n"
                "  }\n"
            )
        query = "query getWatchPositions(" + ", ".join(variable_defs) + ") {\n" + "".join(fields) + "}\n"
        try:
            result = self._graphql_query("getWatchPositions", variables=variables, raw_query=query)
        except Exception as e:
            self.log.warning(f"Could not read watch positions: {e}")
            return None
        if not isinstance(result, dict):
            return None
        found = {}
        for index, guid in enumerate(guids):
            position = self._position_from_content(result.get(f"item_{index}"))
            if position is not None:
                found[guid] = position
        return found

    def upsert_watch_position(self, watchable_guid, position, event_type="heartbeat"):
        """Send the current position in seconds. Playback keeps going when this fails.

        The website posts this body to /watch-positions. That is the record behind
        the series-page position link. event_type is heartbeat, pause, stop_exit,
        or complete. The fraction of a second is dropped, matching that player.
        """
        try:
            seconds = int(math.floor(float(position)))
        except (TypeError, ValueError, OverflowError):
            self.log.warning(f"Watch position is not a number: {position!r}")
            return False
        if seconds < 0:
            return False
        if not isinstance(event_type, str) or not event_type:
            event_type = "heartbeat"
        try:
            self.auth_core.ensure_valid_session()
            token = self.auth_core.session_store.get_token()
            if token:
                self._apply_auth_headers(token)
            response = self.session.post(
                angel_watch_positions_url,
                json={
                    "content_id": watchable_guid,
                    "event_type": event_type,
                    "position": seconds,
                },
                headers={
                    "Content-Type": "application/json",
                    "X-ANGEL-APP-NAME": "angel-web",
                },
                timeout=self.timeout,
            )
        except Exception as e:
            self.log.warning(f"Could not save watch position for {watchable_guid}: {e}")
            return False
        if not getattr(response, "ok", False):
            status = getattr(response, "status_code", None)
            self.log.warning(f"Could not save watch position for {watchable_guid}: HTTP {status}")
            return False
        self.log.info(f"Saved watch position {seconds}s for {watchable_guid}")
        return True

    def get_resume_watching(self, first=None, after=None):
        """
        Get resume watching (continue watching) episodes with cursor-based pagination.
        Returns normalized episodes list and pageInfo. Skips edges without content.

        Args:
            first: Number of items to fetch (default: API default, typically 20-50)
            after: Cursor for pagination (pass pageInfo.endCursor from previous call)

        Returns:
            dict with 'episodes' (list of normalized episodes) and 'pageInfo'. Returns {} on error.
        """
        try:
            variables = {}
            if first is not None:
                variables["first"] = first
            if after is not None:
                variables["after"] = after

            self.log.info(f"Fetching resume watching: first={first}, after={after}")
            result = self._graphql_query("resumeWatching", variables=variables)

            if not result or "resumeWatching" not in result:
                self.log.warning("No resumeWatching data in response")
                return {}

            resume_data = result["resumeWatching"]
            page_info = resume_data.get("pageInfo", {})
            nodes = self._unwrap_relay_pagination(resume_data)
            episodes = []
            guids = []
            positions = {}
            for node in nodes:
                # legacy shape
                guid = (node or {}).get("watchableGuid")
                pos = (node or {}).get("position")
                if guid:
                    guids.append(guid)
                    positions[guid] = pos

                # normalized episode
                content = (node or {}).get("content")
                if not isinstance(content, dict):
                    self.log.warning("Edge missing content, skipping")
                    continue
                normalized = self._normalize_resume_episode(content, node)
                episodes.append(normalized)

            # For backward compatibility, omit 'episodes' when there are no nodes
            result_dict = {
                "guids": guids,
                "positions": positions,
                "pageInfo": page_info,
            }
            if nodes:
                result_dict["episodes"] = episodes
            return result_dict
        except Exception as e:
            self.log.error(f"Error fetching resume watching: {e}")
            return {}

    def _unwrap_relay_pagination(self, edges_structure):
        """Return list of 'node' dicts from a Relay-style edges structure.

        Handles None, non-dict inputs, non-list edges, and skips null nodes/edges.
        """
        if not isinstance(edges_structure, dict):
            return []
        edges = edges_structure.get("edges")
        if not isinstance(edges, list):
            return []
        nodes = []
        for edge in edges:
            if not isinstance(edge, dict):
                continue
            node = edge.get("node")
            if isinstance(node, dict):
                nodes.append(node)
        return nodes

    def _normalize_resume_episode(self, content, node):
        """Normalize a ContentEpisode/ContentSpecial/ContentMovie for resume/continue watching list.

        Preserves existing watchPosition; if missing, uses node.position.
        Extracts seasonNumber from season dict when available.
        Maps type-specific aliases like episodeSubtitle/specialSubtitle/movieSubtitle.
        Adds guid from node.watchableGuid.
        """
        out = dict(content) if isinstance(content, dict) else {}
        if not out:
            return {}
        # Add guid from node
        guid = (node or {}).get("watchableGuid")
        if guid:
            out["guid"] = guid
        # watchPosition handling
        wp = out.get("watchPosition")
        if not isinstance(wp, dict):
            pos = (node or {}).get("position")
            if isinstance(pos, (int, float)):
                out["watchPosition"] = {"position": pos}
        # seasonNumber extraction
        season = out.get("season")
        if isinstance(season, dict) and "seasonNumber" in season:
            out["seasonNumber"] = season.get("seasonNumber")
        # alias mapping for all content types
        alias_mappings = {
            "episodeSubtitle": "subtitle",
            "episodeDescription": "description",
            "specialSubtitle": "subtitle",
            "specialDescription": "description",
            "movieSubtitle": "subtitle",
            "movieDescription": "description",
        }
        for alias, canonical in alias_mappings.items():
            if alias in out and canonical not in out:
                out[canonical] = out.get(alias)
                del out[alias]
        # handle url -> source.url for consistency
        if "url" in out and not out.get("source"):
            out["source"] = {"url": out["url"]}
            del out["url"]
        # extract projectSlug from nested project
        if not out.get("projectSlug"):
            project = out.get("project")
            if isinstance(project, dict) and "slug" in project:
                out["projectSlug"] = project["slug"]
        # normalize name from title for specials/movies
        if "title" in out and not out.get("name"):
            out["name"] = out["title"]
        # normalize project name from title
        if "project" in out and isinstance(out["project"], dict):
            project = out["project"]
            name = project.get("name")
            if not name:
                title = project.get("title")
                if isinstance(title, str):
                    name = title
                elif isinstance(title, dict):
                    name = title.get("name") or title.get("title", "Unknown")
            if name:
                project["name"] = name
        # set mediatype based on __typename
        typename = out.get("__typename")
        if typename == "ContentMovie":
            out["mediatype"] = "movie"
        elif typename in ("ContentEpisode", "ContentSpecial"):
            out["mediatype"] = "episode"
        return out

    def _normalize_contentseries_episode(self, episode_data):
        """Normalize ContentSeries episode display data and collect STILLs.

        Returns a dict with display fields (e.g., name) and any STILL entries
        that are dicts. Prunes invalid STILL entries.
        """
        ep = dict(episode_data) if isinstance(episode_data, dict) else {}
        if not ep:
            return {}
        # Collect STILLs
        still_keys = [
            *(f"portraitStill{i}" for i in range(1, 7)),
            *(f"landscapeStill{i}" for i in range(1, 7)),
        ]
        for key in still_keys:
            val = ep.get(key)
            if not isinstance(val, dict):
                # Remove invalid STILL entries
                if key in ep:
                    del ep[key]
        return ep

    def _merge_episode_data(self, contentseries, playback):
        """Merge ContentSeries display data with playback episode data.

        Prefers display name/title fields and overlays display over playback.
        Preserves playback source/url fields. Returns merged dict.
        """
        base = dict(playback) if isinstance(playback, dict) else {}
        display = dict(contentseries) if isinstance(contentseries, dict) else {}
        if display.get("name"):
            base["name"] = display["name"]
        if display.get("displayName") and not base.get("name"):
            base["name"] = display["displayName"]
        # Overlay simple fields from display
        for k, v in display.items():
            if k.startswith("portraitStill") or k.startswith("landscapeStill"):
                base[k] = v
            elif k in ("subtitle", "description"):
                base[k] = v
        return base

    def get_episodes_for_guids(self, guids):
        """
        Fetch full episode data for a list of guids using batch query.
        Uses the EpisodeListItem fragment for consistent field selection.

        Args:
            guids: List of episode guids to fetch

        Returns:
            dict mapping guid keys (episode_<guid>) to episode data dicts
            Returns {} on error, logs and omits individual failed guids
        """
        if not guids:
            return {}

        try:
            self.log.info(f"Fetching {len(guids)} episodes via batch query")

            # Load the fragment once
            fragment = self._load_fragment("EpisodeListItem")

            # Build dynamic query with aliased queries
            # Use sanitized alias names (replace hyphens with underscores since GraphQL aliases can't have hyphens)
            query = "query getEpisodesForGuids {\n"
            for guid in guids:
                sanitized_alias = guid.replace("-", "_")
                query += f'  episode_{sanitized_alias}: episode(guid: "{guid}") {{\n'
                query += "    ...EpisodeListItem\n"
                query += "  }\n"
            query += "}\n"
            query += fragment

            query_dict = {
                "operationName": "getEpisodesForGuids",
                "query": query,
                "variables": {},
            }

            self._debug_log(f"Executing batch episodes query for {len(guids)} guids", category="api")
            self._debug_log(f"Batch GraphQL query:\n{query}", category="api")
            self._debug_log(f"Batch GraphQL variables: {query_dict['variables']}", category="api")

            try:
                response = self.session.post(angel_graphql_url, json=query_dict, timeout=self.timeout)
                response.raise_for_status()
                result = response.json()

                self.log.debug(f"Batch GraphQL response: {json.dumps(result, indent=2)}")

                if "errors" in result:
                    self.log.error(f"GraphQL errors: {result['errors']}")
                    raise AuthenticationRequiredError("Authentication required - session may have expired")

                # Map responses back from sanitized aliases to original guids
                data = result.get("data", {})
                remapped_data = {}
                for guid in guids:
                    sanitized_key = f"episode_{guid.replace('-', '_')}"
                    if sanitized_key in data:
                        remapped_data[f"episode_{guid}"] = data[sanitized_key]

                self.log.info(f"Batch query returned {len(remapped_data)} episodes")
                return remapped_data

            except requests.Timeout:
                self.log.error(f"Batch episodes request timeout ({self.timeout}s)")
                raise Exception(f"Request timeout: Unable to connect to Angel Studios (timeout: {self.timeout}s)")
            except requests.RequestException as e:
                self.log.error(f"Batch episodes request failed: {e}")
                self.log.debug(
                    f"Response status: {e.response.status_code if hasattr(e, 'response') and e.response else 'N/A'}"
                )
                if hasattr(e, "response") and e.response is not None and hasattr(e.response, "text"):
                    self.log.debug(f"Response body: {e.response.text}")
                return {}

        except Exception as e:
            self.log.error(f"Error fetching batch episodes: {e}")
            # Re-raise timeout exceptions to allow UI to handle them
            if isinstance(e, Exception) and "Request timeout" in str(e):
                raise
            return {}

    def session_check(self):
        """Check if the session is authenticated and valid"""
        if not self.auth_core.validate_session():
            self.log.error("Session is not valid")
            raise AuthenticationRequiredError("Session validation failed")
        else:
            self.log.info("Session is valid")

    def force_logout(self):
        """Revoke the saved session before clearing local authentication."""
        try:
            token = self.auth_core.session_store.get_token()
            if not token:
                self.log.error("Logout failed: no session token available")
                return False
            response = requests.get(
                f"{angel_website_url}/auth/logout",
                cookies={"angel_jwt_v3": token},
                allow_redirects=False,
                timeout=self.timeout,
            )
            if response.status_code not in (301, 302, 303, 307, 308):
                self.log.error(f"Logout failed: HTTP {response.status_code}")
                return False
            self.auth_core.logout()
            self.auth_core.session_store.clear_credentials()
            self._apply_auth_headers(None)
            return True
        except Exception as e:
            self.log.error(f"Logout failed: {e}")
            return False

    def get_session_details(self):
        """Return diagnostics for the saved session without signing in."""
        store = self.auth_core.session_store
        token = store.get_token()
        username, _ = store.get_credentials()
        details = {"login_email": username or "Unknown", "authenticated": self.auth_core.validate_session()}
        if token:
            try:
                payload = angel_authentication.decode_jwt_payload(token)
                details["login_email"] = payload.get("email", details["login_email"])
                details["account_id"] = payload.get("sub")
                for claim, label in (("iat", "issued_at"), ("exp", "expires_at")):
                    if claim in payload:
                        timestamp = datetime.fromtimestamp(payload[claim], timezone.utc)
                        details[f"{label}_utc"] = timestamp.isoformat()
                        details[f"{label}_local"] = timestamp.astimezone().isoformat()
                        if claim == "exp":
                            details["expires_in_seconds"] = int(
                                (timestamp - datetime.now(timezone.utc)).total_seconds()
                            )
            except (ValueError, TypeError, OverflowError, OSError):
                self.log.warning("Unable to decode session details")
        return details

    # Interface remains KODI-agnostic and does not manage cache internally
