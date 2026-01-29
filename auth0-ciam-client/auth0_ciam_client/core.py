"""Core authentication logic for Auth0 CIAM Client."""

import logging
import sys
from datetime import datetime, timezone, timedelta
from typing import Optional, Callable
from dataclasses import dataclass

import requests
from bs4 import BeautifulSoup, Tag

from .config import Auth0Config
from .session_store import SessionStore
from .exceptions import (
    AuthenticationError,
    AuthenticationRequiredError,
    InvalidCredentialsError,
    NetworkError,
)


@dataclass
class AuthResult:
    """Result of an authentication operation."""
    success: bool
    token: Optional[str] = None
    error_message: Optional[str] = None


class AuthenticationCore:
    """Core authentication logic for Auth0 CIAM flows.

    This class handles the authentication flow against Auth0-based services,
    including token management, session validation, and automatic refresh.
    """

    def __init__(
        self,
        session_store: SessionStore,
        config: Auth0Config,
        error_callback: Optional[Callable[[str, str], None]] = None,
        logger: Optional[logging.Logger] = None,
    ):
        """Initialize the authentication core.

        Args:
            session_store: Storage backend for tokens and credentials
            config: Auth0 configuration settings
            error_callback: Optional callback for error reporting
            logger: Optional logger instance
        """
        self.session_store = session_store
        self.config = config
        self.error_callback = error_callback

        # Set up logging
        if logger is not None:
            self.log = logger
        else:
            logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)
            self.log = logging.getLogger("AuthenticationCore")

        # Initialize HTTP session
        self.session = requests.Session()

        # Configure default headers
        user_agent = config.user_agent or (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/58.0.3029.110 Safari/537.3"
        )
        self.session.headers.update({"User-Agent": user_agent})

    def authenticate(self, username: str, password: str) -> AuthResult:
        """Authenticate with Auth0 and return result.

        Args:
            username: User email/username
            password: User password

        Returns:
            AuthResult: Authentication result with success status and token/error
        """
        try:
            # Try to get existing token first
            existing_token = self.session_store.get_token()
            if existing_token and self._validate_token(existing_token):
                self.log.info("Using existing valid token")
                return AuthResult(success=True, token=existing_token)

            # Perform full authentication flow
            token = self._perform_authentication(username, password)
            if token:
                self.session_store.save_token(token)
                self.session_store.save_credentials(username, password)
                return AuthResult(success=True, token=token)
            else:
                error_msg = "Authentication failed: No token received"
                if self.error_callback:
                    self.error_callback("auth_failed", error_msg)
                return AuthResult(success=False, error_message=error_msg)

        except AuthenticationError:
            raise  # Re-raise authentication errors as-is
        except Exception as e:
            error_msg = f"Authentication error: {str(e)}"
            self.log.error(error_msg)
            if self.error_callback:
                self.error_callback("auth_error", error_msg)
            return AuthResult(success=False, error_message=error_msg)

    def validate_session(self) -> bool:
        """Check if current session/token is valid.

        Returns:
            bool: True if session is valid, False otherwise
        """
        token = self.session_store.get_token()
        if not token:
            return False
        return self._validate_token(token)

    def ensure_valid_session(self) -> None:
        """Ensure the session is valid, refreshing if necessary.

        Raises:
            AuthenticationRequiredError: If session cannot be validated or refreshed
        """
        token = self.session_store.get_token()
        if token:
            # Check if token is expiring soon
            exp_timestamp = self._get_jwt_expiration_timestamp(token)
            if exp_timestamp is None:
                raise AuthenticationRequiredError("Invalid authentication token")

            buffer_hours = self.session_store.get_expiry_buffer_hours()
            buffer_seconds = buffer_hours * 3600
            now_timestamp = int(datetime.now(timezone.utc).timestamp())

            if exp_timestamp <= (now_timestamp + buffer_seconds):
                self.log.info(f"Token expiring soon (within {buffer_hours}h), attempting refresh")
                # Try to refresh using stored credentials
                username, password = self.session_store.get_credentials()
                if not username or not password:
                    raise AuthenticationRequiredError("Token expiring and no stored credentials for refresh")

                # Attempt authentication with stored credentials
                result = self.authenticate(username, password)
                if not result.success:
                    raise AuthenticationRequiredError(f"Automatic refresh failed: {result.error_message}")

                self.log.info("Token successfully refreshed")
            else:
                self.log.debug("Token is still valid")
        else:
            # No token available, try to authenticate with stored credentials
            self.log.info("No token available, attempting authentication with stored credentials")
            username, password = self.session_store.get_credentials()
            if not username or not password:
                raise AuthenticationRequiredError("No authentication token available and no stored credentials")

            # Attempt authentication with stored credentials
            result = self.authenticate(username, password)
            if not result.success:
                raise AuthenticationRequiredError(f"Authentication failed: {result.error_message}")

            self.log.info("Successfully authenticated with stored credentials")

    def logout(self) -> None:
        """Clear authentication state (token only, preserves credentials for re-auth)."""
        self.session_store.clear_token()
        try:
            self.session.cookies.clear()
            self.session.close()
        except Exception:
            pass
        self.session = requests.Session()

    def _validate_token(self, token: str) -> bool:
        """Validate JWT token format and expiration.

        Args:
            token: JWT token to validate

        Returns:
            bool: True if token is valid, False otherwise
        """
        try:
            # Basic JWT structure validation
            parts = token.split('.')
            if len(parts) != 3:
                return False

            # Decode payload (second part)
            import base64
            import json

            # Add padding if needed
            payload_b64 = parts[1]
            payload_b64 += '=' * (4 - len(payload_b64) % 4)

            payload_bytes = base64.urlsafe_b64decode(payload_b64)
            payload = json.loads(payload_bytes.decode('utf-8'))

            # Check expiration
            exp = payload.get('exp')
            if not exp:
                return False

            now = int(datetime.now(timezone.utc).timestamp())
            return exp > now

        except Exception:
            return False

    def _get_jwt_expiration_timestamp(self, token: str) -> Optional[int]:
        """Extract expiration timestamp from JWT token.

        Args:
            token: JWT token

        Returns:
            Optional[int]: Expiration timestamp, or None if invalid
        """
        try:
            import base64
            import json

            parts = token.split('.')
            if len(parts) != 3:
                return None

            payload_b64 = parts[1]
            payload_b64 += '=' * (4 - len(payload_b64) % 4)

            payload_bytes = base64.urlsafe_b64decode(payload_b64)
            payload = json.loads(payload_bytes.decode('utf-8'))

            return payload.get('exp')

        except Exception:
            return None

    def _perform_authentication(self, username: str, password: str) -> Optional[str]:
        """Perform the full Auth0 authentication flow.

        This is a placeholder implementation that needs to be adapted
        from the original angel_authentication.py logic.

        Args:
            username: User email/username
            password: User password

        Returns:
            Optional[str]: JWT token if successful, None otherwise
        """
        # TODO: Extract and adapt the authentication flow from angel_authentication.py
        # This will include:
        # 1. Get login page
        # 2. Parse state/CSRF tokens
        # 3. Submit credentials
        # 4. Extract JWT from cookies
        # 5. Handle redirects and errors

        self.log.warning("_perform_authentication not yet implemented")
        return None