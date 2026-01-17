"""Final tests to achieve 100% coverage for remaining uncovered lines."""

from unittest.mock import MagicMock, patch

from resources.lib.kodi_ui_interface import KodiUIInterface


class TestKodiUIInterfaceLines1399_1400:
    """Test to cover kodi_ui_interface.py lines 1399-1400."""

    def test_create_list_item_injects_project_logo(self):
        """Test that project logo is injected into episode when episode lacks one (lines 1399-1400)."""
        with (
            patch("xbmcgui.ListItem") as mock_list_item_class,
            patch("xbmcaddon.Addon") as mock_addon,
        ):
            mock_list_item = MagicMock()
            mock_info_tag = MagicMock()
            mock_list_item.getVideoInfoTag.return_value = mock_info_tag
            mock_list_item.getLabel.return_value = "Episode"
            mock_list_item_class.return_value = mock_list_item

            mock_addon_instance = MagicMock()
            mock_addon_instance.getSettingBool.return_value = False
            mock_addon_instance.getSettingString.return_value = "off"
            mock_addon_instance.getSettingInt.return_value = 12
            mock_addon.return_value = mock_addon_instance

            logger_mock = MagicMock()
            angel_interface_mock = MagicMock()
            angel_interface_mock.get_cloudinary_url.return_value = "http://cdn.example.com/logo.jpg"

            ui = KodiUIInterface(
                handle=1,
                url="plugin://plugin.video.angelstudios/",
                logger=logger_mock,
                angel_interface=angel_interface_mock,
            )

            # Episode without logo, project with logo
            episode = {
                "id": "ep1",
                "name": "Episode 1",
                "subtitle": "Test Episode",
                "duration": 3600,
                "source": {"url": "http://example.com/video.m3u8"},
            }
            project = {"logoCloudinaryPath": "project_logo.png"}

            with patch.object(ui.log, "debug") as mock_debug:
                # This calls the code path at lines 1399-1400
                ui.menu_handler._create_list_item_from_episode(episode, project=project, content_type="series")

            # Verify logo injection was logged
            mock_debug.assert_any_call("[ART] Injecting project logo into episode: project_logo.png")


class TestKodiUIInterfaceLines1583_1587:
    """Test to cover kodi_ui_interface.py lines 1583-1587."""

    def test_process_attributes_uses_portrait_stills(self):
        """Test artwork resolution uses portraitStill (lines 1583-1587)."""
        with patch("xbmcaddon.Addon") as mock_addon:
            mock_addon_instance = MagicMock()
            mock_addon_instance.getSettingBool.return_value = False
            mock_addon_instance.getSettingString.return_value = "off"
            mock_addon_instance.getSettingInt.return_value = 12
            mock_addon.return_value = mock_addon_instance

            logger_mock = MagicMock()
            angel_interface_mock = MagicMock()
            angel_interface_mock.get_cloudinary_url.return_value = "http://cdn.example.com/portrait.jpg"

            ui = KodiUIInterface(
                handle=1,
                url="plugin://plugin.video.angelstudios/",
                logger=logger_mock,
                angel_interface=angel_interface_mock,
            )

            list_item = MagicMock()
            info_tag = MagicMock()
            list_item.getVideoInfoTag.return_value = info_tag
            list_item.getLabel.return_value = "Test"

            # portraitStill1 (episode still) - should trigger lines 1583-1587
            info_dict = {"portraitStill1": {"cloudinaryPath": "portrait_still_1.jpg"}}

            with patch.object(ui.log, "debug") as mock_debug:
                ui.menu_handler._process_attributes_to_infotags(list_item, info_dict)

            # Verify the debug log at line 1587
            mock_debug.assert_any_call("[ART] Using portraitStill1: portrait_still_1.jpg")


class TestKodiUIInterfaceLines1589_1597:
    """Test to cover kodi_ui_interface.py lines 1589-1597 (direct portraitTitleImage fallback)."""

    def test_process_attributes_uses_direct_portrait_title_image(self):
        """Test artwork resolution uses direct portraitTitleImage (lines 1589-1597)."""
        with patch("xbmcaddon.Addon") as mock_addon:
            mock_addon_instance = MagicMock()
            mock_addon_instance.getSettingBool.return_value = False
            mock_addon_instance.getSettingString.return_value = "off"
            mock_addon_instance.getSettingInt.return_value = 12
            mock_addon.return_value = mock_addon_instance

            logger_mock = MagicMock()
            angel_interface_mock = MagicMock()
            angel_interface_mock.get_cloudinary_url.return_value = "http://cdn.example.com/portrait.jpg"

            ui = KodiUIInterface(
                handle=1,
                url="plugin://plugin.video.angelstudios/",
                logger=logger_mock,
                angel_interface=angel_interface_mock,
            )

            list_item = MagicMock()
            info_tag = MagicMock()
            list_item.getVideoInfoTag.return_value = info_tag
            list_item.getLabel.return_value = "Test"

            # Direct portraitTitleImage (not nested in title dict)
            info_dict = {"portraitTitleImage": {"cloudinaryPath": "direct_portrait.jpg"}}

            with patch.object(ui.log, "debug") as mock_debug:
                ui.menu_handler._process_attributes_to_infotags(list_item, info_dict)

            # Verify the debug log at lines 1583-1587
            mock_debug.assert_any_call("[ART] direct portraitTitleImage: {'cloudinaryPath': 'direct_portrait.jpg'}")
            mock_debug.assert_any_call("[ART] Using direct portraitTitleImage: direct_portrait.jpg")


