"""The playlist reader decides whether a title is still the right caption case."""

import sys
from pathlib import Path

sys.path.insert(
    0, str(Path(__file__).resolve().parents[2] / "dev/script.angelstudios.integration-testing/resources/lib")
)

from playlist import (  # noqa: E402
    has_regular_and_impaired,
    kensuke_case,
    load_subtitle_tracks,
    source_url,
    subtitle_tracks,
    tuttle_case,
    young_washington_case,
)


def _media(name, language, extra=""):
    return (
        '#EXT-X-MEDIA:TYPE=SUBTITLES,GROUP-ID="subs",NAME="'
        + name
        + '",LANGUAGE="'
        + language
        + '",DEFAULT=NO'
        + extra
        + ',URI="track.m3u8"'
    )


_MASTER = "\n".join(
    [
        "#EXTM3U",
        _media("English", "en", ",AUTOSELECT=NO"),
        _media(
            "English [Closed Captions]",
            "en",
            ',FORCED=NO,CHARACTERISTICS="public.accessibility.transcribes-spoken-dialog"',
        ),
        _media("English [Forced Narrative]", "en", ",FORCED=YES"),
        _media("Spanish (Latam)", "es-419"),
        _media("Portuguese", "pt-BR"),
        '#EXT-X-STREAM-INF:BANDWIDTH=1000,SUBTITLES="subs"',
        "video.m3u8",
    ]
)

_EMPTY = """
#EXTM3U
#EXT-X-STREAM-INF:BANDWIDTH=1000
video.m3u8
"""

_VIDEO = """
#EXTM3U
#EXTINF:6,
segment.ts
"""


def test_master_playlist_lists_subtitle_tracks_and_ignores_the_video_address():
    tracks, variants = subtitle_tracks(_MASTER, "https://cdn.example/master.m3u8")
    assert [track["name"] for track in tracks] == [
        "English",
        "English [Closed Captions]",
        "English [Forced Narrative]",
        "Spanish (Latam)",
        "Portuguese",
    ]
    assert variants == ["https://cdn.example/video.m3u8"]
    assert has_regular_and_impaired(tracks, "en") is True


def test_a_forced_track_does_not_count_as_the_regular_track():
    page = "\n".join(
        [
            _media("English [Forced Narrative]", "en", ",FORCED=YES"),
            _media(
                "English [Closed Captions]",
                "en",
                ',CHARACTERISTICS="public.accessibility.transcribes-spoken-dialog"',
            ),
        ]
    )
    tracks, _variants = subtitle_tracks(page, "https://cdn.example/master.m3u8")
    assert has_regular_and_impaired(tracks, "en") is False


def test_empty_master_checks_a_video_rendition_before_saying_there_are_no_captions():
    pages = {
        "https://cdn.example/master.m3u8": _EMPTY,
        "https://cdn.example/video.m3u8": _MASTER,
    }

    def fetch(url):
        return pages[url]

    tracks = load_subtitle_tracks("https://cdn.example/master.m3u8", fetch)
    assert any(track["name"] == "English" for track in tracks)


def test_no_caption_case_stays_empty_when_the_renditions_have_no_subtitles():
    pages = {
        "https://cdn.example/master.m3u8": _EMPTY,
        "https://cdn.example/video.m3u8": _VIDEO,
    }
    tracks = load_subtitle_tracks("https://cdn.example/master.m3u8", lambda url: pages[url])
    passed, detail = kensuke_case(tracks)
    assert passed is True
    assert detail == "Playlist still has no caption tracks."


def test_kensuke_fails_when_a_caption_track_was_added():
    tracks, _variants = subtitle_tracks(_MASTER, "https://cdn.example/master.m3u8")
    passed, detail = kensuke_case(tracks)
    assert passed is False
    assert detail.startswith("Kensuke's Kingdom now has caption tracks.")


def test_young_washington_and_tuttle_cases_match_their_playlists():
    tracks, _variants = subtitle_tracks(_MASTER, "https://cdn.example/master.m3u8")
    assert young_washington_case(tracks)[0] is True
    assert tuttle_case(tracks)[0] is True
    assert tuttle_case([tracks[0]])[0] is False


def test_source_url_finds_the_episode_and_hides_other_episodes():
    project = {
        "seasons": [
            {"episodes": [{"guid": "other", "source": {"url": "https://cdn.example/other.m3u8"}}]},
            {"episodes": [{"guid": "wanted", "source": {"url": "https://cdn.example/wanted.m3u8"}}]},
        ]
    }
    assert source_url(project, "wanted") == "https://cdn.example/wanted.m3u8"
    assert source_url(project, "missing") == ""
