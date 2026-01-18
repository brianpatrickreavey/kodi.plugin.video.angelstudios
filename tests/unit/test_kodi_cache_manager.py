"""
Unit tests for prefetch functionality in Kodi UI Interface class.
"""

from unittest.mock import MagicMock, patch


class TestDeferredPrefetchProject:
    """Tests for _deferred_prefetch_project helper."""

    def test_prefetch_project_basic_success(self, ui_interface, mock_xbmc):
        """Test basic project prefetch with cache misses."""
        ui, logger_mock, angel_interface_mock = ui_interface

        # Mock cache query - no cached projects
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = []
        ui.cache_manager.cache._execute_sql.return_value = mock_cursor

        # Mock project fetch
        project_slugs = ["proj1", "proj2", "proj3"]
        mock_project = {"slug": "proj1", "name": "Project 1"}
        angel_interface_mock.get_project.return_value = mock_project

        # Execute prefetch
        ui._deferred_prefetch_project(project_slugs, max_count=2)

        # Verify cache query
        ui.cache_manager.cache._execute_sql.assert_called_once()
        assert ui.cache_manager.cache._execute_sql.call_args[0][1][0] == "project_%"

        # Verify only max_count projects fetched
        assert angel_interface_mock.get_project.call_count == 2
        angel_interface_mock.get_project.assert_any_call("proj1")
        angel_interface_mock.get_project.assert_any_call("proj2")

        # Verify cache writes
        assert ui.cache_manager.cache.set.call_count == 2

    def test_prefetch_project_with_cached_projects(self, ui_interface, mock_xbmc):
        """Test prefetch skips already-cached projects."""
        ui, logger_mock, angel_interface_mock = ui_interface

        # Mock cache query - proj1 and proj2 already cached
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [("project_proj1",), ("project_proj2",)]
        ui.cache_manager.cache._execute_sql.return_value = mock_cursor

        mock_project = {"slug": "proj3", "name": "Project 3"}
        angel_interface_mock.get_project.return_value = mock_project

        # Execute prefetch
        project_slugs = ["proj1", "proj2", "proj3", "proj4"]
        ui._deferred_prefetch_project(project_slugs, max_count=5)

        # Verify only uncached projects fetched
        assert angel_interface_mock.get_project.call_count == 2
        angel_interface_mock.get_project.assert_any_call("proj3")
        angel_interface_mock.get_project.assert_any_call("proj4")

    def test_prefetch_project_all_cached(self, ui_interface, mock_xbmc):
        """Test prefetch skips when all projects already cached."""
        ui, logger_mock, angel_interface_mock = ui_interface

        # Mock cache query - all projects cached
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [("project_proj1",), ("project_proj2",)]
        ui.cache_manager.cache._execute_sql.return_value = mock_cursor

        # Execute prefetch
        project_slugs = ["proj1", "proj2"]
        ui._deferred_prefetch_project(project_slugs)

        # Verify no fetches
        angel_interface_mock.get_project.assert_not_called()

        # Verify debug log
        assert any("already cached" in str(call.args[0]) for call in logger_mock.debug.call_args_list)

    def test_prefetch_project_empty_list(self, ui_interface, mock_xbmc):
        """Test prefetch handles empty project list gracefully."""
        ui, logger_mock, angel_interface_mock = ui_interface

        # Execute prefetch with empty list
        ui._deferred_prefetch_project([])

        # Verify no cache queries or fetches
        ui.cache_manager.cache._execute_sql.assert_not_called()
        angel_interface_mock.get_project.assert_not_called()

    def test_prefetch_project_no_max_count(self, ui_interface, mock_xbmc):
        """Test prefetch without max_count limit fetches all uncached projects."""
        ui, logger_mock, angel_interface_mock = ui_interface

        # Mock cache query - no cached projects
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = []
        ui.cache_manager.cache._execute_sql.return_value = mock_cursor

        mock_project = {"slug": "proj", "name": "Project"}
        angel_interface_mock.get_project.return_value = mock_project

        # Execute prefetch without max_count
        project_slugs = ["proj1", "proj2", "proj3", "proj4", "proj5"]
        ui._deferred_prefetch_project(project_slugs, max_count=None)

        # Verify all projects fetched
        assert angel_interface_mock.get_project.call_count == 5

    def test_prefetch_project_api_error_abandons(self, ui_interface, mock_xbmc):
        """Test prefetch abandons silently on API error."""
        ui, logger_mock, angel_interface_mock = ui_interface

        # Mock cache query - no cached projects
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = []
        ui.cache_manager.cache._execute_sql.return_value = mock_cursor

        # Mock API error on first fetch
        angel_interface_mock.get_project.side_effect = Exception("API error")

        # Execute prefetch
        project_slugs = ["proj1", "proj2", "proj3"]
        ui._deferred_prefetch_project(project_slugs)

        # Verify only one fetch attempted (abandons on error)
        assert angel_interface_mock.get_project.call_count == 1

        # Verify error logged
        assert any("abandoning prefetch" in str(call.args[0]) for call in logger_mock.debug.call_args_list)

    def test_prefetch_project_empty_response(self, ui_interface, mock_xbmc):
        """Test prefetch handles empty project response gracefully."""
        ui, logger_mock, angel_interface_mock = ui_interface

        # Mock cache query - no cached projects
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = []
        ui.cache_manager.cache._execute_sql.return_value = mock_cursor

        # Mock empty response
        angel_interface_mock.get_project.return_value = None

        # Execute prefetch
        project_slugs = ["proj1", "proj2"]
        ui._deferred_prefetch_project(project_slugs)

        # Verify fetches attempted but no cache writes
        assert angel_interface_mock.get_project.call_count == 2
        ui.cache_manager.cache.set.assert_not_called()

    def test_prefetch_project_cache_disabled(self, ui_interface, mock_xbmc):
        """Test prefetch skips cache writes when cache disabled."""
        ui, logger_mock, angel_interface_mock = ui_interface

        # Mock cache query
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = []
        ui.cache_manager.cache._execute_sql.return_value = mock_cursor

        # Mock project fetch
        mock_project = {"slug": "proj1", "name": "Project 1"}
        angel_interface_mock.get_project.return_value = mock_project

        # Disable cache via _cache_enabled()
        with patch.object(ui.cache_manager, "_cache_enabled", return_value=False):
            # Execute prefetch
            project_slugs = ["proj1"]
            ui._deferred_prefetch_project(project_slugs)

            # Verify fetch occurred but no cache write
            angel_interface_mock.get_project.assert_called_once_with("proj1")
            ui.cache_manager.cache.set.assert_not_called()

    def test_prefetch_project_no_introspection(self, ui_interface, mock_xbmc):
        """Test prefetch skips when SimpleCache introspection unavailable."""
        ui, logger_mock, angel_interface_mock = ui_interface

        # Remove _execute_sql attribute
        delattr(ui.cache_manager.cache, "_execute_sql")

        # Execute prefetch
        project_slugs = ["proj1", "proj2"]
        ui._deferred_prefetch_project(project_slugs)

        # Verify no fetches
        angel_interface_mock.get_project.assert_not_called()

        # Verify debug log
        assert any("introspection not available" in str(call.args[0]) for call in logger_mock.debug.call_args_list)


