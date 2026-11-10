"""Next Episode timing, the offer window, and the command that starts the next title."""

import json
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest

import next_episode
import next_episode_overlay
from next_episode import (
    NextEpisodeSession,
    NextEpisodeState,
    end_card_visible,
    handle_playback_action,
    inside_intro,
    next_play_command,
    playback_target,
    show_time,
    watchable_now,
)
from next_episode_overlay import NextEpisodeOverlay

ROOT = Path(__file__).resolve().parents[2] / "plugin.video.angelstudios"
NOW = datetime(2026, 11, 10, tzinfo=timezone.utc)
WORMS = "7db6bfd7-02f4-46d8-b13e-1b889bb81d2b"


def _episode(credits=1173, duration=1265, intro=None):
    episode = {"guid": "2f3d0382-ea82-4cdc-958e-84fbadadc710", "source": {"duration": duration}}
    if credits is not None:
        episode["source"]["credits"] = credits
    if intro is not None:
        episode["introStartTime"] = intro[0]
        episode["introEndTime"] = intro[1]
    return episode


def _content(
    typename="ContentEpisode",
    guid=WORMS,
    slug="tuttle-twins",
    status="WATCHABLE",
    subtitle="War of the Worms",
    actions=None,
):
    content = {
        "__typename": typename,
        "id": guid,
        "name": "Episode name",
        "subtitle": subtitle,
        "watchableAvailabilityStatus": status,
    }
    if slug is not None:
        content["project"] = {"slug": slug}
    if actions is not None:
        content["actionsToWatch"] = actions
    return content


def _session(episode=None, content=None, offer=True, autostart=True, now=NOW):
    return NextEpisodeSession(
        _episode() if episode is None else episode,
        _content() if content is None else content,
        offer,
        autostart,
        now=now,
    )


class _Action:
    def __init__(self, action_id):
        self.action_id = action_id

    def getId(self):
        return self.action_id


class _Control:
    def __init__(self, control_id):
        self.control_id = control_id
        self.label = None
        self.visible = None
        self.pos = None
        self.size = None

    def getId(self):
        return self.control_id

    def setLabel(self, text):
        self.label = text

    def setVisible(self, visible):
        self.visible = visible

    def setPosition(self, left, top):
        self.pos = (left, top)

    def setWidth(self, width):
        self.size = (width, None if self.size is None else self.size[1])

    def setHeight(self, height):
        width = None if self.size is None else self.size[0]
        self.size = (width, height)


class _Dialog:
    def __init__(self):
        self.controls = {100: _Control(100), 200: _Control(200), 302: _Control(302)}
        self.shown = False
        self.show_count = 0
        self.closed = 0
        self.focus_id = None
        self.fail_close = False

    def getControl(self, control_id):
        return self.controls[control_id]

    def show(self):
        self.shown = True
        self.show_count += 1

    def close(self):
        if self.fail_close:
            raise RuntimeError("close failed")
        self.shown = False
        self.closed += 1

    def setFocusId(self, control_id):
        self.focus_id = control_id

    def getFocusId(self):
        return self.focus_id

    def isActive(self):
        return self.shown


def _overlay(dialog=None, label="Next Episode", player=None, log=None):
    dialog = _Dialog() if dialog is None else dialog
    addon = SimpleNamespace(getLocalizedString=lambda string_id: label if string_id == 30126 else "")
    player = SimpleNamespace(stop=lambda: None) if player is None else player
    log = SimpleNamespace(info=lambda *args: None, warning=lambda *args: None) if log is None else log
    overlay = NextEpisodeOverlay(addon, player, log, dialog_factory=lambda: dialog)
    return overlay, dialog


class TestShowTime:
    def test_credits_plus_eight_unless_that_passes_the_end_limit(self):
        """S1E1 shows at 1181. S2E2 is held back to 15 seconds before the end."""
        assert show_time(1173, 1265) == 1181
        assert show_time(1375, 1382) == 1367
        assert show_time(None, 1265) == 1250
        assert show_time(0, 100) == 8
        assert show_time(None, None) == 0
        assert show_time(None, 10) == 0
        assert show_time(10, None) == 18

    @pytest.mark.parametrize(
        "position,visible",
        [(1179, False), (1180, True), (1181, True), (1300, True)],
    )
    def test_end_card_starts_one_second_before_show_time(self, position, visible):
        assert end_card_visible(position, 1181) is visible

    def test_show_time_zero_never_shows_the_end_card(self):
        assert end_card_visible(0, 0) is False
        assert end_card_visible(20, 0) is False

    def test_intro_includes_both_ends_and_needs_both_times(self):
        assert inside_intro(127, 127, 169) is True
        assert inside_intro(169, 127, 169) is True
        assert inside_intro(126.9, 127, 169) is False
        assert inside_intro(169.1, 127, 169) is False
        assert inside_intro(130, 127, None) is False
        assert inside_intro(130, None, 169) is False


