import requests
from bs4 import BeautifulSoup
from time import sleep
import urllib.parse
import json
import logging
# import xbmcgui
# import xbmcplugin

logger = logging.getLogger(__name__)

# Choose a logging level: logging.[INFO, DEBUG]
loglevel = logging.DEBUG
logging.basicConfig(level=loglevel)

# username = xbmcplugin.getSetting('username')
# password = xbmcplugin.getSetting('password')

with open('credentials.json') as f:
    credentials = json.load(f)
    username = credentials['username']
    password = credentials['password']

login_session = requests.session()
auth_domain = ''
auth_flow_start_url = 'https://www.angel.com/api/auth/login'
flow_page = login_session.get(auth_flow_start_url)
if flow_page.status_code == 200:
    logger.info("Successfully fetched the login page.")
    logger.debug(f"{flow_page.status_code=}")
else:
    logger.error(f"{flow_page.status_code=}")
    raise

cookies=flow_page.cookies
logger.debug(f"{cookies=}")

email_form_page_soup = BeautifulSoup(flow_page.content, "html.parser")

logger.debug(f"{email_form_page_soup=}")

state=None
for r_input in email_form_page_soup.find_all('input'):
    logger.debug(f"{r_input=}")
    if r_input.get('id') == 'state' and r_input.get('name') == 'state':
        state = r_input.get('value')

logger.debug(f"{state=}")

data = {
    'email': username,
    'state': state
}

encoded_data=urllib.parse.urlencode(data)
full_url = f"https://auth.angel.com/u/login/password?{encoded_data}"
logger.debug(f"{full_url=}")

response1 = login_session.get(full_url)

logger.debug(f"{response1.content=}")

soup2 = BeautifulSoup(response1.content, "html.parser")
state2 = None
csrf_token = None
for r_input in soup2.find_all('input'):
    logger.debug(f"{r_input=}")
    if r_input.get('id') == 'state' and r_input.get('name') == 'state':
        state2 = r_input.get('value')
    elif r_input.get('name') == '_csrf_token':
        csrf_token = r_input.get('value')

data2 = {
    'email': username,
    'password': password,
    'state': state2,
    '_csrf_token': csrf_token,
    'has_agreed': 'true'
}
logger.debug(json.dumps(data2, indent=2))

encoded2 = urllib.parse.urlencode({'state': state2})
post_url = f"https://auth.angel.com/u/login?{encoded2}"

logger.debug(f"{post_url=}")

response2 = login_session.post(post_url, data=data2, allow_redirects=False)
if response2.status_code in [302, 303]:
    redirect_url = response2.headers.get('Location')
    logger.info(f"Following redirect to: {redirect_url}")
    response3 = login_session.get(redirect_url, allow_redirects=True)
    logger.debug(f"{response3.status_code=}")
    logger.debug(f"{response3.url=}")
    logger.debug(f"{response3.headers=}")
elif response2.status_code == 200:
    logger.info("Login step completed with 200 OK.")
else:
    logger.error(f"Login failed: {response2.status_code} {response2.reason}")

html_for_soup = response3.content
soup3 = BeautifulSoup(html_for_soup, "html.parser")
raw_data = soup3.find(id="__NEXT_DATA__").string
with open('raw_data.json', 'w') as f:
    json.dump(json.loads(raw_data), f, indent=2)


tuttle_twins_url = 'https://www.angel.com/watch/tuttle-twins'
response4 = login_session.get(tuttle_twins_url)
if response4.status_code == 200:
    logger.info("Successfully fetched the Tuttle Twins page.")
    logger.debug(f"{response4.status_code=}")
else:
    logger.error(f"{response4.status_code=}")
    raise
soup4 = BeautifulSoup(response4.content, "html.parser")
show_data = json.loads(soup4.find(id="__NEXT_DATA__").string)
with open('project_tuttle_twins.json', 'w') as f:
    json.dump(show_data, f, indent=2)
    


# logger.debug(f"{response2.content=}")
# logger.debug(f"{response2.text=}")
# logger.debug(f"{response2.status_code=}")
# logger.debug(f"{response2.reason=}")
# logger.debug(f"{response2.url=}")
# logger.debug(f"{response2.headers=}")
# logger.debug(f"{response2.cookies=}")


