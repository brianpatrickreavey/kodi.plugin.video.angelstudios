"""Guild Voting menu, ballot, and the Angel calls behind them."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from resources.lib.angel_interface import (
    AngelStudiosInterface,
    AuthenticationRequiredError,
    _guild_torch_details,
    _guild_vote_input,
)
from resources.lib.kodi_menu_handler import _guild_vote_extras, _torch_manifest_type

ADDON_ROOT = Path(__file__).resolve().parents[2] / "plugin.video.angelstudios"
GRAPHQL_DIR = ADDON_ROOT / "resources" / "lib" / "angel_graphql"

LIGHT = "Does this project amplify light?"
DISAPPOINTMENT = "How would you feel if this never became an Angel Studios movie?"
CANNOT_PLAY = "This torch cannot be played yet."
DRM_NOT_INSTALLED = (
    "This torch is protected by DRM. Widevine was not installed. "
    "Install it from the addon settings, under Install Widevine."
)
VOTE_FAILED = "Vote failed. Please try again."
LICENSE_URL = "https://example.test/license"

SPY = {
    "content_id": "spy-id",
    "name": "The Spy Next Door",
    "description": "A man is called to baby-sit his neighbor's children.",
    "project_slug": "the-spy-next-door",
    "menu_content_type": "movies",
    "poster_path": None,
    "landscape_path": None,
}


def _torch_payload(**overrides):
    torch = {
        "id": "torch-1",
        "title": "A Small Film",
        "torchVotes": [
            {
                "voterId": "someone-else",
                "alignment": "NEUTRAL",
                "interest": "NOT_INTERESTED",
                "ageGroups": "1|2",
                "recommendedAge": 4,
                "recommendedAgeReason": "not mine",
            },
            {
                "voterId": None,
                "alignment": "SUPPORTS",
                "interest": "SOMEWHAT_INTERESTED",
                "ageGroups": "8|10",
                "recommendedAge": 8,
                "recommendedAgeReason": "kept from the website",
            },
        ],
        "session": {
            "url": "https://example.test/torch.mpd?token=secret",
            "drmRequired": False,
        },
    }
    torch.update(overrides)
    return torch


@pytest.fixture
def angel_interface():
    auth = MagicMock()
    auth.session_store.get_token.return_value = "token"
    with patch("requests.Session", return_value=MagicMock()):
        interface = AngelStudiosInterface(auth_core=auth, logger=MagicMock())
        yield interface


def _sign_in(ui, signed_in=True):
    ui.angel_interface.auth_core.validate_session.return_value = True if signed_in else False
    ui.angel_interface.auth_core.ensure_valid_session.reset_mock()


class TestGuildVotingApi:
    def test_list_keeps_angel_order(self, angel_interface):
        angel_interface._graphql_query = MagicMock(
            return_value={
                "guildVotingCategories": {
                    "nextInCategory": [
                        {"category": "COMEDY", "torch": {"id": "second", "title": "Second"}},
                        {"category": "DRAMA", "torch": None},
                        "bad-row",
                        {"category": "FAMILY", "torch": {"id": "", "title": "Missing"}},
                        {"category": "ACTION", "torch": {"id": "first", "title": "First"}},
                    ]
                }
            }
        )

        torches = angel_interface.get_guild_voting_torches()

        assert [item["title"] for item in torches] == ["Second", "First"]
        assert [item["id"] for item in torches] == ["second", "first"]
        angel_interface._graphql_query.assert_called_once_with("getGuildVotingCategories", variables={})

    def test_empty_list_is_not_a_failure(self, angel_interface):
        angel_interface._graphql_query = MagicMock(return_value={"guildVotingCategories": {"nextInCategory": []}})
        assert angel_interface.get_guild_voting_torches() == []

    @pytest.mark.parametrize(
        "payload",
        [
            {},
            {"guildVotingCategories": None},
            {"guildVotingCategories": {}},
            {"guildVotingCategories": {"nextInCategory": None}},
        ],
    )
    def test_failed_list_is_none(self, angel_interface, payload):
        angel_interface._graphql_query = MagicMock(return_value=payload)
        assert angel_interface.get_guild_voting_torches() is None

    def test_list_exception_is_none(self, angel_interface):
        angel_interface._graphql_query = MagicMock(side_effect=Exception("down"))
        assert angel_interface.get_guild_voting_torches() is None

    def test_voted_page_keeps_finalized_torches_in_order(self, angel_interface):
        angel_interface._graphql_query = MagicMock(
            return_value={
                "torchVotes": {
                    "hasNext": True,
                    "nextCursor": "page-2",
                    "items": [
                        {"finalized": True, "torch": {"id": "land", "title": "Promised Land"}},
                        {"finalized": False, "torch": {"id": "skipped", "title": "Skipped"}},
                        {"finalized": True, "torch": {"id": "", "title": "Missing"}},
                        {"finalized": True, "torch": {"id": "numbers", "title": ""}},
                        "bad-row",
                    ],
                }
            }
        )

        page = angel_interface.get_guild_voted_torches()

        assert page["torches"] == [
            {"id": "land", "title": "Promised Land"},
            {"id": "numbers", "title": "Torch"},
        ]
        assert page["has_next"] is True
        assert page["cursor"] == "page-2"
        angel_interface._graphql_query.assert_called_once_with(
            "getTorchVoteHistory", variables={"input": {"take": 24}}
        )

    def test_voted_page_passes_the_cursor(self, angel_interface):
        angel_interface._graphql_query = MagicMock(
            return_value={"torchVotes": {"hasNext": False, "nextCursor": None, "items": []}}
        )

        page = angel_interface.get_guild_voted_torches("page-2")

        assert page == {"torches": [], "has_next": False, "cursor": None}
        variables = angel_interface._graphql_query.call_args.kwargs["variables"]
        assert variables["input"] == {"take": 24, "nextCursor": "page-2"}

    def test_voted_page_without_a_cursor_is_not_a_next_page(self, angel_interface):
        angel_interface._graphql_query = MagicMock(
            return_value={"torchVotes": {"hasNext": True, "items": []}}
        )
        page = angel_interface.get_guild_voted_torches()
        assert page["has_next"] is False
        assert page["cursor"] is None

    def test_voted_page_failure_is_none(self, angel_interface):
        angel_interface._graphql_query = MagicMock(return_value={"torchVotes": None})
        assert angel_interface.get_guild_voted_torches() is None
        angel_interface._graphql_query = MagicMock(side_effect=Exception("down"))
        assert angel_interface.get_guild_voted_torches() is None

    def test_membership(self, angel_interface):
        angel_interface._graphql_query = MagicMock(return_value={"user": {"isGuildMember": True}})
        assert angel_interface.is_guild_member() is True
        angel_interface._graphql_query.assert_called_once_with("guildMemberStatus", variables={})

        angel_interface._graphql_query = MagicMock(return_value={"user": {"isGuildMember": False}})
        assert angel_interface.is_guild_member() is False

        angel_interface._graphql_query = MagicMock(return_value={"user": {}})
        assert angel_interface.is_guild_member() is None

        angel_interface._graphql_query = MagicMock(side_effect=Exception("down"))
        assert angel_interface.is_guild_member() is None

    def test_torch_uses_the_viewers_vote_and_streaming_args(self, angel_interface):
        angel_interface._graphql_query = MagicMock(return_value={"torch": _torch_payload()})

        torch = angel_interface.get_guild_torch("torch-1")

        assert torch["title"] == "A Small Film"
        assert torch["stream_url"].endswith("torch.mpd?token=secret")
        assert torch["drm_required"] is False
        assert torch["drm_license_url"] is None
        assert torch["drm_certificate_url"] is None
        assert torch["vote"]["alignment"] == "SUPPORTS"
        assert torch["vote"]["interest"] == "SOMEWHAT_INTERESTED"
        assert torch["vote"]["age_groups"] == "8|10"
        assert torch["vote"]["recommended_age"] == 8
        assert torch["vote"]["recommended_age_reason"] == "kept from the website"
        variables = angel_interface._graphql_query.call_args.kwargs["variables"]
        assert variables["torchId"] == "torch-1"
        assert variables["streamingArgs"]["segmentFormat"] == "M4S"
        assert variables["streamingArgs"]["drmType"] == "WIDEVINE_L3"
        assert variables["streamingArgs"]["maxHevcLevel"] == "LEVEL_0"
        assert angel_interface._graphql_query.call_count == 1
        angel_interface.session.headers.pop.assert_called_with("x-drm-type", None)

    def test_torch_without_a_voter_id_falls_back_to_the_first_vote(self):
        details = _guild_torch_details(
            {
                "id": "torch-1",
                "title": "A Small Film",
                "torchVotes": [{"voterId": "other", "alignment": "HINDERS", "interest": "INTERESTED"}],
                "session": None,
            }
        )
        assert details["vote"]["alignment"] == "HINDERS"
        assert details["stream_url"] is None
        assert details["drm_required"] is False
        assert details["drm_license_url"] is None
        assert details["drm_certificate_url"] is None

    def test_torch_keeps_widevine_urls(self):
        details = _guild_torch_details(
            {
                "id": "torch-1",
                "title": "A Small Film",
                "session": {
                    "url": "https://example.test/a.m3u8",
                    "drmRequired": True,
                    "drmLicenseUrl": "https://example.test/license",
                    "drmCertificateUrl": "https://example.test/cert",
                },
            }
        )
        assert details["drm_license_url"] == "https://example.test/license"
        assert details["drm_certificate_url"] == "https://example.test/cert"

    def test_torch_drops_blank_widevine_urls(self):
        details = _guild_torch_details(
            {
                "id": "torch-1",
                "title": "A Small Film",
                "session": {
                    "url": "https://example.test/a.m3u8",
                    "drmRequired": True,
                    "drmLicenseUrl": "",
                    "drmCertificateUrl": 12,
                },
            }
        )
        assert details["drm_license_url"] is None
        assert details["drm_certificate_url"] is None

    def test_age_field_refusal_reads_the_ballot_without_them(self, angel_interface):
        angel_interface._graphql_query = MagicMock(
            side_effect=[
                AuthenticationRequiredError("Cannot query field recommendedAge"),
                {"torch": _torch_payload()},
            ]
        )

        torch = angel_interface.get_guild_torch("torch-1")

        assert torch["id"] == "torch-1"
        operations = [call.args[0] for call in angel_interface._graphql_query.call_args_list]
        assert operations == ["getTorchVoteTorch", "getTorchVoteTorchCore"]

    def test_empty_rich_read_uses_the_core_ballot(self, angel_interface):
        angel_interface._graphql_query = MagicMock(side_effect=[{}, {"torch": _torch_payload()}])

        torch = angel_interface.get_guild_torch("torch-1")

        assert torch["id"] == "torch-1"
        operations = [call.args[0] for call in angel_interface._graphql_query.call_args_list]
        assert operations == ["getTorchVoteTorch", "getTorchVoteTorchCore"]

    def test_failed_torch_read_is_none(self, angel_interface):
        angel_interface._graphql_query = MagicMock(return_value={})
        assert angel_interface.get_guild_torch("torch-1") is None
        assert angel_interface._graphql_query.call_count == 2

        angel_interface._graphql_query = MagicMock(side_effect=Exception("down"))
        assert angel_interface.get_guild_torch("torch-1") is None
        assert angel_interface._graphql_query.call_count == 1
        assert angel_interface.get_guild_torch("") is None

    def test_first_submit_sends_only_the_two_answers(self, angel_interface):
        angel_interface._graphql_query = MagicMock(
            side_effect=[
                {"submitVote": True},
                {"publishUserDraftCommentsByParent": True},
                {"finalizeTorchVote": True},
            ]
        )

        assert angel_interface.submit_guild_torch_vote("torch-1", "SUPPORTS", "INTERESTED", {}) is True

        submit, publish, finalize = angel_interface._graphql_query.call_args_list
        assert submit.args[0] == "submitTorchVote"
        assert submit.kwargs["variables"]["vote"] == {
            "torchId": "torch-1",
            "alignment": "SUPPORTS",
            "interest": "INTERESTED",
        }
        assert publish.args[0] == "publishTorchVoteDraftComments"
        assert publish.kwargs["variables"] == {"parentType": "TORCH", "parentId": "torch-1"}
        assert finalize.args[0] == "finalizeGuildTorchVote"
        assert finalize.kwargs["variables"] == {"torchId": "torch-1"}

    def test_later_submit_echoes_saved_age_and_does_not_send_a_comment(self):
        vote = _guild_vote_input(
            "torch-1",
            "HINDERS",
            "NOT_INTERESTED",
            {
                "ageGroups": "8|10",
                "recommendedAge": 8,
                "recommendedAgeReason": "kept from the website",
                "comment": "do not send",
                "message": "",
                "skipped": True,
                "watchLater": True,
            },
        )

        assert vote == {
            "torchId": "torch-1",
            "alignment": "HINDERS",
            "interest": "NOT_INTERESTED",
            "ageGroups": "8|10",
            "recommendedAge": 8,
            "recommendedAgeReason": "kept from the website",
        }
        assert "comment" not in vote
        assert "message" not in vote

    def test_missing_age_is_omitted(self):
        vote = _guild_vote_input(
            "torch-1",
            "NEUTRAL",
            "SOMEWHAT_INTERESTED",
            {"ageGroups": None, "recommendedAge": None, "recommendedAgeReason": ""},
        )
        assert set(vote) == {"torchId", "alignment", "interest"}

    def test_empty_age_groups_string_is_sent_back(self):
        vote = _guild_vote_input("torch-1", "SUPPORTS", "INTERESTED", {"ageGroups": ""})
        assert vote["ageGroups"] == ""

    def test_failed_submit_does_not_publish_or_finalize(self, angel_interface):
        angel_interface._graphql_query = MagicMock(return_value={})
        assert angel_interface.submit_guild_torch_vote("torch-1", "SUPPORTS", "INTERESTED") is False
        angel_interface._graphql_query.assert_called_once()

        angel_interface._graphql_query = MagicMock(return_value={"submitVote": False})
        assert angel_interface.submit_guild_torch_vote("torch-1", "SUPPORTS", "INTERESTED") is False
        angel_interface._graphql_query.assert_called_once()

    def test_publish_failure_still_finalizes(self, angel_interface):
        angel_interface._graphql_query = MagicMock(
            side_effect=[
                {"submitVote": True},
                Exception("publish down"),
                {"finalizeTorchVote": True},
            ]
        )
        assert angel_interface.submit_guild_torch_vote("torch-1", "SUPPORTS", "INTERESTED") is True
        assert [call.args[0] for call in angel_interface._graphql_query.call_args_list][-1] == (
            "finalizeGuildTorchVote"
        )

    def test_finalize_refusal_is_a_failed_vote(self, angel_interface):
        angel_interface._graphql_query = MagicMock(
            side_effect=[
                {"submitVote": True},
                {"publishUserDraftCommentsByParent": True},
                {"finalizeTorchVote": False},
            ]
        )
        assert angel_interface.submit_guild_torch_vote("torch-1", "SUPPORTS", "INTERESTED") is False

    def test_bad_answer_is_not_sent(self, angel_interface):
        angel_interface._graphql_query = MagicMock()
        assert angel_interface.submit_guild_torch_vote("torch-1", "YES", "INTERESTED") is False
        angel_interface._graphql_query.assert_not_called()

    def test_queries_use_the_site_operations(self):
        submit = (GRAPHQL_DIR / "query_submitTorchVote.graphql").read_text(encoding="utf-8")
        assert "mutation submitTorchVote($vote: TorchVoteInput)" in submit
        assert "submitVote(vote: $vote)" in submit
        finalize = (GRAPHQL_DIR / "query_finalizeGuildTorchVote.graphql").read_text(encoding="utf-8")
        assert "finalizeTorchVote(torchId: $torchId)" in finalize
        publish = (GRAPHQL_DIR / "query_publishTorchVoteDraftComments.graphql").read_text(encoding="utf-8")
        assert "publishUserDraftCommentsByParent" in publish
        listing = (GRAPHQL_DIR / "query_getGuildVotingCategories.graphql").read_text(encoding="utf-8")
        assert "nextInCategory(category: $category)" in listing
        history = (GRAPHQL_DIR / "query_getTorchVoteHistory.graphql").read_text(encoding="utf-8")
        assert "query getTorchVoteHistory($input: TorchVotesInput)" in history
        assert "torchVotes(input: $input)" in history
        assert "finalized" in history
        member = (GRAPHQL_DIR / "query_guildMemberStatus.graphql").read_text(encoding="utf-8")
        assert "isGuildMember" in member
        assert "email" not in member.split("query guildMemberStatus", 1)[1]


class TestGuildVotingMenu:
    def test_signed_out_menu_has_no_guild_voting(self, ui_interface, mock_xbmc):
        ui, _logger, _angel = ui_interface
        _sign_in(ui, signed_in=False)
        ui.addon.getSettingBool.return_value = True

        ui.main_menu()

        labels = [item["label"] for item in ui.menu_handler.menu_items]
        assert "Guild Voting" not in labels
        assert labels[-1] == "Settings"
        ui.angel_interface.auth_core.ensure_valid_session.assert_not_called()

    def test_signed_in_menu_puts_guild_voting_above_settings(self, ui_interface, mock_xbmc):
        ui, _logger, _angel = ui_interface
        _sign_in(ui, signed_in=True)
        ui.addon.getSettingBool.return_value = True

        ui.main_menu()

        labels = [item["label"] for item in ui.menu_handler.menu_items]
        assert labels[-2:] == ["Guild Voting", "Settings"]
        guild = ui.menu_handler.menu_items[-2]
        assert guild["action"] == "guild_voting_menu"
        ui.angel_interface.auth_core.ensure_valid_session.assert_not_called()

    def test_signed_out_list_plays_nothing(self, ui_interface, mock_xbmc):
        ui, _logger, angel = ui_interface
        _sign_in(ui, signed_in=False)
        mock_add_item, mock_end_dir, _list_item = mock_xbmc

        with patch.object(ui, "show_error") as show_error:
            assert ui.guild_voting_menu() is False

        show_error.assert_called_once_with("Sign in to vote.")
        mock_add_item.assert_not_called()
        mock_end_dir.assert_not_called()
        angel.get_guild_voting_torches.assert_not_called()

    def test_non_member_sees_join(self, ui_interface, mock_xbmc):
        ui, _logger, angel = ui_interface
        _sign_in(ui)
        angel.is_guild_member.return_value = False

        with patch.object(ui, "show_error") as show_error:
            assert ui.guild_voting_menu() is False

        show_error.assert_called_once_with("Join the Guild to vote.")
        angel.get_guild_voting_torches.assert_not_called()

    def test_membership_failure_is_not_the_empty_list(self, ui_interface):
        ui, _logger, angel = ui_interface
        _sign_in(ui)
        angel.is_guild_member.return_value = None

        with patch.object(ui, "show_error") as show_error:
            assert ui.guild_voting_menu() is False

        show_error.assert_called_once_with("Failed to load Guild Voting.")

    def test_empty_ballot_still_opens_already_voted_on(self, ui_interface, mock_xbmc):
        ui, _logger, angel = ui_interface
        _sign_in(ui)
        angel.is_guild_member.return_value = True
        angel.get_guild_voting_torches.return_value = []
        mock_add_item, mock_end_dir, mock_list_item = mock_xbmc

        with patch.object(ui, "show_error") as show_error:
            assert ui.guild_voting_menu() is True

        show_error.assert_not_called()
        assert [call.kwargs["label"] for call in mock_list_item.call_args_list] == [
            "Already voted on"
        ]
        assert mock_add_item.call_args_list[0].args[3] is True
        mock_end_dir.assert_called_once_with(1)

    def test_list_failure_message(self, ui_interface):
        ui, _logger, angel = ui_interface
        _sign_in(ui)
        angel.is_guild_member.return_value = True
        angel.get_guild_voting_torches.return_value = None

        with patch.object(ui, "show_error") as show_error:
            assert ui.guild_voting_menu() is False

        show_error.assert_called_once_with("Failed to load Guild Voting.")

    def test_torch_labels_keep_fixture_order(self, ui_interface, mock_xbmc):
        ui, _logger, angel = ui_interface
        _sign_in(ui)
        angel.is_guild_member.return_value = True
        angel.get_guild_voting_torches.return_value = [
            {"id": "b", "title": "Second"},
            {"id": "a", "title": "First"},
        ]
        mock_add_item, mock_end_dir, mock_list_item = mock_xbmc

        assert ui.guild_voting_menu() is True

        labels = [call.kwargs["label"] for call in mock_list_item.call_args_list]
        assert labels == ["Already voted on", "Second", "First"]
        urls = [call.args[1] for call in mock_add_item.call_args_list]
        assert "action=guild_voted_menu" in urls[0]
        assert "torch_id=b" in urls[1]
        assert "torch_id=a" in urls[2]
        assert mock_add_item.call_args_list[0].args[3] is True
        assert all(call.args[3] is False for call in mock_add_item.call_args_list[1:])
        mock_end_dir.assert_called_once_with(1)

    def test_voted_menu_plays_without_opening_the_ballot(self, ui_interface, mock_xbmc):
        ui, _logger, angel = ui_interface
        _sign_in(ui)
        angel.is_guild_member.return_value = True
        angel.get_guild_voted_torches.return_value = {
            "torches": [{"id": "land", "title": "Promised Land"}],
            "has_next": True,
            "cursor": "page-2",
        }
        mock_add_item, _mock_end_dir, mock_list_item = mock_xbmc

        assert ui.guild_voted_menu() is True

        labels = [call.kwargs["label"] for call in mock_list_item.call_args_list]
        assert labels == ["Promised Land", "[Load More...]"]
        urls = [call.args[1] for call in mock_add_item.call_args_list]
        assert "action=play_voted_torch" in urls[0]
        assert "torch_id=land" in urls[0]
        assert "action=guild_voted_menu" in urls[1]
        assert "after=page-2" in urls[1]
        assert mock_add_item.call_args_list[0].args[3] is False
        assert mock_add_item.call_args_list[1].args[3] is True

    def test_voted_menu_passes_the_cursor(self, ui_interface):
        ui, _logger, angel = ui_interface
        _sign_in(ui)
        angel.is_guild_member.return_value = True
        angel.get_guild_voted_torches.return_value = {
            "torches": [],
            "has_next": False,
            "cursor": None,
        }

        with patch.object(ui, "show_error") as show_error:
            assert ui.guild_voted_menu("page-2") is False

        angel.get_guild_voted_torches.assert_called_once_with("page-2")
        show_error.assert_called_once_with("You haven't voted on anything yet.")

    def test_replay_does_not_ask_the_questions(self, ui_interface):
        ui, _logger, angel = ui_interface
        _prepare_ballot(ui, angel)
        dialog = MagicMock()

        with (
            patch("kodi_menu_handler.xbmcgui.Dialog", return_value=dialog),
            patch.object(ui, "play_video", return_value=True) as play_video,
        ):
            assert ui.play_voted_torch("torch-1") is True

        play_video.assert_called_once()
        dialog.select.assert_not_called()
        dialog.yesno.assert_not_called()
        angel.submit_guild_torch_vote.assert_not_called()

    def test_cancel_sends_nothing(self, ui_interface):
        ui, _logger, angel = ui_interface
        _prepare_ballot(ui, angel, stream_url="https://example.test/torch.m3u8", drm_required=False)
        dialog = MagicMock()
        dialog.select.return_value = -1

        with (
            patch("kodi_menu_handler.xbmcgui.Dialog", return_value=dialog),
            patch.object(ui, "play_video") as play_video,
            patch.object(ui, "show_error") as show_error,
        ):
            assert ui.play_torch("torch-1") is False

        play_video.assert_called_once()
        angel.submit_guild_torch_vote.assert_not_called()
        show_error.assert_not_called()

    def test_no_on_submit_sends_nothing(self, ui_interface):
        ui, _logger, angel = ui_interface
        _prepare_ballot(ui, angel)
        dialog = MagicMock()
        dialog.select.side_effect = [0, 2]
        dialog.yesno.return_value = False

        with patch("kodi_menu_handler.xbmcgui.Dialog", return_value=dialog):
            assert ui.play_torch("torch-1") is False

        angel.submit_guild_torch_vote.assert_not_called()
        assert dialog.select.call_args_list[0].args[0] == LIGHT
        assert dialog.select.call_args_list[1].args[0] == DISAPPOINTMENT
        dialog.yesno.assert_called_once_with("Guild Voting", "Submit this vote?")

    def test_submit_sends_the_two_answers_and_echoes_saved_age(self, ui_interface):
        ui, _logger, angel = ui_interface
        _prepare_ballot(ui, angel)
        dialog = MagicMock()
        dialog.select.side_effect = [1, 0]
        dialog.yesno.return_value = True
        angel.submit_guild_torch_vote.return_value = True

        with patch("kodi_menu_handler.xbmcgui.Dialog", return_value=dialog):
            assert ui.play_torch("torch-1") is True

        angel.submit_guild_torch_vote.assert_called_once_with(
            "torch-1",
            "HINDERS",
            "INTERESTED",
            {
                "ageGroups": "8|10",
                "recommendedAge": 8,
                "recommendedAgeReason": "kept from the website",
            },
        )
        assert dialog.select.call_args_list[0].kwargs["preselect"] == 0
        assert dialog.select.call_args_list[1].kwargs["preselect"] == 1

    def test_failed_submit_keeps_the_saved_vote(self, ui_interface):
        ui, _logger, angel = ui_interface
        _prepare_ballot(ui, angel)
        saved = dict(angel.get_guild_torch.return_value["vote"])
        dialog = MagicMock()
        dialog.select.side_effect = [2, 2]
        dialog.yesno.return_value = True
        angel.submit_guild_torch_vote.return_value = False

        with (
            patch("kodi_menu_handler.xbmcgui.Dialog", return_value=dialog),
            patch.object(ui, "show_error") as show_error,
        ):
            assert ui.play_torch("torch-1") is False

        show_error.assert_called_once_with(VOTE_FAILED)
        assert angel.get_guild_torch.return_value["vote"] == saved
        angel.submit_guild_torch_vote.assert_called_once()

    def test_unplayable_torch_does_not_ask_the_questions(self, ui_interface):
        ui, _logger, angel = ui_interface
        _prepare_ballot(ui, angel, stream_url=None, drm_required=True)
        dialog = MagicMock()

        with (
            patch("kodi_menu_handler.xbmcgui.Dialog", return_value=dialog),
            patch.object(ui, "play_video") as play_video,
            patch.object(ui, "show_error") as show_error,
            patch.object(ui.playback_handler, "widevine_ready") as widevine_ready,
        ):
            assert ui.play_torch("torch-1") is False

        play_video.assert_not_called()
        widevine_ready.assert_not_called()
        show_error.assert_called_once_with(CANNOT_PLAY)
        dialog.select.assert_not_called()

    def test_drm_cancel_explains_where_to_install(self, ui_interface):
        ui, _logger, angel = ui_interface
        _prepare_ballot(ui, angel, drm_required=True, license_url=LICENSE_URL)
        dialog = MagicMock()
        dialog.select.return_value = -1

        with (
            patch("kodi_menu_handler.xbmcgui.Dialog", return_value=dialog),
            patch.object(ui, "play_video") as play_video,
            patch.object(ui, "show_error") as show_error,
            patch.object(ui.playback_handler, "widevine_ready", return_value=False) as ready,
        ):
            ui.play_torch("torch-1")

        ready.assert_called_once_with("hls")
        play_video.assert_not_called()
        show_error.assert_called_once_with(DRM_NOT_INSTALLED)
        dialog.select.assert_not_called()

    def test_drm_plays_when_widevine_is_ready(self, ui_interface):
        ui, _logger, angel = ui_interface
        _prepare_ballot(
            ui,
            angel,
            drm_required=True,
            license_url=LICENSE_URL,
            certificate_url="https://example.test/cert",
        )
        dialog = MagicMock()
        dialog.select.return_value = -1

        with (
            patch("kodi_menu_handler.xbmcgui.Dialog", return_value=dialog),
            patch.object(ui, "play_video") as play_video,
            patch.object(ui.playback_handler, "widevine_ready", return_value=True),
            patch.object(ui.playback_handler, "widevine_certificate", return_value="CERT"),
        ):
            ui.play_torch("torch-1")

        play_video.assert_called_once_with(
            stream_url="https://example.test/torch.m3u8",
            manifest_type="hls",
            widevine={"license_url": LICENSE_URL, "server_certificate": "CERT"},
        )
        dialog.select.assert_called_once()

    def test_questions_open_after_the_torch_stops(self, ui_interface):
        ui, _logger, angel = ui_interface
        _prepare_ballot(ui, angel)
        dialog = MagicMock()
        dialog.select.return_value = -1
        state = {"playing": False, "window": False, "asked": False}

        class Player:
            def isPlayingVideo(self):
                return state["playing"]

            def stop(self):
                state["stopped"] = True

        class Monitor:
            def abortRequested(self):
                return False

            def waitForAbort(self, seconds):
                if seconds == 0.2 and not state["playing"]:
                    state["playing"] = True
                elif seconds == 0.2 and not state["window"]:
                    state["window"] = True
                elif seconds == 0.2 and state["window"] and state["playing"]:
                    state["playing"] = False
                return False

        def visible(condition):
            assert condition == "VideoPlayer.IsFullscreen"
            return state["window"] is True

        def dialog_factory():
            assert state["playing"] is False
            assert state["window"] is True
            state["asked"] = True
            return dialog

        with (
            patch("kodi_menu_handler.xbmc.Player", Player),
            patch("kodi_menu_handler.xbmc.Monitor", Monitor),
            patch("kodi_menu_handler.xbmc.getCondVisibility", visible),
            patch("kodi_menu_handler.xbmcgui.Dialog", side_effect=dialog_factory),
            patch.object(ui, "play_video", return_value=True),
        ):
            assert ui.play_torch("torch-1") is False

        assert state["asked"] is True
        dialog.select.assert_called_once()
        assert state.get("stopped") is not True

    def test_a_later_video_after_the_picture_is_left_alone(self, ui_interface):
        ui, _logger, angel = ui_interface
        _prepare_ballot(ui, angel)
        dialog = MagicMock()
        state = {
            "file": "plugin://plugin.video.angelstudios/?action=play_torch&torch_id=torch-1",
        }

        class Player:
            def isPlayingVideo(self):
                return True

            def getPlayingFile(self):
                return state["file"]

            def stop(self):
                state["stopped"] = True

        class Monitor:
            def abortRequested(self):
                return False

            def waitForAbort(self, seconds):
                if seconds == 0.2:
                    state["file"] = (
                        "plugin://plugin.video.angelstudios/"
                        "?action=play_episode&episode_guid=other"
                    )
                return False

        with (
            patch("kodi_menu_handler.xbmc.Player", Player),
            patch("kodi_menu_handler.xbmc.Monitor", Monitor),
            patch("kodi_menu_handler.xbmc.getCondVisibility", return_value=True),
            patch("kodi_menu_handler.xbmcgui.Dialog", return_value=dialog),
            patch.object(ui, "play_video", return_value=True),
            patch.object(ui, "show_error") as show_error,
        ):
            assert ui.play_torch("torch-1") is False

        dialog.select.assert_not_called()
        show_error.assert_not_called()
        assert state.get("stopped") is not True

    def test_no_picture_skips_the_questions(self, ui_interface):
        ui, _logger, angel = ui_interface
        _prepare_ballot(ui, angel)
        dialog = MagicMock()
        player = MagicMock()
        player.isPlayingVideo.return_value = False
        monitor = MagicMock()
        monitor.abortRequested.return_value = False
        monitor.waitForAbort.return_value = False
        clock = {"now": 0.0}

        def monotonic():
            clock["now"] += 30
            return clock["now"]

        with (
            patch("kodi_menu_handler.xbmc.Player", return_value=player),
            patch("kodi_menu_handler.xbmc.Monitor", return_value=monitor),
            patch("kodi_menu_handler.xbmcgui.Dialog", return_value=dialog),
            patch("kodi_menu_handler.time.monotonic", monotonic),
            patch.object(ui, "play_video", return_value=True),
            patch.object(ui, "show_error") as show_error,
        ):
            assert ui.play_torch("torch-1") is False

        dialog.select.assert_not_called()
        show_error.assert_called_once_with(CANNOT_PLAY)
        player.stop.assert_not_called()

    def test_blank_player_stops_without_the_questions(self, ui_interface):
        ui, _logger, angel = ui_interface
        _prepare_ballot(ui, angel)
        dialog = MagicMock()
        player = MagicMock()
        player.isPlayingVideo.return_value = True
        monitor = MagicMock()
        monitor.abortRequested.return_value = False
        monitor.waitForAbort.return_value = False
        clock = {"now": 0.0}

        def monotonic():
            clock["now"] += 30
            return clock["now"]

        with (
            patch("kodi_menu_handler.xbmc.Player", return_value=player),
            patch("kodi_menu_handler.xbmc.Monitor", return_value=monitor),
            patch("kodi_menu_handler.xbmc.getCondVisibility", return_value=False),
            patch("kodi_menu_handler.xbmcgui.Dialog", return_value=dialog),
            patch("kodi_menu_handler.time.monotonic", monotonic),
            patch.object(ui, "play_video", return_value=True),
            patch.object(ui, "show_error") as show_error,
        ):
            assert ui.play_torch("torch-1") is False

        dialog.select.assert_not_called()
        show_error.assert_called_once_with(CANNOT_PLAY)
        player.stop.assert_called_once_with()

    def test_stopping_the_torch_ends_the_wait(self, ui_interface):
        ui, _logger, angel = ui_interface
        _prepare_ballot(ui, angel)
        dialog = MagicMock()
        state = {"playing": True}

        class Player:
            def isPlayingVideo(self):
                return state["playing"]

            def getPlayingFile(self):
                return "plugin://plugin.video.angelstudios/?action=play_torch&torch_id=torch-1"

            def stop(self):
                state["stopped"] = True

        class Monitor:
            def abortRequested(self):
                return False

            def waitForAbort(self, _seconds):
                state["playing"] = False
                return False

        with (
            patch("kodi_menu_handler.xbmc.Player", Player),
            patch("kodi_menu_handler.xbmc.Monitor", Monitor),
            patch("kodi_menu_handler.xbmc.getCondVisibility", return_value=False),
            patch("kodi_menu_handler.xbmcgui.Dialog", return_value=dialog),
            patch.object(ui, "play_video", return_value=True),
            patch.object(ui, "show_error") as show_error,
        ):
            assert ui.play_torch("torch-1") is False

        dialog.select.assert_not_called()
        show_error.assert_not_called()
        assert state.get("stopped") is not True

    def test_a_later_video_is_left_alone(self, ui_interface):
        ui, _logger, angel = ui_interface
        _prepare_ballot(ui, angel)
        dialog = MagicMock()
        player = MagicMock()
        player.isPlayingVideo.return_value = True
        player.getPlayingFile.return_value = (
            "plugin://plugin.video.angelstudios/?action=play_episode&episode_guid=other"
        )
        monitor = MagicMock()
        monitor.abortRequested.return_value = False
        monitor.waitForAbort.return_value = False
        clock = {"now": 0.0}

        def monotonic():
            clock["now"] += 30
            return clock["now"]

        with (
            patch("kodi_menu_handler.xbmc.Player", return_value=player),
            patch("kodi_menu_handler.xbmc.Monitor", return_value=monitor),
            patch("kodi_menu_handler.xbmc.getCondVisibility", return_value=False),
            patch("kodi_menu_handler.xbmcgui.Dialog", return_value=dialog),
            patch("kodi_menu_handler.time.monotonic", monotonic),
            patch.object(ui, "play_video", return_value=True),
            patch.object(ui, "show_error") as show_error,
        ):
            assert ui.play_torch("torch-1") is False

        dialog.select.assert_not_called()
        show_error.assert_not_called()
        player.stop.assert_not_called()

    def test_playback_failure_skips_the_questions(self, ui_interface):
        ui, _logger, angel = ui_interface
        _prepare_ballot(ui, angel)
        dialog = MagicMock()

        with (
            patch("kodi_menu_handler.xbmcgui.Dialog", return_value=dialog),
            patch.object(ui, "play_video", return_value=False),
        ):
            assert ui.play_torch("torch-1") is False

        dialog.select.assert_not_called()

    def test_drm_plays_when_the_certificate_cannot_be_read(self, ui_interface):
        ui, _logger, angel = ui_interface
        _prepare_ballot(ui, angel, drm_required=True, license_url=LICENSE_URL)
        dialog = MagicMock()
        dialog.select.return_value = -1

        with (
            patch("kodi_menu_handler.xbmcgui.Dialog", return_value=dialog),
            patch.object(ui, "play_video") as play_video,
            patch.object(ui.playback_handler, "widevine_ready", return_value=True),
            patch.object(ui.playback_handler, "widevine_certificate", return_value=None),
        ):
            ui.play_torch("torch-1")

        play_video.assert_called_once_with(
            stream_url="https://example.test/torch.m3u8",
            manifest_type="hls",
            widevine={"license_url": LICENSE_URL},
        )
        dialog.select.assert_called_once()

    def test_drm_without_a_license_url_does_not_prompt(self, ui_interface):
        ui, _logger, angel = ui_interface
        _prepare_ballot(ui, angel, drm_required=True)
        dialog = MagicMock()
        dialog.select.return_value = -1

        with (
            patch("kodi_menu_handler.xbmcgui.Dialog", return_value=dialog),
            patch.object(ui, "play_video") as play_video,
            patch.object(ui, "show_error") as show_error,
            patch.object(ui.playback_handler, "widevine_ready") as ready,
        ):
            ui.play_torch("torch-1")

        ready.assert_not_called()
        play_video.assert_not_called()
        show_error.assert_called_once_with(CANNOT_PLAY)
        dialog.select.assert_not_called()

    def test_drm_license_with_a_pipe_is_not_played(self, ui_interface):
        ui, _logger, angel = ui_interface
        _prepare_ballot(ui, angel, drm_required=True, license_url="https://example.test/lic|ense")
        dialog = MagicMock()
        dialog.select.return_value = -1

        with (
            patch("kodi_menu_handler.xbmcgui.Dialog", return_value=dialog),
            patch.object(ui, "play_video") as play_video,
            patch.object(ui, "show_error") as show_error,
            patch.object(ui.playback_handler, "widevine_ready") as ready,
        ):
            ui.play_torch("torch-1")

        ready.assert_not_called()
        play_video.assert_not_called()
        show_error.assert_called_once_with(CANNOT_PLAY)
        dialog.select.assert_not_called()

    def test_drm_unknown_extension_is_not_played(self, ui_interface):
        ui, _logger, angel = ui_interface
        _prepare_ballot(
            ui,
            angel,
            stream_url="https://example.test/torch.bin?sig=1",
            drm_required=True,
            license_url=LICENSE_URL,
        )
        dialog = MagicMock()
        dialog.select.return_value = -1

        with (
            patch("kodi_menu_handler.xbmcgui.Dialog", return_value=dialog),
            patch.object(ui, "play_video") as play_video,
            patch.object(ui, "show_error") as show_error,
            patch.object(ui.playback_handler, "widevine_ready") as ready,
        ):
            ui.play_torch("torch-1")

        ready.assert_not_called()
        play_video.assert_not_called()
        show_error.assert_called_once_with(CANNOT_PLAY)
        dialog.select.assert_not_called()

    def test_clear_mpd_uses_dash_manifest(self, ui_interface):
        ui, _logger, angel = ui_interface
        _prepare_ballot(ui, angel, stream_url="https://example.test/video.mpd?sig=1")
        dialog = MagicMock()
        dialog.select.return_value = -1

        with (
            patch("kodi_menu_handler.xbmcgui.Dialog", return_value=dialog),
            patch.object(ui, "play_video") as play_video,
        ):
            ui.play_torch("torch-1")

        play_video.assert_called_once_with(
            stream_url="https://example.test/video.mpd?sig=1",
            manifest_type="mpd",
        )

    def test_movie_row_does_not_open_a_guild_vote(self, ui_interface, mock_xbmc):
        ui, _logger, angel = ui_interface
        angel.get_default_watchlist.return_value = [SPY]

        ui.watchlist_menu()

        urls = [call.args[1] for call in mock_xbmc[0].call_args_list]
        assert urls
        assert all("play_torch" not in url and "guild_voting" not in url for url in urls)
        assert all("action=seasons_menu" in url for url in urls)

    def test_manifest_type_ignores_the_signed_query(self):
        assert _torch_manifest_type("https://example.test/a.mpd?token=secret") == "mpd"
        assert _torch_manifest_type("https://example.test/a.m3u8?token=secret") == "hls"
        assert _torch_manifest_type("https://example.test/a") is None

    def test_extras_skip_a_missing_age(self):
        assert _guild_vote_extras({"alignment": "SUPPORTS"}) == {}


def _prepare_ballot(
    ui,
    angel,
    stream_url="https://example.test/torch.m3u8",
    drm_required=False,
    license_url=None,
    certificate_url=None,
):
    _sign_in(ui)
    angel.is_guild_member.return_value = True
    angel.get_guild_torch.return_value = {
        "id": "torch-1",
        "title": "A Small Film",
        "stream_url": stream_url,
        "drm_required": drm_required,
        "drm_license_url": license_url,
        "drm_certificate_url": certificate_url,
        "vote": {
            "alignment": "SUPPORTS",
            "interest": "SOMEWHAT_INTERESTED",
            "age_groups": "8|10",
            "recommended_age": 8,
            "recommended_age_reason": "kept from the website",
        },
    }


class TestTorchManifestPlayback:
    def test_mpd_sets_dash_inputstream(self, ui_interface):
        ui, _logger, _angel = ui_interface
        addon = MagicMock()
        addon.getSettingBool.return_value = True
        addon.getSettingString.return_value = "auto"
        list_item = MagicMock()

        with (
            patch.object(ui, "addon", addon),
            patch("xbmcgui.ListItem", return_value=list_item),
            patch("xbmcplugin.setResolvedUrl"),
            patch.object(ui.playback_handler, "_ensure_isa_available", return_value=True),
        ):
            ui.play_video(stream_url="https://example.test/torch.mpd", manifest_type="mpd")

        list_item.setProperty.assert_any_call("inputstream.adaptive.manifest_type", "mpd")
        list_item.setMimeType.assert_called_once_with("application/dash+xml")
        license_calls = [
            call.args[0]
            for call in list_item.setProperty.call_args_list
            if call.args and call.args[0] == "inputstream.adaptive.license_type"
        ]
        assert license_calls == []

    def test_widevine_sets_license_properties_when_isa_is_off(self, ui_interface):
        ui, logger, _angel = ui_interface
        addon = MagicMock()
        addon.getSettingBool.return_value = False
        addon.getSettingString.return_value = "auto"
        list_item = MagicMock()
        stream_url = "https://example.test/torch.m3u8"

        with (
            patch.object(ui, "addon", addon),
            patch("xbmcgui.ListItem", return_value=list_item),
            patch("xbmcplugin.setResolvedUrl"),
            patch.object(ui.playback_handler, "_ensure_isa_available", return_value=True) as ensure,
        ):
            ui.play_video(
                stream_url=stream_url,
                manifest_type="hls",
                widevine={"license_url": LICENSE_URL, "server_certificate": "Y2VydA=="},
            )

        ensure.assert_called_once_with("hls", drm="widevine")
        list_item.setProperty.assert_any_call("inputstream", "inputstream.adaptive")
        list_item.setProperty.assert_any_call(
            "inputstream.adaptive.license_type", "com.widevine.alpha"
        )
        list_item.setProperty.assert_any_call(
            "inputstream.adaptive.license_key",
            LICENSE_URL + "|Content-Type=application%2Foctet-stream|R{SSM}|R",
        )
        list_item.setProperty.assert_any_call("inputstream.adaptive.server_certificate", "Y2VydA==")
        list_item.setProperty.assert_any_call("inputstream.adaptive.chooser_resolution_max", "720p")
        list_item.setProperty.assert_any_call(
            "inputstream.adaptive.chooser_resolution_secure_max", "720p"
        )
        list_item.setProperty.assert_any_call(
            "inputstream.adaptive.stream_selection_type", "fixed-res"
        )
        logged = " ".join(
            str(call)
            for call in (
                logger.info.call_args_list
                + logger.warning.call_args_list
                + logger.error.call_args_list
            )
        )
        assert LICENSE_URL not in logged
        assert stream_url not in logged
        logger.info.assert_any_call("Playing protected stream")
        logger.info.assert_any_call(
            "Software Widevine cannot decrypt the 1080p torch track. Playing 720p."
        )

    def test_software_widevine_caps_1080_at_720(self, ui_interface):
        ui, _logger, _angel = ui_interface
        addon = MagicMock()
        addon.getSettingBool.return_value = True
        addon.getSettingString.return_value = "1080p"
        list_item = MagicMock()

        with (
            patch.object(ui, "addon", addon),
            patch("xbmcgui.ListItem", return_value=list_item),
            patch("xbmcplugin.setResolvedUrl"),
            patch.object(ui.playback_handler, "_ensure_isa_available", return_value=True),
        ):
            ui.play_video(
                stream_url="https://example.test/torch.m3u8",
                manifest_type="hls",
                widevine={"license_url": LICENSE_URL},
            )

        list_item.setProperty.assert_any_call("inputstream.adaptive.chooser_resolution_max", "720p")
        chosen = [
            call.args[1]
            for call in list_item.setProperty.call_args_list
            if call.args and call.args[0] == "inputstream.adaptive.chooser_resolution_max"
        ]
        assert chosen == ["720p"]

    def test_software_widevine_keeps_a_lower_quality_choice(self, ui_interface):
        ui, logger, _angel = ui_interface
        addon = MagicMock()
        addon.getSettingBool.return_value = True
        addon.getSettingString.return_value = "480p"
        list_item = MagicMock()

        with (
            patch.object(ui, "addon", addon),
            patch("xbmcgui.ListItem", return_value=list_item),
            patch("xbmcplugin.setResolvedUrl"),
            patch.object(ui.playback_handler, "_ensure_isa_available", return_value=True),
        ):
            ui.play_video(
                stream_url="https://example.test/torch.m3u8",
                manifest_type="hls",
                widevine={"license_url": LICENSE_URL},
            )

        list_item.setProperty.assert_any_call("inputstream.adaptive.chooser_resolution_max", "480p")
        logger.info.assert_any_call("Playing protected stream")
        capped = [
            call
            for call in logger.info.call_args_list
            if call.args and "1080p torch track" in str(call.args[0])
        ]
        assert capped == []

    def test_hardware_widevine_keeps_1080(self, ui_interface):
        ui, logger, _angel = ui_interface
        addon = MagicMock()
        addon.getSettingBool.return_value = True
        addon.getSettingString.return_value = "1080p"
        list_item = MagicMock()

        def platform(name):
            return name == "System.Platform.Android"

        with (
            patch.object(ui, "addon", addon),
            patch("xbmcgui.ListItem", return_value=list_item),
            patch("xbmcplugin.setResolvedUrl"),
            patch(
                "resources.lib.kodi_playback_handler.xbmc.getCondVisibility",
                side_effect=platform,
            ),
            patch.object(ui.playback_handler, "_ensure_isa_available", return_value=True),
        ):
            ui.play_video(
                stream_url="https://example.test/torch.m3u8",
                manifest_type="hls",
                widevine={"license_url": LICENSE_URL},
            )

        list_item.setProperty.assert_any_call(
            "inputstream.adaptive.chooser_resolution_max", "1080p"
        )
        capped = [
            call
            for call in logger.info.call_args_list
            if call.args and "1080p torch track" in str(call.args[0])
        ]
        assert capped == []
