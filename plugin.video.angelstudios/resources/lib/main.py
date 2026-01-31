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

import sys
import os
import xbmcvfs  # type: ignore

# Ensure the dependencies directory is in the path for bundled dependencies
lib_path = os.path.join(os.path.dirname(__file__), '../dependencies')
sys.path.insert(0, lib_path)

from urllib.parse import parse_qsl

import xbmcaddon  # type: ignore
import xbmcgui  # type: ignore

from angel_interface import AngelStudiosInterface
from angel_authentication import AuthenticationCore, Auth0Config, KodiSessionStore
from kodi_utils import KodiLogger
from kodi_ui_interface import KodiUIInterface

# Ensure the dependencies directory is in the path for bundled dependencies
lib_path = os.path.join(os.path.dirname(__file__), '../dependencies')
sys.path.insert(0, lib_path)

# Plugin constants
URL = sys.argv[0]
HANDLE = int(sys.argv[1])
ADDON = xbmcaddon.Addon()

# Instantiate the logger with debug promotion settings
promote_all_debug = ADDON.getSettingBool("debug_promote_all")

# Define category-to-setting mapping
category_settings = {
    "art": "debug_art_promotion",
    "timing": "debug_timing_promotion",
    "api": "debug_api_promotion",
    "cache": "debug_cache_promotion",
}

# Load category promotions from settings
category_promotions = {}
for category, setting_id in category_settings.items():
    try:
        category_promotions[category] = ADDON.getSettingBool(setting_id)
    except Exception:
        category_promotions[category] = False

# Load general promotion settings
uncategorized_promotion = ADDON.getSettingBool("debug_uncategorized_promotion")
miscategorized_promotion = ADDON.getSettingBool("debug_miscategorized_promotion")

logger = KodiLogger(
    promote_all_debug=promote_all_debug,
    category_promotions=category_promotions,
    uncategorized_promotion=uncategorized_promotion,
    miscategorized_promotion=miscategorized_promotion,
)

# Create Angel Studios interface
angel_interface = None

# ui_interface will be created in main guard

# Get credentials from addon settings once at module load
USERNAME = ADDON.getSettingString("username")
PASSWORD = ADDON.getSettingString("password")
TIMEOUT = ADDON.getSettingInt("request_timeout")


def router(paramstring, ui_interface):
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
            elif params["action"] == "all_content_menu":
                # Show all content (except podcasts & livestreams)
                # all_content_menu()
                pass
            elif params["action"] == "seasons_menu":
                # Show seasons for a project
                ui_interface.seasons_menu(params["content_type"], params["project_slug"])
            elif params["action"] == "episodes_menu":
                # Show episodes for a season using individual parameters
                ui_interface.episodes_menu(params["content_type"], params["project_slug"], params.get("season_id"))
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
    logger.info(f"Addon invoked with argv: {sys.argv}")

    if not USERNAME or not PASSWORD:
        # Show error if credentials are not set
        xbmcgui.Dialog().ok(
            "Angel Studios",
            "Please configure your Angel.com username and password in the addon settings.",
        )
    else:
        # Initialize UI interface
        ui_interface = KodiUIInterface(HANDLE, URL, logger=logger, angel_interface=None)

        try:
            # Call the router function with plugin parameters
            # Initialize Angel Studios authentication with session management

            # Get the query path for GraphQL queries (relatvie to the addon path)
            query_path = xbmcvfs.translatePath(ADDON.getAddonInfo("path") + "/resources/lib/angel_graphql/")
            logger.info(f"Using query path: {query_path}")

            # Initialize AuthenticationCore with Kodi session store
            config = Auth0Config(
                base_url="https://www.angel.com",
                user_agent=None,
                request_timeout=TIMEOUT,
            )
            auth_core = AuthenticationCore(  # type: ignore
                session_store=KodiSessionStore(ADDON), config=config, logger=None
            )

            # Initialize Angel Studios interface with authentication core
            asi = AngelStudiosInterface(
                logger=logger,
                auth_core=auth_core,
                query_path=query_path,
                tracer=ui_interface.get_trace_callback(),
                timeout=TIMEOUT,
            )
            # Initialize UI helper
            logger.info(f"Setting Angel Interface for Kodi UI {asi}")
            ui_interface.setAngelInterface(asi)

            # Call the router with parameters from the command line
            logger.info(f"Calling router with params: {sys.argv[2][1:]}")
            router(sys.argv[2][1:], ui_interface)

        except Exception as e:
            logger.error(f"Addon initialization error: {e}")
            ui_interface.show_error(f"Addon failed to start: {str(e)}")
