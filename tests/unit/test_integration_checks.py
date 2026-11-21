"""Names and row helpers for the Kodi integration checks.

These do not start Kodi. The live runs are the make kodi-test-* targets.
"""

import json
import os
import stat
import sys
from pathlib import Path

_LIB = Path(__file__).resolve().parents[2] / "dev/script.angelstudios.integration-testing/resources/lib"
sys.path.insert(0, str(_LIB))

from listing import has_entry, rows, tag_summary  # noqa: E402
from recovery_file import write_recovery  # noqa: E402
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


def _mode(path):
    return stat.S_IMODE(os.stat(path).st_mode)


def test_recovery_file_is_private_even_with_a_loose_umask(tmp_path):
    path = tmp_path / "login-recovery.json"
    previous = os.umask(0)
    try:
        write_recovery(str(path), "viewer", "pw")
    finally:
        os.umask(previous)
    assert _mode(path) == 0o600
    assert json.loads(path.read_text()) == {"username": "viewer", "password": "pw"}


def test_recovery_file_replaces_a_readable_file(tmp_path):
    path = tmp_path / "login-recovery.json"
    path.write_text("old")
    os.chmod(path, 0o644)
    write_recovery(str(path), "viewer", "pw")
    assert _mode(path) == 0o600
    assert json.loads(path.read_text())["username"] == "viewer"


def test_recovery_file_replaces_a_symlink_without_writing_the_target(tmp_path):
    target = tmp_path / "other-file"
    target.write_text("keep")
    link = tmp_path / "login-recovery.json"
    link.symlink_to(target)
    write_recovery(str(link), "viewer", "pw")
    assert target.read_text() == "keep"
    assert not link.is_symlink()
    assert _mode(link) == 0o600
    assert json.loads(link.read_text())["username"] == "viewer"
