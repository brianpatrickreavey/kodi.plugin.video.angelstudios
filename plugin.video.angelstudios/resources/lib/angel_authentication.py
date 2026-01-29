import logging
import os
import pickle
import sys
import requests
from bs4 import BeautifulSoup, Tag
import urllib.parse
import base64
import json
from datetime import datetime, timezone, timedelta
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, Callable
import angel_utils


class AuthenticationError(Exception):
    """Base class for authentication-related errors"""

    pass


class AuthenticationRequiredError(AuthenticationError):
    """Raised when authentication is required but not available"""

    pass


class SessionExpiredError(AuthenticationError):
    """Raised when the current session has expired"""

    pass


class InvalidCredentialsError(AuthenticationError):
    """Raised when provided credentials are invalid"""

    pass


@dataclass
class AuthResult:
    """Result of an authentication operation"""

    success: bool
    token: Optional[str] = None
    error_message: Optional[str] = None


class SessionStore(ABC):
    """Abstract base class for session persistence"""

    @abstractmethod
    def save_token(self, token: str) -> None:
        """Save the JWT token to persistent storage"""
        pass

    @abstractmethod
    def get_token(self) -> str | None:
        """Retrieve the JWT token from persistent storage"""
        pass

    @abstractmethod
    def clear_token(self) -> None:
        """Clear the stored JWT token"""
        pass

    @abstractmethod
    def save_credentials(self, username: str, password: str) -> None:
        """Save username and password to persistent storage"""
        pass

    @abstractmethod
    def get_credentials(self) -> tuple[str | None, str | None]:
        """Retrieve username and password from persistent storage"""
        pass

    @abstractmethod
    def clear_credentials(self) -> None:
        """Clear stored username and password"""
        pass

    def get_expiry_buffer_hours(self) -> int:
        """Get the expiry buffer in hours (default implementation returns 1)"""
        return 1


class KodiSessionStore(SessionStore):
    """Kodi addon settings-based session store"""

    def __init__(self, addon):
        self.addon = addon

    def save_token(self, token: str) -> None:
        """Save JWT token to Kodi addon settings"""
        self.addon.setSettingString("jwt_token", token)

    def get_token(self) -> str | None:
        """Get JWT token from Kodi addon settings"""
        token = self.addon.getSettingString("jwt_token")
        return token if token else None

    def clear_token(self) -> None:
        """Clear JWT token from Kodi addon settings"""
        self.addon.setSettingString("jwt_token", "")

    def save_credentials(self, username: str, password: str) -> None:
        """Save username and password to Kodi addon settings"""
        self.addon.setSettingString("username", username)
        self.addon.setSettingString("password", password)

    def get_credentials(self) -> tuple[str | None, str | None]:
        """Get username and password from Kodi addon settings"""
        username = self.addon.getSettingString("username")
        password = self.addon.getSettingString("password")
        return (username if username else None, password if password else None)

    def clear_credentials(self) -> None:
        """Clear username and password from Kodi addon settings"""
        self.addon.setSettingString("username", "")
        self.addon.setSettingString("password", "")

    def get_expiry_buffer_hours(self) -> int:
        """Get the expiry buffer in hours from addon settings (default 1 hour)"""
        try:
            buffer_str = self.addon.getSettingString("expiry_buffer_hours")
            if buffer_str:
                return int(buffer_str)
            return 1  # Default 1 hour
        except (ValueError, TypeError):
            return 1


