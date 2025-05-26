# Copyright (C) 2023, Roman V. M.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""
Example video plugin that is compatible with Kodi 20.x "Nexus" and above
"""
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'resources/lib'))

from urllib.parse import urlencode, parse_qsl
import hashlib

import xbmc # type: ignore
import xbmcgui # type: ignore
import xbmcplugin # type: ignore
from xbmcaddon import Addon # type: ignore
from xbmcvfs import translatePath # type: ignore

import requests
import bs4
import json

import authenticate

# Get the plugin url in plugin:// notation.
URL = sys.argv[0]
# Get a plugin handle as an integer number.
HANDLE = int(sys.argv[1])
# Get addon base path
ADDON_PATH = translatePath(Addon().getAddonInfo('path'))
ICONS_DIR = os.path.join(ADDON_PATH, 'resources', 'images', 'icons')
FANART_DIR = os.path.join(ADDON_PATH, 'resources', 'images', 'fanart')
POSTER_DIR = os.path.join(ADDON_PATH, 'resources', 'images', 'posters')

# Get the addon settings
angel_username = Addon().getSetting('username')
angel_password = Addon().getSetting('password')

# Hash the password with SHA-256
hashed_password = hashlib.sha256(angel_password.encode('utf-8')).hexdigest()
xbmc.log(f"username: {angel_username}, hashed_password: {hashed_password}", xbmc.LOGINFO)

session = authenticate.get_authenticated_session(
    username=angel_username,
    password=angel_password,
)


'We need: Login, and Whole Site'

"""
Copy Watch Menue (What's in Watch dropdown, don't copy + paste)

