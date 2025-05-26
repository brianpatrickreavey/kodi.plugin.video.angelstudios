import os
import pickle
import requests
from bs4 import BeautifulSoup
import urllib.parse
import xbmc       # type: ignore
import xbmcaddon  # type: ignore
import xbmcvfs    # type: ignore


def get_session_file():
    addon = xbmcaddon.Addon()
    addon_id = addon.getAddonInfo('id')
    cache_dir = xbmcvfs.translatePath(f'special://profile/addon_data/{addon_id}/')
    if not xbmcvfs.exists(cache_dir):
        xbmcvfs.mkdirs(cache_dir)
    return os.path.join(cache_dir, 'angel_session.pkl')


def save_session_cookies(session):
    session_file = get_session_file()
    with open(session_file, 'wb') as f:
        pickle.dump(session.cookies, f)


def load_session_cookies(session):
    session_file = get_session_file()
    try:
        with open(session_file, 'rb') as f:
            session.cookies.update(pickle.load(f))
        return True
    except FileNotFoundError:
        return False


def get_authenticated_session(username: str = None, password: str = None):
    """
    Get a session object for making requests to the Angel.com API.
    """
    xbmc.log("Getting authenticated session for Angel.com", xbmc.LOGINFO)
    session = requests.Session()
    if load_session_cookies(session):
        xbmc.log("Loaded session cookies from file.", xbmc.LOGINFO)
        if is_session_valid(session):
            xbmc.log("Session is valid, returning existing session.", xbmc.LOGINFO)
            return session
        else:
            xbmc.log("Session is invalid, starting new authentication flow.", xbmc.LOGINFO)
    else:
        xbmc.log("No session cookies found, starting new authentication flow.", xbmc.LOGINFO)

    login_url = "https://www.angel.com/api/auth/login"
    session.headers.update({
        'User-Agent': (
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
            'AppleWebKit/537.36 (KHTML, like Gecko) '
            'Chrome/58.0.3029.110 Safari/537.3'
        )
    })

    # Step 1: Get login page
    login_page_response = session.get(login_url)
    if login_page_response.status_code != 200:
        xbmc.log(f"Failed to fetch the login page: {login_page_response.status_code}", xbmc.LOGERROR)
        raise Exception("Failed to fetch the login page")
    xbmc.log("Successfully fetched the login page.", xbmc.LOGINFO)

    # Step 2: Parse state from login page
    soup = BeautifulSoup(login_page_response.content, "html.parser")
    state = next((input_element.get('value') for input_element in soup.find_all('input')
                  if input_element.get('id') == 'state' and input_element.get('name') == 'state'), None)

    email_payload = {'email': username, 'state': state}
    xbmc.log(f"Email payload: {email_payload}", xbmc.LOGDEBUG)
    email_uri = f"https://auth.angel.com/u/login/password?{urllib.parse.urlencode(email_payload)}"

    # Step 3: Get post-email page
    email_response = session.get(email_uri)
    if email_response.status_code != 200:
        xbmc.log(f"Failed to fetch the post-email page: {email_response.status_code}", xbmc.LOGERROR)
        raise Exception("Failed to fetch the post-email page")
    xbmc.log("Successfully fetched the post-email page.", xbmc.LOGINFO)

    # Step 4: Parse state and csrf_token from post-email page
    soup = BeautifulSoup(email_response.content, "html.parser")
    state2 = None
    csrf_token = None
    for input_element in soup.find_all('input'):
        if input_element.get('id') == 'state' and input_element.get('name') == 'state':
            state2 = input_element.get('value')
        elif input_element.get('name') == '_csrf_token':
            csrf_token = input_element.get('value')

    password_uri = f"https://auth.angel.com/u/login?{urllib.parse.urlencode({'state': state2})}"
    password_payload = {
        'email': username,
        'password': password,
        'state': state2,
        '_csrf_token': csrf_token,
        'has_agreed': 'true'
    }

    # Step 5: Post password
    password_response = session.post(password_uri, data=password_payload, allow_redirects=False)
    if password_response.status_code in (302, 303):
        redirect_url = password_response.headers.get('Location')
        xbmc.log(f"Following redirect to: {redirect_url}", xbmc.LOGINFO)
        # Follow the redirect - required to complete the login process
        redirect_response = session.get(redirect_url, allow_redirects=True)

        xbmc.log(f"{redirect_response.status_code=}", xbmc.LOGDEBUG)
        xbmc.log(f"{redirect_response.url=}", xbmc.LOGDEBUG)
        xbmc.log(f"{redirect_response.headers=}", xbmc.LOGDEBUG)
        if redirect_response.status_code == 200:
            xbmc.log(f"Login successful!", xbmc.LOGINFO)
            xbmc.log(f"Login step completed with 200 OK.", xbmc.LOGDEBUG)
            xbmc.log(f"Login step completed with {password_response.status_code} REDIRECT to {redirect_url}", xbmc.LOGINFO)
        else:
            xbmc.log(f"Login failed after redirect: {redirect_response.status_code} {redirect_response.reason}", xbmc.LOGERROR)
            raise Exception("Login failed after redirect")
    elif password_response.status_code == 200:
        xbmc.log("Login successful!", xbmc.LOGINFO)
        xbmc.log("Login step completed with 200 OK.", xbmc.LOGDEBUG)
    else:
        xbmc.log(f"Login failed: {password_response.status_code} {password_response.reason}", xbmc.LOGERROR)
        raise Exception("Login failed")

    # Step 6: Check for error message in response
    soup = BeautifulSoup(password_response.content, "html.parser")
    if soup.find('div', class_='error-message'):
        raise Exception("Login failed: Invalid username or password")

    save_session_cookies(session)
    return session


def is_session_valid(session):
    """Check if the current session is still authenticated."""
    test_url = "https://www.angel.com/account"
    resp = session.get(test_url, allow_redirects=False)
    if resp.status_code in (401, 403):
        xbmc.log("Session is invalid: Unauthorized or Forbidden", xbmc.LOGINFO)
        return False
    # Check for redirect to login
    if resp.status_code in (302, 303):
        location = resp.headers.get('Location', '')
        if 'login' in location:
            xbmc.log("Session is invalid: Redirected to login page", xbmc.LOGINFO)
            return False
    # Optionally, check page content for login form
    #if "Sign In" in resp.text or "Log In" in resp.text:
    #    xbmc.log("Session is invalid: Login form found in response", xbmc.LOGINFO)
    #    return False
    return True


