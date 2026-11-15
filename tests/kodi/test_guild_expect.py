"""The Guild Voting comparison does not call Angel or Kodi."""

import sys
from pathlib import Path

sys.path.insert(
    0, str(Path(__file__).resolve().parents[2] / "dev/script.angelstudios.integration-testing/resources/lib")
)

from guild_expect import directory_rows, folder_problem, menu_problem, parse_member, parse_torches  # noqa: E402


def _payload(*rows):
    return {"guildVotingCategories": {"nextInCategory": list(rows)}}


def _torch(torch_id, title):
    return {"torch": {"id": torch_id, "title": title}}


def _file(action, label, torch_id=""):
    query = "action=" + action
    if torch_id:
        query += "&torch_id=" + torch_id
    return {"label": label, "file": "plugin://plugin.video.angelstudios/?" + query}


def test_parse_keeps_angel_order_and_skips_a_row_with_no_id():
    torches = parse_torches(
        _payload(
            _torch("torch-1", "First"),
            {"torch": {"title": "Skipped"}},
            {"torch": None},
            _torch("torch-2", ""),
        )
    )
    assert torches == [
        {"id": "torch-1", "title": "First"},
        {"id": "torch-2", "title": "Torch"},
    ]


def test_an_empty_list_is_not_a_failed_read():
    assert parse_torches(_payload()) == []


def test_a_missing_list_is_not_an_empty_list():
    assert parse_torches({}) is None
    assert parse_torches({"guildVotingCategories": {}}) is None


def test_membership_is_true_only_when_angel_says_so():
    assert parse_member({"user": {"isGuildMember": True}}) is True
    assert parse_member({"user": {"isGuildMember": False}}) is False
    assert parse_member({"user": {}}) is None
    assert parse_member({}) is None


def test_menu_wants_guild_voting_directly_above_settings():
    rows = directory_rows(
        [
            _file("movies_menu", "Movies"),
            _file("guild_voting_menu", "Guild Voting"),
            _file("settings", "Settings"),
        ]
    )
    assert menu_problem(rows) == ""


def test_menu_reports_a_missing_item_and_a_bad_neighbor():
    assert menu_problem(directory_rows([_file("settings", "Settings")])) == (
        "The main menu showed 0 Guild Voting items."
    )
    rows = directory_rows(
        [
            _file("guild_voting_menu", "Guild Voting"),
            _file("movies_menu", "Movies"),
        ]
    )
    assert menu_problem(rows) == "The item under Guild Voting is Movies."


def test_folder_accepts_the_history_folder_and_torch_links():
    rows = directory_rows(
        [
            _file("guild_voted_menu", "Already voted on"),
            _file("play_torch", "First", "torch-1"),
            _file("play_torch", "Second", "torch-2"),
        ]
    )
    assert folder_problem(rows) == ""


def test_folder_accepts_history_when_there_is_nothing_to_vote_on():
    rows = directory_rows([_file("guild_voted_menu", "Already voted on")])
    assert folder_problem(rows) == ""


def test_folder_rejects_a_row_that_does_not_open_a_torch():
    rows = directory_rows(
        [
            _file("guild_voted_menu", "Already voted on"),
            _file("play_episode", "First", "torch-1"),
        ]
    )
    assert folder_problem(rows) == "Torch 1 opens play_episode instead of the torch."


def test_folder_rejects_a_torch_with_no_id():
    rows = directory_rows(
        [
            _file("guild_voted_menu", "Already voted on"),
            _file("play_torch", "First"),
        ]
    )
    assert folder_problem(rows) == "Torch 1 has no torch id."


def test_folder_requires_already_voted_on_first():
    rows = directory_rows([_file("play_torch", "First", "torch-1")])
    assert folder_problem(rows) == "Guild Voting does not open with Already voted on."


def test_an_empty_folder_is_not_a_torch_list():
    assert folder_problem([]) == "Kodi opened Guild Voting and listed nothing."