class TestWatchable:
    def test_watchable_status_is_kept(self):
        assert watchable_now(_content(), NOW) is True

    def test_guild_start_that_has_passed_is_kept(self):
        """S5E1 was ACTION_REQUIRED with a Guild start on 2026-11-04."""
        actions = [{"__typename": "GuildAvailabilityAction", "startDatetime": "2026-11-04T00:00:00Z"}]
        content = _content(status="ACTION_REQUIRED", actions=actions)
        assert watchable_now(content, NOW) is True
        assert watchable_now(content, datetime(2026, 11, 4, tzinfo=timezone.utc)) is True
        assert watchable_now(content, datetime(2026, 11, 4)) is True

    def test_future_or_unreadable_guild_start_is_dropped(self):
        future = [{"__typename": "GuildAvailabilityAction", "startDatetime": "2026-12-01T00:00:00Z"}]
        broken = [{"__typename": "GuildAvailabilityAction", "startDatetime": "tomorrow"}]
        other = [{"__typename": "SomethingElse", "startDatetime": "2020-01-01T00:00:00Z"}]
        assert watchable_now(_content(status="ACTION_REQUIRED", actions=future), NOW) is False
        assert watchable_now(_content(status="ACTION_REQUIRED", actions=broken), NOW) is False
        assert watchable_now(_content(status="ACTION_REQUIRED", actions=other), NOW) is False
        assert watchable_now(_content(status="ACTION_REQUIRED", actions="nope"), NOW) is False
        assert watchable_now(_content(status="ACTION_REQUIRED", actions=[None, "x"]), NOW) is False
        assert (
            watchable_now(
                _content(
                    status="ACTION_REQUIRED",
                    actions=[{"__typename": "GuildAvailabilityAction", "startDatetime": ""}],
                ),
                NOW,
            )
            is False
        )
        assert (
            watchable_now(
                _content(
                    status="ACTION_REQUIRED",
                    actions=[{"__typename": "GuildAvailabilityAction", "startDatetime": None}],
                ),
                NOW,
            )
            is False
        )
        naive = [{"__typename": "GuildAvailabilityAction", "startDatetime": "2026-11-04T00:00:00"}]
        assert watchable_now(_content(status="ACTION_REQUIRED", actions=naive), NOW) is True
        assert watchable_now("nope", NOW) is False
        assert watchable_now({"__typename": "ContentTrailer"}, NOW) is False

    def test_playback_target_requires_a_known_type_id_and_slug(self):
        assert playback_target(_content())["content_type"] == "series"
        assert playback_target(_content(typename="ContentSpecial"))["content_type"] == "specials"
        movie = playback_target(_content(typename="ContentMovie", subtitle="The Spy Next Door"))
        assert movie["content_type"] == "movies"
        assert movie["title"] == "The Spy Next Door"
        assert playback_target(_content(slug=None)) is None
        assert playback_target(_content(guid="")) is None
        assert playback_target({"__typename": "ContentEpisode", "id": "x", "project": {}}) is None
        assert playback_target(None) is None

    def test_blank_subtitle_falls_through_to_the_name(self):
        content = _content(subtitle="  ")
        content["name"] = "Needs, Rights and Flamingo Fights"
        assert playback_target(content)["title"] == "Needs, Rights and Flamingo Fights"


