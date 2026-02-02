"""
Angel Studios Authentication Module

This module provides authentication functionality for Angel Studios,
now backed by the auth0-ciam-client package.
"""

import logging
import sys
import requests
import base64
import json
from datetime import datetime, timezone
from typing import Optional, Tuple

from auth0_ciam_client import (
    AuthenticationCore,
    Auth0Config,
    SessionStore,
    AuthResult,
    AuthenticationError,
    AuthenticationRequiredError,
    InvalidCredentialsError,
    NetworkError,
    InMemorySessionStore,
    create_angel_studios_config,
    SessionExpiredError,
)


def decode_jwt_payload(token):
    """
    Decode JWT payload without signature verification.
    Equivalent to jwt.decode(token, options={"verify_signature": False})
    """
    try:
        # JWT format: header.payload.signature
        parts = token.split('.')
        if len(parts) != 3:
            raise ValueError("Invalid JWT token format")

        payload_b64 = parts[1]
        # Add padding if needed for base64 decoding
        payload_b64 += '=' * (4 - len(payload_b64) % 4)

        payload_bytes = base64.urlsafe_b64decode(payload_b64)
        payload_str = payload_bytes.decode('utf-8')
        return json.loads(payload_str)
    except Exception as e:
        raise ValueError(f"Failed to decode JWT payload: {e}")


# Re-export for backward compatibility
__all__ = [
    "AuthenticationCore",
    "Auth0Config",
    "SessionStore",
    "AuthResult",
    "AuthenticationError",
    "AuthenticationRequiredError",
    "InvalidCredentialsError",
    "NetworkError",
    "SessionExpiredError",
    "KodiSessionStore",
    "AngelStudioSession",
]


class KodiSessionStore(SessionStore):
    """Kodi addon settings-based session store"""

    def __init__(self, addon):
        self.addon = addon

    def save_token(self, token: str) -> None:
        """Save JWT token to Kodi addon settings"""
        self.addon.setSettingString("jwt_token", token)

    def get_token(self) -> Optional[str]:
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

    def get_credentials(self) -> Tuple[Optional[str], Optional[str]]:
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


