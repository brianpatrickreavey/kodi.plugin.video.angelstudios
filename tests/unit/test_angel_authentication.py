"""Unit tests for AngelStudioSession covering auth flows, cookies, and JWT parsing."""

import base64
import json
import pickle
from datetime import datetime, timezone, timedelta
from types import SimpleNamespace
from unittest.mock import MagicMock, mock_open, patch

import pytest
import requests
from bs4 import Tag

from resources.lib.angel_authentication import AngelStudioSession
import resources.lib.angel_utils as angel_utils


def test_sanitize_headers_for_logging():
    """Test that sensitive headers are redacted and others pass through."""
    # Mixed headers with sensitive and non-sensitive
    headers = {
        "Authorization": "Bearer secret_token",
        "Cookie": "session=abc123",
        "X-API-Key": "api_key_value",
        "Content-Type": "application/json",
        "Accept": "text/html",
        "User-Agent": "test-agent",
    }

    result = angel_utils.sanitize_headers_for_logging(headers)

    # Sensitive headers should be redacted
    assert result["Authorization"] == "[REDACTED]"
    assert result["Cookie"] == "[REDACTED]"
    assert result["X-API-Key"] == "[REDACTED]"

    # Non-sensitive headers should pass through unchanged
    assert result["Content-Type"] == "application/json"
    assert result["Accept"] == "text/html"
    assert result["User-Agent"] == "test-agent"


def _make_jwt(exp_ts: int) -> str:
    header = base64.urlsafe_b64encode(json.dumps({"alg": "HS256"}).encode()).rstrip(b"=")
    payload = base64.urlsafe_b64encode(json.dumps({"exp": exp_ts}).encode()).rstrip(b"=")
    return f"{header.decode()}.{payload.decode()}.signature"


def _make_jwt_with_claims(payload: dict) -> str:
    header = base64.urlsafe_b64encode(json.dumps({"alg": "HS256"}).encode()).rstrip(b"=")
    payload_b64 = base64.urlsafe_b64encode(json.dumps(payload).encode()).rstrip(b"=")
    return f"{header.decode()}.{payload_b64.decode()}.signature"


class DummyCookies:
    """Lightweight cookie stand-in to avoid requests' real cookie jar."""

    def __init__(self, mapping=None, iterable=None):
        self._mapping = mapping or {}
        self._iterable = iterable or []

    def get(self, key, default=None):
        return self._mapping.get(key, default)

    def clear(self):
        self._mapping.clear()

    def update(self, other):
        self._mapping.update(getattr(other, "_mapping", {}))

    def __iter__(self):
        return iter(self._iterable)

    def get_dict(self):
        return self._mapping


class FakeInput(Tag):
    """Minimal BeautifulSoup input element stub that passes isinstance(Tag) check."""

    def __init__(self, mapping):
        # Initialize Tag with minimal required args (name, can_be_empty_element)
        super().__init__(name="input")
        self.mapping = mapping

    def get(self, key, default=None):
        return self.mapping.get(key, default)


