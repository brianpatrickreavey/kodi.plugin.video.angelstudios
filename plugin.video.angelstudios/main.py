# Copyright (C) 2025, Brian Patrick Reavey
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
Angel Studios Kodi addon - Clean, modular implementation
"""

import os
import sys
import json
from urllib.parse import parse_qsl, urlencode

import requests
import pickle

# Add resources/lib to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'resources/lib'))

from helpers import KodiLogger, get_session_file, create_plugin_url

import xbmc  # type: ignore
import xbmcaddon  # type: ignore
import xbmcplugin  # type: ignore
import xbmcgui  # type: ignore
import xbmcvfs  # type: ignore

from angel_interface import AngelStudiosInterface
from helpers import KodiLogger, get_session_file, create_plugin_url
from kodi_ui_interface import KodiUIInterface

# Plugin constants
URL = sys.argv[0]
HANDLE = int(sys.argv[1])
ADDON = xbmcaddon.Addon()

logger = KodiLogger()  # Create an instance of the logger class

ui_interface = KodiUIInterface(HANDLE, URL, logger=logger, angel_interface=None)

# Get credentials from addon settings once at module load
USERNAME = ADDON.getSetting('username')
PASSWORD = ADDON.getSetting('password')

def router(paramstring):
    """
    Router function that calls other functions based on the provided paramstring
    Main menu offers content browsing options and special menus mimicing the Angel.com website:
    - Series
    - Movies
    - Dry Bar Comedy Specials
    - Podcasts
    - Livestreams
    - Currently Watching
    - Savced/Favorites
    - All content
    """
    # Parse URL parameters
    params = dict(parse_qsl(paramstring))
    xbmc.log(f"Router called with params: {params}", xbmc.LOGINFO)

    try:
        # Route to appropriate function
        if not params:
            # Main entry point - show main menu with fresh authentication
            # xbmc.log("Fresh app load - forcing reauthentication", xbmc.LOGINFO) # TODO fix this
            # angel_studios_authentication.clear_session_cache()
            ui_interface.main_menu()
        else:
            # Subsequent navigation - use existing session if available
            if params['action'] == 'movies_menu':
                # Show movies
                ui_interface.projects_menu(content_type='movies')
            elif params['action'] == 'series_menu':
                # Show series
                ui_interface.projects_menu(content_type='series')
            elif params['action'] == 'specials_menu':
                # Show Dry Bar Comedy Specials
                ui_interface.projects_menu(content_type='specials')
            elif params['action'] == 'podcast_menu':
                # Show Podcasts
                ui_interface.projects_menu(content_type='podcasts')
            elif params['action'] == 'livestream_menu':
                # Show Livestreams
                ui_interface.projects_menu(content_type='livestreams')
            elif params['action'] == 'all_content_menu':
                # Show all content (except podcasts & livestreams)
                #all_content_menu()
                pass
            elif params['action'] == 'seasons_menu':
                # Show seasons for a project
                ui_interface.seasons_menu(params['content_type'], params['project_slug'])
            elif params['action'] == 'episodes_menu':
                # Show episodes for a season using individual parameters
                ui_interface.episodes_menu(params['content_type'], params['project_slug'], params['season_id'])
            elif params['action'] == 'play_episode':
                # Play an episode
                ui_interface.play_episode(params['episode_guid'], params['project_slug'])
            elif params['action'] == 'info':
                # Show info message for unavailable episodes
                message = params.get('message', 'This content is not available.')
                ui_interface.show_error(message)
            else:
                # Unknown action
                raise ValueError(f'Invalid action: {params.get("action", "unknown")}')

    except KeyError as e:
        xbmc.log(f"Missing required parameter: {e}", xbmc.LOGERROR)
        ui_interface.show_error(f"Missing parameter: {str(e)}")
    except Exception as e:
        xbmc.log(f"Router error: {e}", xbmc.LOGERROR)
        ui_interface.show_error(f"Navigation error: {str(e)}")

if __name__ == '__main__':
    try:
        if not USERNAME or not PASSWORD:
            # Show error if credentials are not set
            xbmcgui.Dialog().ok(
                "Configuration Error",
                "Please configure your Angel.com username and password in the addon settings."
            )
        else:
            # Call the router function with plugin parameters
            # Initialize Angel Studios authentication with session management

            # Get the query path for GraphQL queries (relatvie to the addon path)
            query_path = xbmcvfs.translatePath(
                ADDON.getAddonInfo('path') +
                '/resources/lib/angel_graphql/'
            )
            logger.info(f"Using query path: {query_path}")

            # Initialize Angel Studios interface with session management
            asi = AngelStudiosInterface(
                username=USERNAME,
                password=PASSWORD,
                session_file=get_session_file(),  # Use session file for persistent authentication
                logger=logger,
                query_path=query_path
            )
            # Initialize UI helper
            xbmc.log(f"Setting Angel Interface for Kodi UI {asi}", xbmc.LOGINFO)
            ui_interface.setAngelInterface(asi)

            # Call the router with parameters from the command line
            logger.info(f"Calling router with params: {sys.argv[2][1:]}")
            router(sys.argv[2][1:])

    except Exception as e:
        logger.error(f"Addon initialization error: {e}")
        ui_interface.show_error(f"Addon failed to start: {str(e)}")
