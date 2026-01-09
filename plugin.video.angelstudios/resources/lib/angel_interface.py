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
import os
import re
import sys

import angel_authentication
import requests

# Library constants
angel_website_url = "https://www.angel.com"
angel_graphql_url = "https://api.angelstudios.com/graphql"


class AngelStudiosInterface:
    """
    Interface for Angel Studios website HTML and GraphQL queries.
    - GraphQL queries are used to fetch project data, seasons, episodes, and more.
    - helpers translate native graphql queries into useable data
    """

    def __init__(
        self,
        username=None,
        password=None,
        session_file="",
        logger=None,
        query_path=None,
        tracer=None,
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

        # Set the tracer function provided by the calling function
        self.tracer = tracer

        # No cache in the KODI-agnostic interface; rely on callers to cache

        # Use provided session file or get authenticated session
        self.angel_studios_session = angel_authentication.AngelStudioSession(
            username=username,
            password=password,
            session_file=session_file,
            logger=self.log,
        )
        self.angel_studios_session.authenticate()

        self.session = self.angel_studios_session.get_session()

        # Test if session is authenticated and valid:
        # Log authentication status more meaningfully
        if self.session:
            auth_header = self.session.headers.get("Authorization")
            cookie_count = len(self.session.cookies) if self.session.cookies else 0
            if auth_header:
                self.log.info(f"Authenticated Session: JWT token present, {cookie_count} cookies")
            else:
                self.log.info(f"Session initialized: No JWT token, {cookie_count} cookies")

            self.query_path = query_path or "resources/lib/angel_graphql"
            self._query_cache = {}
            self._fragment_cache = {}
        else:
            self.log.error("Failed to initialize session: No session available")
            raise Exception("Failed to initialize session: No session available")

    def _load_query(self, operation: str) -> str:
        """Load and cache a GraphQL query file by operation name."""
        if operation in self._query_cache:
            return self._query_cache[operation]
        query_file = os.path.join(self.query_path, f"query_{operation}.graphql")
        try:
            with open(query_file, "r") as f:
                query = f.read()
                self._query_cache[operation] = query
                return query
        except Exception as e:
            self.log.error(f"Error loading query file '{query_file}': {e}")
            return ""

    def _load_fragment(self, fragment_name: str) -> str:
        """Load and cache a GraphQL fragment file by fragment name."""
        if fragment_name in self._fragment_cache:
            return self._fragment_cache[fragment_name]
        fragment_path = os.path.join(self.query_path, f"fragment_{fragment_name}.graphql")
        try:
            with open(fragment_path, "r") as f:
                fragment = f.read()
                self._fragment_cache[fragment_name] = fragment
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

    def _graphql_query(self, operation: str, variables=None) -> dict:
        """Generalized GraphQL query executor with automatic fragment loading and caching."""
        variables = variables or {}
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
        self.log.debug(f"Executing GraphQL query: {operation}")
        self.log.debug(f"GraphQL query body:\n{query}")
        self.log.debug(f"GraphQL variables: {variables}")
        try:
            response = self.session.post(angel_graphql_url, json=query_dict)
            response.raise_for_status()
            result = response.json()
            self.log.debug(f"GraphQL response data: {json.dumps(result, indent=2)}")
            if "errors" in result:
                self.log.error(f"GraphQL errors: {result['errors']}")
                self.log.error(f"session headers: {self.session.headers}")
                self.angel_studios_session.authenticate(force_reauthentication=True)
                data = {}
            else:
                data = result.get("data", {})

            self._trace_request(operation, query_dict, status=response.status_code, response_data=data)
            return data
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
        # TODO This should be cached, since we pull it for every menu load
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
                sanitized_alias = slug.replace('-', '_')
                query += f'  project_{sanitized_alias}: project(slug: "{slug}") {{\n'
                query += "    name\n"
                query += "    id\n"
                query += "    __typename\n"
                query += "  }\n"
            query += "}\n"
            
            query_dict = {
                "operationName": "getProjectsForSlugs",
                "query": query,
                "variables": {},
            }
            
            self.log.debug(f"Batch projects query for {len(slugs)} slugs")
            self.log.debug(f"Batch projects query:\n{query}")
            
            try:
                response = self.session.post(angel_graphql_url, json=query_dict)
                response.raise_for_status()
                result = response.json()
                
                self.log.debug(f"Batch projects response: {json.dumps(result, indent=2)}")
                
                if "errors" in result:
                    self.log.error(f"GraphQL errors: {result['errors']}")
                    self.angel_studios_session.authenticate(force_reauthentication=True)
                    return {}
                
                # Map responses back from sanitized aliases to original slugs
                data = result.get("data", {})
                remapped_data = {}
                for slug in slugs:
                    sanitized_key = f"project_{slug.replace('-', '_')}"
                    if sanitized_key in data:
                        remapped_data[slug] = data[sanitized_key]
                
                self.log.info(f"Batch query returned {len(remapped_data)} projects")
                return remapped_data
                
            except requests.RequestException as e:
                self.log.error(f"Batch projects request failed: {e}")
                if hasattr(e, "response") and e.response is not None and hasattr(e.response, "text"):
                    self.log.error(f"GraphQL response body: {e.response.text}")
                return {}
                
        except Exception as e:
            self.log.error(f"Error fetching batch projects: {e}")
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

    def get_resume_watching(self, first=None, after=None):
        """
        Get resume watching (continue watching) episode guids with cursor-based pagination.
        Returns minimal data: just guids, positions, and pagination info.
        Full episode data should be fetched via get_episodes_for_guids().
        
        Args:
            first: Number of items to fetch (default: API default, typically 20-50)
            after: Cursor for pagination (pass pageInfo.endCursor from previous call)
        
        Returns:
            dict with 'guids' (ordered list of episode guids), 'positions' (dict of guid->position),
            and 'pageInfo' (pagination state). Returns {} on error.
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
            edges = resume_data.get("edges", [])
            page_info = resume_data.get("pageInfo", {})
            
            self.log.info(f"Resume watching: {len(edges)} items, hasNextPage={page_info.get('hasNextPage')}")
            
            # Extract guids in order, track positions
            guids = []
            positions = {}
            for edge in edges:
                node = edge.get("node", {})
                guid = node.get("watchableGuid")
                position = node.get("position")
                
                if guid:
                    guids.append(guid)
                    positions[guid] = position
            
            return {
                "guids": guids,
                "positions": positions,
                "pageInfo": page_info,
            }
        except Exception as e:
            self.log.error(f"Error fetching resume watching: {e}")
            return {}

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
                sanitized_alias = guid.replace('-', '_')
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
            
            self.log.debug(f"Executing batch episodes query for {len(guids)} guids")
            self.log.debug(f"Batch GraphQL query:\n{query}")
            self.log.debug(f"Batch GraphQL variables: {query_dict['variables']}")
            
            try:
                response = self.session.post(angel_graphql_url, json=query_dict)
                response.raise_for_status()
                result = response.json()
                
                self.log.debug(f"Batch GraphQL response: {json.dumps(result, indent=2)}")
                
                if "errors" in result:
                    self.log.error(f"GraphQL errors: {result['errors']}")
                    self.angel_studios_session.authenticate(force_reauthentication=True)
                    return {}
                
                # Map responses back from sanitized aliases to original guids
                data = result.get("data", {})
                remapped_data = {}
                for guid in guids:
                    sanitized_key = f"episode_{guid.replace('-', '_')}"
                    if sanitized_key in data:
                        remapped_data[f"episode_{guid}"] = data[sanitized_key]
                
                self.log.info(f"Batch query returned {len(remapped_data)} episodes")
                return remapped_data
                
            except requests.RequestException as e:
                self.log.error(f"Batch episodes request failed: {e}")
                self.log.debug(f"Response status: {e.response.status_code if hasattr(e, 'response') and e.response else 'N/A'}")
                if hasattr(e, 'response') and e.response is not None and hasattr(e.response, "text"):
                    self.log.debug(f"Response body: {e.response.text}")
                return {}
                
        except Exception as e:
            self.log.error(f"Error fetching batch episodes: {e}")
            return {}

    def session_check(self):
        """Check if the session is authenticated and valid"""
        session_valid = self.angel_studios_session._validate_session()
        if not session_valid:
            self.log.info("Session is not valid, re-authenticating...")
            self.angel_studios_session.authenticate(force_reauthentication=True)
            if not self.angel_studios_session.session_valid:
                self.log.error("Session re-authentication failed")
                raise Exception("Session re-authentication failed")
        else:
            self.log.info("Session is valid")

    def force_logout(self):
        """Force a local logout; future enhancement may call remote logout API."""
        try:
            result = self.angel_studios_session.logout()
            self.session = self.angel_studios_session.get_session()
            return result
        except Exception as e:
            self.log.error(f"Logout failed: {e}")
            return False

    # Interface remains KODI-agnostic and does not manage cache internally
