"""Names and row helpers for the Kodi integration checks.

These do not start Kodi. The live runs are the make kodi-test-* targets.
"""

import sys
from pathlib import Path

_LIB = Path(__file__).resolve().parents[2] / "dev/script.angelstudios.integration-testing/resources/lib"
sys.path.insert(0, str(_LIB))

from listing import has_entry, rows, tag_summary  # noqa: E402
from resume_expect import parse_resume, resume_candidate  # noqa: E402
from selection import LEAVES, expand  # noqa: E402


def test_caption_run_stays_the_caption_leaves():
    assert expand("all") == list(LEAVES)
    for name in (
        "catalog",
        "folders",
        "continue",
        "playback",
        "title-tags",
        "maintenance",
        "auth",
        "signed-out",
        "watchlist",
        "guild",
    ):
        for leaf in expand(name):
            assert leaf not in LEAVES


def test_directory_rows_keep_the_action():
    parsed = rows(
        [
            {
                "label": "Movies",
                "file": "plugin://plugin.video.angelstudios/?action=movies_menu&content_type=movie",
            }
        ]
    )
    assert has_entry(parsed, "Movies", "movies_menu")
    assert not has_entry(parsed, "Movies", "series_menu")


def test_tag_summary_uses_plot_rating_and_genre():
    assert tag_summary({"plot": "Ages 8+\n\nA story.", "mpaa": "TV-PG", "genre": ["Family"]}) == "plot TV-PG Family"
    assert tag_summary({}) == ""
    assert tag_summary({"rating": 7.3}) == "rating 7.3"


def test_resume_candidate_skips_the_opening_and_the_ending():
    items = parse_resume(
        {
            "resumeWatching": {
                "edges": [
                    {
                        "node": {
                            "watchableGuid": "early",
                            "position": 12,
                            "content": {
                                "__typename": "ContentMovie",
                                "name": "Early",
                                "duration": 5000,
                                "project": {"slug": "early", "name": "Early"},
                            },
                        }
                    },
                    {
                        "node": {
                            "watchableGuid": "middle",
                            "position": 400,
                            "content": {
                                "__typename": "ContentEpisode",
                                "name": "Middle",
                                "duration": 1800,
                                "project": {"slug": "show", "name": "Show"},
                            },
                        }
                    },
                ]
            }
        }
    )
    chosen = resume_candidate(items)
    assert chosen["guid"] == "middle"
    assert chosen["content_type"] == "series"
    assert chosen["position"] == 400


def test_resume_candidate_is_none_when_nothing_qualifies():
    assert resume_candidate([]) is None
    assert parse_resume({}) is None
    assert parse_resume({"resumeWatching": {"edges": []}}) == []