class TestPrefetchIntegration:
    """Tests for prefetch integration in menu methods."""

    def test_projects_menu_prefetch_enabled(self, ui_interface, mock_xbmc):
        """Test projects_menu calls prefetch when enabled."""
        ui, logger_mock, angel_interface_mock = ui_interface

        # Mock settings
        ui.addon.getSettingBool.side_effect = lambda key: {
            "disable_cache": False,
            "enable_prefetch": True,
        }.get(key, False)
        ui.addon.getSettingInt.return_value = 3  # prefetch_project_count

        # Mock projects
        projects = [
            {"name": "Proj1", "projectType": "series", "slug": "proj1"},
            {"name": "Proj2", "projectType": "series", "slug": "proj2"},
        ]
        angel_interface_mock.get_projects.return_value = projects
        ui.cache_manager.cache.get.return_value = None

        # Mock prefetch
        with (
            patch.object(ui.menu_handler, "_process_attributes_to_infotags", return_value=None),
            patch.object(ui, "_deferred_prefetch_project") as mock_prefetch,
        ):
            ui.projects_menu("series")

            # Verify prefetch called with correct args
            mock_prefetch.assert_called_once_with(["proj1", "proj2"], 3)

    def test_projects_menu_prefetch_disabled(self, ui_interface, mock_xbmc):
        """Test projects_menu skips prefetch when disabled."""
        ui, logger_mock, angel_interface_mock = ui_interface

        # Mock settings - prefetch disabled
        ui.addon.getSettingBool.side_effect = lambda key: {
            "disable_cache": False,
            "enable_prefetch": False,
        }.get(key, False)

        # Mock projects
        projects = [{"name": "Proj1", "projectType": "series", "slug": "proj1"}]
        angel_interface_mock.get_projects.return_value = projects
        ui.cache_manager.cache.get.return_value = None

        # Mock prefetch
        with (
            patch.object(ui.menu_handler, "_process_attributes_to_infotags", return_value=None),
            patch.object(ui, "_deferred_prefetch_project") as mock_prefetch,
        ):
            ui.projects_menu("series")

            # Verify prefetch not called
            mock_prefetch.assert_not_called()

    def test_projects_menu_prefetch_settings_error(self, ui_interface, mock_xbmc):
        """Test projects_menu handles prefetch settings read errors gracefully."""
        ui, logger_mock, angel_interface_mock = ui_interface

        # Mock settings read error
        ui.addon.getSettingBool.side_effect = Exception("Settings error")

        # Mock projects
        projects = [{"name": "Proj1", "projectType": "series", "slug": "proj1"}]
        angel_interface_mock.get_projects.return_value = projects
        ui.cache_manager.cache.get.return_value = None

        # Execute (should not raise)
        with patch.object(ui.menu_handler, "_process_attributes_to_infotags", return_value=None):
            ui.projects_menu("series")

        # Verify warning logged
        assert any("prefetch settings read failed" in str(call.args[0]) for call in logger_mock.warning.call_args_list)

    def test_projects_menu_prefetch_max_count_fallback(self, ui_interface, mock_xbmc):
        """Test projects_menu uses default max_count when setting is invalid."""
        ui, logger_mock, angel_interface_mock = ui_interface

        # Mock settings - invalid max_count
        ui.addon.getSettingBool.side_effect = lambda key: {
            "disable_cache": False,
            "enable_prefetch": True,
        }.get(key, False)
        ui.addon.getSettingInt.return_value = 0  # Invalid - should default to 5

        # Mock projects
        projects = [{"name": f"Proj{i}", "projectType": "series", "slug": f"proj{i}"} for i in range(10)]
        angel_interface_mock.get_projects.return_value = projects
        ui.cache_manager.cache.get.return_value = None

        # Mock prefetch
        with (
            patch.object(ui.menu_handler, "_process_attributes_to_infotags", return_value=None),
            patch.object(ui, "_deferred_prefetch_project") as mock_prefetch,
        ):
            ui.projects_menu("series")

            # Verify prefetch called with default max_count of 5
            assert mock_prefetch.call_count == 1
            call_args = mock_prefetch.call_args
            assert call_args[0][1] == 5  # max_count should be 5

    def test_prefetch_project_exception_in_outer_try(self, ui_interface, mock_xbmc):
        """Test _deferred_prefetch_project handles outer exception gracefully."""
        ui, logger_mock, angel_interface_mock = ui_interface

        # Mock cache query to raise exception
        ui.cache_manager.cache._execute_sql.side_effect = Exception("Cache query error")

        # Execute prefetch (should not raise)
        ui._deferred_prefetch_project(["proj1"])

        # Verify error logged
        assert any("Project prefetch failed" in str(call.args[0]) for call in logger_mock.error.call_args_list)


