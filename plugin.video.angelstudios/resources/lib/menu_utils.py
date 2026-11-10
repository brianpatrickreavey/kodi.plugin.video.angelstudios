"""
Menu Utilities for Angel Studios Kodi addon.
Shared utilities and mappings used across menu handlers.
"""

import xbmcgui  # type: ignore
from kodi_utils import TimedBlock
from urllib.parse import urlencode

# Map menu content types to Angel Studios project types for API calls
angel_menu_content_mapper = {
    "movies": "movie",
    "series": "series",
    "specials": "special",
}

# Map Angel Studios content types to Kodi content types
kodi_content_mapper = {
    "movies": "movies",
    "series": "tvshows",
    "specials": "videos",
}

# ListItem media types. These are not the directory content types above.
_TITLE_MEDIA_TYPES = {
    "movie": "movie",
    "series": "tvshow",
    "special": "video",
}


def _calendar_date(value):
    """Return YYYY-MM-DD, or None when the value is not a date."""
    if not isinstance(value, str):
        return None
    text = value.strip()
    if len(text) < 10 or text[4] != "-" or text[7] != "-":
        return None
    year, month, day = text[:4], text[5:7], text[8:10]
    if not (year.isdigit() and month.isdigit() and day.isdigit()):
        return None
    return text[:10]


def _rating_by_source(ratings):
    chosen = {}
    if not isinstance(ratings, list):
        return chosen
    for item in ratings:
        if not isinstance(item, dict):
            continue
        source = item.get("source")
        rating = item.get("rating")
        if not source or not isinstance(rating, str) or not rating.strip():
            continue
        if source not in chosen:
            chosen[source] = rating.strip()
    return chosen


def _rated_label(project_type, ratings):
    """Series uses USA_PR. A movie or special uses MPA, then USA_PR. Otherwise NR."""
    chosen = _rating_by_source(ratings)
    if project_type == "series":
        return chosen.get("USA_PR") or "NR"
    return chosen.get("MPA") or chosen.get("USA_PR") or "NR"


def _synopsis(title, theater_description):
    short = title.get("shortDescription")
    if isinstance(short, str) and short.strip():
        return short.strip()
    if isinstance(theater_description, str) and theater_description.strip():
        return theater_description.strip()
    return None


def _recommended_age(title):
    recommended = title.get("recommendedAge")
    if not isinstance(recommended, dict):
        return None
    age = recommended.get("age")
    if isinstance(age, bool) or not isinstance(age, int):
        return None
    return age


def _title_plot(title, theater_description):
    synopsis = _synopsis(title, theater_description)
    age = _recommended_age(title)
    if age is None:
        return synopsis
    if synopsis:
        return f"Ages {age}+\n\n{synopsis}"
    return f"Ages {age}+\n\n"


def watch_page_facts(project):
    """Kodi fields for a movie, series, or special that carries watch-page title data.

    Returns None for other project types, and for a cached project that was stored
    before these fields were requested. That copy keeps its previous labels.
    """
    if not isinstance(project, dict):
        return None
    project_type = project.get("projectType")
    media_type = _TITLE_MEDIA_TYPES.get(project_type)
    if not media_type:
        return None
    title = project.get("title")
    if not isinstance(title, dict):
        return None
    if not any(key in title for key in ("contentRatings", "shortDescription", "originalReleaseDate")):
        return None

    facts = {
        "media_type": media_type,
        "mpaa": _rated_label(project_type, title.get("contentRatings")),
    }

    date = _calendar_date(title.get("originalReleaseDate"))
    if date:
        facts["year"] = int(date[:4])
        if project_type == "movie":
            facts["premiered"] = date
        else:
            facts["first_aired"] = date

    genres = title.get("genres")
    if isinstance(genres, list):
        names = [genre for genre in genres if isinstance(genre, str) and genre.strip()]
        if names:
            facts["genres"] = names

    if project_type in ("movie", "special"):
        duration = title.get("duration")
        if isinstance(duration, (int, float)) and not isinstance(duration, bool) and duration > 0:
            facts["duration"] = int(duration)

    score = project.get("highestScore")
    if isinstance(score, (int, float)) and not isinstance(score, bool) and score >= 70:
        facts["rating"] = float(score)

    plot = _title_plot(title, project.get("theaterDescription"))
    if plot is not None:
        facts["plot"] = plot
    return facts


