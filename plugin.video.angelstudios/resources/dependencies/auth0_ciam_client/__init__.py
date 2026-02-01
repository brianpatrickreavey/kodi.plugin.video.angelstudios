"""Auth0 CIAM Client - Customer Identity and Access Management for Auth0"""

__version__ = "0.1.0"
__author__ = "Brian Reavey"
__email__ = "brian@reavey05.com"
__license__ = "GPL-3.0-only"

from .core import AuthenticationCore, AuthResult
from .session_store import SessionStore, InMemorySessionStore
from .exceptions import (
    AuthenticationError,
    AuthenticationRequiredError,
    SessionExpiredError,
    InvalidCredentialsError,
    NetworkError,
)
from .config import Auth0Config, create_angel_studios_config

__all__ = [
    "AuthenticationCore",
    "AuthResult",
    "SessionStore",
    "InMemorySessionStore",
    "AuthenticationError",
    "AuthenticationRequiredError",
    "SessionExpiredError",
    "InvalidCredentialsError",
    "NetworkError",
    "Auth0Config",
    "create_angel_studios_config",
]
