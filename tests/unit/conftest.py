"""
conftest.py for unit tests.
Provides fixtures and setup for mocking Kodi dependencies.
"""
import pytest
import sys
import os
from unittest.mock import MagicMock

# Add resources/lib to path (from unit directory: ../../plugin.video.angelstudios/resources/lib)
lib_path = os.path.join(os.path.dirname(__file__), '../..', 'plugin.video.angelstudios/resources/lib')
sys.path.insert(0, lib_path)

# Mock Kodi modules
sys.modules['xbmc'] = MagicMock()
sys.modules['xbmcgui'] = MagicMock()
sys.modules['xbmcplugin'] = MagicMock()
sys.modules['xbmcaddon'] = MagicMock()
sys.modules['xbmcvfs'] = MagicMock()

# Mock simplecache module
sys.modules['simplecache'] = MagicMock()
sys.modules['simplecache'].SimpleCache = MagicMock