def apply_watch_page_facts(info_tag, facts):
    """Write watch-page facts onto a video info tag. No-op when facts is None."""
    if not facts:
        return
    info_tag.setMediaType(facts["media_type"])
    if "year" in facts:
        info_tag.setYear(facts["year"])
    if "premiered" in facts:
        info_tag.setPremiered(facts["premiered"])
    if "first_aired" in facts:
        info_tag.setFirstAired(facts["first_aired"])
    if facts.get("genres"):
        info_tag.setGenres(facts["genres"])
    info_tag.setMpaa(facts["mpaa"])
    if "duration" in facts:
        info_tag.setDuration(facts["duration"])
    if "rating" in facts:
        # Kodi ignores a rating above 10, so 73 is stored as 7.3.
        info_tag.setRating(facts["rating"] / 10)
    if facts.get("plot") is not None:
        info_tag.setPlot(facts["plot"])


class MenuUtils:
    """Shared utilities for menu operations."""

    def __init__(self, parent):
        """
        Initialize Menu Utils.
        Takes the parent KodiUIInterface instance for shared state.
        """
        self.parent = parent
        self.kodi_handle = parent.handle
        self.kodi_url = parent.kodi_url
        self.log = parent.log

    def _get_angel_project_type(self, menu_content_type):
        """Map menu content type to Angel Studios project type for API calls."""
        return angel_menu_content_mapper.get(menu_content_type, "videos")

    def _get_kodi_content_type(self, content_type):
        """Map content type to Kodi media type for info tags."""
        return kodi_content_mapper.get(content_type, "video")

    def create_plugin_url(self, **kwargs):
        """Create a URL for calling the plugin recursively"""
        return f"{self.kodi_url}?{urlencode(kwargs)}"

    def _build_list_item_for_content(self, content, content_type_str, **options):
        """
        Build a Kodi ListItem for content (episode, project, season, etc.).

        Args:
            content (dict): Content data (from API)
            content_type_str (str): 'episode', 'project', 'season', etc.
            **options: Additional configuration options
                - overlay_progress (bool): Whether to add resume point overlay
                - include_resume (bool): Whether to populate watchPosition
                - is_playback (bool): Whether this is for playback (vs directory)
                - project (dict): Optional project data for episodes
                - stream_url (str): Optional stream URL for playback
                - content_type (str): Content type for media type mapping

        Returns:
            xbmcgui.ListItem: Configured list item ready for addDirectoryItem()
        """
        # Handle episode-specific logic
        if content_type_str == "episode":
            list_item = self._create_list_item_from_episode(
                content,
                project=options.get("project"),
                content_type=options.get("content_type", ""),
                stream_url=options.get("stream_url"),
                is_playback=options.get("is_playback", False),
            )
            # Apply progress bar for directory mode episodes (like continue watching)
            if (
                options.get("overlay_progress")
                and not options.get("is_playback", False)
                and content.get("watchPosition")
            ):
                self._apply_progress_bar(list_item, content["watchPosition"], content.get("duration", 0))
            return list_item

        # General content handling for projects, seasons, etc.
        label = content.get("name", "Unknown")

        # Handle unavailable content
        if content_type_str == "episode" and not content.get("source"):
            label = f"[I] {label} (Unavailable)[/I]"

        list_item = xbmcgui.ListItem(label=label)

        # Set basic properties
        if content_type_str == "episode":
            list_item.setProperty("IsPlayable", "true" if content.get("source") else "false")
            list_item.setIsFolder(False if options.get("is_playback", False) else True)
        else:
            list_item.setIsFolder(True)

        # Set infotags
        info_tag = list_item.getVideoInfoTag()
        if content_type_str == "episode":
            info_tag.setMediaType("video")
        else:
            # Use the content_type from options if provided (for seasons, projects, etc.)
            media_content_type = options.get("content_type", "")
            info_tag.setMediaType(self._get_kodi_content_type(media_content_type))

        self._process_attributes_to_infotags(list_item, content)

        # Apply progress bar if requested
        if options.get("overlay_progress") and content.get("watchPosition"):
            self._apply_progress_bar(list_item, content["watchPosition"], content.get("duration", 0))

        return list_item

    def _process_attributes_to_infotags(self, list_item, info_dict):
        """
        Set VideoInfoTag attributes using direct dictionary access for performance.

        This function optimizes metadata processing by avoiding generic loops over all dict keys,
        which previously caused 85-90% overhead (33ms → 3-5ms per episode). It uses explicit
        attribute checks for known API schema fields to eliminate unnecessary iterations,
        logging, and conditional evaluations.

        Key optimizations:
        - Direct dict.get() access: No loop over 25+ keys; only processes known attributes.
        - Cloudinary URL reuse: Builds URLs once and reuses for multiple art keys (e.g., logo
          for logo/clearlogo/icon) to avoid redundant API calls (~2-3ms savings per episode).
        - Minimal logging: Debug logs removed from hot path; timing traces available in trace mode.

        Performance impact (measured):
        - Episodes: 33ms → 3-5ms (85-90% reduction)
        - Movies: 11ms → 2-3ms (73-82% reduction)
        - Seasons: 5ms → 1-2ms (60-80% reduction)

        Schema assumptions:
        - Based on Angel Studios API v1 schema (stable; new attributes require manual updates).
        - Handles nested data (metadata, season, cast) and fallbacks (e.g., discoveryPoster*).
        - Skips irrelevant fields (source, watchPosition) handled elsewhere.

        Args:
            list_item (xbmcgui.ListItem): The Kodi list item to update.
            info_dict (dict): Episode/project metadata dict from API.

        Note: For agents/AI: This is a performance-critical hot path. Avoid adding loops or
        per-key logging. If schema changes, update direct checks explicitly.
        """
        with TimedBlock("_process_attributes_to_infotags"):
            self.log.info(f"Processing attributes for list item: {list_item.getLabel()}")
            info_tag = list_item.getVideoInfoTag()

        facts = watch_page_facts(info_dict)

        # Direct attribute setting (no loop, no per-key logging)
        if info_dict.get("name"):
            info_tag.setTitle(info_dict["name"])
        if facts is None and info_dict.get("description"):
            info_tag.setPlot(info_dict["description"])
        if facts is None and info_dict.get("theaterDescription"):
            info_tag.setPlot(info_dict["theaterDescription"])
        if facts is None and info_dict.get("duration"):
            info_tag.setDuration(info_dict["duration"])
        if info_dict.get("episodeNumber"):
            info_tag.setEpisode(info_dict["episodeNumber"])
        if info_dict.get("seasonNumber") is not None and info_dict["seasonNumber"] != 0:
            info_tag.setSeason(info_dict["seasonNumber"])
        if info_dict.get("media_type"):
            info_tag.setMediaType(info_dict["media_type"])

        # Handle nested metadata. A watch-page title uses its own rating and genres.
        metadata = info_dict.get("metadata", {})
        if facts is None and metadata.get("contentRating"):
            info_tag.setMpaa(metadata["contentRating"])
        if facts is None and metadata.get("genres"):
            info_tag.setGenres(metadata["genres"])

        # Handle cast
        cast_list = info_dict.get("cast")
        if isinstance(cast_list, list):
            valid_actors = []
            for actor_entry in cast_list:
                if not isinstance(actor_entry, dict):
                    continue
                name = actor_entry.get("name")
                if name and isinstance(name, str) and name.strip():
                    try:
                        valid_actors.append(__import__("xbmc").Actor(name=name.strip()))
                    except Exception:
                        pass
            if valid_actors:
                info_tag.setCast(valid_actors)

        # Handle nested season
        season_dict = info_dict.get("season")
        if isinstance(season_dict, dict):
            season_num = season_dict.get("seasonNumber")
            if season_num is not None:
                info_tag.setSeason(season_num)

        # Skip nested source and watchPosition - handled elsewhere

        # Handle artwork with URL reuse
        art_dict = {}
        poster_path = info_dict.get("discoveryPosterCloudinaryPath") or info_dict.get("posterCloudinaryPath")
        if poster_path:
            art_dict["poster"] = self.parent.angel_interface.get_cloudinary_url(poster_path)

        landscape_path = info_dict.get("discoveryPosterLandscapeCloudinaryPath") or info_dict.get(
            "posterLandscapeCloudinaryPath"
        )
        if landscape_path:
            url = self.parent.angel_interface.get_cloudinary_url(landscape_path)
            art_dict["landscape"] = url
            art_dict["fanart"] = url  # Reuse: avoids duplicate get_cloudinary_url() call

        logo_path = info_dict.get("logoCloudinaryPath")
        if logo_path:
            url = self.parent.angel_interface.get_cloudinary_url(logo_path)
            art_dict["logo"] = url
            art_dict["clearlogo"] = url
            art_dict["icon"] = url  # Reuse: same URL for all logo variants

        # Handle stills
        for still_key in ("portraitStill1", "portraitStill2", "portraitTitleImage"):
            still_dict = info_dict.get(still_key)
            if not isinstance(still_dict, dict):
                # Check nested in title for projects
                title_dict = info_dict.get("title", {})
                if isinstance(title_dict, dict):
                    still_dict = title_dict.get(still_key)
            if isinstance(still_dict, dict):
                cp = still_dict.get("cloudinaryPath")
                if cp:
                    url = self.parent.angel_interface.get_cloudinary_url(cp)
                    self.log.debug(f"Using {still_key} for poster: {cp}", category="art")
                    if still_key == "portraitTitleImage":
                        art_dict["poster"] = url
                    elif still_key == "portraitStill1":
                        art_dict["poster"] = url
                    art_dict.setdefault("thumb", url)

        for still_key in ("landscapeStill1", "landscapeStill2"):
            still_dict = info_dict.get(still_key)
            if isinstance(still_dict, dict):
                cp = still_dict.get("cloudinaryPath")
                if cp:
                    url = self.parent.angel_interface.get_cloudinary_url(cp)
                    self.log.debug(f"Using {still_key} for landscape: {cp}", category="art")
                    art_dict.setdefault("landscape", url)
                    art_dict.setdefault("fanart", url)

        if art_dict:
            list_item.setArt(art_dict)

        apply_watch_page_facts(info_tag, facts)
        return

    def _create_list_item_from_episode(
        self, episode, project=None, content_type="", stream_url=None, is_playback=False
    ):
        """
        Unified helper to create a ListItem from an episode dict.
        - episode: Raw episode dict.
        - project: Optional project dict (for playback metadata).
        - content_type: For directory media type.
        - stream_url: If provided, enables playback mode.
        - is_playback: True for playback mode (sets offscreen, path, etc.).
        """
        self.log.info(
            f"Creating ListItem for episode: {episode.get('name', 'Unknown Episode')}, is_playback={is_playback}"
        )
        episode_available = bool(episode.get("source"))
        episode_subtitle = episode.get("subtitle", episode.get("name", "Unknown Episode"))

        # If the episode is not available (no source), indicate that in the subtitle with italics.
        if not episode_available:
            episode_subtitle = f"[I] {episode_subtitle} (Unavailable)[/I]"

        # Both directory items and playback items must be set to IsPlayable true
        # if the episode is available.
        list_item = __import__("xbmcgui").ListItem(label=episode_subtitle, offscreen=is_playback)
        list_item.setProperty("IsPlayable", "true" if episode_available else "false")

        # Create ListItem
        if is_playback:
            quality_pref = self.parent._get_quality_pref()
            quality_mode = quality_pref["mode"]
            target_height = quality_pref["target_height"]
            manifest_url = (episode.get("source") or {}).get("url", stream_url)

            list_item.setIsFolder(False)

            if manifest_url:
                self.log.info(f"Loading Manifest: {manifest_url}")

            use_isa = self.parent.addon.getSettingBool("use_isa")
            isa_ready = False
            stream_selection_type = None

            if use_isa:
                isa_ready = self.parent._ensure_isa_available("hls")
                if not isa_ready:
                    isa_ready = __import__("xbmc").getCondVisibility("System.HasAddon(inputstream.adaptive)")
                    if isa_ready:
                        self.log.info("ISA detected via System.HasAddon; proceeding without inputstreamhelper")

                if isa_ready:
                    if quality_mode == "manual":
                        stream_selection_type = "ask-quality"
                    elif quality_mode == "fixed":
                        stream_selection_type = "fixed-res"
                    else:
                        stream_selection_type = "adaptive"

                    if manifest_url:
                        list_item.setPath(manifest_url)
                    list_item.setProperty("inputstream", "inputstream.adaptive")
                    list_item.setProperty("inputstream.adaptive.manifest_type", "hls")
                    if stream_selection_type:
                        list_item.setProperty(
                            "inputstream.adaptive.stream_selection_type",
                            stream_selection_type,
                        )
                    if target_height and quality_mode != "manual":
                        chooser_map = {
                            1080: "1080p",
                            720: "720p",
                            480: "480p",
                            360: "360p",
                        }
                        chooser_value = chooser_map.get(target_height)
                        if chooser_value:
                            list_item.setProperty(
                                "inputstream.adaptive.chooser_resolution_max",
                                chooser_value,
                            )
                            list_item.setProperty(
                                "inputstream.adaptive.chooser_resolution_secure_max",
                                chooser_value,
                            )
                    list_item.setMimeType("application/vnd.apple.mpegurl")
                    list_item.setContentLookup(False)
                else:
                    self.log.info("ISA requested but unavailable; falling back to native playback")
            else:
                self.log.info("ISA disabled via settings; using Kodi builtin HLS handling")

            if not isa_ready:
                if not manifest_url:
                    self.log.warning("No manifest URL available; skipping quality selection")
                else:
                    list_item.setPath(manifest_url)

            # Stream details
            video_stream_detail = __import__("xbmc").VideoStreamDetail()
            video_stream_detail.setCodec("h264")
            video_stream_detail.setWidth(1920)
            video_stream_detail.setHeight(1080)
            info_tag = list_item.getVideoInfoTag()
            info_tag.addVideoStream(video_stream_detail)
        else:
            list_item.setIsFolder(True)

        # Set common metadata (inject project logo if episode lacks one)
        art_info = dict(episode) if isinstance(episode, dict) else {}
        try:
            if project and isinstance(project, dict) and "logoCloudinaryPath" in project:
                if "logoCloudinaryPath" not in art_info:
                    self.log.debug(
                        f"[ART] Injecting project logo into episode: {project['logoCloudinaryPath']}", category="art"
                    )
                    art_info["logoCloudinaryPath"] = project["logoCloudinaryPath"]
        except Exception:
            pass

        self._process_attributes_to_infotags(list_item, art_info)

        # Set media type and additional metadata
        info_tag = list_item.getVideoInfoTag()
        if episode_available:
            info_tag.setDuration(episode.get("source", {}).get("duration", 0))
        if is_playback:
            info_tag.setMediaType("video")
            # Additional playback metadata from project
            if project and isinstance(project.get("name"), str) and project["name"].strip():
                info_tag.setTvShowTitle(project["name"])
        else:
            info_tag.setMediaType(self._get_kodi_content_type(content_type))
            info_tag.setTitle(episode_subtitle)
            if (
                episode.get("mediatype") == "episode"
                and project
                and isinstance(project.get("name"), str)
                and project["name"].strip()
            ):
                info_tag.setTvShowTitle(project["name"])
        self._overlay_opened_title(info_tag, project, content_type)
        return list_item  # noqa: E129

    def _overlay_opened_title(self, info_tag, project, content_type):
        """Use the watch-page facts on the row a movie or special opens onto.

        A series episode keeps its own plot and its own duration.
        """
        if content_type not in ("movies", "specials"):
            return
        apply_watch_page_facts(info_tag, watch_page_facts(project))

    def _apply_progress_bar(self, list_item, watch_position_data, duration_seconds):
        """
        Apply native Kodi resume point indicator to a ListItem.

        Args:
            list_item: xbmcgui.ListItem to apply progress to
            watch_position_data: Watch position data - either a number (seconds) or dict with 'position' field
            duration_seconds: Total duration in seconds (float)

        Returns:
            None. Modifies list_item in place.
        """
        # Extract position from data structure
        if isinstance(watch_position_data, dict):
            watch_position_seconds = watch_position_data.get("position")
            if watch_position_seconds is None:
                self.log.warning(f"Invalid watchPosition data: missing 'position' field in {watch_position_data}")
                return
        else:
            watch_position_seconds = watch_position_data

        if watch_position_seconds is None or duration_seconds is None or duration_seconds == 0:
            self.log.debug(
                f"Skipping progress bar: watch_position={watch_position_seconds}, " f"duration={duration_seconds}"
            )
            return

        try:
            resume_point = float(watch_position_seconds) / float(duration_seconds)
            # Clamp to [0.0, 1.0]
            resume_point = max(0.0, min(1.0, resume_point))

            info_tag = list_item.getVideoInfoTag()
            info_tag.setResumePoint(resume_point)
            self.log.debug(
                f"Applied progress bar: {watch_position_seconds}s / {duration_seconds}s = {resume_point:.2%}"
            )
        except Exception as e:
            self.log.warning(
                f"Failed to apply progress bar: {e}. "
                f"watch_position={watch_position_seconds}, duration={duration_seconds}"
            )
