"""test_kodi_ui_interface.py
This module provides unit tests for the Kodi UI Interface class.
"""
import pytest
import unittest
from unittest.mock import MagicMock, patch

from datetime import timedelta

from kodi_ui_interface import KodiUIInterface

from .unittest_data import MOCK_PROJECTS_DATA

def test_kodi_ui_interface_init():
    """Test KodiUIInterface initialization with mocked dependencies."""
    logger_mock = MagicMock()
    angel_interface_mock = MagicMock()

    ui_interface = KodiUIInterface(handle=1, url="test_url", logger=logger_mock, angel_interface=angel_interface_mock)

    assert ui_interface.handle == 1
    assert ui_interface.kodi_url == "test_url"
    assert ui_interface.log == logger_mock
    assert ui_interface.angel_interface == angel_interface_mock
    # Add assertions for cache initialization if applicable

def test_set_angel_interface():
    """Test setting the angel interface."""
    logger_mock = MagicMock()
    angel_interface_mock = MagicMock()
    new_angel_interface_mock = MagicMock()

    ui_interface = KodiUIInterface(handle=1, url="test_url", logger=logger_mock, angel_interface=angel_interface_mock)
    ui_interface.setAngelInterface(new_angel_interface_mock)

    assert ui_interface.angel_interface == new_angel_interface_mock

def test_create_plugin_url():
    """Test creating a Kodi URL."""
    logger_mock = MagicMock()
    angel_interface_mock = MagicMock()

    ui_interface = KodiUIInterface(handle=1, url="test_url", logger=logger_mock, angel_interface=angel_interface_mock)
    kodi_url = ui_interface.create_plugin_url(param1="value1", param2="value2")

    assert kodi_url == "test_url?param1=value1&param2=value2"

def test_main_menu():
    """Test that main_menu adds directory items via xbmcplugin."""
    logger_mock = MagicMock()
    angel_interface_mock = MagicMock()

    ui_interface = KodiUIInterface(handle=1, url="test_url", logger=logger_mock, angel_interface=angel_interface_mock)

    with patch('xbmcplugin.addDirectoryItem') as mock_add_item, \
         patch('xbmcplugin.endOfDirectory') as mock_end_dir, \
         patch('xbmcplugin.setContent'), \
         patch('xbmcgui.ListItem') as mock_list_item:

        mock_list_item.return_value = MagicMock()

        ui_interface.main_menu()

        # Assert addDirectoryItem was called for each menu item (9 items in main_menu)
        assert mock_add_item.call_count == len(ui_interface.menu_items)

        # Verify each call matches the expected menu item
        for i, item in enumerate(ui_interface.menu_items):
            expected_url = ui_interface.create_plugin_url(
                base_url=ui_interface.kodi_url,
                action=item['action'],
                content_type=item['content_type']
            )
            call_args = mock_add_item.call_args_list[i]
            kwargs = call_args[0]  # Positional args

            assert kwargs[0] == ui_interface.handle          # handle
            assert kwargs[1] == expected_url                 # url
            assert kwargs[2] is mock_list_item.return_value  # listitem
            assert kwargs[3] == True                         # isFolder

            # Check that ListItem was created with the correct label
            list_item_call = mock_list_item.call_args_list[i]
            assert list_item_call[1]['label'] == item['label']

        mock_end_dir.assert_called_once_with(1)


