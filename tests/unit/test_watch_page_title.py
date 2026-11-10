"""Watch-page title tags for movies, series, and specials."""

import os
from unittest.mock import MagicMock, patch

from resources.lib.kodi_menu_handler import KodiMenuHandler
from resources.lib.menu_projects import ProjectsMenu
from resources.lib.menu_utils import MenuUtils, apply_watch_page_facts, watch_page_facts

GRAPHQL_DIR = os.path.join(
    os.path.dirname(__file__),
    "..",
    "..",
    "plugin.video.angelstudios",
    "resources",
    "lib",
    "angel_graphql",
)

SPY_PLOT = (
    "Ages 8+\n\n" "A man is called to baby-sit his neighbor's children and winds up having to fight off secret agents."
)
TUTTLE_PLOT = "Ages 9+\n\nEthan and Emily Tuttle go on adventures through time to learn about liberty and freedom."
KABIR_PLOT = (
    "Ages 15+\n\nFrom door-to-door window sales to his astronaut cousin, Kabir Singh shows his crowd work skills."
)
ZERO_PLOT = "Ages 13+\n\nA terrified king orders the slaughter of the innocents to destroy newborn hope."
DRY_BAR_TOONS_PLOT = "Hilarious stand-up moments come to life in Dry Bar Toons!"


def _project(project_type, title, highest_score=None, theater=None, **extra):
    project = {
        "name": extra.pop("name", "Title"),
        "projectType": project_type,
        "highestScore": highest_score,
        "theaterDescription": theater,
        "title": title,
    }
    project.update(extra)
    return project


def _title(**fields):
    title = {
        "contentRatings": fields.pop("contentRatings", []),
        "shortDescription": fields.pop("shortDescription", None),
        "originalReleaseDate": fields.pop("originalReleaseDate", None),
        "genres": fields.pop("genres", []),
    }
    title.update(fields)
    return title


SPY = _project(
    "movie",
    _title(
        originalReleaseDate="2010-01-15",
        genres=["Action", "Adventure", "Comedy", "Family"],
        duration=5659,
        shortDescription=(
            "A man is called to baby-sit his neighbor's children and winds up having to fight off secret agents."
        ),
        recommendedAge={"age": 8},
        contentRatings=[{"source": "MPA", "rating": "PG"}, {"source": "USA_PR", "rating": "TV-PG"}],
    ),
    highest_score=73,
    theater="Jackie Chan stars in the long theater description.",
    name="The Spy Next Door",
    metadata={"contentRating": "pg", "genres": ["action", "adventure", "comedy", "family"]},
)

TUTTLE = _project(
    "series",
    _title(
        originalReleaseDate="2021-06-30",
        genres=["Adventure", "Comedy", "Family"],
        shortDescription="Ethan and Emily Tuttle go on adventures through time to learn about liberty and freedom.",
        recommendedAge={"age": 9},
        contentRatings=[{"source": "USA_PR", "rating": "TV-G"}],
    ),
    highest_score=94,
    theater="A grandma with a time-traveling wheelchair takes her twin grandkids on hilarious adventures.",
    name="Tuttle Twins",
    metadata={"contentRating": "tv_y7", "genres": ["comedy", "family", "adventure", "animation"]},
)

DRY_BAR_TOONS = _project(
    "series",
    _title(
        originalReleaseDate="2025-05-07",
        genres=["Comedy"],
        shortDescription=DRY_BAR_TOONS_PLOT,
        recommendedAge=None,
        contentRatings=[{"source": "MPA", "rating": "PG"}, {"source": "USA_PR", "rating": "TV-PG"}],
    ),
    highest_score=None,
    theater=" Hilarious stand-up moments come to life in Dry Bar Toons!",
    name="Dry Bar Toons",
    metadata={"genres": ["comedy", "animation"]},
)

FOR_THE_ONE = _project(
    "movie",
    _title(
        contentRatings=[{"source": "USA_PR", "rating": "TV-G"}, {"source": "MPA", "rating": "G"}],
        duration=5659,
    ),
    highest_score=70,
    name="For the One",
)

KABIR = _project(
    "special",
    _title(
        originalReleaseDate="2026-10-09",
        genres=["Comedy"],
        duration=2528,
        shortDescription=(
            "From door-to-door window sales to his astronaut cousin, Kabir Singh shows his crowd work skills."
        ),
        recommendedAge={"age": 15},
        contentRatings=[{"source": "USA_PR", "rating": "TV-PG"}],
    ),
    highest_score=66,
    name="Kabir Singh - The Last Laugh",
)

