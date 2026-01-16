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
from urllib.parse import parse_qsl

import xbmcaddon  # type: ignore
import xbmcgui  # type: ignore
import xbmcvfs  # type: ignore

from angel_interface import AngelStudiosInterface
from kodi_utils import KodiLogger, get_session_file
from kodi_ui_interface import KodiUIInterface

# Plugin constants
URL = sys.argv[0]
HANDLE = int(sys.argv[1])
ADDON = xbmcaddon.Addon()

# Instantiate the logger in debug-promotion mode if debug_mode is either 'debug' or 'trace'
debug_mode = (ADDON.getSettingString("debug_mode") or "off").lower()
debug_promotion = debug_mode in {"debug", "trace"}
logger = KodiLogger(debug_promotion=debug_promotion)

ui_interface = KodiUIInterface(HANDLE, URL, logger=logger, angel_interface=None)

# Get credentials from addon settings once at module load
USERNAME = ADDON.getSettingString("username")
PASSWORD = ADDON.getSettingString("password")


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
    logger.info(f"Router called with params: {params}")

    try:
        # Route to appropriate function
        if not params:
            # Main entry point - show main menu with fresh authentication
            # xbmc.log("Fresh app load - forcing reauthentication", xbmc.LOGINFO) # TODO fix this
            # angel_studios_authentication.clear_session_cache()
            ui_interface.main_menu()
        else:
            # Subsequent navigation - use existing session if available
            if params["action"] == "movies_menu":
                # Show movies
                ui_interface.projects_menu(content_type="movies")
            elif params["action"] == "series_menu":
                # Show series
                ui_interface.projects_menu(content_type="series")
            elif params["action"] == "specials_menu":
                # Show Dry Bar Comedy Specials
                ui_interface.projects_menu(content_type="specials")
            elif params["action"] == "podcast_menu":
                # Show Podcasts
                ui_interface.projects_menu(content_type="podcasts")
            elif params["action"] == "livestream_menu":
                # Show Livestreams
                ui_interface.projects_menu(content_type="livestreams")
            elif params["action"] == "watchlist_menu":
                # Show Watchlist (placeholder)
                ui_interface.watchlist_menu()
            elif params["action"] == "continue_watching_menu":
                # Show Continue Watching with optional pagination cursor
                after = params.get("after")
                ui_interface.continue_watching_menu(after=after)
            elif params["action"] == "top_picks_menu":
                # Show Top Picks (placeholder)
                ui_interface.top_picks_menu()
            elif params["action"] == "other_content_menu":
                # Show Other Content (placeholder)
                ui_interface.other_content_menu()
            elif params["action"] == "all_content_menu":
                # Show all content (except podcasts & livestreams)
                # all_content_menu()
                pass
            elif params["action"] == "seasons_menu":
                # Show seasons for a project
                ui_interface.seasons_menu(params["content_type"], params["project_slug"])
            elif params["action"] == "episodes_menu":
                # Show episodes for a season using individual parameters
                ui_interface.episodes_menu(params["content_type"], params["project_slug"], params["season_id"])
            elif params["action"] == "play_episode":
                # Play an episode
                ui_interface.play_episode(params["episode_guid"], params["project_slug"])
            elif params["action"] == "info":
                # Show info message for unavailable episodes
                message = params.get("message", "This content is not available.")
                ui_interface.show_error(message)
            elif params["action"] == "settings":
                # Open addon settings dialog
                ADDON.openSettings()
            elif params["action"] == "clear_cache":
                logger.info("Settings: clear_cache button pressed")
                ui_interface.clear_cache_with_notification()
            elif params["action"] == "force_logout":
                logger.info("Settings: force_logout button pressed")
                ui_interface.force_logout_with_notification()
            elif params["action"] == "clear_debug_data":
                logger.info("Settings: clear_debug_data button pressed")
                ui_interface.clear_debug_data_with_notification()
            elif params["action"] == "show_information":
                ui_interface.show_auth_details_dialog()
            else:
                # Unknown action
                raise ValueError(f'Invalid action: {params.get("action", "unknown")}')

    except KeyError as e:
        logger.error(f"Missing required parameter: {e}")
        ui_interface.show_error(f"Missing parameter: {str(e)}")
    except Exception as e:
        logger.error(f"Router error: {e}")
        ui_interface.show_error(f"Navigation error: {str(e)}")


if __name__ == "__main__":
    try:
        logger.info(f"Addon invoked with argv: {sys.argv}")

        if not USERNAME or not PASSWORD:
            # Show error if credentials are not set
            xbmcgui.Dialog().ok(
                "Angel Studios",
                "Please configure your Angel.com username and password in the addon settings.",
            )
        else:
            # Call the router function with plugin parameters
            # Initialize Angel Studios authentication with session management

            # Get the query path for GraphQL queries (relatvie to the addon path)
            query_path = xbmcvfs.translatePath(ADDON.getAddonInfo("path") + "/resources/lib/angel_graphql/")
            logger.info(f"Using query path: {query_path}")

            # Initialize Angel Studios interface with session management
            asi = AngelStudiosInterface(
                username=USERNAME,
                password=PASSWORD,
                session_file=get_session_file(),  # Use session file for persistent authentication
                logger=logger,
                query_path=query_path,
                tracer=ui_interface.get_trace_callback(),
            )
            # Initialize UI helper
            logger.info(f"Setting Angel Interface for Kodi UI {asi}")
            ui_interface.setAngelInterface(asi)

            # Call the router with parameters from the command line
            logger.info(f"Calling router with params: {sys.argv[2][1:]}")
            router(sys.argv[2][1:])

    except Exception as e:
        logger.error(f"Addon initialization error: {e}")
        ui_interface.show_error(f"Addon failed to start: {str(e)}")