class AuthenticationCore:
    """Pure authentication logic - no UI dependencies"""

    def __init__(
        self,
        session_store: SessionStore,
        error_callback: Optional[Callable[[str, str], None]] = None,
        logger=None,
        timeout=30,
    ):
        self.session_store = session_store
        self.error_callback = error_callback
        self.timeout = timeout
        self.session = requests.Session()

        # Use the provided logger, or default to the module logger
        if logger is not None:
            self.log = logger
        else:
            logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)
            self.log = logging.getLogger("AuthenticationCore")

        self.web_url = "https://www.angel.com"
        self.auth_url = "https://auth.angel.com"

    def authenticate(self, username: str, password: str) -> AuthResult:
        """Authenticate with Angel Studios and return result"""
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

        except Exception as e:
            error_msg = f"Authentication error: {str(e)}"
            self.log.error(error_msg)
            if self.error_callback:
                self.error_callback("auth_error", error_msg)
            return AuthResult(success=False, error_message=error_msg)

    def validate_session(self) -> bool:
        """Check if current session/token is valid"""
        token = self.session_store.get_token()
        if not token:
            return False
        return self._validate_token(token)

    def refresh_token(self) -> bool:
        """Attempt to refresh the authentication token"""
        # For now, this is a placeholder - refresh token support would be implemented here
        # According to the plan, this should attempt to refresh using refresh tokens
        # If refresh fails, return False (fail and reauth as per plan)
        self.log.warning("Token refresh not yet implemented")
        return False

    def ensure_valid_session(self) -> None:
        """Ensure the session is valid, refreshing if necessary"""
        token = self.session_store.get_token()
        if token:
            # Check if token is expiring soon
            exp_timestamp = self._get_jwt_expiration_timestamp(token)
            if exp_timestamp is None:
                raise AuthenticationRequiredError("Invalid authentication token")

            buffer_hours = 1  # Default buffer
            if hasattr(self.session_store, "get_expiry_buffer_hours"):
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
        """Clear authentication state (token only, preserves credentials for re-auth)"""
        self.session_store.clear_token()
        try:
            self.session.close()
        except Exception:
            pass
        self.session = requests.Session()

    def get_session_details(self):
        """Return session diagnostics for UI display without exposing token contents."""
        details = {
            "login_email": "Unknown",
            "account_id": None,
            "authenticated": False,
            "expires_at_utc": None,
            "expires_at_local": None,
            "expires_in_seconds": None,
            "expires_in_human": None,
            "issued_at_utc": None,
            "issued_at_local": None,
            "jwt_present": False,
            "cookie_names": [],
        }

        try:
            # Get credentials for login email
            username, password = self.session_store.get_credentials()
            if username:
                details["login_email"] = username

            # Check if we have a valid token
            token = self.session_store.get_token()
            if token and self._validate_token(token):
                details["authenticated"] = True

                # Parse JWT token for details
                try:
                    header, payload, signature = token.split(".")
                    payload_decoded = base64.urlsafe_b64decode(payload + "==")
                    claims = json.loads(payload_decoded)

                    exp_timestamp = claims.get("exp")
                    iat_timestamp = claims.get("iat")
                    email_claim = claims.get("email")
                    sub_claim = claims.get("sub")

                    if email_claim:
                        details["login_email"] = email_claim
                    if sub_claim:
                        details["account_id"] = sub_claim

                    if exp_timestamp:
                        exp_datetime_utc = datetime.fromtimestamp(exp_timestamp, tz=timezone.utc)
                        exp_datetime_local = exp_datetime_utc.astimezone()
                        details["expires_at_utc"] = exp_datetime_utc.isoformat()
                        details["expires_at_local"] = exp_datetime_local.strftime("%Y-%m-%d %H:%M:%S %Z")

                        now_timestamp = int(datetime.now(timezone.utc).timestamp())
                        expires_in_seconds = exp_timestamp - now_timestamp
                        details["expires_in_seconds"] = expires_in_seconds

                        if expires_in_seconds > 0:
                            days, rem = divmod(expires_in_seconds, 86400)
                            hours, rem = divmod(rem, 3600)
                            minutes, seconds = divmod(rem, 60)
                            parts = []
                            if days:
                                parts.append(f"{days}d")
                            if hours:
                                parts.append(f"{hours}h")
                            if minutes:
                                parts.append(f"{minutes}m")
                            if seconds or not parts:
                                parts.append(f"{seconds}s")
                            details["expires_in_human"] = " ".join(parts)
                        else:
                            details["expires_in_human"] = "Expired"

                    if iat_timestamp:
                        iat_datetime_utc = datetime.fromtimestamp(iat_timestamp, tz=timezone.utc)
                        iat_datetime_local = iat_datetime_utc.astimezone()
                        details["issued_at_utc"] = iat_datetime_utc.isoformat()
                        details["issued_at_local"] = iat_datetime_local.strftime("%Y-%m-%d %H:%M:%S %Z")

                    details["jwt_present"] = True

                except Exception as e:
                    self.log.debug(f"Failed to parse JWT token: {e}")

            # Get cookie information
            if self.session and self.session.cookies:
                details["cookie_names"] = [c.name for c in self.session.cookies]

        except Exception as e:
            self.log.error(f"Error getting session details: {e}")

        return details

    def _validate_token(self, token: str) -> bool:
        """Validate JWT token expiration"""
        try:
            exp_timestamp = self._get_jwt_expiration_timestamp(token)
            if exp_timestamp:
                now_timestamp = int(datetime.now(timezone.utc).timestamp())
                return exp_timestamp > now_timestamp
        except Exception:
            pass
        return False

    def _get_jwt_expiration_timestamp(self, jwt_token: str) -> Optional[int]:
        """Extract expiration timestamp from JWT token"""
        try:
            header, payload, signature = jwt_token.split(".")
            payload_decoded = base64.urlsafe_b64decode(payload + "==")
            claims = json.loads(payload_decoded)
            return claims.get("exp")
        except Exception:
            return None

    def _perform_authentication(self, username: str, password: str) -> Optional[str]:
        """Perform the full OAuth authentication flow"""
        self.log.info("Starting full authentication flow")

        login_url = f"{self.web_url}/auth/login"
        self.log.info(f"Login URL: {login_url}")
        self.session.headers.update(
            {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/58.0.3029.110 Safari/537.3"
                )
            }
        )

        # Ensure no stale Authorization header for login fetch
        self.session.headers.pop("Authorization", None)

        # Clear cookies to avoid cached responses based on session state
        self.session.cookies.clear()

        # Step 1: Get login page
        self.log.info(f"Fetching login page: {login_url}")
        try:
            login_page_response = self.session.get(login_url, timeout=self.timeout)
        except requests.Timeout:
            self.log.error(f"Timeout ({self.timeout}s) fetching login page")
            raise Exception(f"Request timeout: Unable to connect to Angel Studios (timeout: {self.timeout}s)")
        except requests.RequestException as e:
            self.log.error(f"Failed to fetch login page: {e}")
            raise Exception("Failed to fetch the login page")

        if login_page_response.status_code != 200:
            self.log.error(f"Failed to fetch the login page: {login_page_response.status_code}")
            raise Exception("Failed to fetch the login page")
        self.log.info("Successfully fetched the login page.")

        # Step 2: Parse state from login page
        soup = BeautifulSoup(login_page_response.content, "html.parser")
        state = self.session.cookies.get("angelSession", "")
        for element in soup.find_all("input"):
            if not isinstance(element, Tag):
                continue
            if element.get("id") == "state" and element.get("name") == "state":
                state = element.get("value")

        email_payload = {"email": username, "state": state}
        email_uri = f"{self.auth_url}/u/login/password?{urllib.parse.urlencode(email_payload)}"

        # Step 3: Get post-email page
        self.log.info(f"Fetching post-email page: {email_uri}")
        try:
            email_response = self.session.get(email_uri, headers={"Cache-Control": "no-cache"}, timeout=self.timeout)
        except requests.Timeout:
            self.log.error(f"Timeout ({self.timeout}s) fetching post-email page")
            raise Exception(f"Request timeout: Unable to connect to Angel Studios (timeout: {self.timeout}s)")
        except requests.RequestException as e:
            self.log.error(f"Failed to fetch the post-email page: {e}")
            raise Exception("Failed to fetch the post-email page")

        if email_response.status_code != 200:
            self.log.error(f"Failed to fetch the post-email page: {email_response.status_code}")
            raise Exception("Failed to fetch the post-email page")
        self.log.info("Successfully fetched the post-email page.")

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

        password_uri = f"{self.auth_url}/u/login?{urllib.parse.urlencode({'state': state2})}"
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
                password_uri, data=password_payload, allow_redirects=False, timeout=self.timeout
            )
        except requests.Timeout:
            self.log.error(f"Timeout ({self.timeout}s) posting password")
            raise Exception(f"Request timeout: Unable to connect to Angel Studios (timeout: {self.timeout}s)")
        except requests.RequestException as e:
            self.log.error(f"Password post failed: {e}")
            raise Exception("Login failed")

        if password_response.status_code in (302, 303):
            redirect_url = password_response.headers.get("Location")
            if not redirect_url:
                self.log.error("Redirect response missing Location header")
                raise Exception("Login redirect missing Location header")
            self.log.info(f"Following redirect to: {redirect_url}")
            # Follow the redirect - required to complete the login process
            try:
                redirect_response = self.session.get(redirect_url, allow_redirects=True, timeout=self.timeout)
            except requests.Timeout:
                self.log.error(f"Timeout ({self.timeout}s) following login redirect")
                raise Exception(f"Request timeout: Unable to connect to Angel Studios (timeout: {self.timeout}s)")
            except requests.RequestException as e:
                self.log.error(f"Redirect follow failed: {e}")
                raise Exception("Login failed after redirect")

            if redirect_response.status_code == 200:
                self.log.info("Login successful!")
            else:
                self.log.error(
                    f"Login failed after redirect: {redirect_response.status_code} {redirect_response.reason}"
                )
                raise Exception("Login failed after redirect")
        elif password_response.status_code == 200:
            self.log.info("Login successful!")
        else:
            self.log.error(f"Login failed: {password_response.status_code} {password_response.reason}")
            raise Exception("Login failed")

        # Step 6: Check for error message in response
        soup = BeautifulSoup(password_response.content, "html.parser")
        if soup.find("div", class_="error-message"):
            self.log.error("Login failed: Invalid username or password")
            raise Exception("Login failed: Invalid username or password")

        # Step 7: Extract JWT token from cookies
        jwt_token = ""
        for cookie in self.session.cookies:
            # Check for the current JWT cookie name
            if cookie.name == "angel_jwt_v2":
                jwt_token = str(cookie.value)
                self.log.debug(f"Found JWT token in cookie '{cookie.name}': {jwt_token[:20]}...")
                break
            # Fallback to old cookie name for backward compatibility
            elif cookie.name == "angel_jwt":
                jwt_token = str(cookie.value)
                self.log.debug(f"Found JWT token in legacy cookie '{cookie.name}': {jwt_token[:20]}...")
                break

        if jwt_token:
            self.log.info("Found JWT token in cookies")
            return jwt_token
        else:
            self.log.warning("No JWT token found in cookies")
            return None


