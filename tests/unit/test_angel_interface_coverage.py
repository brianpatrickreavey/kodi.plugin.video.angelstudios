"""Additional tests to achieve 100% coverage for angel_interface.py edge cases."""

import pytest
from unittest.mock import MagicMock, patch

from resources.lib.angel_interface import AngelStudiosInterface


class TestNormalizerCoverage:
    """Tests for _normalize_resume_episode edge cases."""

    @pytest.fixture
    def angel_interface(self):
        """Fixture for a mocked AngelStudiosInterface instance."""
        with (
            patch("angel_authentication.AngelStudioSession") as mock_session_class,
            patch("angel_authentication.requests.Session") as mock_requests_session,
        ):
            # Mock requests.Session instance with valid JWT
            mock_requests_instance = MagicMock()
            mock_jwt_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJleHAiOjk5OTk5OTk5OTksInN1YiI6InRlc3QtdXNlciJ9.test-signature"
            mock_requests_instance.cookies.get.return_value = mock_jwt_token
            mock_requests_session.return_value = mock_requests_instance

            mock_session_instance = MagicMock()
            mock_session_instance.headers.get.return_value = None
            mock_session_instance.cookies = []
            mock_session_class.return_value.authenticate.return_value = None
            mock_session_class.return_value.get_session.return_value = mock_session_instance
            mock_session_class.return_value._validate_session.return_value = True

            interface = AngelStudiosInterface(logger=MagicMock())
            return interface

    def test_normalize_with_missing_season_dict(self, angel_interface):
        """Test normalizer handles missing season gracefully."""
        content = {
            "__typename": "ContentEpisode",
            "id": "ep-1",
            # season is missing entirely
        }
        node = {"watchableGuid": "guid-1", "position": 100}

        result = angel_interface._normalize_resume_episode(content, node)

        assert result["guid"] == "guid-1"
        assert "seasonNumber" not in result or result.get("seasonNumber") is None

    def test_normalize_with_non_dict_season(self, angel_interface):
        """Test normalizer handles season that is not a dict."""
        content = {
            "__typename": "ContentEpisode",
            "id": "ep-1",
            "season": "not-a-dict",  # Season is not a dict
        }
        node = {"watchableGuid": "guid-1", "position": 100}

        result = angel_interface._normalize_resume_episode(content, node)

        assert result["guid"] == "guid-1"
        # seasonNumber should not be set when season is not a dict
        assert "seasonNumber" not in result or result.get("seasonNumber") is None

    def test_normalize_with_existing_watch_position(self, angel_interface):
        """Test normalizer doesn't override existing watchPosition."""
        content = {
            "__typename": "ContentEpisode",
            "id": "ep-1",
            "watchPosition": {"position": 200},
        }
        node = {"watchableGuid": "guid-1", "position": 100}

        result = angel_interface._normalize_resume_episode(content, node)

        # Should keep original watchPosition, not override with node.position
        assert result["watchPosition"]["position"] == 200

    def test_normalize_without_node_position(self, angel_interface):
        """Test normalizer handles missing node position."""
        content = {
            "__typename": "ContentEpisode",
            "id": "ep-1",
        }
        node = {"watchableGuid": "guid-1"}  # No position field

        result = angel_interface._normalize_resume_episode(content, node)

        assert result["guid"] == "guid-1"
        # watchPosition should not be set when node.position is missing
        assert "watchPosition" not in result or result.get("watchPosition") is None

    def test_normalize_with_season_dict_and_position(self, angel_interface):
        """Test normalizer extracts seasonNumber from season dict and sets watchPosition from node."""
        content = {
            "__typename": "ContentEpisode",
            "id": "ep-1",
            "episodeSubtitle": "The First Episode",  # Type-specific alias that should be mapped
            "episodeDescription": "A test episode",  # Another alias to map
            "season": {
                "id": "season-1",
                "seasonNumber": 2,
            },
            # No existing watchPosition
        }
        node = {"watchableGuid": "guid-1", "position": 150}

        result = angel_interface._normalize_resume_episode(content, node)

        assert result["guid"] == "guid-1"
        # Should map episodeSubtitle to subtitle (line 339)
        assert result["subtitle"] == "The First Episode"
        assert "episodeSubtitle" not in result  # Original key should be removed
        # Should map episodeDescription to description
        assert result["description"] == "A test episode"
        assert "episodeDescription" not in result
        # Should extract seasonNumber from season dict
        assert result["seasonNumber"] == 2
        # Should set watchPosition from node.position
        assert result["watchPosition"]["position"] == 150