class TestSession:
    def test_player_control_and_end_card_follow_the_issue_examples(self):
        """Tuttle Twins positions from the issue, including the intro on S1E2."""
        opening = _session()
        assert opening.view_at(0) == NextEpisodeState(True, False, "")
        assert opening.view_at(1179) == NextEpisodeState(True, False, "")
        assert opening.view_at(1180) == NextEpisodeState(True, True, "War of the Worms")

        second = _session(_episode(credits=1205, duration=1255, intro=(127, 169)))
        assert second.view_at(110) == NextEpisodeState(True, False, "")
        assert second.view_at(130) == NextEpisodeState(False, False, "")
        assert second.view_at(170) == NextEpisodeState(True, False, "")
        assert second.show_time == 1213

        held = _session(_episode(credits=1375, duration=1382))
        assert held.view_at(1365) == NextEpisodeState(True, False, "")
        assert held.view_at(1366) == NextEpisodeState(True, True, "War of the Worms")
        assert held.show_time == 1367

    def test_intro_hides_the_end_card_too(self):
        episode = _episode(intro=(1170, 1190))
        assert _session(episode).view_at(1180) == NextEpisodeState(False, False, "")

    def test_missing_credits_uses_fifteen_seconds_before_the_end(self):
        """One intro time is not a window. The end card still uses duration minus 15."""
        episode = {"duration": 100, "introStartTime": 1}
        session = _session(episode)
        assert session.show_time == 85
        assert session.view_at(83) == NextEpisodeState(True, False, "")
        assert session.view_at(84) == NextEpisodeState(True, True, "War of the Worms")

    def test_bool_credits_are_not_a_number(self):
        episode = {"source": {"credits": True, "duration": 100}}
        assert _session(episode).show_time == 85
        assert _session({"source": {"credits": False, "duration": False}, "duration": 100}).show_time == 85

    def test_zero_credits_are_set_and_source_wins(self):
        episode = {"source": {"credits": 0, "duration": 100}, "credits": 50, "duration": 400}
        assert _session(episode).show_time == 8

    def test_top_level_credits_are_used_when_the_source_has_none(self):
        episode = {"source": {"duration": 100}, "credits": 20}
        assert _session(episode).show_time == 28
        assert next_episode.next_title({}) == ""

    def test_no_position_or_no_target_hides_both(self):
        assert _session().view_at(None) == NextEpisodeState(False, False, "")
        assert _session().view_at("nope") == NextEpisodeState(False, False, "")
        assert _session(content={}).view_at(10) == NextEpisodeState(False, False, "")
        assert next_episode.credits_and_duration(None) == (None, None)
        assert next_episode.intro_bounds(["nope"]) == (None, None)

    @pytest.mark.parametrize(
        "offer,autostart,ended,chosen,expected",
        [
            (True, True, True, False, True),
            (True, True, False, False, False),
            (True, False, True, False, False),
            (True, False, False, True, True),
            (True, True, False, True, True),
            (False, True, True, True, False),
        ],
    )
    def test_should_start(self, offer, autostart, ended, chosen, expected):
        """Choosing starts the next title. Auto-start runs only when both settings are on and it ends."""
        session = _session(offer=offer, autostart=autostart)
        assert session.should_start(ended, chosen) is expected

    def test_offer_off_clears_auto_start(self):
        session = _session(offer=False, autostart=True, now=datetime(2026, 11, 10))
        assert session.offer_enabled is False
        assert session.autostart_enabled is False
        assert session.target is None

    def test_play_command_starts_at_the_beginning_without_the_resume_dialog(self):
        command = next_play_command(_content())
        assert command == (
            'PlayMedia("plugin://plugin.video.angelstudios/?action=play_episode'
            "&content_type=series&project_slug=tuttle-twins"
            f'&episode_guid={WORMS}&from_beginning=1",noresume)'
        )
        assert next_play_command(_session().target) == command
        assert next_play_command({"content_type": "series"}) is None
        assert next_play_command(None) is None

    @pytest.mark.parametrize(
        "action_id,focused,expected",
        [
            (7, True, "choose"),
            (100, True, "choose"),
            (135, True, "choose"),
            (3, False, "focus"),
            (3, True, None),
            (4, True, "unfocus"),
            (10, True, "unfocus"),
            (92, True, "unfocus"),
            (7, False, "osd"),
            (24, False, "osd"),
            (243, False, "osd"),
            (1, False, "smallbackward"),
            (1, True, "smallbackward"),
            (2, False, "smallforward"),
            (97, False, "bigforward"),
            (4, False, "bigbackward"),
            (98, False, "bigbackward"),
            (12, False, "pause"),
            (79, True, "pause"),
            (229, False, "pause"),
            (13, True, "stop"),
            (10, False, "back"),
            (92, False, "back"),
            (18, True, "back"),
            (11, False, "info"),
            (88, False, "volumeup"),
            (89, False, "volumedown"),
            (91, False, "mute"),
            (999, False, None),
        ],
    )
    def test_playback_actions(self, action_id, focused, expected):
        assert handle_playback_action(action_id, focused) == expected


