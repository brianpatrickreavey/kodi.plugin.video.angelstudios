from unittest.mock import patch, MagicMock
import json
import pytest
from .unittest_data import MOCK_PROJECT_DATA, MOCK_EPISODE_DATA, TEST_EXCEPTION_MESSAGE
import copy


class TestEpisodePlayback:
    @pytest.mark.parametrize("cache_hit", [False, True])
    @pytest.mark.parametrize("project_data", MOCK_PROJECT_DATA.values())
    def test_play_episode(self, ui_interface, mock_xbmc, mock_cache, project_data, cache_hit):
        """Test refactored play_episode using cached project data."""
        ui, logger_mock, angel_interface_mock = ui_interface
        mock_add_item, mock_end_dir, mock_list_item = mock_xbmc

        project_slug = project_data["slug"]
        episode_data = project_data["seasons"][0]["episodes"][0]
        episode_guid = episode_data["guid"]

        # Setup _get_project to return project data
        with (
            patch.object(ui, "_get_project", return_value=project_data) as mock_get_project,
            patch.object(ui.playback_handler, "play_video") as mock_play_video,
        ):
            ui.play_episode(episode_guid, project_slug)

            # Assertions
            mock_get_project.assert_called_once_with(project_slug)
            mock_play_video.assert_called_once_with(
                episode_data={"episode": episode_data, "project": project_data},
                resume_at=None,
                saved_position=None,
                clear_kodi_stop=False,
            )

    def test_play_episode_project_not_found(self, ui_interface, mock_xbmc, mock_cache):
        """Test play_episode when project is not found."""
        ui, logger_mock, angel_interface_mock = ui_interface
        mock_add_item, mock_end_dir, mock_list_item = mock_xbmc

        with (
            patch.object(ui, "_get_project", return_value=None),
            patch.object(ui, "show_error") as mock_show_error,
        ):
            ui.play_episode("guid", "project-slug")

            mock_show_error.assert_called_once_with("Project not found: project-slug")

    def test_play_episode_episode_not_found_in_project(self, ui_interface, mock_xbmc, mock_cache):
        """Test play_episode when episode GUID not found in project."""
        ui, logger_mock, angel_interface_mock = ui_interface
        mock_add_item, mock_end_dir, mock_list_item = mock_xbmc

        project_data = copy.deepcopy(MOCK_PROJECT_DATA["single_season_project"])

        with (
            patch.object(ui, "_get_project", return_value=project_data),
            patch.object(ui, "show_error") as mock_show_error,
        ):
            ui.play_episode("nonexistent-guid", project_data["slug"])

            mock_show_error.assert_called_once_with("Episode not found: nonexistent-guid")

    def test_play_episode_no_stream(self, ui_interface, mock_xbmc, mock_cache):
        """Test play_episode when episode has no stream."""
        ui, logger_mock, angel_interface_mock = ui_interface
        mock_add_item, mock_end_dir, mock_list_item = mock_xbmc

        # Setup project with episode that has no source
        project_data = copy.deepcopy(MOCK_PROJECT_DATA["single_season_project"])
        project_data["seasons"][0]["episodes"][0]["source"] = None

        with (
            patch.object(ui, "_get_project", return_value=project_data),
            patch.object(ui, "show_error") as mock_show_error,
        ):
            episode_guid = project_data["seasons"][0]["episodes"][0]["guid"]
            ui.play_episode(episode_guid, project_data["slug"])

            mock_show_error.assert_called_once_with("No playable stream URL found for this episode")

    def test_play_episode_no_url_in_source(self, ui_interface, mock_xbmc, mock_cache):
        """Test play_episode when source exists but url is missing."""
        ui, logger_mock, angel_interface_mock = ui_interface
        mock_add_item, mock_end_dir, mock_list_item = mock_xbmc

        # Setup project with episode that has source but no URL
        project_data = copy.deepcopy(MOCK_PROJECT_DATA["single_season_project"])
        project_data["seasons"][0]["episodes"][0]["source"] = {"duration": 3600}

        with (
            patch.object(ui, "_get_project", return_value=project_data),
            patch.object(ui, "show_error") as mock_show_error,
        ):
            episode_guid = project_data["seasons"][0]["episodes"][0]["guid"]
            ui.play_episode(episode_guid, project_data["slug"])

            # Assertions: Error shown
            mock_show_error.assert_called_once_with("No playable stream URL found for this episode")

    def test_play_episode_exception_handling(self, ui_interface, mock_xbmc, mock_cache):
        """Test play_episode handles exceptions gracefully."""
        ui, logger_mock, angel_interface_mock = ui_interface
        mock_add_item, mock_end_dir, mock_list_item = mock_xbmc

        with (
            patch.object(ui, "_get_project", side_effect=Exception(TEST_EXCEPTION_MESSAGE)),
            patch.object(ui, "show_error") as mock_show_error,
        ):
            ui.play_episode("guid", "slug")

            # Verify error handling
            mock_show_error.assert_called_once_with(f"Failed to play episode: {TEST_EXCEPTION_MESSAGE}")