class TestCacheUtils:
    def test_clear_cache_sql_path_non_empty(self, ui_interface):
        """clear_cache deletes all SQL rows and window properties, returns True."""
        ui, logger_mock, angel_interface_mock = ui_interface
        cache_mock = MagicMock()
        ui.cache_manager.cache = cache_mock

        cache_mock._execute_sql = MagicMock()
        cache_mock._execute_sql.side_effect = [
            MagicMock(fetchall=MagicMock(return_value=[("id1",), ("id2",)])),  # initial ids
            None,  # delete id1
            None,  # delete id2
            MagicMock(fetchall=MagicMock(return_value=[])),  # after ids
        ]
        cache_mock._win = MagicMock()

        assert ui.cache_manager.clear_cache() is True
        assert cache_mock._execute_sql.call_count == 4
        assert cache_mock._win.clearProperty.call_count == 2

    def test_clear_cache_sql_path_empty(self, ui_interface):
        """clear_cache returns True on empty cache."""
        ui, logger_mock, angel_interface_mock = ui_interface
        cache_mock = MagicMock()
        ui.cache_manager.cache = cache_mock

        cache_mock._execute_sql = MagicMock()
        cache_mock._execute_sql.side_effect = [
            MagicMock(fetchall=MagicMock(return_value=[])),  # initial ids
        ]
        cache_mock._win = MagicMock()

        assert ui.cache_manager.clear_cache() is True
        assert cache_mock._execute_sql.call_count == 1
        cache_mock._win.clearProperty.assert_not_called()

    def test_clear_cache_sql_exception(self, ui_interface):
        """clear_cache returns False on SQL failures."""
        ui, logger_mock, angel_interface_mock = ui_interface
        cache_mock = MagicMock()
        ui.cache_manager.cache = cache_mock

        cache_mock._execute_sql = MagicMock(side_effect=Exception("boom"))
        cache_mock._win = MagicMock()
        assert ui.cache_manager.clear_cache() is False

    def test_clear_cache_no_introspection(self, ui_interface):
        """clear_cache returns False and logs when cache lacks SQL helpers."""
        ui, logger_mock, angel_interface_mock = ui_interface
        ui.cache_manager.cache = object()

        assert ui.cache_manager.clear_cache() is False
        logger_mock.info.assert_any_call("SimpleCache before clear: introspection not available")

    def test_clear_cache_clear_property_exception(self, ui_interface):
        """clear_cache swallows window clear exceptions and still returns True."""
        ui, logger_mock, angel_interface_mock = ui_interface
        cache_mock = MagicMock()
        ui.cache_manager.cache = cache_mock

        cache_mock._execute_sql = MagicMock()
        cache_mock._execute_sql.side_effect = [
            MagicMock(fetchall=MagicMock(return_value=[("id1",), ("id2",)])),  # initial ids
            None,  # delete id1
            None,  # delete id2
            MagicMock(fetchall=MagicMock(return_value=[])),  # after ids
        ]
        cache_mock._win = MagicMock()
        cache_mock._win.clearProperty.side_effect = [Exception("win boom"), Exception("win boom 2")]

        assert ui.cache_manager.clear_cache() is True
        assert cache_mock._execute_sql.call_count == 4
        assert cache_mock._win.clearProperty.call_count == 2

    def test_cache_enabled_disable_cache_true_probe_false(self, ui_interface):
        from unittest.mock import MagicMock, patch

        ui, logger_mock, angel_interface_mock = ui_interface

        # Fresh addon scoped to this test only to avoid leaking disable_cache state
        fresh_addon = MagicMock()
        fresh_addon.getSettingBool.return_value = True
        fresh_addon.getSettingString.return_value = "off"
        fresh_addon.getSettingInt.return_value = 12

        ui.addon = fresh_addon
        ui.cache_manager.addon = fresh_addon

        assert ui.cache_manager._cache_enabled() is False

    def test_cache_enabled_not_callable(self, ui_interface):
        ui, _, _ = ui_interface
        ui.addon.getSettingBool = None

        assert ui.cache_manager._cache_enabled() is True

        ui.addon.getSettingBool = MagicMock(return_value=False)

    def test_cache_enabled_disabled_false_returns_true(self, ui_interface):
        ui, _, _ = ui_interface
        ui.addon.getSettingBool = MagicMock(return_value=False)

        assert ui.cache_manager._cache_enabled() is True

    def test_cache_enabled_exception_returns_true(self, ui_interface):
        ui, _, _ = ui_interface
        ui.addon.getSettingBool = MagicMock(side_effect=RuntimeError("boom"))

        assert ui.cache_manager._cache_enabled() is True

    def test_cache_enabled_non_bool_disable_value(self, ui_interface):
        ui, _, _ = ui_interface

        def fake_get(key):
            if key == "disable_cache":
                return "y"
            if key == "__cache_probe__":
                return False
            return False

        ui.addon.getSettingBool = MagicMock(side_effect=fake_get)

        assert ui.cache_manager._cache_enabled() is True

    def test_cache_enabled_probe_not_bool(self, ui_interface):
        ui, _, _ = ui_interface

        def fake_get(key):
            if key == "disable_cache":
                return True
            if key == "__cache_probe__":
                return "maybe"
            return False

        ui.cache_manager.addon.getSettingBool.side_effect = fake_get

        assert ui.cache_manager._cache_enabled() is False
