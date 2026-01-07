"""Unit tests for AngelStudioSession covering auth flows, cookies, and JWT parsing."""

import base64
import json
import os
import pickle
from datetime import datetime, timezone, timedelta
from types import SimpleNamespace
from unittest.mock import MagicMock, mock_open, patch

import pytest

from angel_authentication import AngelStudioSession


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


class FakeInput:
	"""Minimal BeautifulSoup input element stub."""
	def __init__(self, mapping):
		self.mapping = mapping

	def get(self, key):
		return self.mapping.get(key)


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
			patch("angel_authentication.requests.Session") as mock_session_ctor,
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
			patch("angel_authentication.requests.Session") as session_ctor,
			patch.object(inst, "_AngelStudioSession__load_session_cookies", return_value=True) as mock_load,
			patch.object(inst, "_validate_session", return_value=True) as mock_validate,
		):
			sess = MagicMock()
			sess.cookies = DummyCookies()
			sess.headers = {}
			session_ctor.return_value = sess
			assert inst.authenticate(force_reauthentication=True) is True
			mock_clear.assert_called_once()
			mock_load.assert_called_once()
			mock_validate.assert_called_once()

	def test_authenticate_loaded_cookies_invalid_starts_new_flow(self, logger):
		"""Invalid cached cookies should fall through to full login."""
		inst = AngelStudioSession(username="u", password="p", session_file="/tmp/sess", logger=logger)
		with (
			patch("angel_authentication.requests.Session") as session_ctor,
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
			mock_validate.assert_called_once()

	def test_authenticate_uses_loaded_valid_cookies(self, logger):
		inst = AngelStudioSession(logger=logger, session_file="/tmp/sess")
		with (
			patch("angel_authentication.requests.Session") as session_ctor,
			patch.object(inst, "_AngelStudioSession__load_session_cookies", return_value=True) as mock_load,
			patch.object(inst, "_validate_session", return_value=True) as mock_validate,
		):
			sess = MagicMock()
			session_ctor.return_value = sess
			result = inst.authenticate()
			assert result is True
			mock_load.assert_called_once()
			mock_validate.assert_called_once()
			sess.get.assert_not_called()

	def test_authenticate_full_login_flow_success(self, logger):
		"""Happy-path login through email, password, redirect, and JWT capture."""
		inst = AngelStudioSession(username="u", password="p", session_file="/tmp/sess", logger=logger)

		login_page = MagicMock(status_code=200, reason="OK", headers={})
		login_page.content = b"<html><input id='state' name='state' value='state1'></html>"

		email_page = MagicMock(status_code=200, content=b"<html><input id='state' name='state' value='state2'><input name='_csrf_token' value='csrf'></html>")

		password_response = MagicMock(status_code=302, headers={"Location": "https://auth.angel.com/redirect"}, content=b"")
		redirect_response = MagicMock(status_code=200, reason="OK", headers={})

		cookie_obj = SimpleNamespace(name='angel_jwt', value='tok123')
		cookies = DummyCookies(mapping={'angelSession': 'state_cookie'}, iterable=[cookie_obj])

		sess = MagicMock()
		sess.cookies = cookies
		sess.headers = {}
		sess.get.side_effect = [login_page, email_page, redirect_response]
		sess.post.return_value = password_response

		with (
			patch("angel_authentication.requests.Session", return_value=sess),
			patch.object(inst, "_AngelStudioSession__save_session_cookies") as mock_save,
			patch("angel_authentication.BeautifulSoup") as mock_bs,
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
			assert sess.headers.get('Authorization') == f"Bearer {cookie_obj.value}"

	def test_authenticate_no_credentials_parses_state_and_clears_authorization(self, logger):
		"""Missing credentials still walks flow and clears stale Authorization when no JWT."""
		inst = AngelStudioSession(session_file="/tmp/sess", logger=logger)

		login_page = MagicMock(status_code=200, reason="OK", headers={}, content=b"<html></html>")
		email_page = MagicMock(status_code=200, reason="OK", headers={}, content=b"<html></html>")
		password_response = MagicMock(status_code=200, headers={}, content=b"<html></html>")

		cookies = DummyCookies(mapping={'angelSession': 'state_cookie'}, iterable=[])
		sess = MagicMock()
		sess.cookies = cookies
		sess.headers = {'Authorization': 'Bearer old'}
		sess.get.side_effect = [login_page, email_page]
		sess.post.return_value = password_response

		with (
			patch("angel_authentication.requests.Session", return_value=sess),
			patch.object(inst, "_AngelStudioSession__save_session_cookies") as mock_save,
			patch("angel_authentication.BeautifulSoup") as mock_bs,
		):
			login_inputs = [FakeInput({'id': 'state', 'name': 'state', 'value': 'state_from_input'})]
			email_inputs = [
				FakeInput({'id': 'state', 'name': 'state', 'value': 'state_two'}),
				FakeInput({'name': '_csrf_token', 'value': 'csrf_token'}),
			]
			soup_login = MagicMock()
			soup_login.find_all.return_value = login_inputs
			soup_email = MagicMock()
			soup_email.find_all.return_value = email_inputs
			soup_password = MagicMock()
			soup_password.find.return_value = None
			mock_bs.side_effect = [soup_login, soup_email, soup_password]

			assert inst.authenticate() is True
			assert 'Authorization' not in sess.headers
			mock_save.assert_called_once()

	def test_authenticate_login_page_failure(self, logger):
		"""Abort when the initial login page fetch fails."""
		inst = AngelStudioSession(username="u", password="p", logger=logger)
		bad_resp = MagicMock(status_code=500, reason="err", headers={}, content=b"")
		sess = MagicMock()
		sess.get.return_value = bad_resp
		sess.cookies = DummyCookies()
		with patch("angel_authentication.requests.Session", return_value=sess):
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
			patch("angel_authentication.requests.Session", return_value=sess),
			patch("angel_authentication.BeautifulSoup") as mock_bs,
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
			patch("angel_authentication.requests.Session", return_value=sess),
			patch("angel_authentication.BeautifulSoup") as mock_bs,
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
			patch("angel_authentication.requests.Session", return_value=sess),
			patch("angel_authentication.BeautifulSoup") as mock_bs,
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
			patch("angel_authentication.requests.Session", return_value=sess),
			patch("angel_authentication.BeautifulSoup") as mock_bs,
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
		inst.session.cookies = DummyCookies(mapping={'angel_jwt': token})
		assert inst._validate_session() is True

	def test_get_session_details_no_session(self, logger):
		"""Without a session or jwt, return defaults."""
		inst = AngelStudioSession(username="user@example.com", logger=logger)
		inst.session = None
		details = inst.get_session_details()
		assert details['login_email'] == "user@example.com"
		assert details['jwt_present'] is False
		assert details['cookie_names'] == []

	def test_get_session_details_malformed_jwt(self, logger):
		"""Malformed jwt is handled gracefully and still marks presence."""
		inst = AngelStudioSession(username="user@example.com", logger=logger)
		sess = MagicMock()
		sess.cookies = DummyCookies(mapping={'angel_jwt': 'badtoken'})
		inst.session = sess
		details = inst.get_session_details()
		assert details['jwt_present'] is True
		assert details['login_email'] == "user@example.com"

	def test_get_session_details_with_claims_and_auth_header(self, logger):
		"""Claims populate email/account and compute expirations with auth header set."""
		now = datetime.now(timezone.utc)
		future = int((now + timedelta(hours=1)).timestamp())
		iat = int(now.timestamp())
		token = _make_jwt_with_claims({
			"exp": future,
			"iat": iat,
			"email": "jwt@example.com",
			"sub": "account-123",
		})
		cookie_obj = SimpleNamespace(name='angel_jwt', value=token)
		sess = MagicMock()
		sess.cookies = DummyCookies(mapping={'angel_jwt': token}, iterable=[cookie_obj])
		sess.headers = {'Authorization': 'Bearer x'}

		inst = AngelStudioSession(username="fallback@example.com", logger=logger)
		inst.session = sess

		details = inst.get_session_details()

		assert details['jwt_present'] is True
		assert details['login_email'] == "jwt@example.com"
		assert details['account_id'] == "account-123"
		assert details['authenticated'] is True
		assert details['expires_in_seconds'] is not None
		assert 'angel_jwt' in details['cookie_names']
		assert details['issued_at_local']
		assert details['expires_at_local']

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
		assert inst.session is None

	def test_get_session_details_outer_exception(self, logger):
		"""Outer try/except safely swallows unexpected errors."""
		inst = AngelStudioSession(logger=logger)

		class BadSession:
			@property
			def cookies(self):
				raise RuntimeError("boom")

		inst.session = BadSession()

		details = inst.get_session_details()
		assert details['jwt_present'] is False

	def test_validate_session_expired(self, logger):
		"""Expired JWT marks session invalid."""
		past = int((datetime.now(timezone.utc) - timedelta(hours=1)).timestamp())
		token = _make_jwt(past)
		inst = AngelStudioSession(logger=logger)
		inst.session = MagicMock()
		inst.session.cookies = DummyCookies(mapping={'angel_jwt': token})
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
		cookies_obj = DummyCookies(mapping={}, iterable=[SimpleNamespace(name='angel_jwt', value='tok')])
		sess = MagicMock()
		sess.cookies = DummyCookies(mapping={}, iterable=[SimpleNamespace(name='angel_jwt', value='tok')])
		sess.headers = {}
		inst = AngelStudioSession(session_file="/tmp/sess", logger=logger)
		inst.session = sess
		with (
			patch("builtins.open", mock_open(read_data=pickle.dumps(cookies_obj))),
			patch("pickle.load", return_value=cookies_obj),
		):
			assert inst._AngelStudioSession__load_session_cookies() is True
			assert sess.headers.get('Authorization') == 'Bearer tok'

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
			m_open.assert_called_once_with("/tmp/sess", 'wb')
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
		sess.cookies = DummyCookies(mapping={'a': 'b'})
		sess.headers = {'Authorization': 'Bearer tok'}
		inst.session = sess
		inst.session_valid = True

		with (
			patch("os.path.exists", return_value=True),
			patch("os.remove") as mock_remove,
		):
			assert inst.logout() is True

		mock_remove.assert_called_once_with(str(session_file))
		assert inst.session is None
		assert inst.session_valid is False
		assert sess.headers.get('Authorization') is None
		assert sess.cookies.get_dict() == {}

	def test_logout_returns_false_when_cache_delete_fails(self, logger):
		"""logout still clears in-memory state even if file removal fails."""
		inst = AngelStudioSession(session_file="/tmp/sess", logger=logger)
		sess = MagicMock()
		sess.cookies = DummyCookies(mapping={'a': 'b'})
		sess.headers = {'Authorization': 'Bearer tok'}
		inst.session = sess
		inst.session_valid = True

		with (
			patch("os.path.exists", return_value=True),
			patch("os.remove", side_effect=Exception("boom")),
		):
			assert inst.logout() is False

		assert inst.session is None
		assert inst.session_valid is False
		assert sess.headers.get('Authorization') is None
		assert sess.cookies.get_dict() == {}
