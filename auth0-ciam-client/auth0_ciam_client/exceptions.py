"""Exception classes for Auth0 CIAM Client."""

from typing import Optional


class AuthenticationError(Exception):
    """Base class for authentication-related errors."""

    def __init__(self, message: str, error_code: Optional[str] = None):
        super().__init__(message)
        self.error_code = error_code


class AuthenticationRequiredError(AuthenticationError):
    """Raised when authentication is required but not available."""

    pass


class SessionExpiredError(AuthenticationError):
    """Raised when the current session has expired."""

    pass


class InvalidCredentialsError(AuthenticationError):
    """Raised when provided credentials are invalid."""

    pass


class NetworkError(AuthenticationError):
    """Raised when network-related errors occur during authentication."""

    pass


class ConfigurationError(AuthenticationError):
    """Raised when configuration is invalid or incomplete."""

    pass
