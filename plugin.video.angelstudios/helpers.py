import xbmc # type: ignore
import xbmcaddon # type: ignore
import xbmcvfs # type: ignore
import os
import pickle
from urllib.parse import urlencode

import inspect

class KodiLogger:
    """Simple logger class to log messages to Kodi log"""
    def __init__(self, debug_promotion=False):
        self.debug_promotion = debug_promotion

    def debug(self, message):
        promoted_message = f"(debug) {message}" if self.debug_promotion else message
        level = xbmc.LOGINFO if self.debug_promotion else xbmc.LOGDEBUG
        self.xbmclog(promoted_message, level)

    def info(self, message):
        self.xbmclog(message, xbmc.LOGINFO)

    def warning(self, message):
        self.xbmclog(message, xbmc.LOGWARNING)

    def error(self, message):
        self.xbmclog(message, xbmc.LOGERROR)

    def critical(self, message):
        self.xbmclog(message, xbmc.LOGFATAL)

    def xbmclog(self, message, level):
        """Log a message to Kodi's log with the specified level"""
        stack = inspect.stack(context=0)
        handler = "Unknown Handler"

        for frame_info in stack[1:]:  # skip xbmclog itself
            module = inspect.getmodule(frame_info.frame)
            module_name = module.__name__ if module else None

            # Skip frames from this helpers module to find the caller
            if module_name and module_name.startswith(__name__):
                continue

            self_obj = frame_info.frame.f_locals.get('self')
            if not self_obj:
                continue

            class_name = self_obj.__class__.__name__
            function_name = frame_info.function

            parts = []
            if module_name:
                parts.append(module_name)
            if class_name:
                parts.append(class_name)
            if function_name:
                parts.append(function_name)

            if parts:
                handler = ".".join(parts)
            break

        xbmc.log(f"Angel Studios: Handler: {handler}: {message}", level)


def get_session_file():
    ''' Load the session for Angel Studios authentication '''
    addon = xbmcaddon.Addon()
    addon_id = addon.getAddonInfo('id')
    cache_dir = xbmcvfs.translatePath(f'special://profile/addon_data/{addon_id}/')
    if not xbmcvfs.exists(cache_dir):
        xbmcvfs.mkdirs(cache_dir)
    return os.path.join(cache_dir, 'angel_session.pkl')

def get_session_data():
    ''' Load the session for Angel Studios authentication '''
    session_file = get_session_file()
    if not xbmcvfs.exists(session_file):
        return None
    with open(session_file, 'rb') as f:
        return pickle.load(f)

def save_session_data(session_data):
    ''' Save the session for Angel Studios authentication '''
    session_file = get_session_file()
    with open(session_file, 'wb') as f:
        pickle.dump(session_data, f)
    xbmc.log(f"Session data saved to {session_file}", xbmc.LOGINFO)

def create_plugin_url(base_url, **kwargs):
    """Create a URL for calling the plugin recursively"""
    return f'{base_url}?{urlencode(kwargs)}'