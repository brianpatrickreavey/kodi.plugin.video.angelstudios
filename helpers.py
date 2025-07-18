import xbmc # type: ignore
import xbmcaddon # type: ignore
import xbmcvfs # type: ignore
import os
import pickle
from urllib.parse import urlencode

import inspect

class KodiLogger:
    """Simple logger class to log messages to Kodi log"""
    def debug(self, message):
        self.xbmclog(message, xbmc.LOGDEBUG)

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
        stack = inspect.stack()
        for i in stack:
            xbmc.log(
                f"Function: {i.function}, Class: {i.frame.f_locals.get('self', None).__class__.__name__ if i.frame.f_locals.get('self', None) else None}",
                xbmc.LOGDEBUG)

        if len(stack) >= 3:
            class_name = stack[2].frame.f_locals.get('self', None).__class__.__name__ if stack[2].frame.f_locals.get('self', None) else None
            function_name = stack[2].function
        else:
            class_name = stack[len(stack)-1].frame.f_locals.get('self', None).__class__.__name__ if stack[len(stack)-1].frame.f_locals.get('self', None) else None
            function_name = stack[len(stack)-1].function

        handler = f"{class_name}.{function_name}" if class_name and function_name else "Unknown Handler"
        xbmc.log(f"Handler: {handler} (stack_len:{len(stack)})", xbmc.LOGDEBUG)
        xbmc.log(f"Angel Studios Addon: {handler}: {message}", level)


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