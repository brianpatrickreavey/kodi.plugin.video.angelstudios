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

kodi_content_mapper = {
    'movies': 'movies',
    'series': 'tvshows',
    'special': 'videos',  # Specials are treated as generic videos
    'podcast': 'videos',  # Podcasts are also generic videos
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

    def setAngelInterface(self, angel_interface):
        '''Set the Angel Studios interface for this UI helper'''
        self.angel_interface = angel_interface

    def create_plugin_url(self, **kwargs):
        """Create a URL for calling the plugin recursively"""
        return f'{self.kodi_url}?{urlencode(kwargs)}'

    def main_menu(self):
        """Show the main menu with content type options"""
        self.angel_interface.session_check()  # Ensure session is authenticated
        xbmcplugin.setContent(self.handle, 'files')

        # Main menu options
        # Process Movies, TV Shows, and Specials first
        menu_items = [
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
            },
            {
                'label': 'TEST VIDEO',
                'content_type': 'test', # settings are not content, but a special action
                'action': 'test_video',
                'description': 'Play a test video'
            }
        ]

        # Create directory items for each menu option
        for item in menu_items:
            # Create list item
            list_item = xbmcgui.ListItem(label=item['label'])

            # Set info tags
            info_tag = list_item.getVideoInfoTag()
            info_tag.setPlot(item['description'])

            # Create URL
            self.log.debug(f"Creating URL for action: {item['action']}, content_type: {item['content_type']}")
            url = self.create_plugin_url(base_url=self.kodi_url, action=item['action'], content_type=item['content_type'])

            # Add to directory (True = is folder)
            xbmcplugin.addDirectoryItem(self.handle, url, list_item, isFolder=True)

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
                self.cache.set(cache_key, projects, expiration=timedelta(hours=1))  # cache

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
                xbmcplugin.addDirectoryItem(self.handle, url, list_item, isFolder=True)

            xbmcplugin.addSortMethod(self.handle, xbmcplugin.SORT_METHOD_LABEL)
            xbmcplugin.endOfDirectory(self.handle)

        except Exception as e:
            self.log.error(f"Error listing movies: {e}")
            self.log.error(f"Last processing: {project['name']}")
            self.show_error(f"Failed to load movies: {str(e)}")
            raise e

    def seasons_menu(self, content_type, project_slug):
        """Display a menu of seasons for a specific project, with persistent caching."""
        xbmc.log(f"Fetching seasons for project: {project_slug}", xbmc.LOGINFO)
        try:
            self.log.info(f"Fetching seasons for project: {project_slug}")
            cache_key = f"seasons_{project_slug}"
            project = self.cache.get(cache_key)
            if project is None:
                project = self.angel_interface._get_project(project_slug)
                self.cache.set(cache_key, project, expiration=timedelta(hours=1))
            if not project:
                self.log.error(f"Project not found: {project_slug}")
                self.show_error(f"Project not found: {project_slug}")
                return
            self.log.info(f"Project details: {json.dumps(project, indent=2)}")
            self.log.info(f"Processing {len(project.get('seasons', []))} seasons for project: {project_slug}")

            kodi_content_type = 'movies' if content_type == 'movies' else 'tvshows' if content_type == 'series' else 'videos'
            self.log.info(f"Setting content type for Kodi: {content_type} ({kodi_content_type})")
            xbmcplugin.setContent(self.handle, kodi_content_type)

            if len(project.get('seasons', [])) == 1:
                self.log.info(f"Single season found: {project['seasons'][0]['name']}")
                self.episodes_menu(content_type, project['slug'], season_id=project['seasons'][0]['id'])
            else:
                for season in project.get('seasons', []):
                    self.log.info(f"Processing season: {season['name']}")
                    self.log.info(f"Season dictionary: {json.dumps(season, indent=2)}")
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
            cache_key = f"episodes_{project_slug}_{season_id}"
            project = self.cache.get(cache_key)
            if project is None:
                project = self.angel_interface._get_project(project_slug)
                self.cache.set(cache_key, project, expiration=timedelta(hours=1))
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
                self.log.info(f"Processing episode: {episode['name']}")
                if not episode.get('source', None):
                    self.log.warning(f"No source found for episode: {episode['name']}, unavailable")
                    episode_available = False
                    stream_url = None
                    episode_subtitle = episode.get('subtitle', 'Unknown') + " (Unavailable)"
                else:
                    episode_available = True
                    stream_url = episode['source'].get('url', None)
                    episode_subtitle = episode.get('subtitle', 'Unknown')

                self.log.info(f"Episode source: {episode.get('source', {})}")
                self.log.info(f"Episode dictionary: {json.dumps(episode, indent=2)}")

                season_number = episode.get('seasonNumber', 0)

                # Create list item
                list_item = xbmcgui.ListItem(label=episode_subtitle)
                info_tag = list_item.getVideoInfoTag()
                info_tag.setMediaType(kodi_content_mapper.get(content_type, 'video'))
                info_tag.setTitle(f"{episode_subtitle} ({episode['name']})")
                self._process_attributes_to_infotags(list_item, episode)

                if season_number > 0:
                    info_tag.setTitle(f"{episode_subtitle}")
                else:
                    info_tag.setSortTitle('-'.join([
                        str(episode.get('seasonNumber', 0)),
                        str(episode.get('episodeNumber', 0)),
                        episode.get('name', '')
                    ]))
                    info_tag.setTitle(f"{episode.get('subtitle', '')} ({episode.get('name', '')})")


                # Create URL for seasons listing
                url = self.create_plugin_url(
                    base_url=self.kodi_url,
                    action='play_content' if episode_available else 'info',
                    content_type=content_type,
                    project_slug=project_slug,
                    season_id=season['id'],
                    episode_id=episode['id'],
                    episode_guid=episode.get('guid', ''),
                    stream_url=stream_url
                )

                list_item.setProperty('IsPlayable', 'true' if episode_available else 'false')
                self.log.info(f"Creating URL for episode: {episode['name']} with stream URL: {stream_url}")
                xbmcplugin.addDirectoryItem(self.handle, url, list_item, isFolder=False)

            if season['episodes'][0].get('seasonNumber', 0) > 0:
                xbmcplugin.addSortMethod(self.handle, xbmcplugin.SORT_METHOD_EPISODE)
            else:
                xbmcplugin.addSortMethod(self.handle, xbmcplugin.SORT_METHOD_VIDEO_SORT_TITLE)
            xbmcplugin.addSortMethod(self.handle, xbmcplugin.SORT_METHOD_VIDEO_SORT_TITLE)
            xbmcplugin.addSortMethod(self.handle, xbmcplugin.SORT_METHOD_LABEL)
            xbmcplugin.endOfDirectory(self.handle)

        except Exception as e:
            # TODO: this needs to handle episodes that are stubs.  Should not fail completely if one episode is bad.
            self.log.error(f"Error fetching season {season_id}: {e}")
            self.show_error(f"Error fetching season {season_id}: {str(e)}")
            return

    def play_content(self, stream_url):
        """Play a video stream"""
        self.log.info(f"Playing content from URL: {stream_url}")
        self.play_video_enhanced(stream_url, e)
        try:
            # Create playable item
            play_item = xbmcgui.ListItem(offscreen=True)
            play_item.setPath(stream_url)

            # Set stream info if available
            play_item.addStreamInfo('video', {
                'codec': 'h264'  # Most Angel Studios content is H.264
            })

            # Resolve and play
            xbmcplugin.setResolvedUrl(self.handle, True, listitem=play_item)
            self.log.info(f"Playing stream: {stream_url}")

        except Exception as e:
            self.log.error(f"Error playing video: {e}")
            xbmcplugin.setResolvedUrl(self.handle, False, listitem=xbmcgui.ListItem())

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
            # 'name': info_tag.setTitle,
            'theaterDescription': info_tag.setPlot,
            'description': info_tag.setPlot,
            'year': info_tag.setYear,
            'genres': info_tag.setGenres,
            'contentRating': info_tag.setMpaa,
            'original_title': info_tag.setOriginalTitle,
            'sort_title': info_tag.setSortTitle,
            'tagline': info_tag.setTagLine,
            'duration': info_tag.setDuration,
            # 'director': info_tag.setDirector,
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

    def play_episode(self, episode_guid, project_slug):
        """Play an episode with enhanced metadata, with persistent caching."""
        try:
            cache_key = f"episode_data_{episode_guid}_{project_slug}"
            data = self.cache.get(cache_key)
            if data is None:
                data = self.angel_interface.get_episode_data(episode_guid, project_slug)
                self.cache.set(cache_key, data, expiration=timedelta(hours=1))
            if not data:
                self.show_error(f"Episode not found: {episode_guid}")
                return
        except Exception as e:
            xbmc.log(f"Error playing episode {episode_guid}: {e}", xbmc.LOGERROR)
            self.show_error(f"Failed to play episode: {str(e)}")

        # Extract stream URL and metadata
        stream_url = data['episode']['source']['url']
        self.log.info(f"Playing episode: {data['episode']['name']} from project: {project_slug}")
        if not stream_url:
            self.show_error("No playable stream URL found for this episode")
            return

        # Play the video with enhanced metadata
        self.play_video_enhanced(stream_url, data)

    def play_video_enhanced(self, stream_url, episode_data):
        """Play a video stream with enhanced metadata"""
        try:
            episode = episode_data.get('episode', {})
            project = episode_data.get('project', {})

            stream_url = episode.get('source', {}).get('url', stream_url)

            # Create playable item with enhanced metadata
            list_item = xbmcgui.ListItem(offscreen=True)
            list_item.setPath(stream_url)
            list_item.setIsFolder(False)
            xbmcplugin.setResolvedUrl(self.handle, True, listitem=list_item)

            # Set playable property
            list_item.setProperty('IsPlayable','true')

            # Set detailed info tags
            info_tag = list_item.getVideoInfoTag()
            info_tag.setMediaType('video')

            if episode.get('name'):
                info_tag.setTitle(episode['name'])
            if episode.get('subtitle'):
                info_tag.setPlotOutline(episode['subtitle'])
            if episode.get('description'):
                info_tag.setPlot(episode['description'])
            if project and project.get('name'):
                info_tag.setTvShowTitle(project['name'])
            if episode.get('episode_number'):
                info_tag.setEpisode(episode['episode_number'])
            if episode.get('season_number'):
                info_tag.setSeason(episode['season_number'])
            if episode.get('duration'):
                info_tag.setDuration(episode['duration'])

            # Set artwork
            art_dict = {}
            if episode.get('poster'):
                art_dict['thumb'] = episode['poster']
            if episode.get('fanart'):
                art_dict['fanart'] = episode['fanart']
            if project and project.get('poster'):
                art_dict['poster'] = project['poster']

            list_item.setArt(art_dict)

            video_stream_detail = xbmc.VideoStreamDetail()
            video_stream_detail.setCodec('h264')
            video_stream_detail.setWidth(1920)
            video_stream_detail.setHeight(1080)
            info_tag.addVideoStream(video_stream_detail)

            # Handle resume position if available
            if episode.get('watch_position'):
                info_tag.setResumePoint(episode['watch_position'])

            self.log.info(f"Playing enhanced video: {episode.get('subtitle', 'Unknown')} from project: {project.get('name', 'Unknown')}")
            self.log.info(f"Stream URL: {stream_url}")
            # Resolve and play
            self.log.info(f"{self.handle=} {list_item=}")
            xbmcplugin.setResolvedUrl(self.handle, True, listitem=list_item)
            xbmc.log(f"Playing enhanced stream: {list_item.getPath()}", xbmc.LOGINFO)

        except Exception as e:
            xbmc.log(f"Error playing enhanced video: {e}", xbmc.LOGERROR)
            # Fallback to basic play
            return

    def show_error(self, message, title="Angel Studios"):
        """Show error dialog to user"""
        xbmcgui.Dialog().ok(title, message)
        xbmc.log(f"Error shown to user: {message}", xbmc.LOGERROR)

    def show_notification(self, message, title="Angel Studios", time=5000):
        """Show notification to user"""
        xbmcgui.Dialog().notification(title, message, time=time)
        xbmc.log(f"Notification: {message}", xbmc.LOGINFO)
