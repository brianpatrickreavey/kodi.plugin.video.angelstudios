"""Session storage abstractions for Auth0 CIAM Client."""

from abc import ABC, abstractmethod
from typing import Optional, Tuple


class SessionStore(ABC):
    """Abstract base class for session persistence.

    This interface defines how authentication tokens and credentials
    are stored and retrieved. Implementations can use various backends
    like memory, files, databases, or platform-specific storage.
    """

    @abstractmethod
    def save_token(self, token: str) -> None:
        """Save the JWT token to persistent storage."""
        pass

    @abstractmethod
    def get_token(self) -> Optional[str]:
        """Retrieve the JWT token from persistent storage."""
        pass

    @abstractmethod
    def clear_token(self) -> None:
        """Clear the stored JWT token."""
        pass

    @abstractmethod
    def save_credentials(self, username: str, password: str) -> None:
        """Save username and password to persistent storage."""
        pass

    @abstractmethod
    def get_credentials(self) -> Tuple[Optional[str], Optional[str]]:
        """Retrieve username and password from persistent storage."""
        pass

    @abstractmethod
    def clear_credentials(self) -> None:
        """Clear stored username and password."""
        pass

    def get_expiry_buffer_hours(self) -> int:
        """Get the expiry buffer in hours (default implementation returns 1)."""
        return 1


class InMemorySessionStore(SessionStore):
    """In-memory session store for testing and simple applications.

    This implementation stores all data in memory and is not persistent
    across application restarts. Useful for testing or stateless applications.
    """

    def __init__(self):
        self._token: Optional[str] = None
        self._username: Optional[str] = None
        self._password: Optional[str] = None

    def save_token(self, token: str) -> None:
        """Save JWT token to memory."""
        self._token = token

    def get_token(self) -> Optional[str]:
        """Get JWT token from memory."""
        return self._token

    def clear_token(self) -> None:
        """Clear JWT token from memory."""
        self._token = None

    def save_credentials(self, username: str, password: str) -> None:
        """Save username and password to memory."""
        self._username = username
        self._password = password

    def get_credentials(self) -> Tuple[Optional[str], Optional[str]]:
        """Get username and password from memory."""
        return (self._username, self._password)

    def clear_credentials(self) -> None:
        """Clear username and password from memory."""
        self._username = None
        self._password = None
