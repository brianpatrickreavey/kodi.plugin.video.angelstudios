"""Tests for choosing a caption track from Kodi's subtitle settings."""

import json
from unittest.mock import MagicMock

from captions import (
    apply_playback_captions,
    choose_caption_track,
    kodi_convert_language,
    language_keys,
)


def _convert(value):
    """Stand-in for Kodi's convertLanguage. Covers the codes these tests use."""
    table = {
        "en": "en",
        "eng": "en",
        "english": "en",
        "es": "es",
        "spa": "es",
        "spanish": "es",
        "pt": "pt",
        "por": "pt",
        "portuguese": "pt",
        "fr": "fr",
        "fra": "fr",
        "french": "fr",
    }
    return table.get(value.strip().lower(), "")


def _track(index, name, language, forced=False, impaired=False):
    return {
        "index": index,
        "name": name,
        "language": language,
        "isdefault": False,
        "isforced": forced,
        "isimpaired": impaired,
    }


TUTTLE_TWINS = [
    _track(0, "English", "eng"),
    _track(1, "Spanish (Latam)", "es-419"),
    _track(2, "Portuguese", "por"),
]


def _choose(preference, tracks=None, hearing=False, audio="eng"):
    return choose_caption_track(preference, tracks if tracks is not None else TUTTLE_TWINS, hearing, audio, _convert)


class TestChooseCaptionTrack:
    def test_english_turns_on_the_english_track(self):
        assert _choose("en") == {"enable": True, "index": 0}

    def test_spanish_turns_on_spanish_latam(self):
        assert _choose("es") == {"enable": True, "index": 1}

    def test_portuguese_turns_on_portuguese(self):
        assert _choose("pt") == {"enable": True, "index": 2}

    def test_none_leaves_captions_off_once_tracks_are_listed(self):
        assert _choose("none") == {"enable": False}

    def test_none_waits_until_the_track_list_exists(self):
        assert _choose("none", tracks=[]) == {"wait": True}

    def test_forced_only_stays_off_when_no_track_is_forced(self):
        assert _choose("forced_only") == {"enable": False}

    def test_forced_only_turns_on_a_forced_track_in_the_audio_language(self):
        tracks = [
            _track(0, "English", "eng"),
            _track(1, "Spanish (Latam)", "es-419", forced=True),
            _track(2, "English", "eng", forced=True),
        ]
        assert _choose("forced_only", tracks=tracks, audio="eng") == {"enable": True, "index": 2}

    def test_forced_only_ignores_a_forced_track_in_another_language(self):
        tracks = [_track(0, "Spanish (Latam)", "es-419", forced=True)]
        assert _choose("forced_only", tracks=tracks, audio="eng") == {"enable": False}

    def test_forced_only_waits_for_the_audio_language(self):
        tracks = [_track(0, "English", "eng", forced=True)]
        assert _choose("forced_only", tracks=tracks, audio="") == {"wait": True}

    def test_original_and_interface_language_stay_with_kodi(self):
        assert _choose("original") is None
        assert _choose("default") is None
        assert _choose("") is None
        assert _choose(None) is None

    def test_hearing_impaired_prefers_that_track_when_both_exist(self):
        tracks = [
            _track(0, "English", "eng"),
            _track(1, "English SDH", "eng", impaired=True),
        ]
        assert _choose("en", tracks=tracks, hearing=True) == {"enable": True, "index": 1}
        assert _choose("en", tracks=tracks, hearing=False) == {"enable": True, "index": 0}

    def test_a_language_skips_the_forced_track(self):
        tracks = [
            _track(0, "English [Forced Narrative]", "eng", forced=True),
            _track(1, "English", "eng"),
            _track(2, "English [Closed Captions]", "eng", impaired=True),
        ]
        assert _choose("en", tracks=tracks, hearing=False) == {"enable": True, "index": 1}
        assert _choose("en", tracks=tracks, hearing=True) == {"enable": True, "index": 2}

    def test_a_language_stays_off_when_the_only_track_is_forced(self):
        tracks = [
            _track(0, "English [Forced Narrative]", "eng", forced=True),
            _track(1, "English [Forced Narrative]", "eng", forced=True, impaired=True),
        ]
        assert _choose("en", tracks=tracks, hearing=False) == {"enable": False}
        assert _choose("en", tracks=tracks, hearing=True) == {"enable": False}

    def test_hearing_impaired_uses_the_only_track_when_no_pair_exists(self):
        tracks = [_track(0, "English SDH", "eng", impaired=True)]
        assert _choose("en", tracks=tracks, hearing=False) == {"enable": True, "index": 0}

    def test_a_language_with_no_match_turns_captions_off(self):
        assert _choose("fr") == {"enable": False}

    def test_a_language_waits_while_the_track_list_is_empty(self):
        assert _choose("en", tracks=[]) == {"wait": True}

    def test_skips_a_track_with_no_index(self):
        tracks = [{"name": "English", "language": "eng"}, _track(3, "English", "eng")]
        assert _choose("en", tracks=tracks) == {"enable": True, "index": 3}


class TestLanguageKeys:
    def test_region_code_matches_the_primary_language(self):
        assert "es" in language_keys("es-419", _convert)
        assert language_keys("es", _convert) & language_keys("Spanish (Latam)", _convert)


class _Rpc:
    def __init__(self, steps):
        self.steps = list(steps)
        self.calls = []

    def __call__(self, raw):
        request = json.loads(raw)
        self.calls.append(request)
        if not self.steps:
            raise AssertionError(request["method"])
        return json.dumps(self.steps.pop(0))


