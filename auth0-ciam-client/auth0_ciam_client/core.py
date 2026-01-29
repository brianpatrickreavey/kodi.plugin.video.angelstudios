"""Core authentication logic for Auth0 CIAM Client."""

import logging
import sys
import urllib.parse
from datetime import datetime, timezone
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
            parts = token.split(".")
            if len(parts) != 3:
                return False

            # Decode payload (second part)
            import base64
            import json

            # Add padding if needed
            payload_b64 = parts[1]
            payload_b64 += "=" * (4 - len(payload_b64) % 4)

            payload_bytes = base64.urlsafe_b64decode(payload_b64)
            payload = json.loads(payload_bytes.decode("utf-8"))

            # Check expiration
            exp = payload.get("exp")
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

            parts = token.split(".")
            if len(parts) != 3:
                return None

            payload_b64 = parts[1]
            payload_b64 += "=" * (4 - len(payload_b64) % 4)

            payload_bytes = base64.urlsafe_b64decode(payload_b64)
            payload = json.loads(payload_bytes.decode("utf-8"))

            return payload.get("exp")

        except Exception:
            return None

    def _perform_authentication(self, username: str, password: str) -> Optional[str]:
        """Perform the full Auth0 authentication flow.

        This method implements the web scraping approach to Auth0 authentication,
        which is necessary when proper OAuth PKCE flows are not available.

        Args:
            username: User email/username
            password: User password

        Returns:
            Optional[str]: JWT token if successful, None otherwise

        Raises:
            NetworkError: For network-related failures
            InvalidCredentialsError: For authentication failures
            AuthenticationError: For other authentication errors
        """
        self.log.info("Starting full authentication flow")

        # Derive URLs from base_url (assuming Auth0 subdomain pattern)
        # This can be made more configurable later if needed
        base_url = self.config.base_url.rstrip("/")
        web_url = base_url
        # For now, assume auth subdomain - this could be configurable
        auth_url = base_url.replace("://www.", "://auth.").replace("://", "://auth.")

        login_url = f"{web_url}/auth/login"
        self.log.info(f"Login URL: {login_url}")

        # Set User-Agent from config or use default
        user_agent = self.config.user_agent or (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/58.0.3029.110 Safari/537.3"
        )
        self.session.headers.update({"User-Agent": user_agent})

        # Ensure no stale Authorization header for login fetch
        self.session.headers.pop("Authorization", None)

        # Clear cookies to avoid cached responses based on session state
        self.session.cookies.clear()

        # Step 1: Get login page
        self.log.info(f"Fetching login page: {login_url}")
        try:
            login_page_response = self.session.get(login_url, timeout=self.config.request_timeout)
        except requests.Timeout:
            error_msg = f"Request timeout: Unable to connect to {base_url} (timeout: {self.config.request_timeout}s)"
            self.log.error(error_msg)
            raise NetworkError(error_msg)
        except requests.RequestException as e:
            error_msg = f"Failed to fetch login page: {e}"
            self.log.error(error_msg)
            raise NetworkError(error_msg)

        if login_page_response.status_code != 200:
            error_msg = f"Failed to fetch login page: HTTP {login_page_response.status_code}"
            self.log.error(error_msg)
            raise NetworkError(error_msg)

        self.log.info("Successfully fetched login page.")

        # Step 2: Parse state from login page
        soup = BeautifulSoup(login_page_response.content, "html.parser")
        state = self.session.cookies.get("angelSession", "")  # This might be Auth0-specific
        for element in soup.find_all("input"):
            if not isinstance(element, Tag):
                continue
            if element.get("id") == "state" and element.get("name") == "state":
                state = element.get("value")

        email_payload = {"email": username, "state": state}
        email_uri = f"{auth_url}/u/login/password?{urllib.parse.urlencode(email_payload)}"

        # Step 3: Get post-email page
        self.log.info(f"Fetching post-email page: {email_uri}")
        try:
            email_response = self.session.get(
                email_uri, headers={"Cache-Control": "no-cache"}, timeout=self.config.request_timeout
            )
        except requests.Timeout:
            error_msg = f"Request timeout: Unable to connect to {auth_url} (timeout: {self.config.request_timeout}s)"
            self.log.error(error_msg)
            raise NetworkError(error_msg)
        except requests.RequestException as e:
            error_msg = f"Failed to fetch post-email page: {e}"
            self.log.error(error_msg)
            raise NetworkError(error_msg)

        if email_response.status_code != 200:
            error_msg = f"Failed to fetch post-email page: HTTP {email_response.status_code}"
            self.log.error(error_msg)
            raise NetworkError(error_msg)

        self.log.info("Successfully fetched post-email page.")

        # Step 4: Parse state and csrf_token from post-email page
        soup = BeautifulSoup(email_response.content, "html.parser")
        state2 = None
        csrf_token = None
        for input_element in soup.find_all("input"):
            if not isinstance(input_element, Tag):
                continue
            if input_element.get("id") == "state" and input_element.get("name") == "state":
                state2 = input_element.get("value")
            elif input_element.get("name") == "_csrf_token":
                csrf_token = input_element.get("value")

        password_uri = f"{auth_url}/u/login?{urllib.parse.urlencode({'state': state2})}"
        password_payload = {
            "email": username,
            "password": password,
            "state": state2,
            "_csrf_token": csrf_token,
            "has_agreed": "true",
        }

        # Step 5: Post password
        try:
            password_response = self.session.post(
                password_uri, data=password_payload, allow_redirects=False, timeout=self.config.request_timeout
            )
        except requests.Timeout:
            error_msg = f"Request timeout: Unable to connect to {auth_url} (timeout: {self.config.request_timeout}s)"
            self.log.error(error_msg)
            raise NetworkError(error_msg)
        except requests.RequestException as e:
            error_msg = f"Password submission failed: {e}"
            self.log.error(error_msg)
            raise NetworkError(error_msg)

        # Handle authentication response
        if password_response.status_code in (302, 303):
            redirect_url = password_response.headers.get("Location")
            if not redirect_url:
                error_msg = "Login redirect missing Location header"
                self.log.error(error_msg)
                raise AuthenticationError(error_msg)

            self.log.info(f"Following redirect to: {redirect_url}")
            # Follow the redirect - required to complete the login process
            try:
                redirect_response = self.session.get(
                    redirect_url, allow_redirects=True, timeout=self.config.request_timeout
                )
            except requests.Timeout:
                error_msg = f"Request timeout following login redirect (timeout: {self.config.request_timeout}s)"
                self.log.error(error_msg)
                raise NetworkError(error_msg)
            except requests.RequestException as e:
                error_msg = f"Redirect follow failed: {e}"
                self.log.error(error_msg)
                raise NetworkError(error_msg)

            if redirect_response.status_code == 200:
                self.log.info("Login successful!")
            else:
                error_msg = f"Login failed after redirect: HTTP {redirect_response.status_code}"
                self.log.error(error_msg)
                raise InvalidCredentialsError(error_msg)

        elif password_response.status_code == 200:
            self.log.info("Login successful!")
        else:
            error_msg = f"Login failed: HTTP {password_response.status_code}"
            self.log.error(error_msg)
            raise InvalidCredentialsError(error_msg)

        # Step 6: Check for error message in response
        soup = BeautifulSoup(password_response.content, "html.parser")
        if soup.find("div", class_="error-message"):
            error_msg = "Login failed: Invalid username or password"
            self.log.error(error_msg)
            raise InvalidCredentialsError(error_msg)

        # Step 7: Extract JWT token from cookies
        jwt_token = ""
        for cookie in self.session.cookies:
            # Check for configured JWT cookie names in priority order
            for cookie_name in self.config.jwt_cookie_names:
                if cookie.name == cookie_name:
                    jwt_token = str(cookie.value)
                    self.log.debug(f"Found JWT token in cookie '{cookie.name}': {jwt_token[:20]}...")
                    break
            if jwt_token:
                break

        if jwt_token:
            self.log.info("Successfully extracted JWT token from cookies")
            return jwt_token
        else:
            self.log.warning("No JWT token found in cookies")
            return None