@pytest.mark.parametrize("content_type,expected_project_type", [
    ('movies', 'movie'),
    ('series', 'series'),
    ('specials', 'special'),
    ('videos', 'videos'),
])
def test_projects_menu_cache_miss(content_type, expected_project_type):
    """Test projects_menu adds directory items for projects."""
    logger_mock = MagicMock()
    angel_interface_mock = MagicMock()
    angel_interface_mock.get_projects.return_value = MOCK_PROJECTS_DATA[content_type]

    ui_interface = KodiUIInterface(handle=1, url="test_url", logger=logger_mock, angel_interface=angel_interface_mock)

    with patch('xbmcplugin.addDirectoryItem') as mock_add_item, \
         patch('xbmcplugin.endOfDirectory') as mock_end_dir, \
         patch('xbmcgui.ListItem') as mock_list_item, \
         patch.object(ui_interface.cache, 'get', return_value=None) as mock_cache_get, \
         patch.object(ui_interface.cache, 'set') as mock_cache_set:

        # Setup ListItem mock
        mock_list_item.return_value = MagicMock()

        # Call projects_menu
        ui_interface.projects_menu(content_type=content_type)

        # Ensure cache was checked, retruned nothing
        mock_cache_get.assert_called_once()

        # Check if get_projects was called
        angel_interface_mock.get_projects.assert_called_once_with(project_type=expected_project_type)

        # Ensure cache was set with the fetched data
        projects_data = MOCK_PROJECTS_DATA[content_type]
        cache_key = f"projects_{content_type}"
        mock_cache_set.assert_called_once_with(cache_key, projects_data, expiration=timedelta(hours=4))

        assert mock_add_item.call_count == len(projects_data)
        for i, project in enumerate(projects_data):
            call_args = mock_add_item.call_args_list[i]
            kwargs = call_args[0]  # Positional args

            assert kwargs[0] == 1                           # handle
            assert project['slug'] in kwargs[1]             # url
            assert kwargs[2] is mock_list_item.return_value # listitem
            assert kwargs[3] == True                        # isFolder

            # Check ListItem creation
            list_item_call = mock_list_item.call_args_list[i]
            assert list_item_call[1]['label'] == project['name']

        mock_end_dir.assert_called_once_with(1)

@pytest.mark.parametrize("content_type,expected_project_type", [
    ('movies', 'movie'),
    ('series', 'series'),
    ('specials', 'special'),
    ('videos', 'videos'),
])
def test_projects_menu_cache_hit(content_type, expected_project_type):
    """Test projects_menu adds directory items for projects."""
    logger_mock = MagicMock()
    angel_interface_mock = MagicMock()
    angel_interface_mock.get_projects.return_value = MOCK_PROJECTS_DATA[content_type]

    ui_interface = KodiUIInterface(handle=1, url="test_url", logger=logger_mock, angel_interface=angel_interface_mock)

    with patch('xbmcplugin.addDirectoryItem') as mock_add_item, \
         patch('xbmcplugin.endOfDirectory') as mock_end_dir, \
         patch('xbmcgui.ListItem') as mock_list_item, \
         patch.object(ui_interface.cache, 'get', return_value=MOCK_PROJECTS_DATA[content_type]) as mock_cache_get, \
         patch.object(ui_interface.cache, 'set') as mock_cache_set:

        ui_interface.projects_menu(content_type=content_type)

        # Ensure cache was checked, retruned data
        mock_cache_get.assert_called_once()

        # Assert get_projects was NOT called since cache hit
        angel_interface_mock.get_projects.assert_not_called()

        # Assert cache.set was NOT called since cache hit
        mock_cache_set.assert_not_called()

        projects_data = MOCK_PROJECTS_DATA[content_type]
        assert mock_add_item.call_count == len(projects_data)
        for i, project in enumerate(projects_data):
            call_args = mock_add_item.call_args_list[i]
            kwargs = call_args[0]  # Positional args

            assert kwargs[0] == 1                           # handle
            assert project['slug'] in kwargs[1]             # url
            assert kwargs[2] is mock_list_item.return_value # listitem
            assert kwargs[3] == True                        # isFolder

            # Check ListItem creation
            list_item_call = mock_list_item.call_args_list[i]
            assert list_item_call[1]['label'] == project['name']

        mock_end_dir.assert_called_once_with(1)

def test_seasons_menu_cache_miss():
    assert True

def test_seasons_menu_cache_hit():
    assert True

def test_episodes_menu_cache_miss():
    assert True

def test_episodes_menu_cache_hit():
    assert True

def test_play_content():
    assert True

def test_process_attributes_to_infotags():
    assert True