class TestVideoPlayback:
    def test_play_video_with_stream(self, ui_interface, mock_xbmc, mock_cache):
        """Test play_video with stream URL."""
        ui, logger_mock, angel_interface_mock = ui_interface
        mock_add_item, mock_end_dir, mock_list_item = mock_xbmc

        stream_url = "http://example.com/stream"

        with patch("xbmcplugin.setResolvedUrl") as mock_set_resolved_url:
            ui.play_video(stream_url=stream_url)

            # Assertions: setResolvedUrl called
            mock_set_resolved_url.assert_called_once()

    def test_play_video_with_data(self, ui_interface, mock_xbmc, mock_cache):
        """Test play_video with episode data."""
        ui, logger_mock, angel_interface_mock = ui_interface
        mock_add_item, mock_end_dir, mock_list_item = mock_xbmc

        episode_data = MOCK_EPISODE_DATA

        with patch("xbmcplugin.setResolvedUrl") as mock_set_resolved_url:
            ui.play_video(episode_data=episode_data)

            # Assertions: setResolvedUrl called
            mock_set_resolved_url.assert_called_once()

    def test_play_video_both_params(self, ui_interface, mock_xbmc, mock_cache):
        """Test play_video with both stream and data (prioritizes stream)."""
        ui, logger_mock, angel_interface_mock = ui_interface
        mock_add_item, mock_end_dir, mock_list_item = mock_xbmc

        stream_url = "http://example.com/stream"
        episode_data = MOCK_EPISODE_DATA

        with pytest.raises(ValueError, match="Provide only stream_url or episode_data, not both"):
            ui.play_video(stream_url=stream_url, episode_data=episode_data)

    def test_play_video_no_params(self, ui_interface, mock_xbmc, mock_cache):
        """Test play_video with no params."""
        ui, logger_mock, angel_interface_mock = ui_interface
        mock_add_item, mock_end_dir, mock_list_item = mock_xbmc

        with pytest.raises(ValueError, match="Must provide either stream_url or episode_data to play video"):
            ui.play_video()

    def test_play_video_exception(self, ui_interface, mock_xbmc, mock_cache):
        """Test play_video handles exceptions."""
        ui, logger_mock, angel_interface_mock = ui_interface
        mock_add_item, mock_end_dir, mock_list_item = mock_xbmc

        stream_url = "http://example.com/stream"

        with (
            patch("xbmcplugin.setResolvedUrl", side_effect=Exception(TEST_EXCEPTION_MESSAGE)),
            patch.object(ui, "show_error") as mock_show_error,
        ):
            ui.play_video(stream_url=stream_url)

            # Assertions: Error shown
            mock_show_error.assert_called_once_with(f"Error playing video: {TEST_EXCEPTION_MESSAGE}")

    def test_play_video_use_isa_properties(self, ui_interface, mock_cache):
        """When use_isa is enabled, playback should set ISA properties on the ListItem."""
        ui, _, _ = ui_interface

        addon = MagicMock()
        addon.getSettingBool.return_value = True

        with (
            patch.object(ui, "addon", addon),
            patch("xbmcaddon.Addon", return_value=addon),
            patch.object(ui, "_ensure_isa_available", return_value=True),
        ):
            list_item = ui.menu_handler._create_list_item_from_episode(
                episode=MOCK_EPISODE_DATA["episode"],
                project=MOCK_EPISODE_DATA["project"],
                content_type="",
                is_playback=True,
            )

        list_item.setProperty.assert_any_call("inputstream", "inputstream.adaptive")
        list_item.setProperty.assert_any_call("inputstream.adaptive.manifest_type", "hls")
        list_item.setProperty.assert_any_call("inputstream.adaptive.stream_selection_type", "adaptive")
        list_item.setMimeType.assert_called_once_with("application/vnd.apple.mpegurl")
        list_item.setContentLookup.assert_called_once_with(False)

    def test_play_video_quality_exact_match_no_isa(self, ui_interface, monkeypatch):
        ui, _, _ = ui_interface

        manifest_url = "http://example.com/master.m3u8"
        addon = MagicMock()
        addon.getSettingBool.return_value = False
        addon.getSettingString.return_value = "1080p"

        list_item = MagicMock()
        info_tag = MagicMock()
        list_item.getVideoInfoTag.return_value = info_tag

        with (
            patch("xbmcaddon.Addon", return_value=addon),
            patch("xbmcgui.ListItem", return_value=list_item),
            patch("xbmcplugin.setResolvedUrl"),
        ):
            ui.play_video(episode_data={"episode": {"source": {"url": manifest_url}}, "project": {}})

        list_item.setPath.assert_called_once_with(manifest_url)

    def test_get_quality_pref_fallback_to_get_setting(self, ui_interface):
        """Test _get_quality_pref fallback when getSettingString is not callable."""
        ui, _, _ = ui_interface

        addon = MagicMock()
        # Make getSettingString attribute exist but not be callable
        addon.getSettingString = None
        addon.getSetting.return_value = "720p"

        with patch.object(ui, "addon", addon):
            result = ui._get_quality_pref()

        assert result == {"mode": "fixed", "target_height": 720}
        addon.getSetting.assert_called_once_with("video_quality")

    def test_get_quality_pref_exception_defaults_to_auto(self, ui_interface):
        """Test _get_quality_pref returns auto when an exception occurs."""
        ui, _, _ = ui_interface

        with patch("xbmcaddon.Addon", side_effect=Exception("Addon initialization failed")):
            result = ui._get_quality_pref()

        assert result == {"mode": "auto", "target_height": None}

    def test_play_video_no_manifest_logs_warning(self, ui_interface):
        ui, logger_mock, _ = ui_interface

        addon = MagicMock()
        addon.getSettingBool.return_value = False

        list_item = MagicMock()
        info_tag = MagicMock()
        list_item.getVideoInfoTag.return_value = info_tag

        with (
            patch("xbmcaddon.Addon", return_value=addon),
            patch("xbmcgui.ListItem", return_value=list_item),
            patch("xbmcplugin.setResolvedUrl"),
        ):
            ui.play_video(episode_data={"episode": {"source": {}}, "project": {}})

        logger_mock.warning.assert_any_call("No manifest URL available; skipping quality selection")

    def test_play_video_sets_isa_chooser_resolution(self, ui_interface):
        ui, _, _ = ui_interface

        addon = MagicMock()
        addon.getSettingBool.return_value = True
        addon.getSettingString.return_value = "720p"

        manifest_url = "http://example.com/master.m3u8"

        with (
            patch.object(ui, "addon", addon),
            patch("xbmcaddon.Addon", return_value=addon),
            patch.object(ui, "_ensure_isa_available", return_value=True),
        ):
            list_item = ui.menu_handler._create_list_item_from_episode(
                episode={"source": {"url": manifest_url}}, project={}, content_type="", is_playback=True
            )

        list_item.setProperty.assert_any_call("inputstream.adaptive.chooser_resolution_max", "720p")
        list_item.setProperty.assert_any_call("inputstream.adaptive.chooser_resolution_secure_max", "720p")
        list_item.setProperty.assert_any_call("inputstream.adaptive.stream_selection_type", "fixed-res")

    def test_play_video_sets_isa_stream_selection_manual(self, ui_interface):
        ui, _, _ = ui_interface

        addon = MagicMock()
        addon.getSettingBool.return_value = True
        addon.getSettingString.return_value = "manual"

        manifest_url = "http://example.com/master.m3u8"

        with (
            patch.object(ui, "_get_quality_pref", return_value={"mode": "manual", "target_height": None}),
            patch.object(ui, "addon", addon),
            patch.object(ui, "_ensure_isa_available", return_value=True),
        ):
            list_item = ui.menu_handler._create_list_item_from_episode(
                episode={"source": {"url": manifest_url}}, project={}, content_type="", is_playback=True
            )

        list_item.setProperty.assert_any_call("inputstream.adaptive.stream_selection_type", "ask-quality")

    def test_play_video_isa_unavailable_logs_fallback(self, ui_interface):
        ui, logger_mock, _ = ui_interface

        addon = MagicMock()
        addon.getSettingBool.return_value = True
        addon.getSettingString.return_value = "1080p"

        list_item = MagicMock()
        info_tag = MagicMock()
        list_item.getVideoInfoTag.return_value = info_tag

        manifest_url = "http://example.com/master.m3u8"

        with (
            patch.object(ui, "addon", addon),
            patch.object(ui, "_ensure_isa_available", return_value=False),
            patch("xbmc.getCondVisibility", return_value=False),
            patch("xbmcgui.ListItem", return_value=list_item),
            patch("xbmcplugin.setResolvedUrl"),
        ):
            ui.play_video(episode_data={"episode": {"source": {"url": manifest_url}}, "project": {}})

        logger_mock.info.assert_any_call("ISA requested but unavailable; falling back to native playback")

    def test_play_video_isa_helper_missing_but_addon_present(self, ui_interface):
        ui, _, _ = ui_interface

        addon = MagicMock()
        addon.getSettingBool.return_value = True
        addon.getSettingString.return_value = "1080p"

        manifest_url = "http://example.com/master.m3u8"

        with (
            patch.object(ui, "addon", addon),
            patch("xbmcaddon.Addon", return_value=addon),
            patch.object(ui, "_ensure_isa_available", return_value=False),
            patch("xbmc.getCondVisibility", return_value=True),
        ):
            list_item = ui.menu_handler._create_list_item_from_episode(
                episode={"source": {"url": manifest_url}}, project={}, content_type="", is_playback=True
            )

        list_item.setProperty.assert_any_call("inputstream", "inputstream.adaptive")