class _Monitor:
    def __init__(self, abort=False, wait_abort=False):
        self.abort = abort
        self.wait_abort = wait_abort
        self.waits = 0

    def abortRequested(self):
        return self.abort

    def waitForAbort(self, _seconds):
        self.waits += 1
        return self.wait_abort


def _settings(preference="en", hearing=False):
    return [
        {"result": {"value": preference}},
        {"result": {"value": hearing}},
    ]


def _players(playerid=1):
    return {"result": [{"playerid": playerid, "type": "video"}]}


def _properties(tracks, audio="eng"):
    return {
        "result": {
            "subtitles": tracks,
            "currentaudiostream": {"language": audio, "index": 0, "name": "English"},
        }
    }


def _apply(rpc, monitor=None, stopped=None):
    log = MagicMock()
    apply_playback_captions(
        rpc,
        monitor or _Monitor(),
        log,
        _convert,
        stopped or (lambda: False),
    )
    return log


class TestApplyPlaybackCaptions:
    def test_english_enables_the_english_track_once(self):
        rpc = _Rpc(
            _settings("en")
            + [
                _players(),
                _properties(TUTTLE_TWINS),
                {"result": "OK"},
            ]
        )

        log = _apply(rpc)

        set_subtitle = rpc.calls[-1]
        assert set_subtitle["method"] == "Player.SetSubtitle"
        assert set_subtitle["params"] == {"playerid": 1, "subtitle": 0, "enable": True}
        log.info.assert_any_call("Captions on: English")

    def test_none_turns_captions_off_after_the_tracks_are_listed(self):
        rpc = _Rpc(_settings("none") + [_players(), _properties(TUTTLE_TWINS), {"result": "OK"}])

        log = _apply(rpc)

        assert rpc.calls[-1]["params"] == {"playerid": 1, "subtitle": "off"}
        log.info.assert_any_call("Captions off")

    def test_original_does_not_change_the_player(self):
        rpc = _Rpc(_settings("original"))

        log = _apply(rpc)

        assert [call["method"] for call in rpc.calls] == [
            "Settings.GetSettingValue",
            "Settings.GetSettingValue",
        ]
        log.info.assert_called_once_with("Preferred subtitle language is original; Kodi chooses the caption track")

    def test_waits_until_the_tracks_appear(self):
        rpc = _Rpc(
            _settings("es")
            + [
                {"result": []},
                _players(),
                _properties([]),
                _players(),
                _properties(TUTTLE_TWINS),
                {"result": "OK"},
            ]
        )
        monitor = _Monitor()

        log = _apply(rpc, monitor)

        assert monitor.waits == 2
        assert rpc.calls[-1]["params"]["subtitle"] == 1
        log.info.assert_any_call("Captions on: Spanish (Latam)")

    def test_no_tracks_are_logged_and_left_alone(self):
        rpc = _Rpc(_settings("en") + [_players(), _properties([])] * 25)
        monitor = _Monitor()

        log = _apply(rpc, monitor)

        assert not any(call["method"] == "Player.SetSubtitle" for call in rpc.calls)
        log.info.assert_any_call("No caption tracks in this stream")

    def test_a_read_failure_does_not_raise(self):
        rpc = MagicMock(return_value=MagicMock())

        log = _apply(rpc)

        log.warning.assert_called_once()
        assert "preferred subtitle language" in log.warning.call_args.args[0]

    def test_a_rejected_change_is_logged(self):
        rpc = _Rpc(_settings("en") + [_players(), _properties(TUTTLE_TWINS), {"result": "Failed"}])

        log = _apply(rpc)

        log.warning.assert_called_once()
        assert "Could not set the caption track" in log.warning.call_args.args[0]

    def test_abort_while_waiting_does_not_set_a_track(self):
        rpc = _Rpc(_settings("en") + [{"result": []}])
        monitor = _Monitor(wait_abort=True)

        log = _apply(rpc, monitor)

        assert not any(call["method"] == "Player.SetSubtitle" for call in rpc.calls)
        log.info.assert_not_called()

    def test_stop_while_waiting_does_not_set_a_track(self):
        rpc = _Rpc(_settings("en") + [{"result": []}])

        log = _apply(rpc, stopped=lambda: True)

        assert not any(call["method"] == "Player.SetSubtitle" for call in rpc.calls)
        log.info.assert_not_called()


class TestKodiConvertLanguage:
    def test_uses_kodi_when_it_returns_a_code(self, monkeypatch):
        import captions

        xbmc = MagicMock()
        xbmc.convertLanguage.return_value = "es"
        monkeypatch.setitem(__import__("sys").modules, "xbmc", xbmc)

        assert captions.kodi_convert_language("spa") == "es"

    def test_region_code_uses_the_primary_tag_when_kodi_returns_nothing(self, monkeypatch):
        xbmc = MagicMock()
        xbmc.convertLanguage.return_value = ""
        monkeypatch.setitem(__import__("sys").modules, "xbmc", xbmc)

        assert kodi_convert_language("es-419") == "es"

    def test_known_name_is_used_when_kodi_returns_nothing(self, monkeypatch):
        import captions

        xbmc = MagicMock()
        xbmc.convertLanguage.side_effect = RuntimeError("down")
        monkeypatch.setitem(__import__("sys").modules, "xbmc", xbmc)

        assert captions.kodi_convert_language("English") == "en"
        assert captions.kodi_convert_language(None) == ""
        assert captions.kodi_convert_language("   ") == ""