ZERO = _project(
    "movie",
    _title(
        originalReleaseDate="2026-12-11",
        genres=["Drama", "Thriller"],
        duration=6900,
        shortDescription="A terrified king orders the slaughter of the innocents to destroy newborn hope.",
        recommendedAge={"age": 13},
        contentRatings=[],
    ),
    highest_score=76,
    name="Zero A.D.: The Birth of Christ",
    metadata={"contentRating": "tv_14", "genres": ["drama"]},
)


def test_spy_next_door_matches_the_watch_page():
    facts = watch_page_facts(SPY)
    assert facts["media_type"] == "movie"
    assert facts["premiered"] == "2010-01-15"
    assert facts["year"] == 2010
    assert "first_aired" not in facts
    assert facts["genres"] == ["Action", "Adventure", "Comedy", "Family"]
    assert facts["mpaa"] == "PG"
    assert facts["rating"] == 73.0
    assert facts["duration"] == 5659
    assert facts["plot"] == SPY_PLOT


def test_tuttle_twins_uses_usa_pr_and_hides_animation():
    facts = watch_page_facts(TUTTLE)
    assert facts["media_type"] == "tvshow"
    assert facts["first_aired"] == "2021-06-30"
    assert "premiered" not in facts
    assert "duration" not in facts
    assert facts["genres"] == ["Adventure", "Comedy", "Family"]
    assert "Animation" not in facts["genres"]
    assert facts["mpaa"] == "TV-G"
    assert facts["rating"] == 94.0
    assert facts["plot"] == TUTTLE_PLOT


def test_dry_bar_toons_has_no_score_age_or_duration():
    facts = watch_page_facts(DRY_BAR_TOONS)
    assert facts["mpaa"] == "TV-PG"
    assert facts["genres"] == ["Comedy"]
    assert "rating" not in facts
    assert "duration" not in facts
    assert facts["plot"] == DRY_BAR_TOONS_PLOT
    assert not facts["plot"].startswith("Ages")


def test_for_the_one_shows_a_score_of_70_and_the_mpa_rating():
    facts = watch_page_facts(FOR_THE_ONE)
    assert facts["mpaa"] == "G"
    assert facts["rating"] == 70.0


def test_kabir_singh_uses_usa_pr_when_mpa_is_missing():
    facts = watch_page_facts(KABIR)
    assert facts["media_type"] == "video"
    assert facts["first_aired"] == "2026-10-09"
    assert facts["mpaa"] == "TV-PG"
    assert "rating" not in facts
    assert facts["duration"] == 2528
    assert facts["genres"] == ["Comedy"]
    assert facts["plot"] == KABIR_PLOT


def test_zero_ad_is_nr_when_content_ratings_are_empty():
    facts = watch_page_facts(ZERO)
    assert facts["mpaa"] == "NR"
    assert facts["genres"] == ["Drama", "Thriller"]
    assert facts["rating"] == 76.0
    assert facts["duration"] == 6900
    assert facts["plot"] == ZERO_PLOT


def test_missing_short_description_uses_the_theater_description():
    project = _project(
        "movie",
        _title(shortDescription=None, originalReleaseDate=None),
        theater="  The long description.  ",
    )
    facts = watch_page_facts(project)
    assert facts["plot"] == "The long description."
    assert "year" not in facts
    assert "premiered" not in facts


def test_age_without_synopsis_still_starts_the_plot():
    project = _project("special", _title(recommendedAge={"age": 12}, shortDescription="  "))
    facts = watch_page_facts(project)
    assert facts["plot"] == "Ages 12+\n\n"


def test_empty_genres_stay_unset():
    project = _project("movie", _title(genres=[]))
    assert "genres" not in watch_page_facts(project)


def test_score_under_70_leaves_the_rating_unset():
    project = _project("movie", _title(), highest_score=69)
    assert "rating" not in watch_page_facts(project)


def test_old_cached_project_keeps_its_previous_labels():
    assert watch_page_facts({"projectType": "movie", "name": "Cached"}) is None
    assert watch_page_facts({"projectType": "podcast", "title": _title()}) is None
    assert watch_page_facts(None) is None


def test_apply_is_a_no_op_without_facts():
    info_tag = MagicMock()
    apply_watch_page_facts(info_tag, None)
    info_tag.setMediaType.assert_not_called()
    info_tag.setMpaa.assert_not_called()