"""


'''
seasons = [
    'name': 'name of season'
    'season_number': 'number of season'
    'poster': 'season image'
    'description': 'overall description'
    'episodes' : [
        {
        'name': 'name of the episode',
        'subtitle': 'subtitle of the episode',
        'description': 'episode plot',
        'url': 'episode link',
        'thumbnail': 'episode image',
        }
    ]
]'''



# seasons = []
# for raw_season in raw_data['props']['pageProps']['projectData']['seasons']:
#     season = {
#         'name': raw_season['name'],
#         'season_number': raw_season['episodes'][0]['seasonNumber'],
#         'poster': f"{POSTER_DIR}/TT_{raw_season['name'].replace(' ', '')}_Poster.jpg",
#         'description': raw_data['props']['pageProps']['catalogTitle']['description']['long'],
#         'episodes': None
#     }

#     episodes = []
#     for raw_episode in raw_season['episodes']:
#        # xmbcplugin.log(raw_episode['subtitle'])
#         #xmbcplugin.log(raw_episode['source']['url'])
#         if raw_episode['source']== None:
#             continue            
#         elif raw_episode['source']['url'] == None:
#             continue       
#         # find out how to use 'continue' to skip episodes
#         episode = {
#             'episode_name': raw_episode['name'],
#             'title': raw_episode['subtitle'],
#             # The full name of the episode:
#             'name': f"{raw_episode['name']}: {raw_episode['subtitle']}",
#             'episode_number': raw_episode['episodeNumber'],
#             'poster': f"https://images.angelstudios.com/image/upload/f_auto/q_auto/{raw_episode['posterLandscapeCloudinaryPath']}.jpg",
#             'url': raw_episode['source']['url'],
#             'description': raw_episode['description'],
#         } 
#         episodes.append(episode)
#         season['episodes'] = episodes
#     seasons.append(season)

# print(json.dumps(seasons, indent=2))


def get_url(**kwargs):
    """
    Create a URL for calling the plugin recursively from the given set of keyword arguments.

    :param kwargs: "argument=value" pairs
    :return: plugin call URL
    :rtype: str
    """
    return '{}?{}'.format(URL, urlencode(kwargs))


def get_projects(main_url):
    response = session.get(main_url)  # changed from requests.get
    soup = bs4.BeautifulSoup(response.content, 'html.parser')
    angeldata = json.loads(soup.find(id="__NEXT_DATA__").string)

    projects ={}
    for project_data in angeldata['props']['pageProps']['pageDataContext']['start-watching']:
    # for project_guid in angeldata['props']['pageProps']['pageDataContext']['title-map']:
        # project_data = angeldata['props']['pageProps']['pageDataContext']['title-map'][project_guid]
        # if project_data['brand']['name'] == 'Dry Bar Comedy':
        #     xbmc.log(f"skipping Drybar - {project_name}", xbmc.LOGINFO)
        #     continue
        # project_name = project_data['title']
        # project_slug = None
        # for external_id in project_data['externalIds']:
        #     if external_id['source'] == 'hydra_project_slug':
        #         project_slug = external_id['id']
        # if not project_slug:
        #     xbmc.log(f"hydra project slug not found for {project_name}", xbmc.LOGINFO)
        #     continue
        # project_url = f"https://www.angel.com/watch/{project_slug}"
        
        project_name = project_data['name']
        project_slug = project_data['track']['payload']['projectSlug']
        project_url = f"https://www.angel.com/watch/{project_slug}"
        project_guid = project_data['track']['payload']['guid']
        project_description = None
        if project_guid in angeldata['props']['pageProps']['pageDataContext']['title-map']:
            project_description = angeldata['props']['pageProps']['pageDataContext']['title-map'][project_guid]['description']['long']
        else:
            xbmc.log(f"guid not found for {project_name}", xbmc.LOGDEBUG)
        print(f"{project_name} - {project_url}")
        projects[project_slug] = {
                'name': project_name,
                'project_url': project_url,
                'description': project_description,
                'poster': f"https://images.angelstudios.com/image/upload/f_auto/q_auto/{project_data['metadata']['project']['discoveryPosterCloudinaryPath']}.jpg",
                'fanart': f"https://images.angelstudios.com/image/upload/f_auto/q_auto/{project_data['metadata']['project']['discoveryPosterLandscapeCloudinaryPath']}.jpg",
                'icon': f"https://images.angelstudios.com/image/upload/f_auto/q_auto/{project_data['metadata']['project']['logoCloudinaryPath']}.jpg",
                'logo': f"https://images.angelstudios.com/image/upload/f_auto/q_auto/{project_data['metadata']['project']['logoCloudinaryPath']}.jpg"
            }

    # sort projects by slug:
    project_slugs = list(projects.keys())
    project_slugs.sort()
    for project_slug in project_slugs:
        xbmc.log(f"project: {project_slug}, name: {projects[project_slug]['name'], }", xbmc.LOGINFO)
        
    return projects

def get_seasons(project_url):
    response = session.get(project_url)  # changed from requests.get
    soup = bs4.BeautifulSoup(response.content, 'html.parser')
    show_data = json.loads(soup.find(id="__NEXT_DATA__").string)

    seasons = []
    for raw_season in show_data['props']['pageProps']['projectData']['seasons']:
        # if show_data['props']['pageProps']['catalogTitle'] == None:
        #     project_description = raw_season['name']
        # else:
        #     project_description = show_data['props']['pageProps']['catalogTitle']['description']['long']
        
        season = {
            'name': raw_season['name'],
            'season_number': raw_season['episodes'][0]['seasonNumber'],
            'poster': f"https://images.angelstudios.com/image/upload/f_auto/q_auto/{show_data['props']['pageProps']['projectData']['discoveryPosterLandscapeCloudinaryPath']}.jpg",
            # 'description': project_description,
            'episodes': None
            ### We need to build all the episodes here, or call the URL again in the "get_episodes" function
        }

        episodes = []
        for raw_episode in raw_season['episodes']:
        # xmbcplugin.log(raw_episode['subtitle'])
            #xmbcplugin.log(raw_episode['source']['url'])
            if raw_episode['source'] == None:
                xbmc.log(f"Skipping episode {raw_episode['name']} - no source", xbmc.LOGINFO)
                xbmc.log(f"raw_episode: {raw_episode}", xbmc.LOGDEBUG)
                continue
            elif raw_episode['source']['url'] == None:
                xbmc.log(f"Skipping episode {raw_episode['name']} - no URL", xbmc.LOGINFO)
                xbmc.log(f"raw_episode: {raw_episode}", xbmc.LOGDEBUG)
                continue       
            # find out how to use 'continue' to skip episodes
            episode = {
                'episode_name': raw_episode['name'],
                'title': raw_episode['subtitle'],
                # The full name of the episode:
                'name': f"{raw_episode['name']}: {raw_episode['subtitle']}",
                'episode_number': raw_episode['episodeNumber'],
                'poster': f"https://images.angelstudios.com/image/upload/f_auto/q_auto/{raw_episode['posterCloudinaryPath']}.jpg",
                'fanart': f"https://images.angelstudios.com/image/upload/f_auto/q_auto/{raw_episode['posterLandscapeCloudinaryPath']}.jpg",
                'url': raw_episode['source']['url'],
                'description': raw_episode['description'],
            } 
            episodes.append(episode)
            season['episodes'] = episodes
        seasons.append(season)
    return seasons

def get_episodes(raw_season):
    """
    Get the list of videofiles/streams.

    Here you can insert some code that retrieves
    the list of video streams in the given section from some site or API.

    :param genre_index: genre index
    :type genre_index: int
    :return: the list of videos in the category
    :rtype: list
    """

    # TODO This needs to make a call to the tager stub page to get all of the episodes some other way
    # It does not seem that the __NEXT_DATA__ contains all of the episodes.
    # Stub page also does not contain the episodes at all within NEXT_DATA.
    # Nees to use BeautifulSoup to parse the page and get the episodes.

    # episodes = []
    # xbmc.log(f"{raw_season=}", xbmc.LOGINFO)
    # for raw_episode in raw_season['episodes']:
    #    # xmbcplugin.log(raw_episode['subtitle'])
    #     #xmbcplugin.log(raw_episode['source']['url'])
    #     if raw_episode['source']== None:
    #         continue            
    #     elif raw_episode['source']['url'] == None:
    #         continue       
    #     # find out how to use 'continue' to skip episodes
    #     episode = {
    #         'episode_name': raw_episode['name'],
    #         'title': raw_episode['subtitle'],
    #         # The full name of the episode:
    #         'name': f"{raw_episode['name']}: {raw_episode['subtitle']}",
    #         'episode_number': raw_episode['episodeNumber'],
    #         'poster': f"https://images.angelstudios.com/image/upload/f_auto/q_auto/{raw_episode['posterLandscapeCloudinaryPath']}.jpg",
    #         'url': raw_episode['source']['url'],
    #         'description': raw_episode['description'],
    #     } 
    #     episodes.append(episode)
        # season['episodes'] = episodes
    
    return raw_season

def list_projects():
    """
    List the projects in KODI with the project attributes
    If a project is selected, call 'list_seasons' with the URL of the project.
    """
    xbmcplugin.setContent(HANDLE, 'tvshows')
    # We should sort this alphabetically
    projects = get_projects("https://www.angel.com/watch/")
    project_keys = list(projects.keys())
    project_keys.sort()
    for project_key in project_keys:
        project = projects[project_key]
        # start a new project item
        xbmcplugin.setPluginCategory(HANDLE, project['name'])
        list_item = xbmcgui.ListItem(label=project['name'])
        # Add infotags to the item
        info_tag = list_item.getVideoInfoTag()
        info_tag.setMediaType('project')
        info_tag.setTitle(project['name'])
        info_tag.setPlot(project['description'])
        # Add art to the item
        list_item.setArt(
            {
                'poster': project['poster'],
                'fanart': project['fanart'],
                'icon': project['icon'],
                'clearlogo': project['logo']
            }
        )
        url = get_url(action='list_seasons', project_url=project['project_url'])
        is_folder = True
        # Add the item to the directory
        xbmcplugin.addDirectoryItem(HANDLE, url, list_item, is_folder)
    xbmcplugin.addSortMethod(HANDLE, xbmcplugin.SORT_METHOD_PLAYLIST_ORDER)
    xbmcplugin.endOfDirectory(HANDLE)


def list_seasons(project_url):
    xbmcplugin.setContent(HANDLE, 'tvshows')
    xbmc.log(f"{project_url=}", xbmc.LOGINFO)
    # project = json.loads(project_string)
    seasons = get_seasons(project_url)
    if len(seasons) == 1:
        list_episodes(json.dumps(seasons[0]))
    else:  
        for index, season in enumerate(seasons):
            xbmcplugin.setPluginCategory(HANDLE, season['name'])
            list_item = xbmcgui.ListItem(label=season['name'])
            info_tag = list_item.getVideoInfoTag()
            info_tag.setMediaType('season')
            info_tag.setTitle(season['name'])
            # info_tag.setPlot(season['description'])
            list_item.setArt({'poster': season['poster'], 'fanart': season['poster']})
            url = get_url(action='list_episodes', season=json.dumps(season))
            is_folder = True
            xbmcplugin.addDirectoryItem(HANDLE, url, list_item, is_folder)
        xbmcplugin.addSortMethod(HANDLE, xbmcplugin.SORT_METHOD_PLAYLIST_ORDER)
        xbmcplugin.endOfDirectory(HANDLE)



def list_episodes(season):
    """
    Create the list of playable videos in the Kodi interface.

    :param genre_index: the index of genre in the list of movie genres
    :type genre_index: int
    """

    season_info = get_episodes(json.loads(season))


    # Set plugin category. It is displayed in some skins as the name
    # of the current section.
    xbmcplugin.setPluginCategory(HANDLE, season_info['name'])
    # Set plugin content. It allows Kodi to select appropriate views
    # for this type of content.
    xbmcplugin.setContent(HANDLE, 'tvshows',)
    # Get the list of videos in the category.
    episodes = season_info['episodes']
    # Iterate through videos.
    for episode in episodes:
        # Create a list item with a text label
        list_item = xbmcgui.ListItem(label=episode['name'])
        xbmc.log(f"Adding episode: {episode['name']}", xbmc.LOGINFO)
        # Set graphics (thumbnail, fanart, banner, poster, landscape etc.) for the list item.
        # Here we use only poster for simplicity's sake.
        # In a real-life plugin you may need to set multiple image types.
        list_item.setArt(
            {
                'poster': episode['poster'],
                'fanart': episode['fanart'],
            }
        )
        # Set additional info for the list item via InfoTag.
        # 'mediatype' is needed for skin to display info for this ListItem correctly.
        info_tag = list_item.getVideoInfoTag()
        info_tag.setMediaType('episode')
        info_tag.setTitle(episode['name'])
        # info_tag.setSeasons([season_info['name']])
        info_tag.setPlot(episode['description'])
        # info_tag.setYear(video['year'])
        # Set 'IsPlayable' property to 'true'.
        # This is mandatory for playable items!
        list_item.setProperty('IsPlayable', 'true')
        # Create a URL for a plugin recursive call.
        url = get_url(action='play', episode=episode['url'])
        # Add the list item to a virtual Kodi folder.
        # is_folder = False means that this item won't open any sub-list.
        is_folder = False
        # Add our item to the Kodi virtual folder listing.
        xbmcplugin.addDirectoryItem(HANDLE, url, list_item, is_folder)
    # Add sort methods for the virtual folder items
    xbmcplugin.addSortMethod(HANDLE, xbmcplugin.SORT_METHOD_LABEL_IGNORE_THE)
    xbmcplugin.addSortMethod(HANDLE, xbmcplugin.SORT_METHOD_VIDEO_YEAR)
    # Finish creating a virtual folder.
    xbmcplugin.endOfDirectory(HANDLE)


def play_episode(path):
    """
    Play a video by the provided path.

    :param path: Fully-qualified video URL
    :type path: str
    """
    # Create a playable item with a path to play.
    # offscreen=True means that the list item is not meant for displaying,
    # only to pass info to the Kodi player
    play_item = xbmcgui.ListItem(offscreen=True)
    play_item.setPath(path)
    # Pass the item to the Kodi player.
    xbmcplugin.setResolvedUrl(HANDLE, True, listitem=play_item)


def router(paramstring):
    """
    Router function that calls other functions
    depending on the provided paramstring

    :param paramstring: URL encoded plugin paramstring
    :type paramstring: str
    """
    # Parse a URL-encoded paramstring to the dictionary of
    # {<parameter>: <value>} elements
    params = dict(parse_qsl(paramstring))
    xbmc.log(f"ROUTER params={params}", xbmc.LOGINFO)
    # Check the parameters passed to the plugin
    if not params:
        # If the plugin is called from Kodi UI without any parameters,
        # display the list of Angel Projects
        list_projects()
    elif params['action'] == 'list_seasons':
        list_seasons(params['project_url'])
    elif params['action'] == 'list_episodes':
        # Display the list of videos in a provided category.
        list_episodes(params['season'])
    elif params['action'] == 'play':
        # Play a video from a provided URL.
        play_episode(params['episode'])
    else:
        # If the provided paramstring does not contain a supported action
        # we raise an exception. This helps to catch coding errors,
        # e.g. typos in action names.
        raise ValueError(f'Invalid paramstring: {paramstring}!')


if __name__ == '__main__':
    # Call the router function and pass the plugin call parameters to it.
    # We use string slicing to trim the leading '?' from the plugin call paramstring
    router(sys.argv[2][1:])