class TestQueryFragmentParsing:
    @pytest.fixture
    def angel_interface(self):
        """Fixture for a mocked AngelStudiosInterface instance for fragment parsing tests."""
        with (
            patch("angel_authentication.AngelStudioSession") as mock_session_class,
            patch("angel_authentication.requests.Session") as mock_requests_session,
        ):
            # Mock requests.Session with valid JWT
            mock_requests_instance = MagicMock()
            mock_jwt_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJleHAiOjk5OTk5OTk5OTksInN1YiI6InRlc3QtdXNlciJ9.test-signature"
            mock_requests_instance.cookies.get.return_value = mock_jwt_token
            mock_requests_session.return_value = mock_requests_instance

            mock_session_instance = MagicMock()
            mock_session_instance.headers.get.return_value = None
            mock_session_instance.cookies = []
            mock_session_class.return_value.authenticate.return_value = None
            mock_session_class.return_value.get_session.return_value = mock_session_instance
            mock_session_class.return_value._validate_session.return_value = True

            interface = AngelStudiosInterface(logger=MagicMock())
            return interface

    def test_get_resume_watching_edge_missing_content(self, angel_interface):
        """Test edge with missing content is skipped with warning."""
        mock_response = {
            "resumeWatching": {
                "edges": [
                    {
                        "node": {
                            # content is missing
                        }
                    },
                    {
                        "node": {
                            "watchableGuid": "guid-1",
                            "position": 50,
                            "content": {
                                "__typename": "ContentEpisode",
                                "id": "ep-1",
                            },
                        }
                    },
                ],
                "pageInfo": {"hasNextPage": False},
            }
        }

        with patch.object(angel_interface, "_graphql_query", return_value=mock_response):
            result = angel_interface.get_resume_watching()

        # Should have 1 episode (second one), first was skipped
        assert len(result["episodes"]) == 1
        assert result["episodes"][0]["guid"] == "guid-1"
        angel_interface.log.warning.assert_any_call("Edge missing content, skipping")


class TestUnwrapRelayPagination:
    """Tests for _unwrap_relay_pagination edge cases."""

    @pytest.fixture
    def angel_interface(self):
        with (
            patch("angel_authentication.AngelStudioSession") as mock_session_class,
            patch("angel_authentication.requests.Session") as mock_requests_session,
        ):
            # Mock requests.Session with valid JWT
            mock_requests_instance = MagicMock()
            mock_jwt_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJleHAiOjk5OTk5OTk5OTksInN1YiI6InRlc3QtdXNlciJ9.test-signature"
            mock_requests_instance.cookies.get.return_value = mock_jwt_token
            mock_requests_session.return_value = mock_requests_instance

            mock_session_instance = MagicMock()
            mock_session_instance.headers.get.return_value = None
            mock_session_instance.cookies = []
            mock_session_class.return_value.authenticate.return_value = None
            mock_session_class.return_value.get_session.return_value = mock_session_instance
            mock_session_class.return_value._validate_session.return_value = True
            interface = AngelStudiosInterface(logger=MagicMock())
            return interface

    def test_unwrap_with_none_input(self, angel_interface):
        """Test _unwrap_relay_pagination with None input."""
        result = angel_interface._unwrap_relay_pagination(None)
        assert result == []

    def test_unwrap_with_non_dict_input(self, angel_interface):
        """Test _unwrap_relay_pagination with non-dict input."""
        result = angel_interface._unwrap_relay_pagination("not-a-dict")
        assert result == []

    def test_unwrap_with_non_list_edges(self, angel_interface):
        """Test _unwrap_relay_pagination with edges that are not a list."""
        result = angel_interface._unwrap_relay_pagination({"edges": "not-a-list"})
        assert result == []

    def test_unwrap_with_null_nodes(self, angel_interface):
        """Test _unwrap_relay_pagination skips null nodes."""
        edges_structure = {
            "edges": [
                {"node": {"id": "1"}},
                {"node": None},  # Null node
                None,  # Null edge
                {"node": {"id": "2"}},
            ]
        }
        result = angel_interface._unwrap_relay_pagination(edges_structure)
        assert len(result) == 2
        assert result[0]["id"] == "1"
        assert result[1]["id"] == "2"