class TestKodiUIInterfaceLines1622_1624:
    """Test to cover kodi_ui_interface.py lines 1622-1624."""

    def test_process_attributes_uses_landscape_stills(self):
        """Test artwork resolution uses landscapeStill (lines 1622-1624)."""
        with patch("xbmcaddon.Addon") as mock_addon:
            mock_addon_instance = MagicMock()
            mock_addon_instance.getSettingBool.return_value = False
            mock_addon_instance.getSettingString.return_value = "off"
            mock_addon_instance.getSettingInt.return_value = 12
            mock_addon.return_value = mock_addon_instance

            logger_mock = MagicMock()
            angel_interface_mock = MagicMock()
            angel_interface_mock.get_cloudinary_url.return_value = "http://cdn.example.com/landscape.jpg"

            ui = KodiUIInterface(
                handle=1,
                url="plugin://plugin.video.angelstudios/",
                logger=logger_mock,
                angel_interface=angel_interface_mock,
            )

            list_item = MagicMock()
            info_tag = MagicMock()
            list_item.getVideoInfoTag.return_value = info_tag
            list_item.getLabel.return_value = "Test"

            # landscapeStill1 (episode still) - should trigger lines 1622-1624
            info_dict = {"landscapeStill1": {"cloudinaryPath": "landscape_still_1.jpg"}}

            ui.menu_handler._process_attributes_to_infotags(list_item, info_dict)

            # Verify cloudinary URL was called for the landscape still
            angel_interface_mock.get_cloudinary_url.assert_any_call("landscape_still_1.jpg")


class TestMainLine122:
    """Test to cover main.py line 122."""

    def test_main_shows_error_when_credentials_missing(self):
        """Test main module initialization shows error dialog when credentials are missing (line 122)."""
        import sys
        import runpy

        # Remove main from sys.modules if it exists to force fresh load
        for mod in list(sys.modules.keys()):
            if mod == "main" or mod.startswith("plugin.video.angelstudios"):
                del sys.modules[mod]

        old_argv = sys.argv
        old_path = sys.path.copy()
        try:
            # Set up argv as if Kodi is calling the plugin
            sys.argv = ["plugin://plugin.video.angelstudios/", "1", "?"]

            # Add plugin directory to path
            plugin_path = "/home/bpreavey/Code/kodi.plugin.video.angelstudios/plugin.video.angelstudios"
            if plugin_path not in sys.path:
                sys.path.insert(0, plugin_path)

            with (
                patch("xbmcaddon.Addon") as mock_addon_class,
                patch("xbmcgui.Dialog") as mock_dialog_class,
                patch("resources.lib.kodi_utils.KodiLogger"),
                patch("resources.lib.kodi_ui_interface.KodiUIInterface"),
            ):
                # Mock addon to return empty credentials
                mock_addon = MagicMock()
                mock_addon.getSettingString.side_effect = lambda key: "" if key in ["username", "password"] else "off"
                mock_addon.getSettingBool.return_value = False
                mock_addon.getSettingInt.return_value = 12
                mock_addon_class.return_value = mock_addon

                mock_dialog = MagicMock()
                mock_dialog_class.return_value = mock_dialog

                # Run main as __main__ - this triggers line 122
                try:
                    runpy.run_path(
                        "/home/bpreavey/Code/kodi.plugin.video.angelstudios/"
                        "plugin.video.angelstudios/resources/lib/main.py",
                        run_name="__main__",
                    )
                except SystemExit:
                    # Main might call sys.exit, which is fine
                    pass

                # Verify error dialog was shown (line 122)
                mock_dialog.ok.assert_called_once()
                call_args = mock_dialog.ok.call_args[0]
                assert "Angel Studios" in call_args[0]
                assert "username and password" in call_args[1]
        finally:
            sys.argv = old_argv
            sys.path = old_path
            # Clean up
            for mod in list(sys.modules.keys()):
                if mod == "main" or mod.startswith("plugin.video.angelstudios"):
                    del sys.modules[mod]
