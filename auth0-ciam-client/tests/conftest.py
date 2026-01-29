"""
conftest.py for auth0-ciam-client unit tests.
Provides fixtures for testing the authentication package.
"""

import pytest
from unittest.mock import MagicMock

from auth0_ciam_client.config import Auth0Config
from auth0_ciam_client.session_store import InMemorySessionStore


@pytest.fixture
def mock_session_store():
    """Mock session store for testing."""
    return MagicMock(spec=InMemorySessionStore)


@pytest.fixture
def in_memory_session_store():
    """Real in-memory session store for testing."""
    return InMemorySessionStore()


@pytest.fixture
def auth0_config():
    """Default Auth0 configuration for testing."""
    return Auth0Config(
        base_url="https://www.angelstudios.com",
        jwt_cookie_names=["angelSession", "auth_token"],
        request_timeout=30,
        expiry_buffer_hours=1,
        user_agent="Test-Agent/1.0"
    )


@pytest.fixture
def mock_logger():
    """Mock logger for testing."""
    return MagicMock()