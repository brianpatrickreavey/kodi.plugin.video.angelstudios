import pytest
import requests
from unittest.mock import patch, MagicMock, mock_open
import os
import sys

# Add the lib path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'resources', 'lib'))

from angel_interface import AngelStudiosInterface, angel_graphql_url
from .unittest_data import MOCK_PROJECT_DATA, MOCK_EPISODE_DATA, MOCK_GRAPHQL_RESPONSE



class TestAngelStudiosInterface:
    @pytest.fixture
    def angel_interface(self):
        """Fixture for a mocked AngelStudiosInterface instance."""
        with (
            patch('angel_interface.angel_authentication.AngelStudioSession') as mock_session_class,
            patch('angel_interface.requests.Session') as mock_session,
        ):
            mock_session_instance = MagicMock()
            mock_session_class.return_value.authenticate.return_value = None
            mock_session_class.return_value.get_session.return_value = mock_session_instance
            mock_session_class.return_value._validate_session.return_value = True

            interface = AngelStudiosInterface(logger=MagicMock())
            return interface

    @pytest.mark.parametrize(
        "auth_header, expected_log",
        [
            ('token', "Authenticated Session: JWT token present, 0 cookies"),
            (None, "Session initialized: No JWT token, 0 cookies"),
        ],
    )
    def test_init_with_and_without_auth(self, auth_header, expected_log):
        """Test __init__ wiring with and without an auth header."""
        logger = MagicMock()
        with (
            patch('angel_interface.angel_authentication.AngelStudioSession') as mock_session_class,
            patch('angel_interface.requests.Session'),
        ):
            mock_session_instance = MagicMock()
            mock_session_instance.headers.get.return_value = auth_header
            mock_session_instance.cookies = []
            mock_session_class.return_value.authenticate.return_value = None
            mock_session_class.return_value.get_session.return_value = mock_session_instance
            mock_session_class.return_value._validate_session.return_value = True

            interface = AngelStudiosInterface(logger=logger)

            mock_session_class.assert_called_once_with(username=None, password=None, session_file='', logger=logger)
            mock_session_class.return_value.authenticate.assert_called_once()
            mock_session_class.return_value.get_session.assert_called_once()
            assert interface.log is logger
            logger.info.assert_any_call("Custom logger initialized")
            logger.info.assert_any_call(expected_log)

    def test_init_without_logger(self):
        """Test __init__ without logger (uses default)."""
        with (
            patch('angel_interface.angel_authentication.AngelStudioSession'),
            patch('angel_interface.requests.Session'),
        ):
            interface = AngelStudiosInterface()
            # Verify default logger is set and no custom log
            assert interface.log is not None
            # Note: Default logger setup doesn't log "Custom logger initialized"

    def test_init_fails_when_session_is_none(self):
        """Test __init__ raises exception when get_session() returns None."""
        with (
            patch('angel_interface.angel_authentication.AngelStudioSession') as mock_session_class,
        ):
            mock_session_instance = mock_session_class.return_value
            mock_session_instance.authenticate.return_value = True
            # get_session returns None (should never happen, but defensive check)
            mock_session_instance.get_session.return_value = None

            with pytest.raises(Exception, match="Failed to initialize session: No session available"):
                AngelStudiosInterface()

    def test_load_query_success(self, angel_interface):
        """Test _load_query loads and caches a query successfully."""
        with patch('builtins.open', mock_open(read_data='query content')) as mock_file:
            first_result = angel_interface._load_query('test_operation')
            assert first_result == 'query content'
            mock_file.assert_called_once_with(
                os.path.join(angel_interface.query_path, 'query_test_operation.graphql'), 'r')
            assert 'test_operation' in angel_interface._query_cache

            # Second call: hit cache, cover early return
            second_result = angel_interface._load_query('test_operation')
            assert second_result == 'query content'
            # open should not be called again
            mock_file.assert_called_once()  # Still only once
            assert angel_interface._query_cache['test_operation'] == 'query content'

    def test_load_query_failure(self, angel_interface):
        """Test _load_query handles file loading failure."""
        with patch('builtins.open', side_effect=FileNotFoundError) as mock_file:
            result = angel_interface._load_query('test_operation')
            assert result == ""
            assert 'test_operation' not in angel_interface._query_cache
            mock_file.assert_called_once_with(
                os.path.join(angel_interface.query_path, 'query_test_operation.graphql'), 'r')

            # Assert error logging occurred
            expected_path = os.path.join(angel_interface.query_path, 'query_test_operation.graphql')
            angel_interface.log.error.assert_called_once_with(f"Error loading query file '{expected_path}': ")

    def test_load_fragment_success(self, angel_interface):
        """Test _load_fragment loads and caches a fragment successfully."""
        with patch('builtins.open', mock_open(read_data='fragment content')) as mock_file:
            first_result = angel_interface._load_fragment('test_fragment')
            assert first_result == 'fragment content'
            mock_file.assert_called_once_with(
                os.path.join(angel_interface.query_path, 'fragment_test_fragment.graphql'), 'r')
            assert 'test_fragment' in angel_interface._fragment_cache

            # Second call should hit cache and avoid re-opening the file
            second_result = angel_interface._load_fragment('test_fragment')
            assert second_result == 'fragment content'
            mock_file.assert_called_once()

    def test_load_fragment_failure(self, angel_interface):
        """Test _load_fragment handles file loading failure."""
        with patch('builtins.open', side_effect=FileNotFoundError) as mock_file:
            result = angel_interface._load_fragment('test_fragment')
            assert result == ""
            assert 'test_fragment' not in angel_interface._fragment_cache
            mock_file.assert_called_once_with(
                os.path.join(angel_interface.query_path, 'fragment_test_fragment.graphql'), 'r')

            # Assert error logging occurred
            expected_path = os.path.join(angel_interface.query_path, 'fragment_test_fragment.graphql')
            angel_interface.log.error.assert_called_once_with(f"Error loading fragment 'test_fragment' from '{expected_path}': ")

    @pytest.mark.parametrize("operation", ["getProjectsForMenu", "getProject"])
    def test_graphql_query_success(self, angel_interface, operation):
        """Test _graphql_query executes successfully for different operations."""
        with (
            patch.object(angel_interface, '_load_query', return_value='query body without fragments') as mock_load_query,
            patch.object(angel_interface, '_load_fragment') as mock_load_fragment,
            patch.object(angel_interface.session, 'post') as mock_post,
        ):
            mock_response = MagicMock()
            mock_response.json.return_value = MOCK_GRAPHQL_RESPONSE
            mock_post.return_value = mock_response

            result = angel_interface._graphql_query(operation)

            # Assert the method returns the expected data from the response
            expected_data = MOCK_PROJECT_DATA['multi_season_project']
            assert result == expected_data

            # Assert the POST request was made exactly once to the GraphQL URL
            mock_post.assert_called_once()
            call_args = mock_post.call_args
            assert call_args[0][0] == angel_graphql_url  # First positional arg is the URL
            query_payload = call_args[1]['json']  # Keyword arg 'json' contains the payload
            assert query_payload['operationName'] == operation
            assert 'query' in query_payload
            assert query_payload['variables'] == {}

            # Assert supporting calls/logs
            mock_load_query.assert_called_once_with(operation)
            mock_load_fragment.assert_not_called()
            mock_response.raise_for_status.assert_called_once()
            angel_interface.log.debug.assert_any_call(f"Executing GraphQL query: {operation}")

    def test_graphql_query_with_fragment(self, angel_interface):
        """Ensure fragment references trigger fragment loading and still return data."""
        with (
            patch.object(angel_interface, '_load_query', return_value='query ... FragX'),
            patch.object(angel_interface, '_load_fragment', return_value='fragment FragX on Foo { id }') as mock_fragment,
            patch.object(angel_interface.session, 'post') as mock_post,
        ):
            mock_post.return_value.json.return_value = {'data': {'ok': True}}
            mock_post.return_value.raise_for_status.return_value = None

            result = angel_interface._graphql_query('op_with_fragment')

            assert result == {'ok': True}
            mock_fragment.assert_called_once_with('FragX')
            mock_post.assert_called_once()

    def test_graphql_query_with_multiple_fragments(self, angel_interface):
        """Ensure multiple fragment references are de-duplicated and loaded once each."""
        query_body = 'query ... FragX ... FragY ... FragX'
        with (
            patch.object(angel_interface, '_load_query', return_value=query_body),
            patch.object(angel_interface.session, 'post') as mock_post,
            patch.object(angel_interface, '_load_fragment', side_effect=['fragX body', 'fragY body']) as mock_frag,
        ):
            mock_response = MagicMock()
            mock_response.json.return_value = {'data': {'ok': True}}
            mock_post.return_value = mock_response

            result = angel_interface._graphql_query('op_with_frags')

            assert result == {'ok': True}
            assert mock_frag.call_count == 2
            mock_frag.assert_any_call('FragX')
            mock_frag.assert_any_call('FragY')
            mock_post.assert_called_once()
            mock_response.raise_for_status.assert_called_once()

    def test_graphql_query_with_errors(self, angel_interface):
        """Test _graphql_query handles GraphQL errors."""
        with (
            patch.object(angel_interface.session, 'post') as mock_post,
            patch.object(angel_interface.angel_studios_session, 'authenticate') as mock_authenticate,
        ):
            mock_response = MagicMock()
            mock_response.json.return_value = {'errors': ['GraphQL error occurred']}
            mock_post.return_value = mock_response

            result = angel_interface._graphql_query('test_operation')

            # Assert the method returns an empty dict on GraphQL errors
            assert result == {}

            # Assert re-authentication is triggered due to errors
            mock_authenticate.assert_called_once_with(force_reauthentication=True)

            # Assert error logging occurred and raise_for_status was called
            mock_response.raise_for_status.assert_called_once()
            angel_interface.log.error.assert_any_call("GraphQL errors: ['GraphQL error occurred']")
            angel_interface.log.error.assert_any_call(f"session headers: {angel_interface.session.headers}")

    def test_graphql_query_request_failure(self, angel_interface):
        """Test _graphql_query handles request exceptions."""
        with (
            patch.object(angel_interface, '_load_query', return_value='dummy query') as mock_load_query,
            patch.object(angel_interface.session, 'post', side_effect=Exception('Request failed')) as mock_post,
            patch.object(angel_interface.angel_studios_session, 'authenticate') as mock_authenticate
        ):
            result = angel_interface._graphql_query('test_operation')

            # Assert the method returns an empty dict on request failure
            mock_load_query.assert_called_once_with('test_operation')
            mock_post.assert_called_once()
            assert result == {}

            # Assert no re-authentication is triggered (only for GraphQL errors, not general exceptions)
            mock_authenticate.assert_not_called()

            # Assert error logging occurred
            angel_interface.log.error.assert_called_once_with("Unexpected error during GraphQL query: Request failed")


    def test_graphql_query_request_exception(self, angel_interface):
        """Test _graphql_query handles requests.RequestException specifically."""
        with (
            patch.object(angel_interface, '_load_query', return_value='dummy query'),
            patch.object(angel_interface.session, 'post', side_effect=requests.RequestException('boom')) as mock_post,
            patch.object(angel_interface.angel_studios_session, 'authenticate') as mock_authenticate,
        ):
            result = angel_interface._graphql_query('test_operation')

            assert result == {}
            mock_post.assert_called_once()
            mock_authenticate.assert_not_called()
            angel_interface.log.error.assert_called_once_with('GraphQL request failed: boom')


    def test_graphql_query_tracer_filters_headers(self, angel_interface):
        """Tracer receives redacted headers and response data."""
        angel_interface.tracer = MagicMock()
        angel_interface.session.headers = {'Authorization': 'secret', 'Cookie': 'c', 'X-Test': 'ok'}
        response = MagicMock()
        response.json.return_value = {'data': {'ok': True}}
        response.status_code = 200

        with patch.object(angel_interface.session, 'post', return_value=response):
            result = angel_interface._graphql_query('op')

        assert result == {'ok': True}
        angel_interface.tracer.assert_called_once()
        trace_payload = angel_interface.tracer.call_args[0][0]
        assert trace_payload['request']['headers'] == {'X-Test': 'ok'}
        assert trace_payload['response'] == {'ok': True}


    def test_graphql_query_tracer_exception_swallowed(self, angel_interface):
        """Exceptions from tracer do not break flow."""
        angel_interface.tracer = MagicMock(side_effect=RuntimeError("boom"))
        response = MagicMock()
        response.json.return_value = {'data': {'ok': True}}
        response.status_code = 200

        with patch.object(angel_interface.session, 'post', return_value=response):
            result = angel_interface._graphql_query('op')

        assert result == {'ok': True}
        # No exception propagates


    def test_graphql_query_request_exception_tracer(self, angel_interface):
        """Tracer invoked on RequestException with sanitized headers."""
        angel_interface.tracer = MagicMock()
        angel_interface.session.headers = {'Authorization': 'secret', 'Cookie': 'c', 'X-Test': 'ok'}
        exc = requests.RequestException('boom')
        exc.response = MagicMock(status_code=503)

        with patch.object(angel_interface.session, 'post', side_effect=exc):
            result = angel_interface._graphql_query('op')

        assert result == {}
        angel_interface.tracer.assert_called_once()
        payload = angel_interface.tracer.call_args[0][0]
        assert payload['status'] == 503
        assert payload['request']['headers'] == {'X-Test': 'ok'}


    def test_graphql_query_unexpected_exception_tracer(self, angel_interface):
        """Tracer invoked on generic exceptions."""
        angel_interface.tracer = MagicMock()
        angel_interface.session.headers = {'Authorization': 'secret', 'Cookie': 'c', 'X-Test': 'ok'}
        response = MagicMock()
        response.json.side_effect = ValueError("bad json")

        with patch.object(angel_interface.session, 'post', return_value=response):
            result = angel_interface._graphql_query('op')

        assert result == {}
        angel_interface.tracer.assert_called_once()
        payload = angel_interface.tracer.call_args[0][0]
        assert payload['request']['headers'] == {'X-Test': 'ok'}


    def test_graphql_query_request_exception_tracer_raises(self, angel_interface):
        """Tracer exceptions on RequestException are swallowed."""
        angel_interface.tracer = MagicMock(side_effect=RuntimeError("boom"))
        angel_interface.session.headers = {'Authorization': 'secret'}
        exc = requests.RequestException('fail')

        with patch.object(angel_interface.session, 'post', side_effect=exc):
            assert angel_interface._graphql_query('op') == {}


    def test_graphql_query_unexpected_exception_tracer_raises(self, angel_interface):
        """Tracer exceptions on generic exceptions are swallowed."""
        angel_interface.tracer = MagicMock(side_effect=RuntimeError("boom"))
        angel_interface.session.headers = {'Authorization': 'secret'}
        response = MagicMock()
        response.json.side_effect = ValueError("bad json")

        with patch.object(angel_interface.session, 'post', return_value=response):
            assert angel_interface._graphql_query('op') == {}

    @pytest.mark.parametrize("project_type", [None, 'series', 'movie'])
    def test_get_projects(self, angel_interface, project_type):
        """Test get_projects fetches and filters projects."""
        # Prepare mock data: list of projects from MOCK_PROJECT_DATA
        projects_list = list(MOCK_PROJECT_DATA.values())
        mock_response = {'projects': projects_list}

        with patch.object(angel_interface, '_graphql_query') as mock_query:
            mock_query.return_value = mock_response
            result = angel_interface.get_projects(project_type=project_type)

            # Assert _graphql_query was called correctly
            mock_query.assert_called_once_with("getProjectsForMenu", variables={})

            # Assert the result is filtered correctly
            expected = [p for p in projects_list if project_type is None or p.get('projectType') == project_type]
            assert result == expected

            # Assert info logging occurred
            angel_interface.log.info.assert_any_call("Fetching projects using GraphQL...")

    def test_get_projects_exception(self, angel_interface):
        """Test get_projects handles exceptions."""
        with patch.object(angel_interface, '_graphql_query', side_effect=Exception('Query failed')) as mock_query:
            result = angel_interface.get_projects()

            # Assert the method returns an empty list on exception
            assert result == []

            # Assert _graphql_query was attempted
            mock_query.assert_called_once_with("getProjectsForMenu", variables={})

            # Assert error logging occurred
            angel_interface.log.error.assert_called_once_with("Error fetching projects: Query failed")

    @pytest.mark.parametrize("cloudinary_path", [None, 'path/to/image'])
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
        with patch.object(angel_interface, '_graphql_query') as mock_query:
            mock_query.return_value = {'project': {'slug': 'test'}}
            result = angel_interface.get_project('test_slug')

            assert result == {'slug': 'test'}
            mock_query.assert_called_once_with("getProject", variables={"slug": "test_slug", "includePrerelease": True, "includeSeasons": True})

    def test_get_project_not_found(self, angel_interface):
        """Test get_project handles project not found."""
        with patch.object(angel_interface, '_graphql_query') as mock_query:
            mock_query.return_value = {}
            result = angel_interface.get_project('test_slug')

            assert result is None
            mock_query.assert_called_once_with("getProject", variables={"slug": "test_slug", "includePrerelease": True, "includeSeasons": True})
            angel_interface.log.warning.assert_called_once_with("No project found for slug: test_slug")

    def test_get_project_exception(self, angel_interface):
        """Test get_project handles exceptions."""
        with patch.object(angel_interface, '_graphql_query', side_effect=Exception('Query failed')) as mock_query:
            result = angel_interface.get_project('test_slug')

            assert result is None
            mock_query.assert_called_once_with("getProject", variables={"slug": "test_slug", "includePrerelease": True, "includeSeasons": True})
            angel_interface.log.error.assert_called_once_with("Error fetching project by slug 'test_slug': Query failed")

    def test_get_episode_data_success(self, angel_interface):
        """Test get_episode_data fetches episode data successfully."""
        with patch.object(angel_interface, '_graphql_query') as mock_query:
            mock_query.return_value = MOCK_EPISODE_DATA
            result = angel_interface.get_episode_data('ep_guid', 'project_slug')

            assert result == MOCK_EPISODE_DATA
            mock_query.assert_called_once_with("getEpisodeAndUserWatchData", variables={"guid": "ep_guid", "projectSlug": "project_slug", "includePrerelease": True, "authenticated": True, "reactionsRollupInterval": 4000})

    def test_get_episode_data_exception(self, angel_interface):
        """Test get_episode_data handles exceptions."""
        with patch.object(angel_interface, '_graphql_query', side_effect=Exception('Query failed')) as mock_query:
            result = angel_interface.get_episode_data('ep_guid', 'project_slug')

            assert result == {}
            mock_query.assert_called_once_with("getEpisodeAndUserWatchData", variables={"guid": "ep_guid", "projectSlug": "project_slug", "includePrerelease": True, "authenticated": True, "reactionsRollupInterval": 4000})
            angel_interface.log.error.assert_called_once_with("Error fetching episode data for GUID 'ep_guid': Query failed")

    def test_session_check_valid(self, angel_interface):
        """Test session_check when session is valid."""
        with patch.object(angel_interface.angel_studios_session, '_validate_session', return_value=True) as mock_validate:
            angel_interface.session_check()

            mock_validate.assert_called_once()
            angel_interface.log.info.assert_any_call("Session is valid")

    def test_session_check_invalid(self, angel_interface):
        """Test session_check when session is invalid and re-auth succeeds."""
        with (
            patch.object(angel_interface.angel_studios_session, '_validate_session', return_value=False) as mock_validate,
            patch.object(angel_interface.angel_studios_session, 'authenticate') as mock_auth,
        ):
            mock_auth.return_value = None
            angel_interface.angel_studios_session.session_valid = True
            angel_interface.session_check()

            mock_validate.assert_called_once()
            mock_auth.assert_called_once_with(force_reauthentication=True)
            angel_interface.log.info.assert_any_call("Session is not valid, re-authenticating...")

    def test_session_check_reauth_failure(self, angel_interface):
        """Test session_check when re-auth fails."""
        with (
            patch.object(angel_interface.angel_studios_session, '_validate_session', return_value=False) as mock_validate,
            patch.object(angel_interface.angel_studios_session, 'authenticate') as mock_auth,
        ):
            mock_auth.return_value = None
            angel_interface.angel_studios_session.session_valid = False

            with pytest.raises(Exception, match="Session re-authentication failed"):
                angel_interface.session_check()

            mock_validate.assert_called_once()
            mock_auth.assert_called_once_with(force_reauthentication=True)
            angel_interface.log.error.assert_called_once_with("Session re-authentication failed")

    def test_force_logout_exception(self):
        """force_logout returns False on exception and logs error."""
        iface = object.__new__(AngelStudiosInterface)
        iface.log = MagicMock()
        iface.angel_studios_session = MagicMock()
        iface.angel_studios_session.logout.side_effect = RuntimeError("boom")
        iface.session = MagicMock()

        result = iface.force_logout()

        assert result is False
        iface.log.error.assert_called_once()

    def test_force_logout_success(self):
        """force_logout clears session on success."""
        asi = object.__new__(AngelStudiosInterface)
        asi.log = MagicMock()
        asi.angel_studios_session = MagicMock()
        asi.angel_studios_session.logout.return_value = True
        fresh_session = MagicMock()
        asi.angel_studios_session.get_session.return_value = fresh_session
        old_session = MagicMock()
        asi.session = old_session

        result = asi.force_logout()

        assert result is True
        assert asi.session is fresh_session
        assert asi.session is not old_session