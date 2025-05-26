import requests
from bs4 import BeautifulSoup
import urllib.parse
import xbmc  # type: ignore


def get_authenticated_session(username: str = None, password: str = None):
    """
    Get a session object for making requests to the Angel.com API.
    """
    login_url = "https://www.angel.com/api/auth/login"
    session = requests.Session()
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
    state = next((inp.get('value') for inp in soup.find_all('input')
                  if inp.get('id') == 'state' and inp.get('name') == 'state'), None)

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
    for inp in soup.find_all('input'):
        if inp.get('id') == 'state' and inp.get('name') == 'state':
            state2 = inp.get('value')
        elif inp.get('name') == '_csrf_token':
            csrf_token = inp.get('value')

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
        redirect_response = session.get(redirect_url, allow_redirects=True)

        xbmc.log(f"{redirect_response.status_code=}", xbmc.LOGDEBUG)
        xbmc.log(f"{redirect_response.url=}", xbmc.LOGDEBUG)
        xbmc.log(f"{redirect_response.headers=}", xbmc.LOGDEBUG)
        if redirect_response.status_code == 200:
            xbmc.log("Login successful!", xbmc.LOGINFO)
            xbmc.log("Login step completed with 200 OK.", xbmc.LOGDEBUG)
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

    return session


