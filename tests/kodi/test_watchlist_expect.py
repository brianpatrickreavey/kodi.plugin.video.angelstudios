"""The watchlist comparison does not call Angel or Kodi."""

import sys
from pathlib import Path

sys.path.insert(
    0, str(Path(__file__).resolve().parents[2] / "dev/script.angelstudios.integration-testing/resources/lib")
)

from watchlist_expect import (  # noqa: E402
    directory_rows,
    list_difference,
    parse_watchlist,
    watchlist_menu_rows,
)


def _edge(typename, content_id, slug, name):
    return {
        "node": {
            "content": {
                "__typename": typename,
                "id": content_id,
                "name": name,
                "project": {"slug": slug},
            }
        }
    }


def _payload(*edges):
    return {"getMyDefaultWatchList": {"id": "list-id", "items": {"edges": list(edges)}}}


def _file(action, content_type, slug, label):
    return {
        "label": label,
        "file": (
            "plugin://plugin.video.angelstudios/?action="
            + action
            + "&content_type="
            + content_type
            + "&project_slug="
            + slug
        ),
    }


def test_parse_keeps_angel_order_and_skips_rows_that_cannot_be_opened():
    saved = parse_watchlist(
        _payload(
            _edge("ContentMovie", "spy-id", "spy-next-door", "The Spy Next Door"),
            {"node": {"content": {"__typename": "ContentEpisode", "id": "ep", "project": {"slug": "tuttle-twins"}}}},
            _edge("ContentSeries", "", "tuttle-twins", "Tuttle Twins"),
            _edge("ContentSeries", "tuttle-id", "tuttle-twins", "Tuttle Twins"),
        )
    )

    assert [item["name"] for item in saved] == ["The Spy Next Door", "Tuttle Twins"]
    assert saved[0]["menu_content_type"] == "movies"
    assert saved[1]["project_slug"] == "tuttle-twins"


def test_empty_edges_are_an_empty_watchlist():
    assert parse_watchlist(_payload()) == []


def test_a_missing_list_is_not_an_empty_watchlist():
    assert parse_watchlist({}) is None
    assert parse_watchlist({"getMyDefaultWatchList": None}) is None
    assert parse_watchlist("nope") is None


def test_directory_matches_angel_order():
    expected = parse_watchlist(
        _payload(
            _edge("ContentMovie", "spy-id", "spy-next-door", "The Spy Next Door"),
            _edge("ContentSeries", "tuttle-id", "tuttle-twins", "Tuttle Twins"),
        )
    )
    rows = directory_rows(
        [
            _file("seasons_menu", "movies", "spy-next-door", "The Spy Next Door"),
            _file("seasons_menu", "series", "tuttle-twins", "Tuttle Twins"),
        ]
    )

    assert list_difference(rows, expected) == ""


def test_directory_reports_a_different_order():
    expected = parse_watchlist(
        _payload(
            _edge("ContentMovie", "spy-id", "spy-next-door", "The Spy Next Door"),
            _edge("ContentSeries", "tuttle-id", "tuttle-twins", "Tuttle Twins"),
        )
    )
    rows = directory_rows(
        [
            _file("seasons_menu", "series", "tuttle-twins", "Tuttle Twins"),
            _file("seasons_menu", "movies", "spy-next-door", "The Spy Next Door"),
        ]
    )

    assert "Title 1" in list_difference(rows, expected)


def test_opening_a_title_must_not_be_the_remove_action():
    expected = parse_watchlist(_payload(_edge("ContentMovie", "spy-id", "spy-next-door", "The Spy Next Door")))
    row = _file("seasons_menu", "movies", "spy-next-door", "The Spy Next Door")
    row["file"] += "&next=remove_from_watchlist"
    rows = directory_rows([row])
    rows[0]["action"] = "seasons_menu"

    assert list_difference(rows, expected) == "Opening title 1 would change the watchlist."


def test_main_menu_row_is_the_watchlist_action():
    files = [
        {"label": "Movies", "file": "plugin://plugin.video.angelstudios/?action=movies_menu"},
        {"label": "Watchlist", "file": "plugin://plugin.video.angelstudios/?action=watchlist_menu"},
    ]

    hits = watchlist_menu_rows(files)

    assert len(hits) == 1
    assert hits[0]["label"] == "Watchlist"
