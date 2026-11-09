"""Tests for watch-progress reporting rules."""

from unittest.mock import MagicMock

from watch_progress import (
    BEGINNING_SECONDS,
    WatchProgressSession,
    apply_saved_position,
    coerce_seconds,
    native_resume_point,
    patch_project_watch_position,
    position_from_episode,
    should_report_position,
)


class TestCoerceSeconds:
    def test_numbers_and_numeric_strings(self):
        assert coerce_seconds(12) == 12.0
        assert coerce_seconds(12.5) == 12.5
        assert coerce_seconds("8.5") == 8.5

    def test_rejects_non_positions(self):
        assert coerce_seconds(None) is None
        assert coerce_seconds(True) is None
        assert coerce_seconds("nope") is None
        assert coerce_seconds({"position": 1}) is None
        assert coerce_seconds(MagicMock()) is None


class TestPositionFromEpisode:
    def test_prefers_watch_position_dict(self):
        episode = {"watchPosition": {"position": 90}, "watch_position": 10}
        assert position_from_episode(episode) == 90.0

    def test_falls_back_to_watch_position_field(self):
        assert position_from_episode({"watch_position": "40"}) == 40.0

    def test_missing_position(self):
        assert position_from_episode({}) is None
        assert position_from_episode({"watchPosition": {}}) is None
        assert position_from_episode(None) is None


class TestApplySavedPosition:
    def test_updates_the_position_angel_stores(self):
        episode = {"watchPosition": {"id": "ep", "position": 1220}, "watch_position": 1220}
        assert apply_saved_position(episode, 77.4) is True
        assert episode["watchPosition"]["position"] == 77
        assert episode["watchPosition"]["id"] == "ep"
        assert episode["watch_position"] == 77

    def test_creates_watch_position_when_the_episode_has_none(self):
        episode = {"guid": "ep"}
        assert apply_saved_position(episode, 77.6) is True
        assert episode["watchPosition"] == {"position": 78}
        assert "watch_position" not in episode

    def test_rejects_a_value_that_is_not_a_position(self):
        episode = {"watchPosition": {"position": 20}}
        assert apply_saved_position(episode, None) is False
        assert apply_saved_position(None, 10) is False
        assert apply_saved_position(episode, -1) is False
        assert episode["watchPosition"]["position"] == 20

    def test_patches_only_the_matching_episode(self):
        project = {
            "seasons": [
                {
                    "episodes": [
                        {"guid": "this", "watchPosition": {"position": 1220}},
                        {"guid": "other", "watchPosition": {"position": 10}},
                    ]
                },
                "not-a-season",
                {"episodes": [None, {"guid": "this", "watch_position": 1220}]},
            ]
        }
        assert patch_project_watch_position(project, "this", 77) is True
        episodes = project["seasons"][0]["episodes"]
        assert episodes[0]["watchPosition"]["position"] == 77
        assert episodes[1]["watchPosition"]["position"] == 10
        assert project["seasons"][2]["episodes"][1]["watchPosition"]["position"] == 77
        assert project["seasons"][2]["episodes"][1]["watch_position"] == 77
        assert patch_project_watch_position(project, "missing", 5) is False
        assert patch_project_watch_position(None, "this", 5) is False


class TestNativeResumePoint:
    def test_uses_source_duration(self):
        episode = {"watchPosition": {"position": 125}, "source": {"duration": 3600}}
        assert native_resume_point(episode) == (125.0, 3600.0)

    def test_falls_back_to_episode_duration(self):
        episode = {"watchPosition": {"position": 40}, "duration": 1800}
        assert native_resume_point(episode) == (40.0, 1800.0)

    def test_missing_duration_still_qualifies(self):
        assert native_resume_point({"watch_position": 90}) == (90.0, 91.0)

    def test_known_zero_blocks_kodis_own_bookmark(self):
        episode = {"watchPosition": {"position": 0}, "source": {"duration": 3600}}
        assert native_resume_point(episode) == (0.0, 3600.0)
        assert native_resume_point({"watchPosition": {"position": 0.4}}) == (0.0, 1.0)

    def test_missing_position_does_not_qualify(self):
        assert native_resume_point({}) is None
        assert native_resume_point(None) is None
        assert native_resume_point({"watchPosition": {"position": -1}}) is None


class TestShouldReportPosition:
    def test_opening_seconds_do_not_replace_a_later_save(self):
        assert should_report_position(3, 1200) is False
        assert should_report_position(BEGINNING_SECONDS - 1, 600) is False

    def test_beginning_is_not_sent_on_its_own(self):
        assert should_report_position(0, None) is False
        assert should_report_position(0.4, 0) is False

    def test_pause_after_the_opening_is_sent(self):
        assert should_report_position(45, 1200) is True
        assert should_report_position(125, None) is True

    def test_resume_point_is_sent(self):
        assert should_report_position(1203, 1200) is True

    def test_new_title_can_save_a_short_pause(self):
        assert should_report_position(4, None) is True
        assert should_report_position(4, 0) is True


class TestWatchProgressSession:
    def test_periodic_report_waits_one_interval(self):
        session = WatchProgressSession(saved_position=None, interval=60)
        session.start(0)
        assert session.observe(30, 59) is None
        assert session.observe(61, 60) == 61

    def test_periodic_report_skips_while_paused(self):
        session = WatchProgressSession(saved_position=None, interval=60)
        session.start(0)
        assert session.observe(90, 60, paused=True) is None

    def test_periodic_report_skips_the_opening(self):
        session = WatchProgressSession(saved_position=900, interval=60)
        session.start(0)
        assert session.observe(3, 60) is None

    def test_stop_in_the_opening_keeps_the_saved_position(self):
        session = WatchProgressSession(saved_position=900, interval=60)
        session.start(0)
        session.observe(2, 2)
        assert session.on_pause_or_stop(3) is None

    def test_pause_reports_the_current_position(self):
        session = WatchProgressSession(saved_position=100, interval=60)
        assert session.on_pause_or_stop(140) == 140

    def test_stop_uses_the_last_observed_position(self):
        session = WatchProgressSession(saved_position=None, interval=60)
        session.observe(80, 10)
        assert session.on_pause_or_stop(None) == 80

    def test_note_saved_protects_the_new_position(self):
        session = WatchProgressSession(saved_position=None, interval=60)
        session.note_saved(80)
        assert session.on_pause_or_stop(2) is None
