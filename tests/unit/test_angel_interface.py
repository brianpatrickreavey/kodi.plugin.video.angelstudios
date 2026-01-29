import os
import pytest
import requests
from unittest.mock import patch, MagicMock, mock_open, PropertyMock

from resources.lib.angel_interface import AngelStudiosInterface, angel_graphql_url
import resources.lib.angel_utils as angel_utils
from resources.lib.angel_authentication import AuthenticationRequiredError
from .unittest_data import MOCK_PROJECT_DATA, MOCK_EPISODE_DATA, MOCK_GRAPHQL_RESPONSE


class TestAngelStudiosInterface:
    @pytest.fixture
    def angel_interface(self):
        """Fixture for a mocked AngelStudiosInterface instance."""
        with (
            patch("angel_authentication.AuthenticationCore") as mock_auth_core_class,
            patch("angel_authentication.requests.Session") as mock_requests_session,
        ):
            # Mock the requests.Session instance that gets created
            mock_requests_instance = MagicMock()
            mock_requests_session.return_value = mock_requests_instance

            # Mock AuthenticationCore
            mock_auth_core = MagicMock()
            mock_auth_core.session_store.get_token.return_value = "mock-jwt-token"
            mock_auth_core.validate_session.return_value = True
            mock_auth_core_class.return_value = mock_auth_core

            interface = AngelStudiosInterface(auth_core=mock_auth_core, logger=MagicMock())
            return interface

    def test_init_with_auth_core(self):
        """Test __init__ with AuthenticationCore."""
        logger = MagicMock()
        mock_auth_core = MagicMock()
        mock_auth_core.session_store.get_token.return_value = "test-token"

        with patch("angel_authentication.requests.Session") as mock_requests_session:
            mock_requests_instance = MagicMock()
            mock_requests_session.return_value = mock_requests_instance

            interface = AngelStudiosInterface(auth_core=mock_auth_core, logger=logger)

            assert interface.log is logger
            assert interface.auth_core is mock_auth_core
            logger.info.assert_any_call("Custom logger initialized")
            logger.info.assert_any_call("Session prepared with JWT token")

    def test_init_without_logger(self):
        """Test __init__ without logger (uses default)."""
        mock_auth_core = MagicMock()
        with patch("angel_authentication.requests.Session") as mock_requests_session:
            mock_requests_instance = MagicMock()
            mock_requests_session.return_value = mock_requests_instance

            interface = AngelStudiosInterface(auth_core=mock_auth_core)
            # Verify default logger is set and no custom log
            assert interface.log is not None

    def test_init_fails_when_session_is_none(self):
        """Test __init__ raises exception when get_session() returns None."""
        # This test is no longer relevant with the new AuthenticationCore approach
        # The AngelStudiosInterface no longer manages session creation directly
        pass

    def test_load_query_success(self, angel_interface):
        """Test _load_query loads and caches a query successfully."""
        with patch("builtins.open", mock_open(read_data="query content")) as mock_file:
            first_result = angel_interface._load_query("test_operation")
            assert first_result == "query content"
            mock_file.assert_called_once_with(
                os.path.join(angel_interface.query_path, "query_test_operation.graphql"), "r"
            )
            assert "test_operation" in angel_interface._query_file_cache

            # Second call: hit cache, cover early return
            second_result = angel_interface._load_query("test_operation")
            assert second_result == "query content"
            # open should not be called again
            mock_file.assert_called_once()  # Still only once
            assert angel_interface._query_file_cache["test_operation"] == "query content"

    def test_load_query_failure(self, angel_interface):
        """Test _load_query handles file loading failure."""
        with patch("builtins.open", side_effect=FileNotFoundError) as mock_file:
            result = angel_interface._load_query("test_operation")
            assert result == ""
            assert "test_operation" not in angel_interface._query_file_cache
            mock_file.assert_called_once_with(
                os.path.join(angel_interface.query_path, "query_test_operation.graphql"), "r"
            )

            # Assert error logging occurred
            expected_path = os.path.join(angel_interface.query_path, "query_test_operation.graphql")
            angel_interface.log.error.assert_called_once_with(f"Error loading query file '{expected_path}': ")

    def test_load_fragment_success(self, angel_interface):
        """Test _load_fragment loads and caches a fragment successfully."""
        with patch("builtins.open", mock_open(read_data="fragment content")) as mock_file:
            first_result = angel_interface._load_fragment("test_fragment")
            assert first_result == "fragment content"
            mock_file.assert_called_once_with(
                os.path.join(angel_interface.query_path, "fragment_test_fragment.graphql"), "r"
            )
            assert "test_fragment" in angel_interface._fragment_file_cache

            # Second call should hit cache and avoid re-opening the file
            second_result = angel_interface._load_fragment("test_fragment")
            assert second_result == "fragment content"
            mock_file.assert_called_once()

    def test_load_fragment_failure(self, angel_interface):
        """Test _load_fragment handles file loading failure."""
        with patch("builtins.open", side_effect=FileNotFoundError) as mock_file:
            result = angel_interface._load_fragment("test_fragment")
            assert result == ""
            assert "test_fragment" not in angel_interface._fragment_file_cache
            mock_file.assert_called_once_with(
                os.path.join(angel_interface.query_path, "fragment_test_fragment.graphql"), "r"
            )

            # Assert error logging occurred
            expected_path = os.path.join(angel_interface.query_path, "fragment_test_fragment.graphql")
            angel_interface.log.error.assert_called_once_with(
                f"Error loading fragment 'test_fragment' from '{expected_path}': "
            )

    @pytest.mark.parametrize("operation", ["getProjectsForMenu", "getProject"])
    def test_graphql_query_success(self, angel_interface, operation):
        """Test _graphql_query executes successfully for different operations."""
        with (
            patch.object(
                angel_interface, "_load_query", return_value="query body without fragments"
            ) as mock_load_query,
            patch.object(angel_interface, "_load_fragment") as mock_load_fragment,
            patch.object(angel_interface.session, "post") as mock_post,
        ):
            mock_response = MagicMock()
            mock_response.json.return_value = MOCK_GRAPHQL_RESPONSE
            mock_post.return_value = mock_response

            result = angel_interface._graphql_query(operation)

            # Assert the method returns the expected data from the response
            expected_data = MOCK_PROJECT_DATA["multi_season_project"]
            assert result == expected_data

            # Assert the POST request was made exactly once to the GraphQL URL
            mock_post.assert_called_once()
            call_args = mock_post.call_args
            assert call_args[0][0] == angel_graphql_url  # First positional arg is the URL
            query_payload = call_args[1]["json"]  # Keyword arg 'json' contains the payload
            assert query_payload["operationName"] == operation
            assert "query" in query_payload
            assert query_payload["variables"] == {}

            # Assert supporting calls/logs
            mock_load_query.assert_called_once_with(operation)
            mock_load_fragment.assert_not_called()
            mock_response.raise_for_status.assert_called_once()
            angel_interface.log.debug.assert_any_call(f"Executing GraphQL query: {operation}", category="api")

    def test_graphql_query_with_fragment(self, angel_interface):
        """Ensure fragment references trigger fragment loading and still return data."""
        with (
            patch.object(angel_interface, "_load_query", return_value="query ... FragX"),
            patch.object(
                angel_interface, "_load_fragment", return_value="fragment FragX on Foo { id }"
            ) as mock_fragment,
            patch.object(angel_interface.session, "post") as mock_post,
        ):
            mock_post.return_value.json.return_value = {"data": {"ok": True}}
            mock_post.return_value.raise_for_status.return_value = None

            result = angel_interface._graphql_query("op_with_fragment")

            assert result == {"ok": True}
            mock_fragment.assert_called_once_with("FragX")
            mock_post.assert_called_once()

    def test_graphql_query_with_multiple_fragments(self, angel_interface):
        """Ensure multiple fragment references are de-duplicated and loaded once each."""
        query_body = "query ... FragX ... FragY ... FragX"
        with (
            patch.object(angel_interface, "_load_query", return_value=query_body),
            patch.object(angel_interface.session, "post") as mock_post,
            patch.object(angel_interface, "_load_fragment", side_effect=["fragX body", "fragY body"]) as mock_frag,
        ):
            mock_response = MagicMock()
            mock_response.json.return_value = {"data": {"ok": True}}
            mock_post.return_value = mock_response

            result = angel_interface._graphql_query("op_with_frags")

            assert result == {"ok": True}
            assert mock_frag.call_count == 2
            mock_frag.assert_any_call("FragX")
            mock_frag.assert_any_call("FragY")
            mock_post.assert_called_once()
            mock_response.raise_for_status.assert_called_once()

    def test_graphql_query_with_errors(self, angel_interface):
        """Test _graphql_query handles GraphQL errors."""
        with patch.object(angel_interface, "_load_query", return_value="query { test }"):
            mock_response = MagicMock()
            mock_response.json = MagicMock(return_value={"errors": ["GraphQL error occurred"]})
            angel_interface.session.post.return_value = mock_response

            result = angel_interface._graphql_query("test_operation")

            # Assert the method returns an empty dict on GraphQL errors
            assert result == {}

            # Assert error logging occurred and raise_for_status was called
            mock_response.raise_for_status.assert_called_once()
            angel_interface.log.error.assert_any_call("GraphQL errors for operation 'test_operation':")
            angel_interface.log.error.assert_any_call("  - GraphQL error occurred")
            angel_interface.log.error.assert_any_call(
                f"session headers: {angel_utils.sanitize_headers_for_logging(angel_interface.session.headers)}"
            )

    def test_graphql_query_request_failure(self, angel_interface):
        """Test _graphql_query handles request exceptions."""
        with (
            patch.object(angel_interface, "_load_query", return_value="dummy query") as mock_load_query,
            patch.object(angel_interface.session, "post", side_effect=Exception("Request failed")) as mock_post,
        ):
            result = angel_interface._graphql_query("test_operation")

            # Assert the method returns an empty dict on request failure
            mock_load_query.assert_called_once_with("test_operation")
            mock_post.assert_called_once()
            assert result == {}

            # Assert no re-authentication is triggered (only for GraphQL errors, not general exceptions)

            # Assert error logging occurred
            angel_interface.log.error.assert_called_once_with("Unexpected error during GraphQL query: Request failed")

    def test_graphql_query_request_exception(self, angel_interface):
        """Test _graphql_query handles requests.RequestException specifically."""
        with (
            patch.object(angel_interface, "_load_query", return_value="dummy query"),
            patch.object(angel_interface.session, "post", side_effect=requests.RequestException("boom")) as mock_post,
        ):
            result = angel_interface._graphql_query("test_operation")

            assert result == {}
            mock_post.assert_called_once()
            angel_interface.log.error.assert_called_once_with("GraphQL request failed: boom")

    def test_graphql_query_tracer_filters_headers(self, angel_interface):
        """Tracer receives redacted headers and response data."""
        angel_interface.tracer = MagicMock()
        angel_interface.session.headers = {"Authorization": "secret", "Cookie": "c", "X-Test": "ok"}
        response = MagicMock()
        response.json.return_value = {"data": {"ok": True}}
        response.status_code = 200

        with patch.object(angel_interface.session, "post", return_value=response):
            result = angel_interface._graphql_query("op")

        assert result == {"ok": True}
        angel_interface.tracer.assert_called_once()
        trace_payload = angel_interface.tracer.call_args[0][0]
        assert trace_payload["request"]["headers"] == {"X-Test": "ok"}
        assert trace_payload["response"] == {"ok": True}

    def test_graphql_query_tracer_exception_swallowed(self, angel_interface):
        """Exceptions from tracer do not break flow."""
        angel_interface.tracer = MagicMock(side_effect=RuntimeError("boom"))
        response = MagicMock()
        response.json.return_value = {"data": {"ok": True}}
        response.status_code = 200

        with patch.object(angel_interface.session, "post", return_value=response):
            result = angel_interface._graphql_query("op")

        assert result == {"ok": True}
        # No exception propagates

    def test_graphql_query_request_exception_tracer(self, angel_interface):
        """Tracer invoked on RequestException with sanitized headers."""
        angel_interface.tracer = MagicMock()
        angel_interface.session.headers = {"Authorization": "secret", "Cookie": "c", "X-Test": "ok"}
        exc = requests.RequestException("boom")
        exc.response = MagicMock(status_code=503)

        with patch.object(angel_interface.session, "post", side_effect=exc):
            result = angel_interface._graphql_query("op")

        assert result == {}
        angel_interface.tracer.assert_called_once()
        payload = angel_interface.tracer.call_args[0][0]
        assert payload["status"] == 503
        assert payload["request"]["headers"] == {"X-Test": "ok"}

    def test_graphql_query_unexpected_exception_tracer(self, angel_interface):
        """Tracer invoked on generic exceptions."""
        angel_interface.tracer = MagicMock()
        angel_interface.session.headers = {"Authorization": "secret", "Cookie": "c", "X-Test": "ok"}
        response = MagicMock()
        response.json.side_effect = ValueError("bad json")

        with patch.object(angel_interface.session, "post", return_value=response):
            result = angel_interface._graphql_query("op")

        assert result == {}
        angel_interface.tracer.assert_called_once()
        payload = angel_interface.tracer.call_args[0][0]
        assert payload["request"]["headers"] == {"X-Test": "ok"}

    def test_graphql_query_request_exception_tracer_raises(self, angel_interface):
        """Tracer exceptions on RequestException are swallowed."""
        angel_interface.tracer = MagicMock(side_effect=RuntimeError("boom"))
        angel_interface.session.headers = {"Authorization": "secret"}
        exc = requests.RequestException("fail")

        with patch.object(angel_interface.session, "post", side_effect=exc):
            assert angel_interface._graphql_query("op") == {}

    def test_graphql_query_unexpected_exception_tracer_raises(self, angel_interface):
        """Tracer exceptions on generic exceptions are swallowed."""
        angel_interface.tracer = MagicMock(side_effect=RuntimeError("boom"))
        angel_interface.session.headers = {"Authorization": "secret"}
        response = MagicMock()
        response.json.side_effect = ValueError("bad json")

        with patch.object(angel_interface.session, "post", return_value=response):
            assert angel_interface._graphql_query("op") == {}

    @pytest.mark.parametrize("project_type", [None, "series", "movie"])
    def test_get_projects(self, angel_interface, project_type):
        """Test get_projects fetches and filters projects."""
        # Prepare mock data: list of projects from MOCK_PROJECT_DATA
        projects_list = list(MOCK_PROJECT_DATA.values())
        mock_response = {"projects": projects_list}

        with patch.object(angel_interface, "_graphql_query") as mock_query:
            mock_query.return_value = mock_response
            result = angel_interface.get_projects(project_type=project_type)

            # Assert _graphql_query was called correctly
            mock_query.assert_called_once_with("getProjectsForMenu", variables={})

            # Assert the result is filtered correctly
            expected = [p for p in projects_list if project_type is None or p.get("projectType") == project_type]
            assert result == expected

            # Assert info logging occurred
            angel_interface.log.info.assert_any_call("Fetching projects using GraphQL...")

    def test_get_projects_exception(self, angel_interface):
        """Test get_projects handles exceptions."""
        with patch.object(angel_interface, "_graphql_query", side_effect=Exception("Query failed")) as mock_query:
            result = angel_interface.get_projects()

            # Assert the method returns an empty list on exception
            assert result == []

            # Assert _graphql_query was attempted
            mock_query.assert_called_once_with("getProjectsForMenu", variables={})

            # Assert error logging occurred
            angel_interface.log.error.assert_called_once_with("Error fetching projects: Query failed")

    @pytest.mark.parametrize("cloudinary_path", [None, "path/to/image"])
    def test_get_cloudinary_url(self, angel_interface, cloudinary_path):
        """Test get_cloudinary_url constructs URLs."""
        result = angel_interface.get_cloudinary_url(cloudinary_path)

        if cloudinary_path is None:
            assert result is None
        else:
            expected_url = f"https://images.angelstudios.com/image/upload/{cloudinary_path}"
            assert result == expected_url

    def test_get_project_success(self, angel_interface):
        """Test get_project fetches a project successfully."""
        with patch.object(angel_interface, "_graphql_query") as mock_query:
            mock_query.return_value = {"project": {"slug": "test"}}
            result = angel_interface.get_project("test_slug")

            assert result == {"slug": "test"}
            mock_query.assert_called_once_with(
                "getProject", variables={"slug": "test_slug", "includePrerelease": True, "includeSeasons": True}
            )

    def test_get_project_not_found(self, angel_interface):
        """Test get_project handles project not found."""
        with patch.object(angel_interface, "_graphql_query") as mock_query:
            mock_query.return_value = {}
            result = angel_interface.get_project("test_slug")

            assert result is None
            mock_query.assert_called_once_with(
                "getProject", variables={"slug": "test_slug", "includePrerelease": True, "includeSeasons": True}
            )
            angel_interface.log.warning.assert_called_once_with("No project found for slug: test_slug")

    def test_get_project_exception(self, angel_interface):
        """Test get_project handles exceptions."""
        with patch.object(angel_interface, "_graphql_query", side_effect=Exception("Query failed")) as mock_query:
            result = angel_interface.get_project("test_slug")

            assert result is None
            mock_query.assert_called_once_with(
                "getProject", variables={"slug": "test_slug", "includePrerelease": True, "includeSeasons": True}
            )
            angel_interface.log.error.assert_called_once_with(
                "Error fetching project by slug 'test_slug': Query failed"
            )

    def test_get_episode_data_success(self, angel_interface):
        """Test get_episode_data fetches episode data successfully."""
        with patch.object(angel_interface, "_graphql_query") as mock_query:
            mock_query.return_value = MOCK_EPISODE_DATA
            result = angel_interface.get_episode_data("ep_guid", "project_slug")

            assert result == MOCK_EPISODE_DATA
            mock_query.assert_called_once_with(
                "getEpisodeAndUserWatchData",
                variables={
                    "guid": "ep_guid",
                    "projectSlug": "project_slug",
                    "includePrerelease": True,
                    "authenticated": True,
                    "reactionsRollupInterval": 4000,
                },
            )

    def test_get_episode_data_exception(self, angel_interface):
        """Test get_episode_data handles exceptions."""
        with patch.object(angel_interface, "_graphql_query", side_effect=Exception("Query failed")) as mock_query:
            result = angel_interface.get_episode_data("ep_guid", "project_slug")

            assert result == {}
            mock_query.assert_called_once_with(
                "getEpisodeAndUserWatchData",
                variables={
                    "guid": "ep_guid",
                    "projectSlug": "project_slug",
                    "includePrerelease": True,
                    "authenticated": True,
                    "reactionsRollupInterval": 4000,
                },
            )
            angel_interface.log.error.assert_called_once_with(
                "Error fetching episode data for GUID 'ep_guid': Query failed"
            )

    def test_get_resume_watching_success_with_defaults(self, angel_interface):
        """Test get_resume_watching with default parameters."""
        from .unittest_data import MOCK_RESUME_WATCHING_RESPONSE

        with patch.object(angel_interface, "_graphql_query") as mock_query:
            mock_query.return_value = MOCK_RESUME_WATCHING_RESPONSE
            result = angel_interface.get_resume_watching()

            assert "guids" in result
            assert "positions" in result
            assert "pageInfo" in result
            assert len(result["guids"]) == 2
            assert result["guids"][0] == "resume-guid-1"
            assert result["positions"]["resume-guid-1"] == 1200
            assert result["pageInfo"]["hasNextPage"] is True
            mock_query.assert_called_once_with("resumeWatching", variables={})

    def test_get_resume_watching_success_with_pagination(self, angel_interface):
        """Test get_resume_watching with pagination parameters."""
        from .unittest_data import MOCK_RESUME_WATCHING_RESPONSE

        with patch.object(angel_interface, "_graphql_query") as mock_query:
            mock_query.return_value = MOCK_RESUME_WATCHING_RESPONSE
            result = angel_interface.get_resume_watching(first=10, after="cursor-abc")

            assert "guids" in result
            assert len(result["guids"]) == 2
            mock_query.assert_called_once_with("resumeWatching", variables={"first": 10, "after": "cursor-abc"})

    def test_get_resume_watching_empty_response(self, angel_interface):
        """Test get_resume_watching with no items."""
        with patch.object(angel_interface, "_graphql_query") as mock_query:
            mock_query.return_value = {
                "resumeWatching": {"edges": [], "pageInfo": {"hasNextPage": False, "endCursor": None}}
            }
            result = angel_interface.get_resume_watching()

            assert result == {"guids": [], "positions": {}, "pageInfo": {"hasNextPage": False, "endCursor": None}}

    def test_get_resume_watching_no_data(self, angel_interface):
        """Test get_resume_watching when response missing resumeWatching key."""
        with patch.object(angel_interface, "_graphql_query") as mock_query:
            mock_query.return_value = {}
            result = angel_interface.get_resume_watching()

            assert result == {}
            angel_interface.log.warning.assert_called_once_with("No resumeWatching data in response")

    def test_get_resume_watching_exception(self, angel_interface):
        """Test get_resume_watching handles exceptions."""
        with patch.object(angel_interface, "_graphql_query", side_effect=Exception("Query failed")):
            result = angel_interface.get_resume_watching(first=20)

            assert result == {}
            angel_interface.log.error.assert_called_once_with("Error fetching resume watching: Query failed")

    def test_force_logout_exception(self):
        """force_logout returns False on exception and logs error."""
        iface = object.__new__(AngelStudiosInterface)
        iface.log = MagicMock()
        iface.auth_core = MagicMock()
        iface.auth_core.logout.side_effect = RuntimeError("boom")
        iface.session = MagicMock()

        result = iface.force_logout()

        assert result is False
        iface.log.error.assert_called_once()

    def test_force_logout_success(self):
        """force_logout clears session on success."""
        asi = object.__new__(AngelStudiosInterface)
        asi.log = MagicMock()
        asi.auth_core = MagicMock()
        asi.auth_core.logout.return_value = None  # logout doesn't return anything
        asi.session = MagicMock()

        result = asi.force_logout()

        assert result is True
        asi.auth_core.logout.assert_called_once()

    def test_get_episodes_for_guids_empty_list(self, angel_interface):
        """Test get_episodes_for_guids with empty guid list returns empty dict."""
        result = angel_interface.get_episodes_for_guids([])
        assert result == {}

    def test_get_episodes_for_guids_success(self, angel_interface):
        """Test get_episodes_for_guids successfully batches and remaps episode data."""
        guids = ["guid-1", "guid-2", "guid-3"]

        # Mock response with sanitized keys
        mock_response = {
            "data": {
                "episode_guid_1": {"id": "ep1", "title": "Episode 1", "slug": "slug-1"},
                "episode_guid_2": {"id": "ep2", "title": "Episode 2", "slug": "slug-2"},
                "episode_guid_3": {"id": "ep3", "title": "Episode 3", "slug": "slug-3"},
            }
        }

        with (
            patch.object(angel_interface, "_load_fragment", return_value="...EpisodeListItem fragment"),
            patch.object(angel_interface.session, "post") as mock_post,
        ):
            mock_response_obj = MagicMock()
            mock_response_obj.json.return_value = mock_response
            mock_post.return_value = mock_response_obj

            result = angel_interface.get_episodes_for_guids(guids)

            # Verify remapping: sanitized keys (hyphens→underscores) back to episode_guid format
            assert "episode_guid-1" in result
            assert "episode_guid-2" in result
            assert "episode_guid-3" in result
            assert result["episode_guid-1"] == {"id": "ep1", "title": "Episode 1", "slug": "slug-1"}
            assert result["episode_guid-2"] == {"id": "ep2", "title": "Episode 2", "slug": "slug-2"}
            assert result["episode_guid-3"] == {"id": "ep3", "title": "Episode 3", "slug": "slug-3"}

            # Verify query construction: should contain sanitized aliases with underscores
            call_args = mock_post.call_args
            assert call_args is not None
            query_dict = call_args[1]["json"]
            assert "getEpisodesForGuids" in query_dict["operationName"]
            assert "episode_guid_1" in query_dict["query"]
            assert "episode_guid_2" in query_dict["query"]
            assert "episode_guid_3" in query_dict["query"]

    def test_get_episodes_for_guids_with_hyphens_in_guid(self, angel_interface):
        """Test get_episodes_for_guids correctly sanitizes guids with hyphens."""
        guids = ["ep-id-123", "ep-id-456"]

        mock_response = {
            "data": {
                "episode_ep_id_123": {"id": "ep1", "title": "Episode 1"},
                "episode_ep_id_456": {"id": "ep2", "title": "Episode 2"},
            }
        }

        with (
            patch.object(angel_interface, "_load_fragment", return_value="...fragment"),
            patch.object(angel_interface.session, "post") as mock_post,
        ):
            mock_response_obj = MagicMock()
            mock_response_obj.json.return_value = mock_response
            mock_post.return_value = mock_response_obj

            result = angel_interface.get_episodes_for_guids(guids)

            # Verify remapping preserves original guid format
            assert "episode_ep-id-123" in result
            assert "episode_ep-id-456" in result

    def test_get_episodes_for_guids_graphql_error(self, angel_interface):
        """Test get_episodes_for_guids returns empty dict on GraphQL error."""
        guids = ["guid-1", "guid-2"]

        mock_response = {"errors": [{"message": "Invalid query"}]}

        with (patch.object(angel_interface, "_load_fragment", return_value="...fragment"),):
            mock_post_response = MagicMock()
            mock_post_response.json = MagicMock(return_value=mock_response)
            angel_interface.session.post.return_value = mock_post_response

            result = angel_interface.get_episodes_for_guids(guids)

            assert result == {}
            angel_interface.log.error.assert_called()

    def test_get_episodes_for_guids_request_exception(self, angel_interface):
        """Test get_episodes_for_guids returns empty dict on request exception."""
        guids = ["guid-1", "guid-2"]

        with (
            patch.object(angel_interface, "_load_fragment", return_value="...fragment"),
            patch.object(angel_interface.session, "post") as mock_post,
        ):
            mock_post.side_effect = requests.RequestException("Connection failed")

            result = angel_interface.get_episodes_for_guids(guids)

            assert result == {}
            angel_interface.log.error.assert_called()

    def test_get_episodes_for_guids_unexpected_exception(self, angel_interface):
        """Test get_episodes_for_guids returns empty dict on unexpected exception."""
        guids = ["guid-1"]

        with patch.object(angel_interface, "_load_fragment", side_effect=Exception("Unexpected error")):
            result = angel_interface.get_episodes_for_guids(guids)

            assert result == {}
            angel_interface.log.error.assert_called()

    def test_get_projects_by_slugs_empty_list(self, angel_interface):
        """Test get_projects_by_slugs with empty slug list returns empty dict."""
        result = angel_interface.get_projects_by_slugs([])
        assert result == {}

    def test_get_projects_by_slugs_success(self, angel_interface):
        """Test get_projects_by_slugs successfully batches and remaps project data."""
        slugs = ["project-1", "project-2", "project-3"]

        mock_response = {
            "data": {
                "project_project_1": {"id": "p1", "name": "Project 1"},
                "project_project_2": {"id": "p2", "name": "Project 2"},
                "project_project_3": {"id": "p3", "name": "Project 3"},
            }
        }

        with patch.object(angel_interface.session, "post") as mock_post:
            mock_response_obj = MagicMock()
            mock_response_obj.json.return_value = mock_response
            mock_post.return_value = mock_response_obj

            result = angel_interface.get_projects_by_slugs(slugs)

            # Verify remapping: sanitized keys back to original slugs
            assert "project-1" in result
            assert "project-2" in result
            assert "project-3" in result
            assert result["project-1"] == {"id": "p1", "name": "Project 1"}
            assert result["project-2"] == {"id": "p2", "name": "Project 2"}
            assert result["project-3"] == {"id": "p3", "name": "Project 3"}

            # Verify query construction: should contain sanitized aliases with underscores
            call_args = mock_post.call_args
            assert call_args is not None
            query_dict = call_args[1]["json"]
            assert "getProjectsForSlugs" in query_dict["operationName"]
            assert "project_project_1" in query_dict["query"]
            assert "project_project_2" in query_dict["query"]
            assert "project_project_3" in query_dict["query"]

    def test_get_projects_by_slugs_with_hyphens_in_slug(self, angel_interface):
        """Test get_projects_by_slugs correctly sanitizes slugs with hyphens."""
        slugs = ["my-project-slug", "another-project"]

        mock_response = {
            "data": {
                "project_my_project_slug": {"id": "p1", "name": "My Project"},
                "project_another_project": {"id": "p2", "name": "Another Project"},
            }
        }

        with patch.object(angel_interface.session, "post") as mock_post:
            mock_response_obj = MagicMock()
            mock_response_obj.json.return_value = mock_response
            mock_post.return_value = mock_response_obj

            result = angel_interface.get_projects_by_slugs(slugs)

            # Verify remapping preserves original slug format
            assert "my-project-slug" in result
            assert "another-project" in result

    def test_get_projects_by_slugs_partial_response(self, angel_interface):
        """Test get_projects_by_slugs handles partial response (missing some projects)."""
        slugs = ["project-1", "project-2", "project-3"]

        # Only 2 out of 3 projects returned
        mock_response = {
            "data": {
                "project_project_1": {"id": "p1", "name": "Project 1"},
                "project_project_2": {"id": "p2", "name": "Project 2"},
            }
        }

        with patch.object(angel_interface.session, "post") as mock_post:
            mock_response_obj = MagicMock()
            mock_response_obj.json.return_value = mock_response
            mock_post.return_value = mock_response_obj

            result = angel_interface.get_projects_by_slugs(slugs)

            # Should only have the 2 projects that were returned
            assert len(result) == 2
            assert "project-1" in result
            assert "project-2" in result
            assert "project-3" not in result

    def test_get_projects_by_slugs_graphql_error(self, angel_interface):
        """Test get_projects_by_slugs returns empty dict on GraphQL error."""
        slugs = ["project-1", "project-2"]

        mock_response = {"errors": [{"message": "Invalid query"}]}

        mock_post_response = MagicMock()
        mock_post_response.json = MagicMock(return_value=mock_response)
        angel_interface.session.post.return_value = mock_post_response

        result = angel_interface.get_projects_by_slugs(slugs)

        assert result == {}

    def test_get_projects_by_slugs_request_exception(self, angel_interface):
        """Test get_projects_by_slugs returns empty dict on request exception."""
        slugs = ["project-1", "project-2"]

        with patch.object(angel_interface.session, "post") as mock_post:
            mock_post.side_effect = requests.RequestException("Connection failed")

            result = angel_interface.get_projects_by_slugs(slugs)

            assert result == {}
            angel_interface.log.error.assert_called()

    def test_get_projects_by_slugs_unexpected_exception(self, angel_interface):
        """Test get_projects_by_slugs returns empty dict on unexpected exception."""
        slugs = ["project-1"]

        with patch.object(angel_interface.session, "post", side_effect=Exception("Unexpected error")):
            result = angel_interface.get_projects_by_slugs(slugs)

            assert result == {}
            angel_interface.log.error.assert_called()

    def test_get_episodes_for_guids_request_exception_with_response_text_error(self, angel_interface):
        """Test get_episodes_for_guids handles exception when logging response body fails."""
        guids = ["guid-1"]

        # Create mock exception with response that fails when .text is accessed
        mock_exception = requests.RequestException("Test error")
        mock_response = MagicMock()
        mock_response.text = PropertyMock(side_effect=Exception("Cannot read response"))
        mock_exception.response = mock_response

        with (
            patch.object(angel_interface, "_load_fragment", return_value="...fragment"),
            patch.object(angel_interface.session, "post", side_effect=mock_exception),
        ):
            result = angel_interface.get_episodes_for_guids(guids)

            assert result == {}

    def test_get_projects_by_slugs_request_exception_with_response_text_error(self, angel_interface):
        """Test get_projects_by_slugs handles exception when logging response body fails."""
        slugs = ["project-1"]

        # Create mock exception with response that fails when .text is accessed
        mock_exception = requests.RequestException("Test error")
        mock_response = MagicMock()
        mock_response.text = PropertyMock(side_effect=Exception("Cannot read response"))
        mock_exception.response = mock_response

        with patch.object(angel_interface.session, "post", side_effect=mock_exception):
            result = angel_interface.get_projects_by_slugs(slugs)

            assert result == {}

    def test_graphql_timeout_raises_exception(self, angel_interface):
        """GraphQL timeout raises specific timeout exception."""
        with patch.object(angel_interface.session, "post", side_effect=requests.Timeout("Connection timed out")):
            with pytest.raises(
                Exception, match="Request timeout: Unable to connect to Angel Studios \\(timeout: 30s\\)"
            ):
                angel_interface._graphql_query("testOp", {})

    def test_batch_projects_timeout_raises_exception(self, angel_interface):
        """Batch projects timeout raises specific timeout exception."""
        slugs = ["test-slug"]
        with patch.object(angel_interface.session, "post", side_effect=requests.Timeout("Connection timed out")):
            with pytest.raises(
                Exception, match="Request timeout: Unable to connect to Angel Studios \\(timeout: 30s\\)"
            ):
                angel_interface.get_projects_by_slugs(slugs)

    def test_batch_episodes_timeout_raises_exception(self, angel_interface):
        """Batch episodes timeout raises specific timeout exception."""
        guids = ["test-guid"]
        with patch.object(angel_interface.session, "post", side_effect=requests.Timeout("Connection timed out")):
            with pytest.raises(
                Exception, match="Request timeout: Unable to connect to Angel Studios \\(timeout: 30s\\)"
            ):
                angel_interface.get_episodes_for_guids(guids)