class TestNormalizeContentseriesEpisode:
    """Tests for _normalize_contentseries_episode."""

    @pytest.fixture
    def angel_interface(self):
        with (
            patch("angel_authentication.AngelStudioSession") as mock_session_class,
            patch("angel_authentication.requests.Session") as mock_requests_session,
        ):
            # Mock requests.Session with valid JWT
            mock_requests_instance = MagicMock()
            mock_jwt_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJleHAiOjk5OTk5OTk5OTksInN1YiI6InRlc3QtdXNlciJ9.test-signature"
            mock_requests_instance.cookies.get.return_value = mock_jwt_token
            mock_requests_session.return_value = mock_requests_instance

            mock_session_instance = MagicMock()
            mock_session_instance.headers.get.return_value = None
            mock_session_instance.cookies = []
            mock_session_class.return_value.authenticate.return_value = None
            mock_session_class.return_value.get_session.return_value = mock_session_instance
            mock_session_class.return_value._validate_session.return_value = True
            interface = AngelStudiosInterface(logger=MagicMock())
            return interface

    def test_normalize_with_none_input(self, angel_interface):
        """Test normalize with None input."""
        result = angel_interface._normalize_contentseries_episode(None)
        assert result == {}

    def test_normalize_with_non_dict_input(self, angel_interface):
        """Test normalize with non-dict input."""
        result = angel_interface._normalize_contentseries_episode("not-a-dict")
        assert result == {}

    def test_normalize_with_still_data(self, angel_interface):
        """Test normalize copies STILL fields correctly."""
        episode_data = {
            "id": "ep1",
            "name": "Episode 1",
            "portraitStill1": {"cloudinaryPath": "/path1"},
            "portraitStill2": None,  # Null STILL
            "landscapeStill1": {"cloudinaryPath": "/path2"},
            "landscapeStill5": "not-a-dict",  # Invalid STILL
        }
        result = angel_interface._normalize_contentseries_episode(episode_data)

        assert result["id"] == "ep1"
        assert result["name"] == "Episode 1"
        assert "portraitStill1" in result
        assert "portraitStill2" not in result  # Null should not be included
        assert "landscapeStill1" in result
        assert "landscapeStill5" not in result  # Invalid should not be included


class TestMergeEpisodeData:
    """Tests for _merge_episode_data."""

    @pytest.fixture
    def angel_interface(self):
        with (
            patch("angel_authentication.AngelStudioSession") as mock_session_class,
            patch("angel_authentication.requests.Session") as mock_requests_session,
        ):
            # Mock requests.Session with valid JWT
            mock_requests_instance = MagicMock()
            mock_jwt_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJleHAiOjk5OTk5OTk5OTksInN1YiI6InRlc3QtdXNlciJ9.test-signature"
            mock_requests_instance.cookies.get.return_value = mock_jwt_token
            mock_requests_session.return_value = mock_requests_instance

            mock_session_instance = MagicMock()
            mock_session_instance.headers.get.return_value = None
            mock_session_instance.cookies = []
            mock_session_class.return_value.authenticate.return_value = None
            mock_session_class.return_value.get_session.return_value = mock_session_instance
            mock_session_class.return_value._validate_session.return_value = True
            interface = AngelStudiosInterface(logger=MagicMock())
            return interface

    def test_merge_with_none_playback(self, angel_interface):
        """Test merge when playback episode is None."""
        contentseries = {"name": "Content Name", "portraitStill1": {"path": "/p1"}}
        result = angel_interface._merge_episode_data(contentseries, None)

        assert result["name"] == "Content Name"
        assert "portraitStill1" in result

    def test_merge_overlays_display_fields(self, angel_interface):
        """Test merge overlays ContentSeries display fields over playback."""
        playback = {"guid": "g1", "name": "Playback Name", "source": {"url": "http://video"}}
        contentseries = {"name": "Content Name", "subtitle": "CS Subtitle"}

        result = angel_interface._merge_episode_data(contentseries, playback)

        assert result["guid"] == "g1"  # From playback
        assert result["name"] == "Content Name"  # From contentseries (overlay)
        assert result["subtitle"] == "CS Subtitle"  # From contentseries
        assert result["source"]["url"] == "http://video"  # From playback