class TestOfferFiles:
    def test_settings_and_strings_match_the_issue(self):
        settings = (ROOT / "resources/settings.xml").read_text()
        assert 'id="offer_next_episode"' in settings
        assert 'id="autostart_next_episode"' in settings
        assert '<dependency type="enable" setting="offer_next_episode">true</dependency>' in settings
        offer = settings.split('id="offer_next_episode"', 1)[1].split("</setting>", 1)[0]
        autostart = settings.split('id="autostart_next_episode"', 1)[1].split("</setting>", 1)[0]
        assert "<default>true</default>" in offer
        assert "<default>true</default>" in autostart
        assert 'label="30126"' in offer and 'help="30127"' in offer
        assert 'label="30128"' in autostart and 'help="30129"' in autostart

        strings = (ROOT / "resources/language/resource.language.en_gb/strings.po").read_text()
        assert 'msgctxt "#30126"\nmsgid "Next Episode"\nmsgstr "Next Episode"' in strings
        assert (
            'msgctxt "#30127"\nmsgid "Offer Next Episode while an episode plays."\n'
            'msgstr "Offer Next Episode while an episode plays."'
        ) in strings
        assert 'msgctxt "#30128"\nmsgid "Auto-start next episode"\nmsgstr "Auto-start next episode"' in strings
        assert (
            'msgctxt "#30129"\nmsgid "Start the next title when the episode ends."\n'
            'msgstr "Start the next title when the episode ends."'
        ) in strings

    def test_next_content_query_asks_for_guild_start_and_not_source(self):
        query = (ROOT / "resources/lib/angel_graphql/query_getNextContent.graphql").read_text()
        assert "getNextContent" in query
        for name in ("ContentEpisode", "ContentSpecial", "ContentMovie", "GuildAvailabilityAction", "startDatetime"):
            assert name in query
        assert "source" not in query

    def test_skin_keeps_select_on_the_passthrough_control(self):
        xml = (ROOT / "resources/skins/Default/1080i/NextEpisode.xml").read_text()
        assert "<defaultcontrol>100</defaultcontrol>" in xml
        assert 'id="200"' in xml
        assert 'id="302"' in xml
        assert "white.png" in xml
        texture = (ROOT / "resources/skins/Default/media/white.png").read_bytes()
        assert texture.startswith(b"\x89PNG")