# For backward compatibility, keep a minimal AngelStudioSession class
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
            logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)
            self.log = logging.getLogger("AngelStudiosInterface")

    def authenticate(self, force_reauthentication=False):
        """Authenticate with Angel Studios"""
        # For backward compatibility, implement the old logic but using the new package

        # Check if we already have a valid session (for backward compatibility)
        if not force_reauthentication and self._validate_session():
            self.session_valid = True
            return True

        # First, try to load existing session from file
        if self.session_file and not force_reauthentication:
            if self.__load_session_cookies():
                if self._validate_session():
                    self.session_valid = True
                    return True

        # If no valid session loaded, check if we have credentials
        if not self.username or not self.password:
            return False

        # Clear any existing session
        self.session_valid = False
        self.session.headers.pop("Authorization", None)

        try:
            config = create_angel_studios_config()
            config.request_timeout = self.timeout  # Use instance timeout
            store = InMemorySessionStore()
            core = AuthenticationCore(store, config, logger=self.log)
            result = core.authenticate(self.username, self.password)
            if result.success:
                # Set the token in session headers
                self.session.headers.update({"Authorization": f"Bearer {result.token}"})
                self.session_valid = True
                # Save cookies after successful auth
                self.__save_session_cookies()
                return True
        except (NetworkError, InvalidCredentialsError, AuthenticationError):
            self.log.error("Authentication failed", exc_info=True)
            try:
                self.session.close()  # Close session on failure for compatibility
            except Exception:
                pass  # Ignore close errors
            raise  # Re-raise for tests that expect exceptions
        return False

    def _validate_session(self):
        """Validate if the current session is still valid"""
        # Check if Authorization header exists and token is not expired
        auth_header = self.session.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):  # type: ignore
            return False

        token = auth_header.split(" ", 1)[1]  # type: ignore
        try:
            decoded = decode_jwt_payload(token)
            exp = decoded.get("exp")
            if exp:
                import time

                return exp > time.time()
        except Exception:
            pass
        return False

    def __load_session_cookies(self):
        """Load session cookies from file"""
        if not self.session_file:
            return False
        try:
            import os
            import pickle

            if os.path.exists(self.session_file):
                with open(self.session_file, "rb") as f:
                    loaded_cookies = pickle.load(f)
                # Set cookies in session
                self.session.cookies = loaded_cookies
                # Set Authorization header from JWT cookie if present
                jwt_cookie = self.session.cookies.get("angel_jwt")
                if jwt_cookie:
                    self.session.headers["Authorization"] = f"Bearer {jwt_cookie}"
                return True
        except Exception:
            pass
        return False

    def __save_session_cookies(self):
        """Save session cookies to file"""
        if not self.session_file:
            return
        try:
            import pickle

            with open(self.session_file, "wb") as f:
                pickle.dump(self.session.cookies, f)
        except Exception:
            pass

    def __clear_session_cache(self):
        """Clear session cache (stub for compatibility)"""
        if self.session_file:
            try:
                import os

                if os.path.exists(self.session_file):
                    os.remove(self.session_file)
                    return True
            except Exception:
                return False
        return True

    def __get_jwt_expiration_timestamp(self, token):
        """Extract expiration timestamp from JWT"""
        try:
            decoded = decode_jwt_payload(token)
            exp = decoded.get("exp")
            if exp is None:
                return None
            return exp
        except Exception:
            raise ValueError("Invalid JWT token")

    def get_session(self):
        """Get authenticated session"""
        if not self.session_valid:
            if not self.authenticate():
                raise Exception("Failed to authenticate")
        return self.session

    def get_session_details(self):
        """Return session diagnostics"""
        jwt_present = False
        login_email = self.username or "Unknown"
        account_id = None
        expires_in_seconds = None
        issued_at_local = None
        expires_at_local = None
        cookie_names = []

        if self.session:
            try:
                # Check Authorization header first
                auth_header = self.session.headers.get("Authorization")
                token = None
                if auth_header and auth_header.startswith("Bearer "):  # type: ignore
                    token = auth_header.split(" ", 1)[1]  # type: ignore
                    jwt_present = True

                # If no token in header, check cookies
                if not token:
                    jwt_cookie = self.session.cookies.get("angel_jwt")
                    if jwt_cookie:
                        token = jwt_cookie
                        jwt_present = True

                # Extract claims from token
                if token:
                    try:
                        decoded = decode_jwt_payload(token)
                        if "email" in decoded:
                            login_email = decoded["email"]
                        if "sub" in decoded:
                            account_id = decoded["sub"]
                        if "exp" in decoded:
                            import time

                            expires_in_seconds = decoded["exp"] - int(time.time())
                            expires_at_local = (
                                datetime.fromtimestamp(decoded["exp"], timezone.utc).astimezone().isoformat()
                            )
                        if "iat" in decoded:
                            issued_at_local = (
                                datetime.fromtimestamp(decoded["iat"], timezone.utc).astimezone().isoformat()
                            )
                    except Exception:
                        pass

                # Get cookie names
                try:
                    cookie_names = [cookie.name for cookie in self.session.cookies]
                except Exception:
                    cookie_names = []
            except Exception:
                # If session access fails, return defaults
                pass

        return {
            "login_email": login_email,
            "authenticated": self.session_valid,
            "session_file": self.session_file,
            "jwt_present": jwt_present,
            "cookie_names": cookie_names,
            "account_id": account_id,
            "expires_in_seconds": expires_in_seconds,
            "issued_at_local": issued_at_local,
            "expires_at_local": expires_at_local,
        }

    def logout(self):
        """Clear session"""
        self.session_valid = False
        if self.session:
            # Clear cookies and headers, ignoring errors for compatibility
            try:
                self.session.cookies.clear()
            except Exception:
                pass
            try:
                self.session.headers.pop("Authorization", None)
            except Exception:
                pass
            try:
                self.session.close()
            except Exception:
                pass  # Ignore close errors for compatibility
        self.session = requests.Session()

        # Clear session file if it exists
        cache_cleared = self.__clear_session_cache()

        return cache_cleared
