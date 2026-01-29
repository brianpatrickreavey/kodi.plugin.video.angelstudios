"""Unit tests for AuthenticationCore covering auth flows, token validation, and session management."""

import base64
import json
from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock, patch

import pytest
import requests

from auth0_ciam_client.core import AuthenticationCore, AuthResult
from auth0_ciam_client.config import Auth0Config
from auth0_ciam_client.session_store import InMemorySessionStore
from auth0_ciam_client.exceptions import AuthenticationRequiredError, NetworkError, AuthenticationError, InvalidCredentialsError


def _make_jwt(exp_ts: int) -> str:
    """Create a test JWT with given expiration timestamp."""
    header = base64.urlsafe_b64encode(json.dumps({"alg": "HS256"}).encode()).rstrip(b"=")
    payload = base64.urlsafe_b64encode(json.dumps({"exp": exp_ts}).encode()).rstrip(b"=")
    return f"{header.decode()}.{payload.decode()}.signature"


class TestAuthenticationCore:
    """Test AuthenticationCore functionality"""

    def test_init(self, mock_session_store, auth0_config, mock_logger):
        """Test AuthenticationCore initialization"""
        core = AuthenticationCore(
            session_store=mock_session_store,
            config=auth0_config,
            error_callback=None,
            logger=mock_logger
        )

        assert core.session_store == mock_session_store
        assert core.config == auth0_config
        assert core.error_callback is None
        assert core.log == mock_logger

    def test_validate_session_no_token(self, mock_session_store, auth0_config):
        """Test validate_session when no token exists"""
        mock_session_store.get_token.return_value = None

        core = AuthenticationCore(session_store=mock_session_store, config=auth0_config)

        result = core.validate_session()

        assert result is False
        mock_session_store.get_token.assert_called_once()

    def test_validate_session_valid_token(self, mock_session_store, auth0_config):
        """Test validate_session with valid token"""
        # Create a JWT that expires in the future
        future_ts = int((datetime.now(timezone.utc) + timedelta(hours=1)).timestamp())
        valid_token = _make_jwt(future_ts)
        mock_session_store.get_token.return_value = valid_token

        core = AuthenticationCore(session_store=mock_session_store, config=auth0_config)

        result = core.validate_session()

        assert result is True
        mock_session_store.get_token.assert_called_once()

    def test_validate_session_expired_token(self, mock_session_store, auth0_config):
        """Test validate_session with expired token"""
        # Create a JWT that expired in the past
        past_ts = int((datetime.now(timezone.utc) - timedelta(hours=1)).timestamp())
        expired_token = _make_jwt(past_ts)
        mock_session_store.get_token.return_value = expired_token

        core = AuthenticationCore(session_store=mock_session_store, config=auth0_config)

        result = core.validate_session()

        assert result is False
        mock_session_store.get_token.assert_called_once()

    def test_logout(self, mock_session_store, auth0_config):
        """Test logout functionality (clears token only, preserves credentials)"""
        mock_session = MagicMock()

        core = AuthenticationCore(session_store=mock_session_store, config=auth0_config)
        core.session = mock_session

        core.logout()

        mock_session_store.clear_token.assert_called_once()
        # Should NOT clear credentials - they should be preserved for re-auth
        mock_session_store.clear_credentials.assert_not_called()
        mock_session.cookies.clear.assert_called_once()
        mock_session.close.assert_called_once()

    @patch("auth0_ciam_client.core.requests.Session")
    def test_authenticate_with_existing_valid_token(self, mock_session_class, mock_session_store, auth0_config):
        """Test authenticate when valid token already exists"""
        future_ts = int((datetime.now(timezone.utc) + timedelta(hours=1)).timestamp())
        valid_token = _make_jwt(future_ts)
        mock_session_store.get_token.return_value = valid_token

        core = AuthenticationCore(session_store=mock_session_store, config=auth0_config)

        result = core.authenticate("user", "pass")

        assert result.success is True
        assert result.token == valid_token
        # Should not save token again since it already exists
        mock_session_store.save_token.assert_not_called()

    @patch("auth0_ciam_client.core.requests.Session")
    def test_authenticate_no_existing_token_performs_auth(self, mock_session_class, mock_session_store, auth0_config):
        """Test authenticate performs full auth when no token exists"""
        mock_session_store.get_token.return_value = None
        mock_session = MagicMock()
        mock_session_class.return_value = mock_session

        # Mock the login page response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b'<html><input id="state" name="state" value="test_state"></html>'
        mock_session.get.return_value = mock_response

        # Mock cookies to behave like a CookieJar
        mock_cookies = MagicMock()
        mock_cookies.get.return_value = "session_cookie"
        mock_session.cookies = mock_cookies

        # Mock the password post to return success
        mock_password_response = MagicMock()
        mock_password_response.status_code = 200
        mock_password_response.content = b'<html>No error message</html>'
        mock_session.post.return_value = mock_password_response

        # Mock cookies iteration to return a JWT token
        mock_cookie = MagicMock()
        mock_cookie.name = "angelSession"
        mock_cookie.value = "jwt.token.here"
        mock_session.cookies.__iter__.return_value = [mock_cookie]

        core = AuthenticationCore(session_store=mock_session_store, config=auth0_config)

        result = core.authenticate("user", "pass")

        # Should attempt authentication and succeed with mocked token
        assert result.success is True
        assert result.token == "jwt.token.here"
        mock_session_store.save_token.assert_called_once_with("jwt.token.here")
        mock_session_store.save_credentials.assert_called_once_with("user", "pass")

    def test_ensure_valid_session_no_token(self, mock_session_store, auth0_config):
        """Test ensure_valid_session raises error when no token exists and no credentials"""
        mock_session_store.get_token.return_value = None
        mock_session_store.get_credentials.return_value = (None, None)

        core = AuthenticationCore(session_store=mock_session_store, config=auth0_config)

        with pytest.raises(
            AuthenticationRequiredError, match="No authentication token available and no stored credentials"
        ):
            core.ensure_valid_session()

    def test_ensure_valid_session_no_token_with_credentials(self, mock_session_store, auth0_config):
        """Test ensure_valid_session authenticates when no token but credentials exist"""
        mock_session_store.get_token.return_value = None
        mock_session_store.get_credentials.return_value = ("user@example.com", "password")
        mock_session_store.save_token = MagicMock()

        core = AuthenticationCore(session_store=mock_session_store, config=auth0_config)

        # Mock the authenticate method to return success
        with patch.object(core, "authenticate") as mock_auth:
            mock_auth.return_value = AuthResult(success=True, token="new.jwt.token")

            # Should not raise an exception
            core.ensure_valid_session()

            # Should have called authenticate with credentials
            mock_auth.assert_called_once_with("user@example.com", "password")

    def test_ensure_valid_session_invalid_token(self, mock_session_store, auth0_config):
        """Test ensure_valid_session raises error for invalid token"""
        mock_session_store.get_token.return_value = "invalid.jwt.token"

        core = AuthenticationCore(session_store=mock_session_store, config=auth0_config)

        with pytest.raises(AuthenticationRequiredError, match="Invalid authentication token"):
            core.ensure_valid_session()

    def test_ensure_valid_session_valid_token(self, mock_session_store, auth0_config):
        """Test ensure_valid_session succeeds with valid token not expiring soon"""
        # Token expires in 2 hours, buffer is 1 hour, so no refresh needed
        future_ts = int((datetime.now(timezone.utc) + timedelta(hours=2)).timestamp())
        valid_token = _make_jwt(future_ts)
        mock_session_store.get_token.return_value = valid_token
        mock_session_store.get_expiry_buffer_hours.return_value = 1

        core = AuthenticationCore(session_store=mock_session_store, config=auth0_config)

        # Should not raise any exception
        core.ensure_valid_session()

    def test_ensure_valid_session_expiring_no_credentials(self, mock_session_store, auth0_config):
        """Test ensure_valid_session raises error when token expiring and no credentials"""
        # Token expires in 30 minutes, within 1 hour buffer
        soon_ts = int((datetime.now(timezone.utc) + timedelta(minutes=30)).timestamp())
        expiring_token = _make_jwt(soon_ts)
        mock_session_store.get_token.return_value = expiring_token
        mock_session_store.get_credentials.return_value = (None, None)
        mock_session_store.get_expiry_buffer_hours.return_value = 1

        core = AuthenticationCore(session_store=mock_session_store, config=auth0_config)

        with pytest.raises(AuthenticationRequiredError, match="Token expiring and no stored credentials"):
            core.ensure_valid_session()

    @patch("auth0_ciam_client.core.requests.Session")
    def test_ensure_valid_session_expiring_successful_refresh(self, mock_session_class, mock_session_store, auth0_config):
        """Test ensure_valid_session successfully refreshes expiring token"""
        # Token expires in 30 minutes, within 1 hour buffer
        soon_ts = int((datetime.now(timezone.utc) + timedelta(minutes=30)).timestamp())
        expiring_token = _make_jwt(soon_ts)
        mock_session_store.get_token.return_value = expiring_token
        mock_session_store.get_credentials.return_value = ("user", "pass")
        mock_session_store.get_expiry_buffer_hours.return_value = 1

        # Mock successful authentication
        new_token = "new.jwt.token"
        mock_session_store.save_token.return_value = None

        core = AuthenticationCore(session_store=mock_session_store, config=auth0_config)
        # Mock the authenticate method to return success
        with patch.object(core, "authenticate", return_value=AuthResult(success=True, token=new_token)):
            # Should not raise any exception
            core.ensure_valid_session()

            # Should have called authenticate with stored credentials
            core.authenticate.assert_called_once_with("user", "pass")

    @patch("auth0_ciam_client.core.requests.Session")
    def test_ensure_valid_session_expiring_failed_refresh(self, mock_session_class, mock_session_store, auth0_config):
        """Test ensure_valid_session raises error when refresh fails"""
        # Token expires in 30 minutes, within 1 hour buffer
        soon_ts = int((datetime.now(timezone.utc) + timedelta(minutes=30)).timestamp())
        expiring_token = _make_jwt(soon_ts)
        mock_session_store.get_token.return_value = expiring_token
        mock_session_store.get_credentials.return_value = ("user", "pass")
        mock_session_store.get_expiry_buffer_hours.return_value = 1

        core = AuthenticationCore(session_store=mock_session_store, config=auth0_config)
        # Mock failed authentication
        with patch.object(core, "authenticate", return_value=AuthResult(success=False, error_message="Auth failed")):
            with pytest.raises(AuthenticationRequiredError, match="Automatic refresh failed: Auth failed"):
                core.ensure_valid_session()

    def test_validate_token_malformed_jwt(self, mock_session_store, auth0_config):
        """Test _validate_token with malformed JWTs"""
        core = AuthenticationCore(session_store=mock_session_store, config=auth0_config)

        # Test token with wrong number of parts
        assert not core._validate_token("invalid.jwt")
        assert not core._validate_token("only.two.parts")
        assert not core._validate_token("too.many.parts.in.this.jwt.token")

    def test_validate_token_invalid_base64(self, mock_session_store, auth0_config):
        """Test _validate_token with invalid base64"""
        core = AuthenticationCore(session_store=mock_session_store, config=auth0_config)

        # Test token with invalid base64 characters
        assert not core._validate_token("header.!@#$%.signature")

    def test_validate_token_missing_exp(self, mock_session_store, auth0_config):
        """Test _validate_token with JWT missing exp claim"""
        import base64
        import json

        core = AuthenticationCore(session_store=mock_session_store, config=auth0_config)

        # Create JWT without exp claim
        header = base64.urlsafe_b64encode(json.dumps({"alg": "HS256"}).encode()).decode()
        payload = base64.urlsafe_b64encode(json.dumps({"sub": "user123"}).encode()).decode()
        token = f"{header}.{payload}.signature"

        assert not core._validate_token(token)

    def test_validate_token_expired(self, mock_session_store, auth0_config):
        """Test _validate_token with expired JWT"""
        core = AuthenticationCore(session_store=mock_session_store, config=auth0_config)

        # Create expired token
        past_ts = int((datetime.now(timezone.utc) - timedelta(hours=1)).timestamp())
        expired_token = _make_jwt(past_ts)

        assert not core._validate_token(expired_token)

    @patch("auth0_ciam_client.core.requests.Session")
    def test_perform_authentication_login_timeout(self, mock_session_class, mock_session_store, auth0_config):
        """Test _perform_authentication handles login page timeout"""
        mock_session = MagicMock()
        mock_session_class.return_value = mock_session
        mock_session.get.side_effect = requests.Timeout()

        core = AuthenticationCore(session_store=mock_session_store, config=auth0_config)
        core.session = mock_session

        with pytest.raises(NetworkError, match="Request timeout"):
            core._perform_authentication("user", "pass")

    @patch("auth0_ciam_client.core.requests.Session")
    def test_perform_authentication_login_http_error(self, mock_session_class, mock_session_store, auth0_config):
        """Test _perform_authentication handles login page HTTP errors"""
        mock_session = MagicMock()
        mock_session_class.return_value = mock_session

        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_session.get.return_value = mock_response

        core = AuthenticationCore(session_store=mock_session_store, config=auth0_config)
        core.session = mock_session

        with pytest.raises(NetworkError, match="HTTP 500"):
            core._perform_authentication("user", "pass")

    @patch("auth0_ciam_client.core.requests.Session")
    def test_perform_authentication_password_redirect_error(self, mock_session_class, mock_session_store, auth0_config):
        """Test _perform_authentication handles redirect without Location header"""
        mock_session = MagicMock()
        mock_session_class.return_value = mock_session

        # Mock successful login page fetch
        mock_login_response = MagicMock()
        mock_login_response.status_code = 200
        mock_login_response.content = b'<input id="state" name="state" value="test_state">'
        mock_session.get.return_value = mock_login_response

        # Mock password post with redirect but no Location header
        mock_password_response = MagicMock()
        mock_password_response.status_code = 302
        mock_password_response.headers = {}  # No Location header
        mock_session.post.return_value = mock_password_response

        core = AuthenticationCore(session_store=mock_session_store, config=auth0_config)
        core.session = mock_session

        with pytest.raises(AuthenticationError, match="missing Location header"):
            core._perform_authentication("user", "pass")

    @patch("auth0_ciam_client.core.requests.Session")
    def test_perform_authentication_invalid_credentials_401(self, mock_session_class, mock_session_store, auth0_config):
        """Test _perform_authentication handles 401 Unauthorized"""
        mock_session = MagicMock()
        mock_session_class.return_value = mock_session

        # Mock successful login and email pages
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b'<input id="state" name="state" value="test_state"><input name="_csrf_token" value="csrf123">'
        mock_session.get.return_value = mock_response

        # Mock password post returning 401
        mock_password_response = MagicMock()
        mock_password_response.status_code = 401
        mock_password_response.content = b"Unauthorized"
        mock_session.post.return_value = mock_password_response

        core = AuthenticationCore(session_store=mock_session_store, config=auth0_config)
        core.session = mock_session

        with pytest.raises(InvalidCredentialsError, match="HTTP 401"):
            core._perform_authentication("user", "pass")

    @patch("auth0_ciam_client.core.requests.Session")
    def test_perform_authentication_html_error_message(self, mock_session_class, mock_session_store, auth0_config):
        """Test _perform_authentication detects error messages in HTML"""
        mock_session = MagicMock()
        mock_session_class.return_value = mock_session

        # Mock successful login and email pages
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b'<input id="state" name="state" value="test_state"><input name="_csrf_token" value="csrf123">'
        mock_session.get.return_value = mock_response

        # Mock password post with error message in HTML
        mock_password_response = MagicMock()
        mock_password_response.status_code = 200
        mock_password_response.content = b'<div class="error-message">Invalid username or password</div>'
        mock_session.post.return_value = mock_password_response

        core = AuthenticationCore(session_store=mock_session_store, config=auth0_config)
        core.session = mock_session

        with pytest.raises(InvalidCredentialsError, match="Invalid username or password"):
            core._perform_authentication("user", "pass")

    @patch("auth0_ciam_client.core.requests.Session")
    def test_perform_authentication_no_token_found(self, mock_session_class, mock_session_store, auth0_config):
        """Test _perform_authentication returns None when no JWT cookie found"""
        mock_session = MagicMock()
        mock_session_class.return_value = mock_session

        # Mock successful login and email pages
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b'<input id="state" name="state" value="test_state"><input name="_csrf_token" value="csrf123">'
        mock_session.get.return_value = mock_response

        # Mock successful password post
        mock_password_response = MagicMock()
        mock_password_response.status_code = 200
        mock_password_response.content = b'<html>No error</html>'
        mock_session.post.return_value = mock_password_response

        # Mock cookies that behave like CookieJar but return no JWT cookies
        mock_cookies = MagicMock()
        mock_cookies.get.return_value = "session_value"
        mock_session.cookies = mock_cookies

        core = AuthenticationCore(session_store=mock_session_store, config=auth0_config)
        core.session = mock_session

        result = core._perform_authentication("user", "pass")
        assert result is None

    def test_ensure_valid_session_token_refresh_failure(self, mock_session_store, auth0_config):
        """Test ensure_valid_session handles refresh failure"""
        # Token expires in 30 minutes, within 1 hour buffer
        soon_ts = int((datetime.now(timezone.utc) + timedelta(minutes=30)).timestamp())
        expiring_token = _make_jwt(soon_ts)
        mock_session_store.get_token.return_value = expiring_token
        mock_session_store.get_credentials.return_value = ("user", "pass")
        mock_session_store.get_expiry_buffer_hours.return_value = 1

        core = AuthenticationCore(session_store=mock_session_store, config=auth0_config)

        # Mock failed authentication during refresh
        with patch.object(core, "authenticate", return_value=AuthResult(success=False, error_message="Auth failed")):
            with pytest.raises(AuthenticationRequiredError, match="Automatic refresh failed: Auth failed"):
                core.ensure_valid_session()

    def test_ensure_valid_session_no_stored_credentials_for_refresh(self, mock_session_store, auth0_config):
        """Test ensure_valid_session raises error when no credentials for refresh"""
        # Token expires in 30 minutes, within 1 hour buffer
        soon_ts = int((datetime.now(timezone.utc) + timedelta(minutes=30)).timestamp())
        expiring_token = _make_jwt(soon_ts)
        mock_session_store.get_token.return_value = expiring_token
        mock_session_store.get_credentials.return_value = (None, None)
        mock_session_store.get_expiry_buffer_hours.return_value = 1

        core = AuthenticationCore(session_store=mock_session_store, config=auth0_config)

        with pytest.raises(AuthenticationRequiredError, match="no stored credentials for refresh"):
            core.ensure_valid_session()

    def test_authenticate_catches_generic_exception(self, mock_session_store, auth0_config):
        """Test authenticate handles generic exceptions"""
        mock_session_store.get_token.return_value = None

        core = AuthenticationCore(session_store=mock_session_store, config=auth0_config)

        # Mock _perform_authentication to raise a generic exception
        with patch.object(core, "_perform_authentication", side_effect=Exception("Generic error")):
            result = core.authenticate("user", "pass")

            assert result.success is False
            assert "Authentication error: Generic error" in result.error_message