class AngelStudioSession:
    """Class to handle Angel Studios authentication and session management"""

    def __init__(self, username=None, password=None, session_file="", logger=None, timeout=30):
        self.username = username
        self.password = password
        self.session_file = session_file
        self.timeout = timeout
        self.session = requests.Session()
        self.session_valid = False
        self.web_url = "https://www.angel.com"
        self.auth_url = "https://auth.angel.com"
        self.api_url = "https://api.angelstudios.com/graphql"

        # Use the provided logger, or default to the module logger
        if logger is not None:
            self.log = logger
            self.log.info("Custom logger initialized")
        else:
            # Default to the module logger
            logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)
            self.log = logging.getLogger("AngelStudiosInterface")
            self.log.info("STDOUT logger initialized")
        self.log.info(f"{self.log=}")

    def authenticate(self, force_reauthentication=False):
        """
        Get a session object for making requests to the Angel.com API.

        Todo:
            - return an unauthenticated session if no credentials are provided
            - Handle session expiration and re-authentication
            - Add more robust error handling and logging
            - maybe break this into smaller private functions for clarity
              - authenticate_with_credentials
              - authenticate_with_cookies
              - validate_session
        """
        self.log.info("Getting authenticated session for Angel.com")
        if force_reauthentication:
            self.log.info("Forcing re-authentication and clearing session cache")
            self.__clear_session_cache()
            try:
                self.session.close()
            except Exception:
                # Best-effort close; session should always be replaced below
                pass
            self.session = requests.Session()
            self.session_valid = False

        # Validate current session, if any
        self.session_valid = self._validate_session()

        if self.session_valid:
            self.log.info("Session is already authenticated and valid.")
            return True

        self.log.info("No valid session found, starting authentication flow.")
        try:
            self.session.close()
        except Exception:
            pass
        self.session = requests.Session()

        # Try to load existing session cookies
        if self.__load_session_cookies():
            self.log.info("Loaded cookies from file.")
            if self._validate_session():
                self.log.info("Valid session created from cookies.")
                return True
            else:
                self.log.info("Session is invalid, starting new authentication flow.")
        else:
            self.log.info("No session cookies found, starting new authentication flow.")

        # If we don't have credentials, try to get them or return mock
        if self.username is None or self.password is None:
            self.log.info("No credentials provided for authentication.")

        login_url = f"{self.web_url}/auth/login"
        self.log.info(f"Login URL: {login_url}")
        self.session.headers.update(
            {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/58.0.3029.110 Safari/537.3"
                )
            }
        )

        # Ensure no stale Authorization header for login fetch
        self.session.headers.pop("Authorization", None)

        # Clear cookies to avoid cached responses based on session state
        self.session.cookies.clear()

        # Step 1: Get login page
        self.log.info(f"Fetching login page: {login_url}")
        self.log.info(f"Authorization header present before login fetch: {'Authorization' in self.session.headers}")
        try:
            login_page_response = self.session.get(login_url, timeout=self.timeout)
        except requests.Timeout:
            self.log.error(f"Timeout ({self.timeout}s) fetching login page")
            raise Exception(f"Request timeout: Unable to connect to Angel Studios (timeout: {self.timeout}s)")
        except requests.RequestException as e:
            self.log.error(f"Failed to fetch login page: {e}")
            raise Exception("Failed to fetch the login page")

        if login_page_response.status_code != 200:
            self.log.error(f"Failed to fetch the login page: {login_page_response.status_code}")
            raise Exception("Failed to fetch the login page")
        self.log.info("Successfully fetched the login page.")
        self.log.info(f"Login page response: {login_page_response.status_code} {login_page_response.reason}")
        self.log.info(
            f"Login page headers: {angel_utils.sanitize_headers_for_logging(dict(login_page_response.headers))}"
        )
        self.log.info(f"Login page content: {login_page_response.content[:500]}...")  # Log first 500 chars for brevity
        self.log.info(f"Login page cookies: {login_page_response.cookies.get_dict()}")

        # Step 2: Parse state from login page
        soup = BeautifulSoup(login_page_response.content, "html.parser")

        state = self.session.cookies.get("angelSession", "")
        for element in soup.find_all("input"):
            if not isinstance(element, Tag):
                continue
            self.log.info(f"Found input element: {element}")
            if element.get("id") == "state" and element.get("name") == "state":
                state = element.get("value")

        email_payload = {"email": self.username, "state": state}
        self.log.info(f"Email payload: {email_payload}")
        email_uri = f"{self.auth_url}/u/login/password?{urllib.parse.urlencode(email_payload)}"

        # Step 3: Get post-email page
        self.log.info(f"Fetching post-email page: {email_uri}")
        self.log.debug(f"Request method: GET")
        self.log.debug(f"Request headers: {angel_utils.sanitize_headers_for_logging(dict(self.session.headers))}")
        try:
            email_response = self.session.get(email_uri, headers={"Cache-Control": "no-cache"}, timeout=self.timeout)
        except requests.Timeout:
            self.log.error(f"Timeout ({self.timeout}s) fetching post-email page")
            raise Exception(f"Request timeout: Unable to connect to Angel Studios (timeout: {self.timeout}s)")
        except requests.RequestException as e:
            self.log.error(f"Failed to fetch the post-email page: {e}")
            raise Exception("Failed to fetch the post-email page")

        if email_response.status_code != 200:
            self.log.error(f"Failed to fetch the post-email page: {email_response.status_code}")
            self.log.error(f"Post-email page response: {email_response.status_code} {email_response.reason}")
            self.log.error(
                f"Post-email response headers: {angel_utils.sanitize_headers_for_logging(dict(email_response.headers))}"
            )
            self.log.error(f"Post-email response content: {email_response.text}")
            raise Exception("Failed to fetch the post-email page")
        self.log.info("Successfully fetched the post-email page.")

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

        password_uri = f"{self.auth_url}/u/login?{urllib.parse.urlencode({'state': state2})}"
        password_payload = {
            "email": self.username,
            "password": self.password,
            "state": state2,
            "_csrf_token": csrf_token,
            "has_agreed": "true",
        }

        # Step 5: Post password
        try:
            password_response = self.session.post(
                password_uri, data=password_payload, allow_redirects=False, timeout=self.timeout
            )
        except requests.Timeout:
            self.log.error(f"Timeout ({self.timeout}s) posting password")
            raise Exception(f"Request timeout: Unable to connect to Angel Studios (timeout: {self.timeout}s)")
        except requests.RequestException as e:
            self.log.error(f"Password post failed: {e}")
            raise Exception("Login failed")
        if password_response.status_code in (302, 303):
            redirect_url = password_response.headers.get("Location")
            if not redirect_url:
                self.log.error("Redirect response missing Location header")
                raise Exception("Login redirect missing Location header")
            self.log.info(f"Following redirect to: {redirect_url}")
            # Follow the redirect - required to complete the login process
            try:
                redirect_response = self.session.get(redirect_url, allow_redirects=True, timeout=self.timeout)
            except requests.Timeout:
                self.log.error(f"Timeout ({self.timeout}s) following login redirect")
                raise Exception(f"Request timeout: Unable to connect to Angel Studios (timeout: {self.timeout}s)")
            except requests.RequestException as e:
                self.log.error(f"Redirect follow failed: {e}")
                raise Exception("Login failed after redirect")

            self.log.debug(f"{redirect_response.status_code=}")
            self.log.debug(f"{redirect_response.url=}")
            self.log.debug(
                f"Redirect headers: {angel_utils.sanitize_headers_for_logging(dict(redirect_response.headers))}"
            )
            if redirect_response.status_code == 200:
                self.log.info("Login successful!")
                self.log.debug("Login step completed with 200 OK.")
                self.log.info(f"Login step completed with {password_response.status_code} REDIRECT to {redirect_url}")
            else:
                self.log.error(
                    f"Login failed after redirect: {redirect_response.status_code} {redirect_response.reason}"
                )
                raise Exception("Login failed after redirect")
        elif password_response.status_code == 200:
            self.log.info("Login successful!")
            self.log.debug("Login step completed with 200 OK.")
        else:
            self.log.error(f"Login failed: {password_response.status_code} {password_response.reason}")
            raise Exception("Login failed")

        # Step 6: Check for error message in response
        soup = BeautifulSoup(password_response.content, "html.parser")
        if soup.find("div", class_="error-message"):
            self.log.error("Login failed: Invalid username or password")
            raise Exception("Login failed: Invalid username or password")

        # Step 7: Set JWT token in session headers
        """Extract JWT token from cookies and set up Authorization header for GraphQL requests"""
        # Look for the JWT token in cookies
        jwt_token = ""
        for cookie in self.session.cookies:
            if cookie.name == "angel_jwt_v2":
                jwt_token = str(cookie.value)
                self.log.debug(
                    f"Found JWT token in cookie '{cookie.name}': {jwt_token[:10]}..."
                )  # Log first 10 chars for brevity
                break
            # Fallback to old cookie name for backward compatibility
            elif cookie.name == "angel_jwt":
                jwt_token = str(cookie.value)
                self.log.debug(
                    f"Found JWT token in legacy cookie '{cookie.name}': {jwt_token[:10]}..."
                )  # Log first 10 chars for brevity
                break

        if jwt_token:
            self.log.info("Found JWT token in cookies, setting Authorization header")
            # Set the Authorization header for all future requests
            self.session.headers.update({"Authorization": f"Bearer {jwt_token}"})
        else:
            self.log.warning("No JWT token found in cookies")
            # Remove any existing Authorization header
            self.session.headers.pop("Authorization", None)

        self.__save_session_cookies()

        return True

    def _validate_session(self):
        """Check if the current session is valid"""
        jwt_token = self.session.cookies.get("angel_jwt_v2") or self.session.cookies.get("angel_jwt")
        if not jwt_token:
            self.log.warning("No JWT token present in session cookies.")
            return False
        token_exp_timestamp = self.__get_jwt_expiration_timestamp(jwt_token)
        if token_exp_timestamp:
            now_timestamp = int(datetime.now(timezone.utc).timestamp())
            now_datetime = datetime.fromtimestamp(now_timestamp, tz=timezone.utc)
            exp_datetime = datetime.fromtimestamp(token_exp_timestamp, tz=timezone.utc)
            self.log.info(f"Current UTC datetime: {now_datetime.isoformat()}")
            self.log.info(f"JWT token expiration datetime: {exp_datetime.isoformat()}")
            if token_exp_timestamp < now_timestamp:
                self.log.info("JWT token has expired based on expiration timestamp.")
                return False
            else:
                exp_datetime = datetime.fromtimestamp(token_exp_timestamp, tz=timezone.utc)
                self.log.info("JWT token is valid based on expiration timestamp.")
        else:
            self.log.warning("Could not determine JWT token expiration timestamp.")
            return False
        return True

    def __get_jwt_expiration_timestamp(self, jwt_token):
        # Split and decode payload
        header, payload, signature = jwt_token.split(".")
        payload_decoded = base64.urlsafe_b64decode(payload + "==")  # Add padding
        claims = json.loads(payload_decoded)
        exp_timestamp = claims.get("exp")
        if exp_timestamp:
            return exp_timestamp
        return None

    def get_session(self) -> requests.Session:
        """
        Get an authenticated session for making requests to the Angel.com API.

        Returns:
            requests.Session: Authenticated session object
        """
        if not self.session_valid:
            if not self.authenticate():
                raise Exception("Failed to authenticate and create a valid session")

        return self.session

    def get_session_details(self):
        """Return session diagnostics for UI display without exposing token contents."""
        details = {
            "login_email": self.username or "Unknown",
            "account_id": None,
            "authenticated": False,
            "expires_at_utc": None,
            "expires_at_local": None,
            "expires_in_seconds": None,
            "expires_in_human": None,
            "issued_at_utc": None,
            "issued_at_local": None,
            "jwt_present": False,
            "cookie_names": [],
            "session_file": self.session_file,
        }

        try:
            jwt_token = None
            if self.session and self.session.cookies:
                details["cookie_names"] = [c.name for c in self.session.cookies]
                jwt_token = self.session.cookies.get("angel_jwt_v2") or self.session.cookies.get("angel_jwt")

            if not jwt_token:
                return details

            details["jwt_present"] = True

            try:
                header, payload, signature = jwt_token.split(".")
                payload_decoded = base64.urlsafe_b64decode(payload + "==")
                claims = json.loads(payload_decoded)
            except Exception:
                return details

            exp_timestamp = claims.get("exp")
            iat_timestamp = claims.get("iat")
            email_claim = claims.get("email")
            sub_claim = claims.get("sub")
            if email_claim:
                details["login_email"] = email_claim
            if sub_claim:
                details["account_id"] = sub_claim

            now_utc = datetime.now(timezone.utc)
            if exp_timestamp:
                exp_dt_utc = datetime.fromtimestamp(exp_timestamp, tz=timezone.utc)
                exp_dt_local = exp_dt_utc.astimezone()
                remaining = exp_dt_utc - now_utc
                remaining = remaining if remaining > timedelta(0) else timedelta(0)
                details["expires_at_utc"] = exp_dt_utc.strftime("%Y-%m-%d %H:%M:%S %Z")
                details["expires_at_local"] = exp_dt_local.strftime("%Y-%m-%d %H:%M:%S %Z")
                details["expires_in_seconds"] = int(remaining.total_seconds())
                details["expires_in_human"] = str(remaining)
                details["authenticated"] = remaining > timedelta(0)

            if iat_timestamp:
                iat_dt_utc = datetime.fromtimestamp(iat_timestamp, tz=timezone.utc)
                iat_dt_local = iat_dt_utc.astimezone()
                details["issued_at_utc"] = iat_dt_utc.strftime("%Y-%m-%d %H:%M:%S %Z")
                details["issued_at_local"] = iat_dt_local.strftime("%Y-%m-%d %H:%M:%S %Z")

            if self.session and self.session.headers.get("Authorization"):
                details["authenticated"] = details["authenticated"] or True

        except Exception:
            # Intentionally swallow errors to avoid breaking the UI dialog
            pass

        return details

    def __load_session_cookies(self):
        if self.session_file:
            try:
                with open(self.session_file, "rb") as f:
                    self.session.cookies.update(pickle.load(f))
            except FileNotFoundError:
                return False
            try:
                jwt_token = ""
                for cookie in self.session.cookies:
                    if cookie.name == "angel_jwt_v2":
                        jwt_token = str(cookie.value)
                        break
                    # Fallback to old cookie name for backward compatibility
                    elif cookie.name == "angel_jwt":
                        jwt_token = str(cookie.value)
                        break
                        jwt_token = str(cookie.value)
                        self.log.info(f"Loaded JWT token from cookies: {jwt_token[:10]}...")
                        break

                if jwt_token:
                    try:
                        exp_timestamp = self.__get_jwt_expiration_timestamp(jwt_token)
                    except Exception:
                        exp_timestamp = None
                    now_timestamp = int(datetime.now(timezone.utc).timestamp())
                    if exp_timestamp is None or exp_timestamp > now_timestamp:
                        self.session.headers.update({"Authorization": f"Bearer {jwt_token}"})
                        self.log.info("Session cookies loaded successfully.")
                    else:
                        self.log.info("JWT token in cookies is expired, not setting Authorization header.")
                else:
                    self.log.warning("No JWT token found in loaded cookies.")
                return True
            except Exception as e:
                self.log.error(f"Error loading jwt token from cookies: {e}")
                return False
        return False

    def __save_session_cookies(self):
        with open(self.session_file, "wb") as f:
            pickle.dump(self.session.cookies, f)

    def __clear_session_cache(self):
        """Clear the cached session data to force fresh authentication"""
        try:
            if os.path.exists(self.session_file):
                os.remove(self.session_file)
                self.log.info("Cleared cached session data")
                return True
        except Exception as e:
            self.log.error(f"Error clearing session cache: {e}")
        return False

    def logout(self):
        """Clear local session state; TODO: call remote logout endpoint when available."""
        self.log.info("Logging out: clearing local session and cached cookies")

        if self.session:
            try:
                self.session.cookies.clear()
            except Exception as e:
                self.log.warning(f"Failed to clear session cookies: {e}")
            try:
                self.session.headers.pop("Authorization", None)
            except Exception as e:
                self.log.warning(f"Failed to clear Authorization header: {e}")
            try:
                self.session.close()
            except Exception as e:
                self.log.warning(f"Failed to close session during logout: {e}")

        file_cleared = True
        if self.session_file:
            file_cleared = self.__clear_session_cache()
            if not file_cleared:
                self.log.warning("Session cache file could not be cleared during logout")

        # Replace with a fresh session to maintain the invariant of a non-None Session object
        self.session = requests.Session()
        self.session_valid = False

        return file_cleared