class TestInputStreamAdaptive:
    """Tests for InputStream Adaptive availability checking."""

    @staticmethod
    def _make_cond_visibility(helper_installed: bool, isa_installed: bool):
        """Helper to create fake getCondVisibility function."""

        def _fake(query: str, *_args, **_kwargs) -> bool:
            if query == "System.HasAddon(script.module.inputstreamhelper)":
                return helper_installed
            if query == "System.HasAddon(inputstream.adaptive)":
                return isa_installed
            return False

        return _fake

    @staticmethod
    def _install_helper_module(monkeypatch, helper_cls):
        """Install fake inputstreamhelper module for testing."""
        import sys
        from types import ModuleType

        helper_module = ModuleType("inputstreamhelper")
        helper_module.Helper = helper_cls  # type: ignore[attr-defined]
        monkeypatch.setitem(sys.modules, "inputstreamhelper", helper_module)

    def test_ensure_isa_available_helper_missing_no_isa(self, ui_interface, monkeypatch):
        """Test ISA check when both helper and ISA are missing."""
        ui, logger_mock, angel_interface_mock = ui_interface
        monkeypatch.setattr("xbmc.getCondVisibility", self._make_cond_visibility(False, False))
        assert ui.playback_handler._ensure_isa_available("hls") is False

    def test_ensure_isa_available_helper_missing_with_isa(self, ui_interface, monkeypatch):
        """Test ISA check when helper missing but ISA is installed."""
        ui, logger_mock, angel_interface_mock = ui_interface
        monkeypatch.setattr("xbmc.getCondVisibility", self._make_cond_visibility(False, True))
        assert ui.playback_handler._ensure_isa_available("hls") is True

    def test_ensure_isa_available_success(self, ui_interface, monkeypatch):
        """Test ISA check when helper successfully validates ISA."""
        ui, logger_mock, angel_interface_mock = ui_interface

        class DummyHelper:
            def __init__(self, manifest_type):
                self.manifest_type = manifest_type

            def check_inputstream(self):
                return True

        monkeypatch.setattr("xbmc.getCondVisibility", self._make_cond_visibility(True, True))
        self._install_helper_module(monkeypatch, DummyHelper)
        assert ui.playback_handler._ensure_isa_available("hls") is True

    def test_ensure_isa_available_failure(self, ui_interface, monkeypatch):
        """Test ISA check when helper validation fails."""
        ui, logger_mock, angel_interface_mock = ui_interface

        class DummyHelper:
            def __init__(self, manifest_type):
                self.manifest_type = manifest_type

            def check_inputstream(self):
                return False

        monkeypatch.setattr("xbmc.getCondVisibility", self._make_cond_visibility(True, False))
        self._install_helper_module(monkeypatch, DummyHelper)
        assert ui.playback_handler._ensure_isa_available("hls") is False

    def test_ensure_isa_available_import_failure_falls_back_to_isa(self, ui_interface, monkeypatch):
        """Test ISA check falls back to direct check when helper import fails."""
        ui, logger_mock, angel_interface_mock = ui_interface
        monkeypatch.setattr("xbmc.getCondVisibility", self._make_cond_visibility(True, True))

        import builtins

        real_import = builtins.__import__

        def _fake_import(name, *args, **kwargs):
            if name == "inputstreamhelper":
                raise ImportError("inject import failure")
            return real_import(name, *args, **kwargs)

        monkeypatch.setattr(builtins, "__import__", _fake_import)
        assert ui.playback_handler._ensure_isa_available("hls") is True


class _ScriptedPlayer:
    """Playback stand-in whose playing flag and clock are a fixed list."""

    def __init__(self, playing, times=None, pause_at=None, fail_seek=False, stop_after_time=False):
        self.stopped = False
        self.ended = False
        self.paused = False
        self.on_pause = None
        self._playing = list(playing)
        self._times = list(times or [])
        self.pause_at = pause_at
        self.fail_seek = fail_seek
        self.stop_after_time = stop_after_time
        self.seek_calls = []
        self._did_pause = False

    def isPlayingVideo(self):
        if not self._playing:
            return False
        return self._playing.pop(0)

    def getTime(self):
        if self.pause_at is not None and self.on_pause is not None and not self._did_pause:
            self._did_pause = True
            self.paused = True
            self.on_pause(self.pause_at)
        if not self._times:
            raise RuntimeError("no time")
        value = self._times.pop(0)
        if self.stop_after_time:
            self.stopped = True
        return value

    def seekTime(self, seconds):
        if self.fail_seek:
            raise RuntimeError("seek failed")
        self.seek_calls.append(seconds)


class _ScriptedMonitor:
    def __init__(self, abort=False, wait_abort=False, abort_after=None, wait_abort_after=None):
        self.abort = abort
        self.wait_abort = wait_abort
        self.abort_after = abort_after
        self.wait_abort_after = wait_abort_after
        self.abort_calls = 0
        self.wait_calls = 0

    def abortRequested(self):
        self.abort_calls += 1
        if self.abort_after is not None:
            return self.abort_calls >= self.abort_after
        return self.abort

    def waitForAbort(self, _seconds):
        self.wait_calls += 1
        if self.wait_abort_after is not None:
            return self.wait_calls >= self.wait_abort_after
        return self.wait_abort