def test_list_item_uses_title_genres_instead_of_metadata():
    menu = MenuUtils(MagicMock())
    list_item = MagicMock()
    info_tag = MagicMock()
    list_item.getVideoInfoTag.return_value = info_tag
    list_item.getLabel.return_value = "The Spy Next Door"

    menu._process_attributes_to_infotags(list_item, SPY)

    info_tag.setGenres.assert_called_with(["Action", "Adventure", "Comedy", "Family"])
    info_tag.setMpaa.assert_called_with("PG")
    info_tag.setPlot.assert_called_with(SPY_PLOT)
    info_tag.setDuration.assert_called_with(5659)
    info_tag.setMediaType.assert_called_with("movie")
    info_tag.setPremiered.assert_called_with("2010-01-15")
    info_tag.setRating.assert_called_with(7.3)


def test_series_list_item_does_not_set_a_duration():
    menu = MenuUtils(MagicMock())
    list_item = MagicMock()
    info_tag = MagicMock()
    list_item.getVideoInfoTag.return_value = info_tag
    list_item.getLabel.return_value = "Tuttle Twins"

    menu._process_attributes_to_infotags(list_item, TUTTLE)

    info_tag.setDuration.assert_not_called()
    info_tag.setFirstAired.assert_called_with("2021-06-30")
    info_tag.setPremiered.assert_not_called()
    info_tag.setMediaType.assert_called_with("tvshow")


def test_projects_menu_keeps_the_watch_page_media_type():
    parent = MagicMock()
    parent.kodi_url = "plugin://plugin.video.angelstudios/"
    menu = ProjectsMenu(parent)
    project = dict(SPY)
    project["slug"] = "spy-next-door"
    with patch("xbmcgui.ListItem") as list_item_cls:
        info_tag = MagicMock()
        list_item_cls.return_value.getVideoInfoTag.return_value = info_tag
        menu._render_projects_menu([project], "movies")
    info_tag.setMediaType.assert_called_with("movie")


def test_opened_movie_uses_the_title_facts_not_the_stream():
    handler = KodiMenuHandler(MagicMock())
    episode = {
        "name": "The Spy Next Door",
        "subtitle": "The Spy Next Door",
        "description": "This episode sentence must not be the plot.",
        "source": {"url": "https://example.com/stream.m3u8", "duration": 9999},
    }
    with patch("xbmcgui.ListItem") as list_item_cls:
        info_tag = MagicMock()
        list_item_cls.return_value.getVideoInfoTag.return_value = info_tag
        handler._create_list_item_from_episode(episode, project=SPY, content_type="movies")
    info_tag.setPlot.assert_called_with(SPY_PLOT)
    info_tag.setMpaa.assert_called_with("PG")
    info_tag.setDuration.assert_called_with(5659)
    info_tag.setMediaType.assert_called_with("movie")


def test_series_episode_keeps_its_own_plot():
    handler = KodiMenuHandler(MagicMock())
    episode_plot = "The twins visit a town where the laws are silly."
    episode = {
        "name": "When Laws Give You Lemons",
        "subtitle": "When Laws Give You Lemons",
        "description": episode_plot,
        "source": {"url": "https://example.com/stream.m3u8", "duration": 1320},
    }
    with patch("xbmcgui.ListItem") as list_item_cls:
        info_tag = MagicMock()
        list_item_cls.return_value.getVideoInfoTag.return_value = info_tag
        handler._create_list_item_from_episode(episode, project=TUTTLE, content_type="series")
    info_tag.setPlot.assert_called_with(episode_plot)
    info_tag.setDuration.assert_called_with(1320)
    assert info_tag.setPlot.call_args.args[0] != TUTTLE_PLOT


def test_series_selection_does_not_ask_for_duration():
    fragment_path = os.path.join(GRAPHQL_DIR, "fragment_WatchPageTitle.graphql")
    with open(fragment_path, "r") as handle:
        text = handle.read()
    series = text.split("... on ContentSeries", 1)[1].split("... on ContentSpecial", 1)[0]
    assert "duration" not in series
    menu_query = os.path.join(GRAPHQL_DIR, "query_getProjectsForMenu.graphql")
    project_query = os.path.join(GRAPHQL_DIR, "query_getProject.graphql")
    with open(menu_query, "r") as handle:
        assert "...WatchPageTitle" in handle.read()
    with open(project_query, "r") as handle:
        assert "...WatchPageTitle" in handle.read()
