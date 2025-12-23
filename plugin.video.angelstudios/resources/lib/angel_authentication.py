import logging
import os
import pickle
import sys
import requests
from bs4 import BeautifulSoup
import urllib.parse

class AngelStudioSession:
    """Class to handle Angel Studios authentication and session management"""
    def __init__(self, username=None, password=None, session_file=None, logger=None):
        self.username = username
        self.password = password
        self.session_file = session_file
        self.session = None
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
        """
        self.log.info("Getting authenticated session for Angel.com")

        if force_reauthentication:
            self.log.info("Forcing re-authentication and clearing session cache")
            self.__clear_session_cache()
            self.session = None
            self.session_valid = False

        if self.session:
            self.session_valid = self._validate_session()

        if self.session and self.session_valid:
            self.log.info("Session is already authenticated and valid.")
            return True
        elif not self.session or not self.session_valid:
            self.log.info("No valid session found, starting authentication flow.")
        else:
            self.log.warning(f"Unexpected state: session={self.session}, session_valid={self.session_valid}")
            raise Exception("Unexpected state in authentication flow")
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
        self.session.headers.update({
            'User-Agent': (
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                'AppleWebKit/537.36 (KHTML, like Gecko) '
                'Chrome/58.0.3029.110 Safari/537.3'
            )
        })

        # Step 1: Get login page
        login_page_response = self.session.get(login_url)
        if login_page_response.status_code != 200:
            self.log.error(f"Failed to fetch the login page: {login_page_response.status_code}")
            raise Exception("Failed to fetch the login page")
        self.log.info("Successfully fetched the login page.")
        self.log.info(f"Login page response: {login_page_response.status_code} {login_page_response.reason}")
        self.log.info(f"Login page headers: {login_page_response.headers}")
        self.log.info(f"Login page content: {login_page_response.content[:100]}...")  # Log first 100 chars for brevity
        self.log.info(f"Login page cookies: {self.session.cookies.get_dict()}")

        # Step 2: Parse state from login page
        soup = BeautifulSoup(login_page_response.content, "html.parser")

        with open('login_page_content.html', 'w') as f:
            f.write(str(login_page_response.content))

        state = self.session.cookies.get('angelSession', 'asdfasdf')
        for element in soup.find_all('input'):
            self.log.info(f"Found input element: {element}")
            if element.get('id') == 'state' and element.get('name') == 'state':
                state = element.get('value')

        email_payload = {'email': self.username, 'state': state}
        self.log.info(f"Email payload: {email_payload}")
        email_uri = f"{self.auth_url}/u/login/password?{urllib.parse.urlencode(email_payload)}"

        # Step 3: Get post-email page
        self.log.info(f"Fetching post-email page: {email_uri}")
        email_response = self.session.get(email_uri)
        if email_response.status_code != 200:
            self.log.error(f"Failed to fetch the post-email page: {email_response.status_code}")
            raise Exception("Failed to fetch the post-email page")
        self.log.info("Successfully fetched the post-email page.")

        # Step 4: Parse state and csrf_token from post-email page
        soup = BeautifulSoup(email_response.content, "html.parser")
        state2 = None
        csrf_token = None
        for input_element in soup.find_all('input'):
            if input_element.get('id') == 'state' and input_element.get('name') == 'state':
                state2 = input_element.get('value')
            elif input_element.get('name') == '_csrf_token':
                csrf_token = input_element.get('value')

        password_uri = f"{self.auth_url}/u/login?{urllib.parse.urlencode({'state': state2})}"
        password_payload = {
            'email': self.username,
            'password': self.password,
            'state': state2,
            '_csrf_token': csrf_token,
            'has_agreed': 'true'
        }

        # Step 5: Post password
        password_response = self.session.post(password_uri, data=password_payload, allow_redirects=False)
        if password_response.status_code in (302, 303):
            redirect_url = password_response.headers.get('Location')
            self.log.info(f"Following redirect to: {redirect_url}")
            # Follow the redirect - required to complete the login process
            redirect_response = self.session.get(redirect_url, allow_redirects=True)

            self.log.debug(f"{redirect_response.status_code=}")
            self.log.debug(f"{redirect_response.url=}")
            self.log.debug(f"{redirect_response.headers=}")
            if redirect_response.status_code == 200:
                self.log.info(f"Login successful!")
                self.log.debug(f"Login step completed with 200 OK.")
                self.log.info(f"Login step completed with {password_response.status_code} REDIRECT to {redirect_url}")
            else:
                self.log.error(f"Login failed after redirect: {redirect_response.status_code} {redirect_response.reason}")
                raise Exception("Login failed after redirect")
        elif password_response.status_code == 200:
            self.log.info("Login successful!")
            self.log.debug("Login step completed with 200 OK.")
        else:
            self.log.error(f"Login failed: {password_response.status_code} {password_response.reason}")
            raise Exception("Login failed")

        # Step 6: Check for error message in response
        soup = BeautifulSoup(password_response.content, "html.parser")
        if soup.find('div', class_='error-message'):
            self.log.error("Login failed: Invalid username or password")
            raise Exception("Login failed: Invalid username or password")

        # Step 7: Set JWT token in session headers
        """Extract JWT token from cookies and set up Authorization header for GraphQL requests"""
        # Look for the JWT token in cookies
        jwt_token = None
        for cookie in self.session.cookies:
            if cookie.name == 'angel_jwt':
                jwt_token = cookie.value
                self.log.debug(f"Found JWT token in cookies: {jwt_token[:10]}...")  # Log first 10 chars for brevity
                break

        if jwt_token:
            self.log.info("Found JWT token in cookies, setting Authorization header")
            # Set the Authorization header for all future requests
            self.session.headers.update({
                'Authorization': f'Bearer {jwt_token}'
            })
        else:
            self.log.warning("No JWT token found in cookies")
            # Remove any existing Authorization header
            self.session.headers.pop('Authorization', None)

        self.__save_session_cookies()

        return True

    def get_session(self):
        """
        Get an authenticated session for making requests to the Angel.com API.

        Returns:
            requests.Session: Authenticated session object
        """
        if not self.session:
            if not self.authenticate():
                raise Exception("Failed to authenticate and create a valid session")
        return self.session

    def _validate_session(self):
        """Check if the current session is valid"""
        try:
            response = self.session.get(f"{self.web_url}/account", timeout=15)
            return response.status_code == 200
        except requests.RequestException as e:
            # TODO: more specific error handling - check for timeouts specifically
            self.log.error(f"Session validation failed: {e}")
            return False

    def __load_session_cookies(self):
        if self.session_file:
            try:
                with open(self.session_file, 'rb') as f:
                    self.session.cookies.update(pickle.load(f))
            except FileNotFoundError:
                return False
            try:
                jwt_token = None
                for cookie in self.session.cookies:
                    if cookie.name == 'angel_jwt':
                        jwt_token = cookie.value
                        self.log.info(f"Loaded JWT token from cookies: {jwt_token[:10]}...")
                        break

                if jwt_token:
                    self.session.headers.update({
                        'Authorization': f'Bearer {jwt_token}'
                    })
                    self.log.info("Session cookies loaded successfully.")
                else:
                    self.log.warning("No JWT token found in loaded cookies.")
                return True
            except Exception as e:
                self.log.error(f"Error loading jwt token from cookies: {e}")
                return False
        return False

    def __save_session_cookies(self):
        with open(self.session_file, 'wb') as f:
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