class TestWatchProgressPlayback:
    def _project(self):
        project = copy.deepcopy(MOCK_PROJECT_DATA["single_season_project"])
        episode = project["seasons"][0]["episodes"][0]
        return project, episode

    def _play(self, ui, content_type, saved, resume, episode_extra=None):
        project, episode = self._project()
        if episode_extra:
            episode.update(episode_extra)
        ui.angel_interface.get_watch_position.return_value = saved
        with (
            patch.object(ui, "_get_project", return_value=project),
            patch.object(ui.playback_handler, "play_video") as play_video,
        ):
            ui.play_episode(episode["guid"], project["slug"], content_type, resume=resume)
        return play_video, episode, project

    @pytest.mark.parametrize("content_type", ["movies", "series", "specials"])
    def test_resume_choice_seeks_saved_position(self, ui_interface, content_type):
        """Kodi's Resume choice seeks to Angel's saved seconds."""
        ui, _, _ = ui_interface
        play_video, episode, project = self._play(ui, content_type, 125, True)

        play_video.assert_called_once_with(
            episode_data={"episode": episode, "project": project},
            resume_at=125.0,
            saved_position=125.0,
            clear_kodi_stop=True,
        )

    def test_play_from_beginning_does_not_seek(self, ui_interface):
        """Play from beginning still remembers the saved position for the opening guard."""
        ui, _, _ = ui_interface
        play_video, episode, project = self._play(ui, "series", 125, False)

        play_video.assert_called_once_with(
            episode_data={"episode": episode, "project": project},
            resume_at=None,
            saved_position=125.0,
            clear_kodi_stop=True,
        )

    def test_continue_watching_does_not_seek(self, ui_interface):
        """Continue Watching does not use the catalog resume choice."""
        ui, _, _ = ui_interface
        play_video, episode, project = self._play(ui, "", 125, True)

        play_video.assert_called_once_with(
            episode_data={"episode": episode, "project": project},
            resume_at=None,
            saved_position=125.0,
            clear_kodi_stop=False,
        )

    def test_no_saved_position_does_not_seek(self, ui_interface):
        """A title Angel has not started plays from the beginning."""
        ui, _, _ = ui_interface
        play_video, _, _ = self._play(ui, "series", None, True)

        assert play_video.call_args.kwargs["resume_at"] is None
        assert play_video.call_args.kwargs["saved_position"] is None

    def test_fresh_zero_does_not_use_a_stale_episode_position(self, ui_interface):
        """A real zero from Angel wins over an older position copied onto the episode."""
        ui, _, _ = ui_interface
        play_video, _, _ = self._play(
            ui, "series", 0, True, episode_extra={"watch_position": 500, "watchPosition": {"position": 500}}
        )

        assert play_video.call_args.kwargs["saved_position"] == 0.0
        assert play_video.call_args.kwargs["resume_at"] is None

    def test_read_failure_falls_back_to_the_episode(self, ui_interface):
        """When the fresh read fails, Resume seeks to the position already on the episode."""
        ui, logger, _ = ui_interface
        project, episode = self._project()
        episode["watchPosition"] = {"position": 90}
        ui.angel_interface.get_watch_position.side_effect = RuntimeError("down")
        with (
            patch.object(ui, "_get_project", return_value=project),
            patch.object(ui.playback_handler, "play_video") as play_video,
            patch.object(ui, "show_error") as show_error,
        ):
            ui.play_episode(episode["guid"], project["slug"], "specials", resume=True)

        show_error.assert_not_called()
        logger.warning.assert_any_call(f"Could not read watch position for {episode['guid']}: down")
        assert play_video.call_args.kwargs["resume_at"] == 90.0
        assert play_video.call_args.kwargs["saved_position"] == 90.0

    def test_cached_episode_seeks_when_resume_was_chosen(self, ui_interface):
        """A cached catalog title seeks when Kodi chose Resume."""
        ui, _, _ = ui_interface
        _, episode = self._project()
        episode["project"] = {"name": "Cached"}
        ui.angel_interface.get_watch_position.return_value = 40
        with (
            patch.object(ui.cache_manager, "_get_episode", return_value=episode),
            patch.object(ui.playback_handler, "play_video") as play_video,
        ):
            ui.play_episode(episode["guid"], episode["projectSlug"], "movies", resume=True)

        play_video.assert_called_once_with(
            episode_data={"episode": episode, "project": {"name": "Cached"}},
            resume_at=40.0,
            saved_position=40.0,
            clear_kodi_stop=True,
        )

    def _play_url(self):
        plugin = "plugin://plugin.video.angelstudios/"
        query = "?action=play_episode&content_type=series&episode_guid=abc"
        return plugin, query, plugin + query

    def _play_and_record(self, ui, argv, rpc, resume_at, clear_kodi_stop):
        order = []

        def wrapped_rpc(payload):
            order.append("clear")
            return rpc(payload)

        def resolve(*_args, **_kwargs):
            order.append("resolve")

        with (
            patch("kodi_playback_handler.sys.argv", argv),
            patch("kodi_playback_handler.xbmc.executeJSONRPC", side_effect=wrapped_rpc),
            patch("xbmcplugin.setResolvedUrl", side_effect=resolve),
        ):
            ui.playback_handler.play_video(
                episode_data={"episode": {"source": {"url": "http://example/master.m3u8"}}, "project": {}},
                resume_at=resume_at,
                saved_position=80,
                clear_kodi_stop=clear_kodi_stop,
            )
        return order

    @pytest.mark.parametrize("resume_at", [80, None])
    def test_catalog_play_clears_kodi_stop_before_resolve(self, ui_interface, resume_at):
        """Resume and Play from beginning both drop Kodi's stored stop before the stream starts."""
        ui, logger, _ = ui_interface
        plugin, query, play_url = self._play_url()
        seen = {}

        def rpc(payload):
            seen["body"] = json.loads(payload)
            return '{"jsonrpc":"2.0","id":1,"result":"OK"}'

        order = self._play_and_record(ui, [plugin, "5", query, "resume:true"], rpc, resume_at, True)

        assert order == ["clear", "resolve"]
        assert seen["body"]["method"] == "Files.SetFileDetails"
        assert seen["body"]["params"] == {
            "file": play_url,
            "media": "video",
            "resume": {"position": 0, "total": 0},
        }
        logger.info.assert_any_call("Cleared Kodi's stored stop")

    def test_continue_watching_does_not_clear_kodi_stop(self, ui_interface):
        """Continue Watching keeps Kodi's own stop. It does not use the catalog resume time."""
        ui, _, _ = ui_interface
        plugin, query, _ = self._play_url()

        def rpc(_payload):
            raise AssertionError("Continue Watching must not clear Kodi's stored stop")

        order = self._play_and_record(ui, [plugin, "5", query], rpc, None, False)

        assert order == ["resolve"]

    def test_clear_failure_still_starts_playback(self, ui_interface):
        """A JSON-RPC error is logged. The stream still starts."""
        ui, logger, _ = ui_interface
        plugin, query, _ = self._play_url()

        def rpc(_payload):
            return '{"error":{"code":-32602,"message":"Invalid params."}}'

        order = self._play_and_record(ui, [plugin, "5", query], rpc, 80, True)

        assert order == ["clear", "resolve"]
        logger.warning.assert_any_call(
            'Could not clear Kodi\'s stored stop: {"error":{"code":-32602,"message":"Invalid params."}}'
        )

    def test_clear_exception_still_starts_playback(self, ui_interface):
        """A JSON-RPC exception is logged. The stream still starts."""
        ui, logger, _ = ui_interface
        plugin, query, _ = self._play_url()

        def rpc(_payload):
            raise RuntimeError("rpc down")

        order = self._play_and_record(ui, [plugin, "5", query], rpc, None, True)

        assert order == ["clear", "resolve"]
        logger.warning.assert_any_call("Could not clear Kodi's stored stop: rpc down")

    @pytest.mark.parametrize(
        "argv",
        [
            ["plugin://plugin.video.angelstudios/"],
            ["not-a-plugin", "5", "?action=play_episode"],
            ["plugin://plugin.video.angelstudios/", "5", "action=play_episode"],
        ],
    )
    def test_missing_play_url_still_starts_playback(self, ui_interface, argv):
        """No plugin URL means there is nothing to clear. Playback still starts."""
        ui, logger, _ = ui_interface

        def rpc(_payload):
            raise AssertionError("missing play URL must not call JSON-RPC")

        order = self._play_and_record(ui, argv, rpc, 80, True)

        assert order == ["resolve"]
        logger.warning.assert_any_call("Could not clear Kodi's stored stop: play URL is missing")

    def test_player_callbacks_record_pause_and_stop(self):
        """Pause reads the playhead. Stop, end, and error all end the watch."""
        import kodi_playback_handler

        player = kodi_playback_handler._WatchProgressPlayer()
        assert player.isPlayingVideo() is False
        assert player.getTime() == 0
        assert player.seekTime(3) is None

        seen = []
        player.on_pause = seen.append
        player.getTime = MagicMock(return_value=44)
        player.onPlayBackPaused()
        assert player.paused is True
        assert seen == [44]

        player.getTime.side_effect = RuntimeError("gone")
        player.onPlayBackPaused()
        assert seen == [44, None]

        player.on_pause = None
        player.onPlayBackPaused()
        player.onPlayBackResumed()
        assert player.paused is False
        player.onPlayBackStopped()
        assert player.stopped is True
        assert player.ended is False
        player.stopped = False
        player.onPlayBackEnded()
        assert player.stopped is True
        assert player.ended is True
        player.stopped = False
        player.ended = False
        player.onPlayBackError()
        assert player.stopped is True
        assert player.ended is False

        class RealPlayer:
            pass

        original = kodi_playback_handler.xbmc.Player
        kodi_playback_handler.xbmc.Player = RealPlayer
        try:
            assert kodi_playback_handler._kodi_player_type() is RealPlayer
        finally:
            kodi_playback_handler.xbmc.Player = original

    def _run_monitor(
        self, ui, player, saved, resume_at, now_values, guid="title-guid", monitor=None, project_slug=None
    ):
        import kodi_playback_handler

        if monitor is None:
            monitor = _ScriptedMonitor()
        times = iter(now_values)

        def monotonic():
            try:
                return next(times)
            except StopIteration:
                return now_values[-1]

        with (
            patch("kodi_playback_handler._WatchProgressPlayer", return_value=player),
            patch("kodi_playback_handler.xbmc.Monitor", return_value=monitor),
            patch("kodi_playback_handler.time.monotonic", side_effect=monotonic),
        ):
            ui.playback_handler._monitor_watch_progress(guid, saved, resume_at, project_slug)
        return kodi_playback_handler

    def test_monitor_reports_each_minute_and_on_stop(self, ui_interface):
        """Once playback is running, a minute tick and the stop both go to Angel."""
        ui, _, angel = ui_interface
        angel.upsert_watch_position.return_value = True
        player = _ScriptedPlayer([False, True, True, True, False], times=[100, 130])

        self._run_monitor(ui, player, saved=500, resume_at=None, now_values=[0, 60, 61])

        assert angel.upsert_watch_position.call_args_list[0].args == ("title-guid", 100)
        assert angel.upsert_watch_position.call_args_list[0].kwargs == {"event_type": "heartbeat"}
        assert angel.upsert_watch_position.call_args_list[1].args == ("title-guid", 130)
        assert angel.upsert_watch_position.call_args_list[1].kwargs == {"event_type": "stop_exit"}

    def test_successful_save_updates_the_cached_resume_time(self, ui_interface):
        """The next episode list reads the cache, so a save has to land there."""
        ui, _, angel = ui_interface
        angel.upsert_watch_position.return_value = True
        ui.cache_manager.addon.getSettingBool.side_effect = lambda key: key != "disable_cache"
        ui.cache_manager.addon.getSettingInt.return_value = 8
        project = {
            "slug": "tuttle-twins",
            "seasons": [
                {
                    "episodes": [
                        {"guid": "title-guid", "watchPosition": {"position": 1220}},
                        {"guid": "other", "watchPosition": {"position": 10}},
                    ]
                }
            ],
        }
        episode = {"guid": "title-guid", "watchPosition": {"position": 1220}}
        resume = {"episodes": [{"guid": "title-guid", "watchPosition": {"position": 1220}}]}
        store = {
            "project_tuttle-twins": project,
            "episode_title-guid": episode,
            "resume_watching_10_none": resume,
        }
        ui.cache_manager.cache.get.side_effect = store.get
        ui.cache_manager.cache.set.side_effect = lambda key, value, expiration=None: store.__setitem__(key, value)
        player = _ScriptedPlayer([False, True, True, False], times=[77])

        self._run_monitor(ui, player, saved=1220, resume_at=None, now_values=[0, 0], project_slug="tuttle-twins")

        assert project["seasons"][0]["episodes"][0]["watchPosition"]["position"] == 77
        assert project["seasons"][0]["episodes"][1]["watchPosition"]["position"] == 10
        assert episode["watchPosition"]["position"] == 77
        assert resume["episodes"][0]["watchPosition"]["position"] == 1220

    def test_rejected_save_leaves_the_cached_resume_time(self, ui_interface):
        """A failed write must not change the time the resume dialog will show."""
        ui, _, angel = ui_interface
        angel.upsert_watch_position.return_value = False
        player = _ScriptedPlayer([False, True, True, False], times=[77])

        with patch.object(ui.cache_manager, "remember_watch_position") as remember:
            self._run_monitor(ui, player, saved=1220, resume_at=None, now_values=[0, 0], project_slug="tuttle-twins")

        remember.assert_not_called()

    def test_monitor_seeks_then_reports_stop(self, ui_interface):
        """Resume seeks to the saved seconds, then stop reports where playback ended."""
        ui, _, angel = ui_interface
        angel.upsert_watch_position.return_value = True
        player = _ScriptedPlayer([False, True, True, False], times=[130])

        self._run_monitor(ui, player, saved=125, resume_at=125, now_values=[0, 0])

        assert player.seek_calls == [125.0]
        angel.upsert_watch_position.assert_called_once_with("title-guid", 130, event_type="stop_exit")

    def test_stop_in_the_opening_keeps_the_saved_position(self, ui_interface):
        """Stopping in the first few seconds does not replace Angel's saved position."""
        ui, _, angel = ui_interface
        player = _ScriptedPlayer([False, True, True, False], times=[2])

        self._run_monitor(ui, player, saved=1200, resume_at=None, now_values=[0, 0])

        angel.upsert_watch_position.assert_not_called()

    def test_pause_reports_the_playhead(self, ui_interface):
        """Pause sends the current seconds before playback continues."""
        ui, _, angel = ui_interface
        angel.upsert_watch_position.return_value = True
        player = _ScriptedPlayer([False, True, True, False], times=[140], pause_at=140)

        self._run_monitor(ui, player, saved=100, resume_at=None, now_values=[0, 0])

        assert angel.upsert_watch_position.call_count == 2
        assert all(call.args == ("title-guid", 140) for call in angel.upsert_watch_position.call_args_list)
        assert angel.upsert_watch_position.call_args_list[0].kwargs == {"event_type": "pause"}
        assert angel.upsert_watch_position.call_args_list[1].kwargs == {"event_type": "stop_exit"}

    def test_successful_save_blocks_a_later_opening_position(self, ui_interface):
        """After Angel accepts a position, a later reading at the start is not sent."""
        ui, _, angel = ui_interface
        angel.upsert_watch_position.return_value = True
        player = _ScriptedPlayer([False, True, True, True, False], times=[80, 2])

        self._run_monitor(ui, player, saved=None, resume_at=None, now_values=[0, 60, 60])

        angel.upsert_watch_position.assert_called_once_with("title-guid", 80, event_type="heartbeat")

    def test_rejected_save_still_reports_a_later_position(self, ui_interface):
        """A failed write does not pretend Angel stored the position."""
        ui, _, angel = ui_interface
        angel.upsert_watch_position.return_value = False
        player = _ScriptedPlayer([False, True, True, True, False], times=[80, 2])

        self._run_monitor(ui, player, saved=None, resume_at=None, now_values=[0, 60, 60])

        assert angel.upsert_watch_position.call_args_list[0].args == ("title-guid", 80)
        assert angel.upsert_watch_position.call_args_list[1].args == ("title-guid", 2)

    def test_seek_failure_still_reports_stop(self, ui_interface):
        """A failed seek logs and playback still reports where it stopped."""
        ui, logger, angel = ui_interface
        angel.upsert_watch_position.return_value = True
        player = _ScriptedPlayer([False, True, True, False], times=[80], fail_seek=True)

        self._run_monitor(ui, player, saved=None, resume_at=90, now_values=[0, 0])

        logger.warning.assert_any_call("Could not resume at 90s: seek failed")
        angel.upsert_watch_position.assert_called_once_with("title-guid", 80, event_type="stop_exit")

    def test_missing_clock_uses_the_last_position(self, ui_interface):
        """If the playhead disappears, the last reading is what gets sent."""
        ui, _, angel = ui_interface
        angel.upsert_watch_position.return_value = True
        player = _ScriptedPlayer([False, True, True, True, False], times=[80])

        self._run_monitor(ui, player, saved=None, resume_at=None, now_values=[0, 0, 0])

        angel.upsert_watch_position.assert_called_once_with("title-guid", 80, event_type="stop_exit")

    def test_stop_callback_ends_the_watch_and_reports(self, ui_interface):
        """onPlayBackStopped ends the loop and the last position is sent."""
        ui, _, angel = ui_interface
        angel.upsert_watch_position.return_value = True
        player = _ScriptedPlayer([False, True, True], times=[88], stop_after_time=True)

        self._run_monitor(ui, player, saved=None, resume_at=None, now_values=[0, 0])

        assert player.stopped is True
        angel.upsert_watch_position.assert_called_once_with("title-guid", 88, event_type="stop_exit")

    def test_ended_playback_reports_complete(self, ui_interface):
        """A video that finishes sends complete, which is the website's end event."""
        ui, _, angel = ui_interface
        angel.upsert_watch_position.return_value = True
        player = _ScriptedPlayer([False, True, True, False], times=[80])
        player.ended = True

        self._run_monitor(ui, player, saved=None, resume_at=None, now_values=[0, 0])

        angel.upsert_watch_position.assert_called_once_with("title-guid", 80, event_type="complete")

    def test_abort_during_playback_sends_the_last_position(self, ui_interface):
        """Kodi shutting down mid-playback still sends the last position."""
        ui, _, angel = ui_interface
        angel.upsert_watch_position.return_value = True
        player = _ScriptedPlayer([False, True, True], times=[70])
        # Startup uses two abort checks. The play loop reads one sample, then aborts.
        monitor = _ScriptedMonitor(abort_after=4)

        self._run_monitor(ui, player, saved=None, resume_at=None, now_values=[0, 0], monitor=monitor)

        angel.upsert_watch_position.assert_called_once_with("title-guid", 70, event_type="stop_exit")

    def test_wait_abort_during_playback_sends_the_last_position(self, ui_interface):
        """Abort while the loop is waiting still sends the position just read."""
        ui, _, angel = ui_interface
        angel.upsert_watch_position.return_value = True
        player = _ScriptedPlayer([False, True, True], times=[70])
        # The first wait is startup. The second is the play loop.
        monitor = _ScriptedMonitor(wait_abort_after=2)

        self._run_monitor(ui, player, saved=None, resume_at=None, now_values=[0, 0], monitor=monitor)

        angel.upsert_watch_position.assert_called_once_with("title-guid", 70, event_type="stop_exit")

    def test_monitor_stops_when_kodi_aborts(self, ui_interface):
        """Shutdown during startup does not send a position."""
        ui, _, angel = ui_interface
        player = _ScriptedPlayer([True])
        with (
            patch("kodi_playback_handler._WatchProgressPlayer", return_value=player),
            patch("kodi_playback_handler.xbmc.Monitor", return_value=_ScriptedMonitor(abort=True)),
        ):
            ui.playback_handler._monitor_watch_progress("title-guid", 100, None)
        angel.upsert_watch_position.assert_not_called()

    def test_monitor_stops_when_wait_aborts(self, ui_interface):
        """Abort while waiting for playback to start does not send a position."""
        ui, _, angel = ui_interface
        player = _ScriptedPlayer([False])
        with (
            patch("kodi_playback_handler._WatchProgressPlayer", return_value=player),
            patch("kodi_playback_handler.xbmc.Monitor", return_value=_ScriptedMonitor(wait_abort=True)),
        ):
            ui.playback_handler._monitor_watch_progress("title-guid", 100, None)
        angel.upsert_watch_position.assert_not_called()

    def test_playback_that_never_starts_is_not_reported(self, ui_interface, monkeypatch):
        """Give up when the stream never starts, and leave Angel's position alone."""
        ui, logger, angel = ui_interface
        import kodi_playback_handler

        monkeypatch.setattr(kodi_playback_handler, "_PLAYBACK_START_TIMEOUT", 0.2)
        monkeypatch.setattr(kodi_playback_handler, "_PLAYBACK_START_POLL", 0.2)
        player = _ScriptedPlayer([False])
        with (
            patch("kodi_playback_handler._WatchProgressPlayer", return_value=player),
            patch("kodi_playback_handler.xbmc.Monitor", return_value=_ScriptedMonitor()),
        ):
            ui.playback_handler._monitor_watch_progress("title-guid", 100, 100)
        angel.upsert_watch_position.assert_not_called()
        logger.info.assert_any_call("Playback did not start; watch position was not updated")

    def test_monitor_ignores_a_video_that_is_already_playing(self, ui_interface, monkeypatch):
        """A different video that is already playing is not this episode."""
        ui, logger, angel = ui_interface
        import kodi_playback_handler

        monkeypatch.setattr(kodi_playback_handler, "_PLAYBACK_START_TIMEOUT", 0.4)
        monkeypatch.setattr(kodi_playback_handler, "_PLAYBACK_START_POLL", 0.2)
        player = _ScriptedPlayer([True, True], times=[40])
        player.expected_file = "plugin://plugin.video.angelstudios/?action=play_episode&episode_guid=title-guid"
        player.getPlayingFile = lambda: "plugin://plugin.video.angelstudios/?action=play_episode&episode_guid=other"

        self._run_monitor(ui, player, saved=100, resume_at=80, now_values=[0])

        angel.upsert_watch_position.assert_not_called()
        assert player.seek_calls == []
        logger.info.assert_any_call("Playback did not start; watch position was not updated")

    def test_monitor_waits_until_the_requested_episode_starts(self, ui_interface):
        """Seek and progress start only after the playing file is this episode."""
        ui, _, angel = ui_interface
        angel.upsert_watch_position.return_value = True
        expected = "plugin://plugin.video.angelstudios/?action=play_episode&episode_guid=title-guid"
        files = iter(["plugin://other", expected, expected])
        player = _ScriptedPlayer([True, True, True, False], times=[90])
        player.expected_file = expected
        player.getPlayingFile = lambda: next(files)

        self._run_monitor(ui, player, saved=80, resume_at=80, now_values=[0, 0])

        assert player.seek_calls == [80.0]
        angel.upsert_watch_position.assert_called_once_with("title-guid", 90, event_type="stop_exit")

    def test_monitor_accepts_the_resolved_stream_address(self, ui_interface):
        """The stream URL Kodi reports after resolve is still this episode."""
        ui, _, angel = ui_interface
        angel.upsert_watch_position.return_value = True
        plugin = "plugin://plugin.video.angelstudios/?action=play_episode&episode_guid=title-guid"
        stream = "https://api.angelstudios.com/streaming/title-guid/master.m3u8"
        player = _ScriptedPlayer([True, True, False], times=[610])
        player.expected_file = plugin
        player.stream_file = stream
        player.getPlayingFile = lambda: stream

        self._run_monitor(ui, player, saved=600, resume_at=600, now_values=[0, 0])

        assert player.seek_calls == [600.0]
        angel.upsert_watch_position.assert_called_once_with("title-guid", 610, event_type="stop_exit")

    def test_monitor_keeps_watching_when_the_file_becomes_the_stream(self, ui_interface):
        """A change from the plugin URL to the stream URL is the same episode."""
        ui, _, angel = ui_interface
        angel.upsert_watch_position.return_value = True
        plugin = "plugin://plugin.video.angelstudios/?action=play_episode&episode_guid=title-guid"
        stream = "https://api.angelstudios.com/streaming/title-guid/master.m3u8"
        files = iter([plugin, stream, stream])
        player = _ScriptedPlayer([True, True, True, False], times=[610, 620])
        player.expected_file = plugin
        player.stream_file = stream
        player.getPlayingFile = lambda: next(files)

        self._run_monitor(ui, player, saved=600, resume_at=600, now_values=[0, 0])

        angel.upsert_watch_position.assert_called_once_with("title-guid", 620, event_type="stop_exit")

    def test_monitor_ignores_a_different_stream(self, ui_interface, monkeypatch):
        """Another title's stream is not this episode."""
        ui, logger, angel = ui_interface
        import kodi_playback_handler

        monkeypatch.setattr(kodi_playback_handler, "_PLAYBACK_START_TIMEOUT", 0.4)
        monkeypatch.setattr(kodi_playback_handler, "_PLAYBACK_START_POLL", 0.2)
        plugin = "plugin://plugin.video.angelstudios/?action=play_episode&episode_guid=title-guid"
        stream = "https://api.angelstudios.com/streaming/title-guid/master.m3u8"
        player = _ScriptedPlayer([True, True], times=[610])
        player.expected_file = plugin
        player.stream_file = stream
        player.getPlayingFile = lambda: "https://api.angelstudios.com/streaming/other/master.m3u8"

        self._run_monitor(ui, player, saved=600, resume_at=600, now_values=[0])

        angel.upsert_watch_position.assert_not_called()
        assert player.seek_calls == []
        logger.info.assert_any_call("Playback did not start; watch position was not updated")

    def test_stop_uses_the_position_captured_when_playback_stopped(self, ui_interface):
        """A heartbeat sampled earlier does not replace the position taken at stop."""
        ui, _, angel = ui_interface
        angel.upsert_watch_position.return_value = True
        player = _ScriptedPlayer([False, True, True, True, False], times=[100, 100])
        player.stop_position = 155

        self._run_monitor(ui, player, saved=None, resume_at=None, now_values=[0, 60, 61])

        assert angel.upsert_watch_position.call_args_list[0].args == ("title-guid", 100)
        assert angel.upsert_watch_position.call_args_list[0].kwargs == {"event_type": "heartbeat"}
        assert angel.upsert_watch_position.call_args_list[1].args == ("title-guid", 155)
        assert angel.upsert_watch_position.call_args_list[1].kwargs == {"event_type": "stop_exit"}

    def test_player_is_registered_before_the_stream_resolves(self, ui_interface, monkeypatch):
        """The player exists before Resolve, so the previous video's stop is visible."""
        ui, _, _ = ui_interface
        import kodi_playback_handler

        monkeypatch.setattr(kodi_playback_handler, "_PLAYBACK_START_TIMEOUT", 0.2)
        monkeypatch.setattr(kodi_playback_handler, "_PLAYBACK_START_POLL", 0.2)
        plugin, query, play_url = self._play_url()
        order = []
        player = _ScriptedPlayer([False])

        def factory():
            order.append("player")
            return player

        def resolve(*_args, **_kwargs):
            order.append("resolve")

        with (
            patch("kodi_playback_handler.sys.argv", [plugin, "5", query]),
            patch("kodi_playback_handler._WatchProgressPlayer", side_effect=factory),
            patch("xbmcplugin.setResolvedUrl", side_effect=resolve),
            patch("kodi_playback_handler.xbmc.Monitor", return_value=_ScriptedMonitor()),
        ):
            ui.playback_handler.play_video(
                episode_data={"episode": {"guid": "abc", "subtitle": "One"}, "project": {}},
                resume_at=None,
                saved_position=80,
                clear_kodi_stop=False,
            )

        assert order == ["player", "resolve"]
        assert player.expected_file == play_url

    def test_player_records_the_stream_address_before_resolve(self, ui_interface, monkeypatch):
        """The stream URL is stored with the player before Kodi opens the file."""
        ui, _, _ = ui_interface
        import kodi_playback_handler

        monkeypatch.setattr(kodi_playback_handler, "_PLAYBACK_START_TIMEOUT", 0.2)
        monkeypatch.setattr(kodi_playback_handler, "_PLAYBACK_START_POLL", 0.2)
        plugin, query, play_url = self._play_url()
        stream = "https://api.angelstudios.com/streaming/abc/master.m3u8"
        player = _ScriptedPlayer([False])

        class _Item:
            def getPath(self):
                return stream

        with (
            patch("kodi_playback_handler.sys.argv", [plugin, "5", query]),
            patch("kodi_playback_handler._WatchProgressPlayer", return_value=player),
            patch.object(ui.menu_handler, "_create_list_item_from_episode", return_value=_Item()),
            patch("xbmcplugin.setResolvedUrl"),
            patch("kodi_playback_handler.xbmc.Monitor", return_value=_ScriptedMonitor()),
        ):
            ui.playback_handler.play_video(
                episode_data={"episode": {"guid": "abc", "subtitle": "One"}, "project": {}},
                resume_at=None,
                saved_position=80,
                clear_kodi_stop=False,
            )

        assert player.expected_file == play_url
        assert player.stream_file == stream

    def test_send_failure_does_not_raise(self, ui_interface):
        """A write error is logged. The monitor still returns."""
        ui, logger, angel = ui_interface
        angel.upsert_watch_position.side_effect = RuntimeError("down")
        player = _ScriptedPlayer([False, True, True, False], times=[80])

        self._run_monitor(ui, player, saved=None, resume_at=None, now_values=[0, 0])

        logger.warning.assert_any_call("Could not save watch position for title-guid: down")

    def test_missing_writer_is_logged(self, ui_interface):
        """No upsert method means the position is skipped, not a playback error."""
        ui, logger, _ = ui_interface
        ui.angel_interface = object()
        player = _ScriptedPlayer([False, True, True, False], times=[80])

        self._run_monitor(ui, player, saved=None, resume_at=None, now_values=[0, 0])

        logger.warning.assert_any_call("Watch position was not saved for title-guid")

    def test_monitor_error_does_not_show_playback_error(self, ui_interface):
        """A progress failure after the stream starts does not pop the play error."""
        ui, logger, _ = ui_interface
        with (
            patch("xbmcplugin.setResolvedUrl"),
            patch.object(ui.playback_handler, "_monitor_watch_progress", side_effect=RuntimeError("boom")),
            patch.object(ui, "show_error") as show_error,
        ):
            ui.play_video(episode_data=MOCK_EPISODE_DATA)

        show_error.assert_not_called()
        logger.warning.assert_any_call("Watch progress stopped for episode-guid-1: boom")

    def test_resolve_failure_does_not_monitor(self, ui_interface):
        """If Kodi never got the stream, progress is not watched."""
        ui, _, _ = ui_interface
        with (
            patch("xbmcplugin.setResolvedUrl", side_effect=Exception(TEST_EXCEPTION_MESSAGE)),
            patch.object(ui.playback_handler, "_monitor_watch_progress") as monitor,
            patch.object(ui, "show_error") as show_error,
        ):
            ui.play_video(episode_data=MOCK_EPISODE_DATA)

        monitor.assert_not_called()
        show_error.assert_called_once()

    def test_monitor_turns_on_the_preferred_caption_track(self, ui_interface):
        """Once the episode is playing, the preferred caption track is turned on."""
        ui, logger, angel = ui_interface
        angel.upsert_watch_position.return_value = True
        player = _ScriptedPlayer([True, True, False], times=[40])
        requests = []

        def rpc(raw):
            request = json.loads(raw)
            requests.append(request)
            method = request["method"]
            if method == "Settings.GetSettingValue":
                setting = request["params"]["setting"]
                if setting == "locale.subtitlelanguage":
                    return json.dumps({"result": {"value": "en"}})
                return json.dumps({"result": {"value": False}})
            if method == "Player.GetActivePlayers":
                return json.dumps({"result": [{"playerid": 1, "type": "video"}]})
            if method == "Player.GetProperties":
                tracks = [
                    {
                        "index": 0,
                        "name": "English",
                        "language": "eng",
                        "isdefault": False,
                        "isforced": False,
                        "isimpaired": False,
                    },
                    {
                        "index": 1,
                        "name": "Spanish (Latam)",
                        "language": "es-419",
                        "isdefault": False,
                        "isforced": False,
                        "isimpaired": False,
                    },
                ]
                return json.dumps(
                    {
                        "result": {
                            "subtitles": tracks,
                            "currentaudiostream": {"language": "eng"},
                        }
                    }
                )
            if method == "Player.SetSubtitle":
                return json.dumps({"result": "OK"})
            raise AssertionError(method)

        with patch("kodi_playback_handler.xbmc.executeJSONRPC", side_effect=rpc):
            self._run_monitor(ui, player, saved=None, resume_at=None, now_values=[0, 0])

        set_subtitle = requests[-1]
        assert set_subtitle["method"] == "Player.SetSubtitle"
        assert set_subtitle["params"] == {"playerid": 1, "subtitle": 0, "enable": True}
        logger.info.assert_any_call("Captions on: English")
        angel.upsert_watch_position.assert_called()

    def test_caption_failure_still_reports_the_stop(self, ui_interface):
        """A caption failure does not stop the watch-position report."""
        ui, logger, angel = ui_interface
        angel.upsert_watch_position.return_value = True
        player = _ScriptedPlayer([True, True, False], times=[40])

        with patch("kodi_playback_handler.apply_playback_captions", side_effect=RuntimeError("captions down")):
            self._run_monitor(ui, player, saved=None, resume_at=None, now_values=[0, 0])

        logger.warning.assert_any_call("Could not apply the caption preference: captions down")
        angel.upsert_watch_position.assert_called()
