# data.py
# Reusable test data for unit tests

MOCK_PROJECTS_DATA = {
    "movies": [{"slug": "test_movie_project", "name": "Test Movie Name", "projectType": "movie"}],
    "series": [{"slug": "test_series_project", "name": "Test Series Name", "projectType": "series"}],
    "specials": [{"slug": "test_special_project", "name": "Test Special Name", "projectType": "special"}],
}

MOCK_SEASON_DATA = {
    "episodes": [
        {
            "id": 1,
            "guid": "episode-guid-1",
            "name": "Episode Name 1",
            "subtitle": "Episode Subtitle 1",
            "source": {"url": "http://example.com/episode1.mp4"},
        },
        {
            "id": 2,
            "guid": "episode-guid-2",
            "name": "Episode Name 2",
            "subtitle": "Episode Subtitle 2",
            "source": None,  # Unavailable episode
        },
    ]
}

MOCK_PROJECT_DATA = {
    "single_season_project": {
        "name": "A Movie: Single Season Project",
        "slug": "a-movie-single-season-project",
        "projectType": "movie",
        "seasons": [
            {
                "id": "season-uuid-1",
                "name": "Season 1",
                "episodes": [
                    {
                        "id": 1,
                        "name": "A Movie: The Movie",
                        "guid": "guid-guid-guid-guid-guid-1111",
                        "seasonNumber": 1,
                        "episodeNumber": 1,
                        "projectSlug": "a-movie-single-season-project",
                        "slug": "a-movie-the-movie",
                        "source": {"url": "http://example.com/episode1.mp4"},
                    },
                    {
                        "id": 2,
                        "name": "A Movie: Sneak Peak",
                        "guid": "guid-guid-guid-guid-guid-2222",
                        "seasonNumber": 1,
                        "episodeNumber": 2,
                        "projectSlug": "a-movie-single-season-project",
                        "slug": "a-movie-sneak-peak",
                        "source": {"url": "http://example.com/episode2.mp4"},
                    },
                    {
                        "id": 3,
                        "name": "A Movie: Trailer",
                        "guid": "guid-guid-guid-guid-guid-3333",
                        "seasonNumber": 1,
                        "episodeNumber": 3,
                        "projectSlug": "a-movie-single-season-project",
                        "slug": "a-movie-trailer",
                        "source": {"url": "http://example.com/episode3.mp4"},
                    },
                ],
            }
        ],
    },
    "multi_season_project": {
        "name": "Multi Season Project",
        "slug": "test-multi-season-project",
        "projectType": "series",
        "seasons": [
            {
                "id": "multi-season-uuid-1",
                "name": "Season 1",
                "episodes": [
                    {
                        "id": 1,
                        "name": "Season 1 Episode 1",
                        "seasonNumber": 1,
                        "guid": "s1ep1-guid",
                        "source": {"url": "http://example.com/s1ep1.mp4"},
                    },
                    {
                        "id": 2,
                        "name": "Season 1 Episode 2",
                        "seasonNumber": 1,
                        "guid": "s1ep2-guid",
                        "source": {"url": "http://example.com/s1ep2.mp4"},
                    },
                ],
            },
            {
                "id": "multi-season-uuid-2",
                "name": "Season 2",
                "episodes": [
                    {
                        "id": 1,
                        "name": "Season 2 Episode 1",
                        "seasonNumber": 2,
                        "guid": "s2ep1-guid",
                        "source": {"url": "http://example.com/s2ep1.mp4"},
                    },
                    {
                        "id": 2,
                        "name": "Season 2 Episode 2",
                        "seasonNumber": 2,
                        "guid": "s2ep2-guid",
                        "source": {"url": "http://example.com/s2ep2.mp4"},
                    },
                ],
            },
        ],
    },
    "episodes_without_seasons_project": {
        "name": "Episodes Without Seasons Project",
        "slug": "test-episodes-without-seasons-project",
        "projectType": "special",
        "seasons": [
            {
                "id": "special-season-uuid-1",
                "name": "All Episodes",
                "episodes": [
                    {
                        "id": 1,
                        "name": "Special Episode 1",
                        "guid": "spec-ep1-guid",
                        "source": {"url": "http://example.com/spec-ep1.mp4"},
                    },
                    {
                        "id": 2,
                        "name": "Special Episode 2",
                        "guid": "spec-ep2-guid",
                        "source": {"url": "http://example.com/spec-ep2.mp4"},
                    },
                ],
            }
        ],
    },
}

MOCK_EPISODE_DATA = {
    "episode": {
        "id": 1,
        "guid": "episode-guid-1",
        "name": "Episode Name 1",
        "subtitle": "Episode Subtitle 1",
        "source": {"url": "http://example.com/episode1.mp4"},
        "watch_position": 120,  # For resume
        "posterCloudinaryPath": "cloud_path_for_poster",
        "posterLandscapeCloudinaryPath": "cloud_path_for_landscape_poster",
        "logoCloudinaryPath": "cloud_path_for_logo",
        "fakeCloudinaryPath": "cloud_path_for_fake_image",
        "metadata": {
            "description": "This is a test episode description.",
            "duration": 3600,
            "releaseDate": "2023-01-01",
            "rating": "PG-13",
            "genres": ["Drama", "Action"],
            "cast": ["Actor One", "Actor Two"],
            "directors": ["Director One"],
            "writers": ["Writer One"],
        },
        "seasonNumber": 0,
    },
    "project": {"name": "Test Project", "slug": "test-project"},
}

MOCK_GRAPHQL_RESPONSE = {"data": MOCK_PROJECT_DATA["multi_season_project"]}

MOCK_RESUME_WATCHING_RESPONSE = {
    "resumeWatching": {
        "edges": [
            {
                "cursor": "cursor-1",
                "node": {
                    "watchableGuid": "resume-guid-1",
                    "position": 1200,
                    "updatedAt": "2026-01-08T12:00:00Z",
                    "content": {
                        "id": "ep1",
                        "name": "Episode 1",
                        "__typename": "ContentEpisode",
                    },
                    "__typename": "WatchPosition",
                },
            },
            {
                "cursor": "cursor-2",
                "node": {
                    "watchableGuid": "resume-guid-2",
                    "position": 600,
                    "updatedAt": "2026-01-07T12:00:00Z",
                    "content": {
                        "id": "ep2",
                        "name": "Episode 2",
                        "__typename": "ContentEpisode",
                    },
                    "__typename": "WatchPosition",
                },
            },
        ],
        "pageInfo": {
            "hasNextPage": True,
            "endCursor": "cursor-2",
        },
    }
}

# Router dispatch cases for main.py tests
ROUTER_DISPATCH_CASES = [
    ("movies_menu", "projects_menu", {"content_type": "movies"}),
    ("series_menu", "projects_menu", {"content_type": "series"}),
    ("specials_menu", "projects_menu", {"content_type": "specials"}),
    ("podcast_menu", "projects_menu", {"content_type": "podcasts"}),
    ("livestream_menu", "projects_menu", {"content_type": "livestreams"}),
    ("watchlist_menu", "watchlist_menu", {}),
    ("continue_watching_menu", "continue_watching_menu", {}),
    ("top_picks_menu", "top_picks_menu", {}),
    ("other_content_menu", "other_content_menu", {}),
    ("all_content_menu", None, {}),
    ("seasons_menu", "seasons_menu", {"content_type": "series", "project_slug": "slug"}),
    ("episodes_menu", "episodes_menu", {"content_type": "series", "project_slug": "slug", "season_id": "1"}),
    ("play_episode", "play_episode", {"episode_guid": "guid", "project_slug": "slug"}),
]