class TestGetProjectContentSeriesMerge:
    """Tests for get_project() ContentSeries merging logic (lines 334-381)"""

    @pytest.fixture
    def angel_interface(self):
        """Fixture for a mocked AngelStudiosInterface instance."""
        with (
            patch("angel_authentication.AngelStudioSession") as mock_session_class,
            patch("angel_authentication.requests.Session") as mock_requests_session,
        ):
            # Mock requests.Session with valid JWT
            mock_requests_instance = MagicMock()
            mock_jwt_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJleHAiOjk5OTk5OTk5OTksInN1YiI6InRlc3QtdXNlciJ9.test-signature"
            mock_requests_instance.cookies.get.return_value = mock_jwt_token
            mock_requests_session.return_value = mock_requests_instance

            mock_session_instance = MagicMock()
            mock_session_instance.headers.get.return_value = None
            mock_session_instance.cookies = []
            mock_session_class.return_value.authenticate.return_value = None
            mock_session_class.return_value.get_session.return_value = mock_session_instance
            mock_session_class.return_value._validate_session.return_value = True

            interface = AngelStudiosInterface(logger=MagicMock())
            # Store the mock session for use in tests
            interface._session = mock_session_instance
            return interface, mock_session_instance

    def test_get_project_merges_contentseries_with_stills(self, angel_interface):
        """Test get_project() merges ContentSeries display data and STILLs into playback episodes"""
        interface, mock_session = angel_interface

        # GraphQL response with ContentSeries (display data) and playback episodes
        mock_session.post.return_value.status_code = 200
        mock_session.post.return_value.json.return_value = {
            "data": {
                "project": {
                    "id": "proj1",
                    "title": {
                        "__typename": "ContentSeries",
                        "seasons": {
                            "edges": [
                                {
                                    "node": {
                                        "episodes": {
                                            "edges": [
                                                {
                                                    "node": {
                                                        "id": "ep1",
                                                        "name": "Episode 1 Display",
                                                        "portraitStill1": {"cloudinaryPath": "portrait.jpg"},
                                                        "landscapeStill1": {"cloudinaryPath": "landscape.jpg"},
                                                    }
                                                }
                                            ]
                                        }
                                    }
                                }
                            ]
                        },
                    },
                    "seasons": [
                        {
                            "id": "s1",
                            "episodes": [
                                {"id": "ep1", "displayName": "Episode 1 Playback", "videoUrl": "playback.m3u8"}
                            ],
                        }
                    ],
                }
            }
        }

        with patch.object(interface.log, "debug") as mock_debug:
            result = interface.get_project("test-slug")

        # Verify merged data has both display and playback fields
        assert result is not None
        merged_ep = result["seasons"][0]["episodes"][0]
        assert merged_ep["name"] == "Episode 1 Display"  # From ContentSeries
        assert merged_ep["videoUrl"] == "playback.m3u8"  # From playback episode
        assert merged_ep["portraitStill1"] == {"cloudinaryPath": "portrait.jpg"}  # STILL from ContentSeries

        # Verify logging about STILLs
        mock_debug.assert_any_call("Episode ep1: Has STILL fields: ['portraitStill1', 'landscapeStill1']")
        mock_debug.assert_any_call("Merged episode ep1: Has 2 STILL fields")

    def test_get_project_warns_when_no_stills_in_contentseries(self, angel_interface):
        """Test get_project() logs warning when ContentSeries episode has no STILL fields"""
        interface, mock_session = angel_interface

        mock_session.post.return_value.status_code = 200
        mock_session.post.return_value.json.return_value = {
            "data": {
                "project": {
                    "id": "proj1",
                    "title": {
                        "__typename": "ContentSeries",
                        "seasons": {
                            "edges": [
                                {
                                    "node": {
                                        "episodes": {
                                            "edges": [
                                                {
                                                    "node": {
                                                        "id": "ep1",
                                                        "name": "Episode 1",
                                                        # No STILL fields!
                                                    }
                                                }
                                            ]
                                        }
                                    }
                                }
                            ]
                        },
                    },
                    "seasons": [{"id": "s1", "episodes": [{"id": "ep1", "videoUrl": "playback.m3u8"}]}],
                }
            }
        }

        with patch.object(interface.log, "warning") as mock_warning:
            interface.get_project("test-slug")

        # Verify warning logged
        mock_warning.assert_any_call("Episode ep1: No STILL fields found in ContentSeries data")

    def test_get_project_warns_when_stills_lost_after_merge(self, angel_interface):
        """Test get_project() logs warning if STILLs don't survive merge"""
        interface, mock_session = angel_interface

        mock_session.post.return_value.status_code = 200
        mock_session.post.return_value.json.return_value = {
            "data": {
                "project": {
                    "id": "proj1",
                    "title": {
                        "__typename": "ContentSeries",
                        "seasons": {
                            "edges": [
                                {
                                    "node": {
                                        "episodes": {
                                            "edges": [
                                                {
                                                    "node": {
                                                        "id": "ep1",
                                                        "name": "Episode 1",
                                                        "portraitStill1": {"cloudinaryPath": "portrait.jpg"},
                                                    }
                                                }
                                            ]
                                        }
                                    }
                                }
                            ]
                        },
                    },
                    "seasons": [{"id": "s1", "episodes": [{"id": "ep1", "videoUrl": "playback.m3u8"}]}],
                }
            }
        }

        # Mock _merge_episode_data to drop STILLs (simulating a bug)
        with (
            patch.object(
                interface,
                "_merge_episode_data",
                return_value={
                    "id": "ep1",
                    "name": "Episode 1",
                    "videoUrl": "playback.m3u8",
                    # No STILL fields!
                },
            ),
            patch.object(interface.log, "warning") as mock_warning,
        ):
            interface.get_project("test-slug")

        # Verify warning about lost STILLs
        mock_warning.assert_any_call("Merged episode ep1: No STILL fields after merge!")

    def test_get_project_uses_playback_data_when_no_contentseries_match(self, angel_interface):
        """Test get_project() uses playback episode as-is when no ContentSeries match"""
        interface, mock_session = angel_interface

        mock_session.post.return_value.status_code = 200
        mock_session.post.return_value.json.return_value = {
            "data": {
                "project": {
                    "id": "proj1",
                    "title": {
                        "__typename": "ContentSeries",
                        "seasons": {
                            "edges": [
                                {
                                    "node": {
                                        "episodes": {
                                            "edges": [
                                                {"node": {"id": "ep_other", "name": "Other Episode"}}  # Different ID!
                                            ]
                                        }
                                    }
                                }
                            ]
                        },
                    },
                    "seasons": [
                        {
                            "id": "s1",
                            "episodes": [
                                {"id": "ep1", "displayName": "Episode 1 Playback", "videoUrl": "playback.m3u8"}
                            ],
                        }
                    ],
                }
            }
        }

        result = interface.get_project("test-slug")

        # Verify playback data used as-is (not merged)
        assert result is not None
        episode = result["seasons"][0]["episodes"][0]
        assert episode["displayName"] == "Episode 1 Playback"  # Playback name preserved
        assert episode["videoUrl"] == "playback.m3u8"
