"""Unit tests for SessionStore implementations."""

import pytest

from auth0_ciam_client.session_store import InMemorySessionStore


class TestInMemorySessionStore:
    """Test InMemorySessionStore implementation"""

    def test_save_token(self):
        """Test saving a token"""
        store = InMemorySessionStore()

        store.save_token("test_token_123")

        assert store.get_token() == "test_token_123"

    def test_get_token_existing(self):
        """Test getting an existing token"""
        store = InMemorySessionStore()
        store._token = "existing_token_456"

        result = store.get_token()

        assert result == "existing_token_456"

    def test_get_token_none(self):
        """Test getting token when none exists"""
        store = InMemorySessionStore()

        result = store.get_token()

        assert result is None

    def test_clear_token(self):
        """Test clearing the stored token"""
        store = InMemorySessionStore()
        store._token = "some_token"

        store.clear_token()

        assert store.get_token() is None

    def test_save_credentials(self):
        """Test saving credentials"""
        store = InMemorySessionStore()

        store.save_credentials("testuser", "testpass")

        username, password = store.get_credentials()
        assert username == "testuser"
        assert password == "testpass"

    def test_get_credentials_existing(self):
        """Test getting existing credentials"""
        store = InMemorySessionStore()
        store._username = "existing_user"
        store._password = "existing_pass"

        username, password = store.get_credentials()

        assert username == "existing_user"
        assert password == "existing_pass"

    def test_get_credentials_none(self):
        """Test getting credentials when none exist"""
        store = InMemorySessionStore()

        username, password = store.get_credentials()

        assert username is None
        assert password is None

    def test_clear_credentials(self):
        """Test clearing stored credentials"""
        store = InMemorySessionStore()
        store._username = "user"
        store._password = "pass"

        store.clear_credentials()

        username, password = store.get_credentials()
        assert username is None
        assert password is None

    def test_get_expiry_buffer_hours_default(self):
        """Test getting expiry buffer with default value"""
        store = InMemorySessionStore()

        result = store.get_expiry_buffer_hours()

        assert result == 1