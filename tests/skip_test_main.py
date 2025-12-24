import sys
from unittest.mock import MagicMock

# Mock Kodi modules before importing main
sys.modules['xbmc'] = MagicMock()
sys.modules['xbmcgui'] = MagicMock()
sys.modules['xbmcplugin'] = MagicMock()
sys.modules['xbmcaddon'] = MagicMock()
sys.modules['xbmcvfs'] = MagicMock()

# Mock sys.argv for main.py import
sys.argv = ['plugin://plugin.video.angelstudios', '1', '']

import unittest
from unittest.mock import patch, MagicMock
import main

class TestMainFunctions(unittest.TestCase):
    def test_get_url(self):
        # Test that get_url builds the correct URL
        with patch('main.URL', 'plugin://plugin.video.angelstudios'):
            url = main.get_url(action='test', foo='bar')
            self.assertTrue(url.startswith('plugin://plugin.video.angelstudios?'))
            self.assertIn('action=test', url)
            self.assertIn('foo=bar', url)

    @patch('main.requests.get')
    @patch('main.bs4.BeautifulSoup')
    def test_get_projects(self, mock_bs, mock_get):
        # Mock the requests.get and BeautifulSoup to return controlled data
        mock_response = MagicMock()
        mock_response.content = b'{}'
        mock_get.return_value = mock_response

        # Mock the soup and JSON structure as needed for your function
        mock_soup = MagicMock()
        mock_bs.return_value = mock_soup
        mock_soup.find.return_value.string = '{"props":{"pageProps":{"pageDataContext":{"start-watching":[],"title-map":{}}}}}'

        projects = main.get_projects('http://fake-url')
        self.assertIsInstance(projects, dict)

    @patch('main.requests.get')
    @patch('main.bs4.BeautifulSoup')
    def test_get_seasons(self, mock_bs, mock_get):
        # Mock the requests.get and BeautifulSoup to return controlled data
        mock_response = MagicMock()
        mock_response.content = b'{}'
        mock_get.return_value = mock_response

        # Mock the soup and JSON structure as needed for your function
        mock_soup = MagicMock()
        mock_bs.return_value = mock_soup
        with open('tests/data/mock_project_data.json') as f:
            mock_soup.find.return_value.string = f.read()

        seasons = main.get_seasons('http://fake-url')
        self.assertIsInstance(seasons, list)

if __name__ == '__main__':
    unittest.main()