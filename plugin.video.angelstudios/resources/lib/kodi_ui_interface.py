"""
Kodi UI helper functions for Angel Studios addon.
Handles all Kodi-specific UI operations and list item creation.
"""

import json
from urllib.parse import urlencode
from datetime import timedelta

import xbmc  # type: ignore
import xbmcgui  # type: ignore
import xbmcplugin  # type: ignore
import xbmcvfs  # type: ignore

from simplecache import SimpleCache  # type: ignore

angel_menu_content_mapper = {
    'movies': 'movie',
    'series': 'series',
    'specials': 'special'
}

# Map Angel Studios content types to Kodi content types
kodi_content_mapper = {
    'movies': 'movies',
    'series': 'tvshows',
    'special': 'videos',    # Specials are treated as generic videos
    'podcast': 'videos',    # Podcasts are also generic videos
    'livestream': 'videos'  # Livestreams are generic videos
}

class KodiUIInterface:
    """Helper class for Kodi UI operations"""

    def __init__(self, handle, url, logger, angel_interface):
        '''
        Initialize the Kodi UI interface.
        '''
        self.handle = handle
        self.kodi_url = url
        self.log = logger
        self.angel_interface = angel_interface
        self.cache = SimpleCache()  # Initialize cache

        # Log initialization
        self.log.info("KodiUIInterface initialized")
        self.log.debug(f"{self.handle=}, {self.kodi_url=}")

        # Main menu options
        # Process Movies, TV Shows, and Specials first
        self.menu_items = [
            {
                'label': 'Movies',
                'content_type': 'movie', # standard Kodi type for movies
                'action': 'movies_menu',
                'description': 'Browse standalone movies and films'
            },
            {
                'label': 'Series',
                'content_type': 'tvshow', # standard Kodi type for series
                'action': 'series_menu',
                'description': 'Browse series with multiple episodes'
            },
            {
                # Dry Bar Comedy Specials are listed as "specials" in Angel Studios.
                # Code assumes all "specials" are Dry Bar Comedy Specials.
                # If this ever changes, this section will need updating.
                'label': 'Dry Bar Comedy Specials',
                'content_type': 'video', # specials are treated as generic video content
                'action': 'specials_menu',
                'description': 'Browse Dry Bar Comedy Specials'
            },
            {
                'label': 'Podcasts',
                'content_type': 'video', # podcasts are treated as generic video content
                'action': 'podcasts_menu',
                'description': f'Browse Podcast content'
            },
            {
                'label': 'Livestreams',
                'content_type': 'video', # livestreams are also generic video content
                'action': 'livestreams_menu',
                'description': f'Browse Livestream content'
            },
            {
                'label': 'Continue Watching',
                'content_type': 'video', # currently watching is generic video content
                'action': 'continue_watching_menu',
                'description': 'Continue watching your in-progress content'
            },
            {
                'label': 'Top Picks For You',
                'content_type': 'video', # generic video content
                'action': 'top_picks_menu',
                'description': 'Browse top picks for you'
            },
            {
                'label': 'Other Content',
                'content_type': 'video', # generic video content
                'action': 'other_content_menu',
                'description': 'Other content types not categorized above'
            }
        ]

    def setAngelInterface(self, angel_interface):
        '''Set the Angel Studios interface for this UI helper'''
        self.angel_interface = angel_interface

    def create_plugin_url(self, **kwargs):
        """Create a URL for calling the plugin recursively"""
        return f'{self.kodi_url}?{urlencode(kwargs)}'

    def main_menu(self):
        """Show the main menu with content type options"""

        # Create directory items for each menu option
        for item in self.menu_items:
            # Create list item
            list_item = xbmcgui.ListItem(label=item['label'])

            # Set info tags
            info_tag = list_item.getVideoInfoTag()
            info_tag.setPlot(item['description'])

            # Create URL
            self.log.debug(f"Creating URL for action: {item['action']}, content_type: {item['content_type']}")
            url = self.create_plugin_url(base_url=self.kodi_url, action=item['action'], content_type=item['content_type'])

            # Add to directory
            xbmcplugin.addDirectoryItem(self.handle, url, list_item, True)

        # Finish directory
        xbmcplugin.endOfDirectory(self.handle)

    def projects_menu(self, content_type=None):
        """Display a menu of projects based on content type, with persistent caching."""
        try:
            self.log.info("Fetching projects from AngelStudiosInterface...")
            angel_menu_content_mapper = {
                'movies': 'movie',
                'series': 'series',
                'specials': 'special'
            }
            cache_key = f"projects_{content_type or 'all'}"
            projects = self.cache.get(cache_key)
            if projects:
                self.log.info(f"Using cached projects for content type: {content_type}")
            else:
                self.log.info(f"Fetching projects from AngelStudiosInterface for content type: {content_type}")
                projects = self.angel_interface.get_projects(
                    project_type=angel_menu_content_mapper.get(content_type, 'videos'))
                self.cache.set(cache_key, projects, expiration=timedelta(hours=4))

            self.log.info(f"Projects: {json.dumps(projects, indent=2)}")

            if not projects:
                self.show_error(f"No projects found for content type: {content_type}")
                return

            self.log.info(f"Processing {len(projects)} \'{content_type if content_type else 'all content type'}\' projects")

            # Set content type for the plugin
            kodi_content_type = 'movies' if content_type == 'movies' else 'tvshows' if content_type == 'series' else 'videos'
            xbmcplugin.setContent(self.handle, kodi_content_type)
            # Create list items for each project
            for project in projects:
                self.log.info(f"Processing project: {project['name']}")
                self.log.debug(f"Project dictionary: {json.dumps(project, indent=2)}")

                # Create list item
                list_item = xbmcgui.ListItem(label=project['name'])
                info_tag = list_item.getVideoInfoTag()
                info_tag.setMediaType(kodi_content_mapper.get(project['projectType'], 'video'))
                self._process_attributes_to_infotags(list_item, project)

                # Create URL for seasons listing
                url = self.create_plugin_url(
                    base_url=self.kodi_url,
                    action='seasons_menu',
                    content_type=content_type,
                    project_slug=project['slug']
                )

                # Add to directory
                xbmcplugin.addDirectoryItem(self.handle, url, list_item, True)

            xbmcplugin.addSortMethod(self.handle, xbmcplugin.SORT_METHOD_LABEL)
            xbmcplugin.endOfDirectory(self.handle)

        except Exception as e:
            self.log.error(f"Error listing {content_type}: {e}")
            self.show_error(f"Failed to load {angel_menu_content_mapper.get(content_type)}: {str(e)}")
            raise e

    def seasons_menu(self, content_type, project_slug):
        """Display a menu of seasons for a specific project, with persistent caching."""
        self.log.info(f"Fetching seasons for project: {project_slug}")
        try:
            self.log.info(f"Fetching seasons for project: {project_slug}")
            project = self._get_project(project_slug)
            if not project:
                self.log.error(f"Project not found: {project_slug}")
                self.show_error(f"Project not found: {project_slug}")
                return
            self.log.info(f"Project details: {json.dumps(project, indent=2)}")
            self.log.info(f"Processing {len(project.get('seasons', []))} seasons for project: {project_slug}")

            # TODO Map this, this is gross.
            kodi_content_type = 'movies' if content_type == 'movies' else 'tvshows' if content_type == 'series' else 'videos'
            self.log.info(f"Setting content type for Kodi: {content_type} ({kodi_content_type})")
            xbmcplugin.setContent(self.handle, kodi_content_type)

            if len(project.get('seasons', [])) == 1:
                self.log.info(f"Single season found: {project['seasons'][0]['name']}")
                self.episodes_menu(content_type, project['slug'], season_id=project['seasons'][0]['id'])
            else:
                for season in project.get('seasons', []):
                    self.log.info(f"Processing season: {season['name']}")
                    self.log.debug(f"Season dictionary: {json.dumps(season, indent=2)}")
                    # Create list item
                    list_item = xbmcgui.ListItem(label=season['name'])
                    info_tag = list_item.getVideoInfoTag()
                    info_tag.setMediaType(kodi_content_mapper.get(content_type, 'video'))
                    self._process_attributes_to_infotags(list_item, season)


                    # Create URL for seasons listing
                    url = self.create_plugin_url(
                        base_url=self.kodi_url,
                        action='episodes_menu',
                        content_type=content_type,
                        project_slug=project_slug,
                        season_id=season['id']
                    )

                    xbmcplugin.addDirectoryItem(self.handle, url, list_item, True)

                xbmcplugin.addSortMethod(self.handle, xbmcplugin.SORT_METHOD_LABEL)
                xbmcplugin.endOfDirectory(self.handle)

            return True

        except Exception as e:
            self.log.error(f"Error fetching project {project_slug}: {e}")
            self.show_error(f"Error fetching project {project_slug}: {str(e)}")
            return False

    def episodes_menu(self, content_type, project_slug, season_id=None):
        """Display a menu of episodes for a specific season, with persistent caching."""
        self.log.info(f"Fetching episodes for project: {project_slug}, season: {season_id}")
        try:
            project = self._get_project(project_slug)
            if not project:
                self.log.error(f"Project not found: {project_slug}")
                self.show_error(f"Project not found: {project_slug}")
                return

            season = next((s for s in project.get('seasons', []) if s.get('id') == season_id), None)
            if not season:
                self.log.error(f"Season not found: {season_id}")
                self.show_error(f"Season not found: {season_id}")
                return

            self.log.info(f"Processing {len(season.get('episodes', []))} episodes for project: {project_slug}, season: {season_id}")
            kodi_content_type = 'movies' if content_type == 'movies' else 'tvshows' if content_type == 'series' else 'videos'
            self.log.info(f"Setting content type for Kodi: {content_type} ({kodi_content_type})")
            xbmcplugin.setContent(self.handle, kodi_content_type)

            for episode in season.get('episodes', []):
                episode_available = bool(episode.get('source'))
                list_item = self._create_list_item_from_episode(
                    episode,
                    project=None,
                    content_type=content_type,
                    stream_url=None,
                    is_playback=False
                )

                # Create URL for seasons listing
                url = self.create_plugin_url(
                    base_url=self.kodi_url,
                    action='play_episode' if episode_available else 'info',
                    content_type=content_type,
                    project_slug=project_slug,
                    season_id=season['id'],
                    episode_id=episode['id'],
                    episode_guid=episode.get('guid', '')
                )

                xbmcplugin.addDirectoryItem(self.handle, url, list_item, False)

            if season['episodes'][0].get('seasonNumber', 0) > 0:
                xbmcplugin.addSortMethod(self.handle, xbmcplugin.SORT_METHOD_EPISODE)
            else:
                xbmcplugin.addSortMethod(self.handle, xbmcplugin.SORT_METHOD_VIDEO_SORT_TITLE)
            xbmcplugin.addSortMethod(self.handle, xbmcplugin.SORT_METHOD_LABEL)
            xbmcplugin.endOfDirectory(self.handle)

        except Exception as e:
            # TODO: this needs to handle episodes that are stubs.  Should not fail completely if one episode is bad.
            self.log.error(f"Error fetching season {season_id}: {e}")
            self.show_error(f"Error fetching season {season_id}: {str(e)}")
            return

    def play_episode(self, episode_guid, project_slug):
        """Play an episode with enhanced metadata, with persistent caching."""
        try:
            cache_key = f"episode_data_{episode_guid}_{project_slug}"
            data = self.cache.get(cache_key)
            if data is None:
                data = self.angel_interface.get_episode_data(episode_guid, project_slug)
                self.cache.set(cache_key, data, expiration=timedelta(hours=1))
            if not data:
                self.log.info(f"No data: {data}")
                self.log.info(f"Episode not found: {episode_guid}")
                self.show_error(f"Episode not found: {episode_guid}")
                return
        except Exception as e:
            self.log.error(f"Error playing episode {episode_guid}: {e}")
            self.show_error(f"Failed to play episode: {str(e)}")
            return

        # Extract stream URL and metadata
        source = data.get('episode', {}).get('source')
        if not source or not source.get('url'):
            self.show_error("No playable stream URL found for this episode")
            self.log.error(f"No stream URL for episode: {episode_guid} in project: {project_slug}")
            print("No stream URL found")
            print(f"Data: {data}")
            return

        stream_url = source['url']
        self.log.info(f"Playing episode: {data['episode']['name']} from project: {project_slug}")
        self.play_video(episode_data=data)

    def play_video(self, stream_url=None, episode_data=None):
        """Play a video stream with optional enhanced metadata"""
        if stream_url and episode_data:
            raise ValueError("Provide only stream_url or episode_data, not both")
        if not stream_url and not episode_data:
            raise ValueError("Must provide either stream_url or episode_data to play video")
        try:
            if episode_data:
                # Enhanced playback with metadata
                episode = episode_data.get('episode', {})
                project = episode_data.get('project', {})

                stream_url = episode.get('source', {}).get('url', stream_url)

                # Create ListItem with metadata using helper
                list_item = self._create_list_item_from_episode(
                    episode=episode,
                    project=project,
                    content_type=None,
                    stream_url=stream_url,
                    is_playback=True
                )

                self.log.info(f"Playing enhanced video: {episode.get('subtitle', 'Unknown')} from project: {project.get('name', 'Unknown')}")
            elif stream_url:
                # Basic playback (fallback for play_content)
                list_item = xbmcgui.ListItem(offscreen=True)
                list_item.setPath(stream_url)
                list_item.setIsFolder(False)
                list_item.setProperty('IsPlayable', 'true')
                list_item.addStreamInfo('video', {'codec': 'h264'})

                self.log.info(f"Playing basic video from URL: {stream_url}")

            # Resolve and play
            xbmcplugin.setResolvedUrl(self.handle, True, listitem=list_item)
            self.log.info(f"Playing stream: {list_item.getPath()}")

        except Exception as e:
            self.show_error(f"Error playing video: {e}")
            self.log.error(f"Error playing video: {e}")

    def show_error(self, message, title="Angel Studios"):
        """Show error dialog to user"""
        xbmcgui.Dialog().ok(title, message)
        xbmc.log(f"Error shown to user: {message}", xbmc.LOGERROR)

    def show_notification(self, message, title="Angel Studios", time=5000):
        """Show notification to user"""
        xbmcgui.Dialog().notification(title, message, time=time)
        xbmc.log(f"Notification: {message}", xbmc.LOGINFO)

    def _get_project(self, project_slug):
        """
        Helper function to handle fetching and caching project data.
        """
        cache_key = f"project_{project_slug}"
        project = self.cache.get(cache_key)
        if project is None:
            self.log.info(f"Fetching project data from AngelStudiosInterface for: {project_slug}")
            project = self.angel_interface.get_project(project_slug)
            if project:
                self.cache.set(cache_key, project, expiration=timedelta(hours=4))
        else:
            self.log.info(f"Using cached project data for: {project_slug}")
        return project

    def _create_list_item_from_episode(self, episode, project=None, content_type=None, stream_url=None, is_playback=False):
        """
        Unified helper to create a ListItem from an episode dict.
        - episode: Raw episode dict.
        - project: Optional project dict (for playback metadata).
        - content_type: For directory media type.
        - stream_url: If provided, enables playback mode.
        - is_playback: True for playback mode (sets offscreen, path, etc.).
        """
        episode_available = bool(episode.get('source'))
        episode_subtitle = episode.get('subtitle', episode.get('name', 'Unknown Episode'))
        if not episode_available:
            episode_subtitle += " (Unavailable)"

        # Create ListItem
        if is_playback:
            list_item = xbmcgui.ListItem(offscreen=True)
            list_item.setPath(stream_url)
            list_item.setIsFolder(False)
            list_item.setProperty('IsPlayable', 'true')

            # Stream details
            video_stream_detail = xbmc.VideoStreamDetail()
            video_stream_detail.setCodec('h264')
            video_stream_detail.setWidth(1920)
            video_stream_detail.setHeight(1080)
            info_tag = list_item.getVideoInfoTag()
            info_tag.addVideoStream(video_stream_detail)

            # Resume
            if episode.get('watch_position'):
                info_tag.setResumePoint(episode['watch_position'])
        else:
            list_item = xbmcgui.ListItem(label=episode_subtitle)
            list_item.setIsFolder(True)
            list_item.setProperty('IsPlayable', 'true' if is_playback else 'false')

        # Set common metadata
        self._process_attributes_to_infotags(list_item, episode)

        # Set media type and additional metadata
        info_tag = list_item.getVideoInfoTag()
        if is_playback:
            info_tag.setMediaType('video')
            # Additional playback metadata from project
            if project:
                info_tag.setTvShowTitle(project.get('name'))
        else:
            info_tag.setMediaType(kodi_content_mapper.get(content_type, 'video'))
            info_tag.setTitle(episode_subtitle)

        return list_item

    def _process_attributes_to_infotags(self, list_item, info_dict):
        """
        Set VideoInfoTag attributes from a dictionary using known setters.
        Only sets attributes present in the info_dict.
        """
        self.log.info(f"Processing attributes for list item: {list_item.getLabel()}")
        self.log.debug(f"Attribute dict: {info_dict}")
        info_tag = list_item.getVideoInfoTag()
        mapping = {
            'media_type': info_tag.setMediaType,
            'name': info_tag.setTitle,
            'theaterDescription': info_tag.setPlot,
            'description': info_tag.setPlot,
            'year': info_tag.setYear,
            'genres': info_tag.setGenres,
            'contentRating': info_tag.setMpaa,
            'original_title': info_tag.setOriginalTitle,
            'sort_title': info_tag.setSortTitle,
            'tagline': info_tag.setTagLine,
            'duration': info_tag.setDuration,
            'cast': info_tag.setCast,
            'episode': info_tag.setEpisode,
            'episodeNumber': info_tag.setEpisode,
            'season': info_tag.setSeason,
            'seasonNumber': info_tag.setSeason,
            'tvshowtitle': info_tag.setTvShowTitle,
            'premiered': info_tag.setPremiered,
            'rating': info_tag.setRating,
            'votes': info_tag.setVotes,
            'trailer': info_tag.setTrailer,
            'playcount': info_tag.setPlaycount,
            'unique_ids': info_tag.setUniqueIDs,
            'imdbnumber': info_tag.setIMDBNumber,
            'dateadded': info_tag.setDateAdded
        }
        art_dict = {}

        for key, value in info_dict.items():
            self.log.debug(f"Processing key: {key} with value: \'{value}\'")
            # Handle metadata keys that have setters
            if key == 'metadata':
                for meta_key, meta_value in value.items():
                    if meta_key in mapping and meta_value:
                        mapping[meta_key](meta_value)
            # Handle artwork
            elif 'Cloudinary' in key and value:
                if key in ['discoveryPosterCloudinaryPath', 'posterCloudinaryPath']:
                    art_dict['poster'] = self.angel_interface.get_cloudinary_url(value)
                elif key in ['discoveryPosterLandscapeCloudinaryPath', 'posterLandscapeCloudinaryPath']:
                    art_dict['landscape'] = self.angel_interface.get_cloudinary_url(value)
                    art_dict['fanart'] = self.angel_interface.get_cloudinary_url(value)
                elif key == 'logoCloudinaryPath':
                    art_dict['logo'] = self.angel_interface.get_cloudinary_url(value)
                    art_dict['clearlogo'] = self.angel_interface.get_cloudinary_url(value)
                    art_dict['icon'] = self.angel_interface.get_cloudinary_url(value)
                else:
                    self.log.info(f"Unknown Cloudinary key: {key}, skipping")
            elif key == 'seasonNumber' and value == 0:
                self.log.info("Season is 0, skipping season info")
            elif key in mapping:
                mapping[key](value)
            else:
                self.log.debug(f"No known processor for key: {key}, skipping")

        # Set artwork if available
        if art_dict:
            self.log.debug(f"Setting artwork: {art_dict}")
            list_item.setArt(art_dict)
        return