class TestAngelStudioSession:
    @pytest.fixture
    def logger(self):
        return MagicMock()

    @pytest.fixture
    def session_mock(self):
        sess = MagicMock()
        sess.cookies = DummyCookies()
        return sess

    def test_init_with_custom_logger(self, logger):
        inst = AngelStudioSession(logger=logger)
        assert inst.log is logger
        logger.info.assert_any_call("Custom logger initialized")

    def test_init_without_logger_uses_default(self):
        inst = AngelStudioSession()
        assert inst.log is not None

    def test_authenticate_returns_existing_valid_session(self, logger, session_mock):
        """Return early when an in-memory session is already valid."""
        inst = AngelStudioSession(logger=logger)
        inst.session = session_mock
        with (
            patch.object(inst, "_validate_session", return_value=True) as mock_val,
            patch("resources.lib.angel_authentication.requests.Session") as mock_session_ctor,
        ):
            result = inst.authenticate()
            assert result is True
            mock_val.assert_called_once()
            mock_session_ctor.assert_not_called()

    def test_authenticate_force_reauthentication_clears_cache(self, logger):
        """Force path clears cache and rebuilds session from cookies."""
        inst = AngelStudioSession(username="u", password="p", session_file="/tmp/sess", logger=logger)
        inst.session = MagicMock()
        inst.session_valid = True
        with (
            patch.object(inst, "_AngelStudioSession__clear_session_cache") as mock_clear,
            patch("resources.lib.angel_authentication.requests.Session") as session_ctor,
            patch.object(inst, "_AngelStudioSession__load_session_cookies", return_value=True) as mock_load,
            patch.object(inst, "_validate_session", return_value=True) as mock_validate,
        ):
            sess = MagicMock()
            sess.cookies = DummyCookies()
            sess.headers = {}
            session_ctor.return_value = sess
            # Force path: clears cache, validates (returns True via mock), returns early
            assert inst.authenticate(force_reauthentication=True) is True
            mock_clear.assert_called_once()
            # Force path does NOT load cookies; it clears them and validates fresh session
            mock_load.assert_not_called()
            # Validate is called once after clearing cache
            mock_validate.assert_called_once()

    def test_authenticate_handles_session_close_errors(self, logger):
        """authenticate() swallows session.close() exceptions and continues."""
        inst = AngelStudioSession(username="u", password="p", session_file="/tmp/sess", logger=logger)

        # Create a mock session that raises on close()
        bad_session = MagicMock()
        bad_session.close.side_effect = RuntimeError("close boom")
        inst.session = bad_session
        inst.session_valid = True

        with (
            patch.object(inst, "_AngelStudioSession__clear_session_cache") as mock_clear,
            patch("resources.lib.angel_authentication.requests.Session") as session_ctor,
            patch.object(inst, "_validate_session", side_effect=[False, False]),
        ):
            # Fresh session also raises on close to cover line 71-72
            fresh_session = MagicMock()
            fresh_session.close.side_effect = RuntimeError("close boom 2")
            fresh_session.cookies = DummyCookies()
            fresh_session.headers = {}
            bad_login = MagicMock(status_code=500, reason="bad", headers={}, content=b"")
            fresh_session.get.return_value = bad_login
            session_ctor.return_value = fresh_session

            # Force reauth path: both close() calls raise but are caught
            with pytest.raises(Exception, match="Failed to fetch the login page"):
                inst.authenticate(force_reauthentication=True)

            # Verify both close attempts were made and exceptions swallowed
            bad_session.close.assert_called_once()
            fresh_session.close.assert_called_once()
            mock_clear.assert_called_once()
            # Fresh session was created despite close() errors
            assert session_ctor.called

    def test_authenticate_loaded_cookies_invalid_starts_new_flow(self, logger):
        """Invalid cached cookies should fall through to full login."""
        inst = AngelStudioSession(username="u", password="p", session_file="/tmp/sess", logger=logger)
        with (
            patch("resources.lib.angel_authentication.requests.Session") as session_ctor,
            patch.object(inst, "_AngelStudioSession__load_session_cookies", return_value=True) as mock_load,
            patch.object(inst, "_validate_session", return_value=False) as mock_validate,
        ):
            sess = MagicMock()
            sess.cookies = DummyCookies()
            sess.headers = {}
            bad_login = MagicMock(status_code=500, reason="bad", headers={}, content=b"")
            sess.get.return_value = bad_login
            session_ctor.return_value = sess
            with pytest.raises(Exception, match="Failed to fetch the login page"):
                inst.authenticate()
            mock_load.assert_called_once()
            # _validate_session called twice: once initially, once after loading cookies
            assert mock_validate.call_count == 2

    def test_authenticate_uses_loaded_valid_cookies(self, logger):
        """Validate returns True after loading cookies from file."""
        inst = AngelStudioSession(logger=logger, session_file="/tmp/sess")
        with (
            patch("resources.lib.angel_authentication.requests.Session") as session_ctor,
            patch.object(inst, "_AngelStudioSession__load_session_cookies", return_value=True) as mock_load,
            patch.object(inst, "_validate_session", side_effect=[False, True]) as mock_validate,
        ):
            sess = MagicMock()
            session_ctor.return_value = sess
            result = inst.authenticate()
            assert result is True
            mock_load.assert_called_once()
            # _validate_session called twice: once initially (False), once after loading cookies (True)
            assert mock_validate.call_count == 2
            sess.get.assert_not_called()

    def test_authenticate_succeeds_after_full_login_flow(self, logger):
        """Happy-path login through email, password, redirect, and JWT capture."""
        inst = AngelStudioSession(username="u", password="p", session_file="/tmp/sess", logger=logger)

        login_page = MagicMock(status_code=200, reason="OK", headers={})
        login_page.content = b"<html><input id='state' name='state' value='state1'></html>"

        email_page = MagicMock(
            status_code=200,
            content=b"<html><input id='state' name='state' value='state2'>"
            b"<input name='_csrf_token' value='csrf'></html>",
        )

        password_response = MagicMock(
            status_code=302,
            headers={"Location": "https://auth.angel.com/redirect"},
            content=b"",
        )  # noqa: E501
        redirect_response = MagicMock(status_code=200, reason="OK", headers={})

        cookie_obj = SimpleNamespace(name="angel_jwt", value="tok123")
        cookies = DummyCookies(mapping={"angelSession": "state_cookie"}, iterable=[cookie_obj])

        sess = MagicMock()
        sess.cookies = cookies
        sess.headers = {}
        sess.get.side_effect = [login_page, email_page, redirect_response]
        sess.post.return_value = password_response

        with (
            patch("resources.lib.angel_authentication.requests.Session", return_value=sess),
            patch.object(inst, "_AngelStudioSession__save_session_cookies") as mock_save,
            patch("resources.lib.angel_authentication.BeautifulSoup") as mock_bs,
        ):

            soup_login = MagicMock()
            soup_login.find_all.return_value = []
            soup_email = MagicMock()
            soup_email.find_all.return_value = [
                SimpleNamespace(get=lambda k: "state2" if k in ("id", "name") else None),
                SimpleNamespace(get=lambda k: "csrf" if k == "_csrf_token" else None),
            ]
            soup_password = MagicMock()
            soup_password.find.return_value = None
            mock_bs.side_effect = [soup_login, soup_email, soup_password]

            result = inst.authenticate()

            assert result is True
            sess.get.assert_called()
            sess.post.assert_called_once()
            mock_save.assert_called_once()
            assert sess.headers.get("Authorization") == f"Bearer {cookie_obj.value}"

    def test_authenticate_no_credentials_parses_state_and_clears_authorization(self, logger):
        """Missing credentials still walks flow and clears stale Authorization when no JWT."""
        inst = AngelStudioSession(session_file="/tmp/sess", logger=logger)

        login_page = MagicMock(status_code=200, reason="OK", headers={}, content=b"<html></html>")
        email_page = MagicMock(status_code=200, reason="OK", headers={}, content=b"<html></html>")
        password_response = MagicMock(status_code=200, headers={}, content=b"<html></html>")

        cookies = DummyCookies(mapping={"angelSession": "state_cookie"}, iterable=[])
        sess = MagicMock()
        sess.cookies = cookies
        sess.headers = {"Authorization": "Bearer old"}
        sess.get.side_effect = [login_page, email_page]
        sess.post.return_value = password_response

        with (
            patch("resources.lib.angel_authentication.requests.Session", return_value=sess),
            patch.object(inst, "_AngelStudioSession__save_session_cookies") as mock_save,
            patch("resources.lib.angel_authentication.BeautifulSoup") as mock_bs,
        ):
            login_inputs = [FakeInput({"id": "state", "name": "state", "value": "state_from_input"})]
            email_inputs = [
                FakeInput({"id": "state", "name": "state", "value": "state_two"}),
                FakeInput({"name": "_csrf_token", "value": "csrf_token"}),
            ]
            soup_login = MagicMock()
            soup_login.find_all.return_value = login_inputs
            soup_email = MagicMock()
            soup_email.find_all.return_value = email_inputs
            soup_password = MagicMock()
            soup_password.find.return_value = None
            mock_bs.side_effect = [soup_login, soup_email, soup_password]

            assert inst.authenticate() is True
            assert "Authorization" not in sess.headers
            mock_save.assert_called_once()

    def test_authenticate_login_page_failure(self, logger):
        """Abort when the initial login page fetch fails."""
        inst = AngelStudioSession(username="u", password="p", logger=logger)
        bad_resp = MagicMock(status_code=500, reason="err", headers={}, content=b"")
        sess = MagicMock()
        sess.get.return_value = bad_resp
        sess.cookies = DummyCookies()
        with patch("resources.lib.angel_authentication.requests.Session", return_value=sess):
            with pytest.raises(Exception, match="Failed to fetch the login page"):
                inst.authenticate()

    def test_authenticate_post_email_failure(self, logger):
        """Abort when the post-email page cannot be fetched."""
        inst = AngelStudioSession(username="u", password="p", logger=logger)
        login_page = MagicMock(status_code=200, reason="OK", headers={}, content=b"<html></html>")
        bad_email = MagicMock(status_code=500, reason="err", headers={}, content=b"")
        sess = MagicMock()
        sess.cookies = DummyCookies()
        sess.get.side_effect = [login_page, bad_email]
        with (
            patch("resources.lib.angel_authentication.requests.Session", return_value=sess),
            patch("resources.lib.angel_authentication.BeautifulSoup") as mock_bs,
        ):
            mock_bs.return_value.find_all.return_value = []
            with pytest.raises(Exception, match="Failed to fetch the post-email page"):
                inst.authenticate()

    def test_authenticate_redirect_failure(self, logger):
        """Abort when redirect after password submission returns non-200."""
        inst = AngelStudioSession(username="u", password="p", logger=logger)
        login_page = MagicMock(status_code=200, reason="OK", headers={}, content=b"<html></html>")
        email_page = MagicMock(status_code=200, reason="OK", headers={}, content=b"<html></html>")
        password_response = MagicMock(status_code=302, headers={"Location": "redir"}, content=b"")
        redirect_response = MagicMock(status_code=500, reason="bad", headers={})
        sess = MagicMock()
        sess.cookies = DummyCookies()
        sess.get.side_effect = [login_page, email_page, redirect_response]
        sess.post.return_value = password_response
        with (
            patch("resources.lib.angel_authentication.requests.Session", return_value=sess),
            patch("resources.lib.angel_authentication.BeautifulSoup") as mock_bs,
        ):
            mock_bs.return_value.find_all.return_value = []
            with pytest.raises(Exception, match="Login failed after redirect"):
                inst.authenticate()

    def test_authenticate_invalid_credentials(self, logger):
        """Surface error banner from password step as auth failure."""
        inst = AngelStudioSession(username="u", password="p", logger=logger)
        login_page = MagicMock(status_code=200, reason="OK", headers={}, content=b"<html></html>")
        email_page = MagicMock(status_code=200, reason="OK", headers={}, content=b"<html></html>")
        password_response = MagicMock(status_code=200, headers={}, content=b"<div class='error-message'></div>")
        sess = MagicMock()
        sess.cookies = DummyCookies()
        sess.get.side_effect = [login_page, email_page]
        sess.post.return_value = password_response
        with (
            patch("resources.lib.angel_authentication.requests.Session", return_value=sess),
            patch("resources.lib.angel_authentication.BeautifulSoup") as mock_bs,
        ):
            soup_login = MagicMock()
            soup_login.find_all.return_value = []
            soup_email = MagicMock()
            soup_email.find_all.return_value = []
            soup_password = MagicMock()
            soup_password.find.return_value = True
            mock_bs.side_effect = [soup_login, soup_email, soup_password]
            with pytest.raises(Exception, match="Login failed: Invalid username or password"):
                inst.authenticate()

    def test_authenticate_password_post_failure(self, logger):
        """Raise when password submission returns non-success and no redirect."""
        inst = AngelStudioSession(username="u", password="p", session_file="/tmp/sess", logger=logger)
        login_page = MagicMock(status_code=200, reason="OK", headers={}, content=b"<html></html>")
        email_page = MagicMock(status_code=200, reason="OK", headers={}, content=b"<html></html>")
        password_response = MagicMock(status_code=400, reason="bad", headers={}, content=b"")
        sess = MagicMock()
        sess.cookies = DummyCookies()
        sess.get.side_effect = [login_page, email_page]
        sess.post.return_value = password_response
        with (
            patch("resources.lib.angel_authentication.requests.Session", return_value=sess),
            patch("resources.lib.angel_authentication.BeautifulSoup") as mock_bs,
        ):
            soup_login = MagicMock()
            soup_login.find_all.return_value = []
            soup_email = MagicMock()
            soup_email.find_all.return_value = []
            soup_password = MagicMock()
            soup_password.find.return_value = False
            mock_bs.side_effect = [soup_login, soup_email, soup_password]
            with pytest.raises(Exception, match="Login failed"):
                inst.authenticate()

    def test_authenticate_redirect_missing_location_header(self, logger):
        """Redirect without Location header raises exception."""
        inst = AngelStudioSession(username="u", password="p", session_file="/tmp/sess", logger=logger)

        login_page = MagicMock(status_code=200, content=b"<html></html>")
        email_page = MagicMock(status_code=200, content=b"<html></html>")
        # Password response is redirect but missing Location header
        password_response = MagicMock(status_code=302, headers={}, content=b"")

        sess = MagicMock()
        sess.cookies = DummyCookies(mapping={"angelSession": "state_cookie"})
        sess.headers = {}
        sess.get.side_effect = [login_page, email_page]
        sess.post.return_value = password_response

        with (
            patch("resources.lib.angel_authentication.requests.Session", return_value=sess),
            patch("resources.lib.angel_authentication.BeautifulSoup") as mock_bs,
        ):
            soup_login = MagicMock()
            soup_login.find_all.return_value = []
            soup_email = MagicMock()
            soup_email.find_all.return_value = [
                FakeInput({"id": "state", "name": "state", "value": "state2"}),
                FakeInput({"name": "_csrf_token", "value": "csrf"}),
            ]
            mock_bs.side_effect = [soup_login, soup_email]

            with pytest.raises(Exception, match="Login redirect missing Location header"):
                inst.authenticate()

    def test_authenticate_handles_non_tag_elements_in_html_parsing(self, logger):
        """HTML parsing skips non-Tag elements returned by BeautifulSoup."""
        inst = AngelStudioSession(username="u", password="p", session_file="/tmp/sess", logger=logger)

        login_page = MagicMock(status_code=200, content=b"<html></html>")
        email_page = MagicMock(status_code=200, content=b"<html></html>")
        password_response = MagicMock(status_code=200, content=b"<html></html>")

        sess = MagicMock()
        sess.cookies = DummyCookies(mapping={"angelSession": "state_cookie"})
        sess.headers = {}
        sess.get.side_effect = [login_page, email_page]
        sess.post.return_value = password_response

        with (
            patch("resources.lib.angel_authentication.requests.Session", return_value=sess),
            patch.object(inst, "_AngelStudioSession__save_session_cookies"),
            patch("resources.lib.angel_authentication.BeautifulSoup") as mock_bs,
        ):
            # Mix Tag elements with non-Tag elements (e.g., strings, comments)
            non_tag_element = "some text node"  # Not a Tag
            login_inputs = [
                non_tag_element,  # Should be skipped (line 117: continue)
                FakeInput({"id": "state", "name": "state", "value": "state1"}),
            ]
            email_inputs = [
                non_tag_element,  # Should be skipped
                FakeInput({"id": "state", "name": "state", "value": "state2"}),
                FakeInput({"name": "_csrf_token", "value": "csrf"}),
            ]

            soup_login = MagicMock()
            soup_login.find_all.return_value = login_inputs
            soup_email = MagicMock()
            soup_email.find_all.return_value = email_inputs
            soup_password = MagicMock()
            soup_password.find.return_value = None
            mock_bs.side_effect = [soup_login, soup_email, soup_password]

            result = inst.authenticate()
            assert result is True

    def test_validate_session_jwt_expiration_parse_failure(self, logger):
        """_validate_session returns False when JWT expiration can't be parsed."""
        inst = AngelStudioSession(logger=logger)

        # Mock session with JWT cookie
        sess = MagicMock()
        sess.cookies.get.return_value = "valid.jwt.token"
        inst.session = sess

        # Mock __get_jwt_expiration_timestamp to return None (parse failure)
        with patch.object(inst, "_AngelStudioSession__get_jwt_expiration_timestamp", return_value=None):
            result = inst._validate_session()
            assert result is False

    def test_logout_handles_session_close_error(self, logger):
        """logout swallows session.close() exception and continues."""
        inst = AngelStudioSession(session_file="/tmp/sess", logger=logger)

        sess = MagicMock()
        sess.cookies = DummyCookies(mapping={"a": "b"})
        sess.headers = {"Authorization": "Bearer tok"}
        sess.close.side_effect = RuntimeError("close boom")
        inst.session = sess
        inst.session_valid = True

        with (
            patch("os.path.exists", return_value=True),
            patch("os.remove") as mock_remove,
        ):
            result = inst.logout()

        assert result is True
        sess.close.assert_called_once()
        mock_remove.assert_called_once()

    def test_get_session_calls_authenticate_when_missing(self, logger):
        """get_session triggers authenticate when no session exists."""
        inst = AngelStudioSession(logger=logger)
        with patch.object(inst, "authenticate", return_value=True) as mock_auth:
            session = inst.get_session()
            mock_auth.assert_called_once()
            assert session == inst.session

    def test_get_session_raises_when_authenticate_fails(self, logger):
        """get_session bubbles up authentication failure."""
        inst = AngelStudioSession(logger=logger)
        with patch.object(inst, "authenticate", return_value=False):
            with pytest.raises(Exception, match="Failed to authenticate"):
                inst.get_session()

    def test_validate_session_valid(self, logger):
        """JWT exp in the future marks session valid."""
        future = int((datetime.now(timezone.utc) + timedelta(hours=1)).timestamp())
        token = _make_jwt(future)
        inst = AngelStudioSession(logger=logger)
        inst.session = MagicMock()
        inst.session.cookies = DummyCookies(mapping={"angel_jwt": token})
        assert inst._validate_session() is True

    def test_get_session_details_no_session(self, logger):
        """Without a session or jwt, return defaults."""
        inst = AngelStudioSession(username="user@example.com", logger=logger)
        inst.session = None
        details = inst.get_session_details()
        assert details["login_email"] == "user@example.com"
        assert details["jwt_present"] is False
        assert details["cookie_names"] == []

    def test_get_session_details_malformed_jwt(self, logger):
        """Malformed jwt is handled gracefully and still marks presence."""
        inst = AngelStudioSession(username="user@example.com", logger=logger)
        sess = MagicMock()
        sess.cookies = DummyCookies(mapping={"angel_jwt": "badtoken"})
        inst.session = sess
        details = inst.get_session_details()
        assert details["jwt_present"] is True
        assert details["login_email"] == "user@example.com"

    def test_get_session_details_with_claims_and_auth_header(self, logger):
        """Claims populate email/account and compute expirations with auth header set."""
        now = datetime.now(timezone.utc)
        future = int((now + timedelta(hours=1)).timestamp())
        iat = int(now.timestamp())
        token = _make_jwt_with_claims(
            {
                "exp": future,
                "iat": iat,
                "email": "jwt@example.com",
                "sub": "account-123",
            }
        )
        cookie_obj = SimpleNamespace(name="angel_jwt", value=token)
        sess = MagicMock()
        sess.cookies = DummyCookies(mapping={"angel_jwt": token}, iterable=[cookie_obj])
        sess.headers = {"Authorization": "Bearer x"}

        inst = AngelStudioSession(username="fallback@example.com", logger=logger)
        inst.session = sess

        details = inst.get_session_details()

        assert details["jwt_present"] is True
        assert details["login_email"] == "jwt@example.com"
        assert details["account_id"] == "account-123"
        assert details["authenticated"] is True
        assert details["expires_in_seconds"] is not None
        assert "angel_jwt" in details["cookie_names"]
        assert details["issued_at_local"]
        assert details["expires_at_local"]

    def test_logout_handles_cookie_and_header_errors(self, logger):
        """logout swallows cookie/header clearing errors and still returns."""
        inst = AngelStudioSession(logger=logger)

        class BadCookies:
            def clear(self):
                raise RuntimeError("cookie boom")

        class BadHeaders(dict):
            def pop(self, *args, **kwargs):  # type: ignore[override]
                raise RuntimeError("header boom")

        sess = MagicMock()
        sess.cookies = BadCookies()
        sess.headers = BadHeaders()
        inst.session = sess
        inst.session_file = None

        result = inst.logout()
        assert result is True
        assert inst.session is not None
        assert inst.session is not sess
        assert isinstance(inst.session, requests.Session)

    def test_get_session_details_outer_exception(self, logger):
        """Outer try/except safely swallows unexpected errors."""
        inst = AngelStudioSession(logger=logger)

        class BadSession:
            @property
            def cookies(self):
                raise RuntimeError("boom")

        inst.session = BadSession()

        details = inst.get_session_details()
        assert details["jwt_present"] is False

    def test_validate_session_expired(self, logger):
        """Expired JWT marks session invalid."""
        past = int((datetime.now(timezone.utc) - timedelta(hours=1)).timestamp())
        token = _make_jwt(past)
        inst = AngelStudioSession(logger=logger)
        inst.session = MagicMock()
        inst.session.cookies = DummyCookies(mapping={"angel_jwt": token})
        assert inst._validate_session() is False

    def test_validate_session_missing_token(self, logger):
        """Missing JWT results in invalid session."""
        inst = AngelStudioSession(logger=logger)
        inst.session = MagicMock()
        inst.session.cookies = DummyCookies()
        with patch.object(inst, "_AngelStudioSession__get_jwt_expiration_timestamp", return_value=None):
            assert inst._validate_session() is False

    def test_get_jwt_expiration_timestamp(self):
        """Extract exp claim from a well-formed JWT and raise on bad token."""
        exp_ts = int(datetime.now(timezone.utc).timestamp())
        token = _make_jwt(exp_ts)
        inst = AngelStudioSession()
        assert inst._AngelStudioSession__get_jwt_expiration_timestamp(token) == exp_ts
        with pytest.raises(ValueError):
            inst._AngelStudioSession__get_jwt_expiration_timestamp("bad.token")

    def test_get_jwt_expiration_timestamp_without_exp(self):
        """Return None when JWT lacks an exp claim."""
        header = base64.urlsafe_b64encode(json.dumps({"alg": "HS256"}).encode()).rstrip(b"=").decode()
        payload = base64.urlsafe_b64encode(json.dumps({}).encode()).rstrip(b"=").decode()
        token = f"{header}.{payload}.sig"
        inst = AngelStudioSession()
        assert inst._AngelStudioSession__get_jwt_expiration_timestamp(token) is None

    def test_load_session_cookies_success(self, logger):
        """Load cookies file and set Authorization header from JWT."""
        cookies_obj = DummyCookies(mapping={}, iterable=[SimpleNamespace(name="angel_jwt", value="tok")])
        sess = MagicMock()
        sess.cookies = DummyCookies(mapping={}, iterable=[SimpleNamespace(name="angel_jwt", value="tok")])
        sess.headers = {}
        inst = AngelStudioSession(session_file="/tmp/sess", logger=logger)
        inst.session = sess
        with (
            patch("builtins.open", mock_open(read_data=pickle.dumps(cookies_obj))),
            patch("pickle.load", return_value=cookies_obj),
        ):
            assert inst._AngelStudioSession__load_session_cookies() is True
            assert sess.headers.get("Authorization") == "Bearer tok"

    def test_load_session_cookies_file_not_found(self, logger):
        """Gracefully handle missing cookie file."""
        inst = AngelStudioSession(session_file="/tmp/missing", logger=logger)
        inst.session = MagicMock()
        inst.session.cookies = DummyCookies()
        with patch("builtins.open", side_effect=FileNotFoundError):
            assert inst._AngelStudioSession__load_session_cookies() is False

    def test_load_session_cookies_without_jwt_token(self, logger):
        """Return True when file loads but no JWT is present."""
        cookies_obj = DummyCookies(mapping={}, iterable=[])
        sess = MagicMock()
        sess.cookies = DummyCookies(mapping={}, iterable=[])
        sess.headers = {}
        inst = AngelStudioSession(session_file="/tmp/sess", logger=logger)
        inst.session = sess
        with (
            patch("builtins.open", mock_open(read_data=pickle.dumps(cookies_obj))),
            patch("pickle.load", return_value=cookies_obj),
        ):
            assert inst._AngelStudioSession__load_session_cookies() is True
            assert sess.headers.get("Authorization") is None

    def test_load_session_cookies_handles_iteration_error(self, logger):
        """Return False if cookie iteration blows up while loading."""

        class IterErrorCookies(DummyCookies):
            def __iter__(self):
                raise RuntimeError("iter boom")

        cookies_obj = DummyCookies(mapping={}, iterable=[])
        sess = MagicMock()
        sess.cookies = IterErrorCookies(mapping={}, iterable=[])
        inst = AngelStudioSession(session_file="/tmp/sess", logger=logger)
        inst.session = sess
        with (
            patch("builtins.open", mock_open(read_data=pickle.dumps(cookies_obj))),
            patch("pickle.load", return_value=cookies_obj),
        ):
            assert inst._AngelStudioSession__load_session_cookies() is False

    def test_save_session_cookies(self, logger):
        """Persist cookies to disk at configured path."""
        inst = AngelStudioSession(session_file="/tmp/sess", logger=logger)
        inst.session = MagicMock()
        inst.session.cookies = DummyCookies()
        with (
            patch("builtins.open", mock_open()) as m_open,
            patch("pickle.dump") as mock_dump,
        ):
            inst._AngelStudioSession__save_session_cookies()
            m_open.assert_called_once_with("/tmp/sess", "wb")
            mock_dump.assert_called_once_with(inst.session.cookies, m_open())

    def test_clear_session_cache_success(self, logger):
        """Remove cached cookie file when present."""
        inst = AngelStudioSession(session_file="/tmp/sess", logger=logger)
        with (
            patch("os.path.exists", return_value=True),
            patch("os.remove") as mock_remove,
        ):
            assert inst._AngelStudioSession__clear_session_cache() is True
            mock_remove.assert_called_once_with("/tmp/sess")

    def test_clear_session_cache_failure(self, logger):
        """Return False and log when cache removal fails."""
        inst = AngelStudioSession(session_file="/tmp/sess", logger=logger)
        with (
            patch("os.path.exists", return_value=True),
            patch("os.remove", side_effect=Exception("boom")),
        ):
            assert inst._AngelStudioSession__clear_session_cache() is False

    def test_logout_clears_session_and_cache(self, logger, tmp_path):
        """logout clears cookies, auth header, session file, and marks session invalid."""
        session_file = tmp_path / "sess"
        session_file.write_text("data")
        inst = AngelStudioSession(session_file=str(session_file), logger=logger)
        sess = MagicMock()
        sess.cookies = DummyCookies(mapping={"a": "b"})
        sess.headers = {"Authorization": "Bearer tok"}
        inst.session = sess
        inst.session_valid = True

        with (
            patch("os.path.exists", return_value=True),
            patch("os.remove") as mock_remove,
        ):
            assert inst.logout() is True

        mock_remove.assert_called_once_with(str(session_file))
        assert inst.session is not None
        assert inst.session is not sess
        assert isinstance(inst.session, requests.Session)
        assert inst.session_valid is False
        assert sess.headers.get("Authorization") is None
        assert sess.cookies.get_dict() == {}

    def test_logout_returns_false_when_cache_delete_fails(self, logger):
        """logout still clears in-memory state even if file removal fails."""
        inst = AngelStudioSession(session_file="/tmp/sess", logger=logger)
        sess = MagicMock()
        sess.cookies = DummyCookies(mapping={"a": "b"})
        sess.headers = {"Authorization": "Bearer tok"}
        inst.session = sess
        inst.session_valid = True

        with (
            patch("os.path.exists", return_value=True),
            patch("os.remove", side_effect=Exception("boom")),
        ):
            assert inst.logout() is False

        assert inst.session is not None
        assert inst.session is not sess
        assert isinstance(inst.session, requests.Session)
        assert inst.session_valid is False
        assert sess.headers.get("Authorization") is None
        assert sess.cookies.get_dict() == {}

    def test_authenticate_login_page_timeout(self, logger):
        """Raise timeout exception when login page fetch times out."""
        inst = AngelStudioSession(username="u", password="p", logger=logger, timeout=10)
        sess = MagicMock()
        sess.cookies = DummyCookies()
        sess.get.side_effect = requests.Timeout("Connection timed out")

        with patch("resources.lib.angel_authentication.requests.Session", return_value=sess):
            with pytest.raises(
                Exception, match="Request timeout: Unable to connect to Angel Studios \\(timeout: 10s\\)"
            ):
                inst.authenticate()

    def test_authenticate_post_email_timeout(self, logger):
        """Raise timeout exception when post-email page fetch times out."""
        inst = AngelStudioSession(username="u", password="p", logger=logger, timeout=15)
        login_page = MagicMock(status_code=200, reason="OK", headers={}, content=b"<html></html>")
        sess = MagicMock()
        sess.cookies = DummyCookies(mapping={"angelSession": "state_cookie"})
        sess.get.side_effect = [login_page, requests.Timeout("Connection timed out")]

        with patch("resources.lib.angel_authentication.requests.Session", return_value=sess):
            with pytest.raises(
                Exception, match="Request timeout: Unable to connect to Angel Studios \\(timeout: 15s\\)"
            ):
                inst.authenticate()

    def test_authenticate_password_post_timeout(self, logger):
        """Raise timeout exception when password post times out."""
        inst = AngelStudioSession(username="u", password="p", logger=logger, timeout=20)
        login_page = MagicMock(status_code=200, reason="OK", headers={}, content=b"<html></html>")
        email_page = MagicMock(status_code=200, reason="OK", headers={}, content=b"<html></html>")
        sess = MagicMock()
        sess.cookies = DummyCookies(mapping={"angelSession": "state_cookie"})
        sess.get.side_effect = [login_page, email_page]
        sess.post.side_effect = requests.Timeout("Connection timed out")

        with patch("resources.lib.angel_authentication.requests.Session", return_value=sess):
            with pytest.raises(
                Exception, match="Request timeout: Unable to connect to Angel Studios \\(timeout: 20s\\)"
            ):
                inst.authenticate()

    def test_authenticate_redirect_timeout(self, logger):
        """Raise timeout exception when redirect follow times out."""
        inst = AngelStudioSession(username="u", password="p", logger=logger, timeout=25)
        login_page = MagicMock(status_code=200, reason="OK", headers={}, content=b"<html></html>")
        email_page = MagicMock(status_code=200, reason="OK", headers={}, content=b"<html></html>")
        password_response = MagicMock(
            status_code=302, headers={"Location": "https://example.com/redirect"}, content=b""
        )

        sess = MagicMock()
        sess.cookies = DummyCookies(mapping={"angelSession": "state_cookie"})
        sess.get.side_effect = [login_page, email_page, requests.Timeout("Connection timed out")]
        sess.post.return_value = password_response

        with patch("resources.lib.angel_authentication.requests.Session", return_value=sess):
            with pytest.raises(
                Exception, match="Request timeout: Unable to connect to Angel Studios \\(timeout: 25s\\)"
            ):
                inst.authenticate()