class TestOverlay:
    def test_player_control_and_end_card_layouts(self):
        warnings = []
        infos = []
        log = SimpleNamespace(
            info=lambda message: infos.append(message), warning=lambda message: warnings.append(message)
        )
        overlay, dialog = _overlay(log=log)
        overlay.update(NextEpisodeState(True, False, ""))
        button = dialog.controls[200]
        title = dialog.controls[302]
        assert dialog.show_count == 1
        assert dialog.focus_id == 100
        assert button.pos == (1492, 790)
        assert button.size == (380, 70)
        assert button.label == "Next Episode"
        assert title.visible is False

        overlay.on_action(_Action(3))
        assert dialog.focus_id == 200
        overlay.update(NextEpisodeState(True, True, "War of the Worms"))
        assert dialog.focus_id == 200
        assert dialog.show_count == 1
        assert button.pos == (1312, 896)
        assert button.size == (560, 88)
        assert title.pos == (1312, 848)
        assert title.size == (560, 40)
        assert title.visible is True
        assert title.label == "War of the Worms"
        assert infos == ["Next Episode", "Next Episode end card: War of the Worms"]
        assert warnings == []

    def test_intro_closes_the_dialog_and_the_next_position_opens_it_again(self):
        overlay, dialog = _overlay()
        overlay.update(NextEpisodeState(True, False, ""))
        overlay.update(NextEpisodeState(False, False, ""))
        assert dialog.shown is False
        assert dialog.closed == 1
        overlay.update(NextEpisodeState(False, False, ""))
        assert dialog.closed == 1
        overlay.update(NextEpisodeState(True, False, ""))
        assert dialog.shown is True
        assert dialog.focus_id == 100

    def test_select_on_the_button_plays_next_and_select_elsewhere_opens_the_osd(self, monkeypatch):
        builtins = []
        stops = []
        player = SimpleNamespace(stop=lambda: stops.append("stop"))
        overlay, dialog = _overlay(player=player)
        overlay.update(NextEpisodeState(True, False, ""))

        monkeypatch.setattr(next_episode_overlay.xbmc, "executebuiltin", lambda command: builtins.append(command))
        overlay.on_action(_Action(7))
        assert builtins == ["Action(OSD)"]
        assert stops == []

        overlay.on_action(_Action(3))
        overlay.on_action(_Action(7))
        assert stops == ["stop"]
        assert overlay.chosen is True
        overlay.on_action(_Action(7))
        overlay.on_control(dialog.controls[200])
        assert stops == ["stop"]

    def test_click_on_the_button_plays_next(self):
        stops = []
        overlay, dialog = _overlay(player=SimpleNamespace(stop=lambda: stops.append("stop")))
        overlay.update(NextEpisodeState(True, False, ""))
        overlay.on_control(dialog.controls[200])
        assert stops == ["stop"]
        assert overlay.chosen is True

    def test_back_on_the_button_returns_to_passthrough_and_back_again_leaves(self, monkeypatch):
        builtins = []
        overlay, dialog = _overlay()
        overlay.update(NextEpisodeState(True, False, ""))

        def builtin(command):
            builtins.append(command)
            overlay.on_action(_Action(10))

        monkeypatch.setattr(next_episode_overlay.xbmc, "executebuiltin", builtin)
        overlay.on_action(_Action(3))
        overlay.on_action(_Action(10))
        assert dialog.focus_id == 100
        assert overlay._dismissed is False
        assert builtins == []

        overlay.on_action(_Action(10))
        assert overlay._dismissed is True
        assert builtins == ["Action(Back)"]
        assert overlay.chosen is False
        overlay.update(NextEpisodeState(True, True, "War of the Worms"))
        assert dialog.show_count == 1

    def test_left_and_right_seek_the_video_player(self, monkeypatch):
        payloads = []
        overlay, _dialog = _overlay()
        overlay.update(NextEpisodeState(True, False, ""))

        monkeypatch.setattr(
            next_episode_overlay.xbmc, "executeJSONRPC", lambda payload: payloads.append(json.loads(payload))
        )
        overlay.on_action(_Action(1))
        overlay.on_action(_Action(2))
        overlay.on_action(_Action(4))
        assert [item["params"] for item in payloads] == [
            {"playerid": 1, "value": "smallbackward"},
            {"playerid": 1, "value": "smallforward"},
            {"playerid": 1, "value": "bigbackward"},
        ]

    def test_player_commands_are_forwarded(self, monkeypatch):
        builtins = []
        overlay, _dialog = _overlay()
        overlay.update(NextEpisodeState(True, False, ""))

        monkeypatch.setattr(next_episode_overlay.xbmc, "executebuiltin", lambda command: builtins.append(command))
        for action_id in (12, 13, 11, 88, 89, 91, 24):
            overlay.on_action(_Action(action_id))
        assert builtins == [
            "PlayerControl(Play)",
            "PlayerControl(Stop)",
            "Action(Info)",
            "Action(VolumeUp)",
            "Action(VolumeDown)",
            "Action(Mute)",
            "Action(OSD)",
        ]

    def test_broken_dialog_is_not_retried(self):
        warnings = []
        log = SimpleNamespace(info=lambda *_args: None, warning=lambda message: warnings.append(message))

        def factory():
            raise RuntimeError("skin")

        addon = SimpleNamespace()
        overlay = NextEpisodeOverlay(addon, SimpleNamespace(), log, dialog_factory=factory)
        overlay.update(NextEpisodeState(True, False, ""))
        overlay.update(NextEpisodeState(True, False, ""))
        assert warnings == ["Next Episode offer could not be shown: skin"]
        assert overlay._failed is True

    def test_controls_missing_until_init_do_not_drop_the_offer(self):
        """Kodi raises Non-Existent Control until the dialog has opened."""
        warnings = []
        log = SimpleNamespace(info=lambda *_args: None, warning=lambda message: warnings.append(message))

        class LateDialog(_Dialog):
            def __init__(self):
                super().__init__()
                self.ready = False

            def getControl(self, control_id):
                if not self.ready:
                    raise RuntimeError("Non-Existent Control 200")
                return super().getControl(control_id)

        dialog = LateDialog()
        overlay, _dialog = _overlay(dialog=dialog, log=log)
        overlay.update(NextEpisodeState(True, False, ""))
        overlay.update(NextEpisodeState(True, False, ""))
        assert overlay._failed is False
        assert dialog.show_count == 1
        assert dialog.controls[200].label is None
        assert warnings == ["Next Episode controls are not ready: Non-Existent Control 200"]

        dialog.ready = True
        overlay.on_init()
        assert dialog.controls[200].label == "Next Episode"
        assert dialog.controls[200].pos == (1492, 790)
        assert dialog.focus_id == 100

        overlay.on_action(_Action(3))
        overlay.update(NextEpisodeState(True, True, "War of the Worms"))
        assert dialog.focus_id == 200
        assert dialog.controls[302].label == "War of the Worms"
        assert dialog.controls[302].visible is True

    def test_missing_translation_uses_the_english_label(self):
        dialog = _Dialog()
        for label in ("", "30126", None):
            addon = SimpleNamespace(getLocalizedString=lambda _string_id, label=label: label)
            overlay = NextEpisodeOverlay(
                addon, SimpleNamespace(), SimpleNamespace(info=lambda *_a: None), dialog_factory=lambda: dialog
            )
            overlay.update(NextEpisodeState(True, False, ""))
            assert dialog.controls[200].label == "Next Episode"
            overlay.close()

    def test_stop_failure_still_counts_as_chosen(self):
        warnings = []

        def stop():
            raise RuntimeError("busy")

        log = SimpleNamespace(info=lambda *_a: None, warning=lambda message: warnings.append(message))
        overlay, _dialog = _overlay(player=SimpleNamespace(stop=stop), log=log)
        overlay.update(NextEpisodeState(True, False, ""))
        overlay.on_action(_Action(3))
        overlay.on_action(_Action(7))
        assert overlay.chosen is True
        assert warnings == ["Could not stop playback for the next episode: busy"]

    def test_dialog_callbacks_reach_the_overlay(self, monkeypatch):
        created = {}

        class Base:
            def __init__(self, xml, path, skin, res):
                created["args"] = (xml, path, skin, res)

        monkeypatch.setattr(next_episode_overlay.xbmcgui, "WindowXMLDialog", Base)
        addon = SimpleNamespace(getAddonInfo=lambda key: "/addon" if key == "path" else None)
        overlay = NextEpisodeOverlay(addon, SimpleNamespace(stop=lambda: None), SimpleNamespace(info=lambda *_a: None))
        dialog = overlay._ensure_dialog()
        assert created["args"] == ("NextEpisode.xml", "/addon", "Default", "1080i")
        dialog.onInit()
        dialog.onAction(_Action(11))
        dialog.onControl(SimpleNamespace(getId=lambda: 200))
        assert overlay._dialog is dialog

        addon.getAddonInfo = lambda _key: None
        next_episode_overlay._open_dialog(overlay, addon)
        assert created["args"] == ("NextEpisode.xml", "", "Default", "1080i")

    def test_seek_and_builtin_failures_are_logged(self, monkeypatch):
        warnings = []
        log = SimpleNamespace(info=lambda *_a: None, warning=lambda message: warnings.append(message))
        overlay, dialog = _overlay(log=log)
        overlay.update(NextEpisodeState(True, False, ""))

        def fail_rpc(_payload):
            raise RuntimeError("rpc")

        def fail_builtin(_command):
            raise RuntimeError("builtin")

        monkeypatch.setattr(next_episode_overlay.xbmc, "executeJSONRPC", fail_rpc)
        monkeypatch.setattr(next_episode_overlay.xbmc, "executebuiltin", fail_builtin)
        overlay.on_action(_Action(1))
        overlay.on_action(_Action(11))
        dialog.fail_close = True
        overlay.close()
        assert warnings == [
            "Could not seek: rpc",
            "Could not run Action(Info): builtin",
            "Next Episode offer could not be closed: close failed",
        ]

    def test_ignored_actions_do_not_change_focus(self):
        overlay, dialog = _overlay()
        overlay.update(NextEpisodeState(True, False, ""))
        overlay.on_action(SimpleNamespace(getId=lambda: True))
        overlay.on_action(SimpleNamespace(getId=lambda: None))
        overlay.on_action(_Action(999))
        overlay.on_control(SimpleNamespace(getId=lambda: 100))
        assert dialog.focus_id == 100
        assert overlay.chosen is False
