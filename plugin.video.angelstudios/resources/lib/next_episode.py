"""Decide when Next Episode is offered and how the next title is opened.

showTime matches the Angel player. The end card appears one second before
that mark. The player control is available for the rest of the episode,
except while the playhead is inside the intro.
"""

from datetime import datetime, timezone
from typing import NamedTuple, Optional
from urllib.parse import urlencode

from watch_progress import coerce_seconds

NEXT_EPISODE_LABEL = "Next Episode"
UNAVAILABLE_MESSAGE = "This content is not available."

# Kodi action ids. The overlay receives these while it is the active window.
ACTION_MOVE_LEFT = 1
ACTION_MOVE_RIGHT = 2
ACTION_MOVE_UP = 3
ACTION_MOVE_DOWN = 4
ACTION_SELECT_ITEM = 7
ACTION_PREVIOUS_MENU = 10
ACTION_SHOW_INFO = 11
ACTION_PAUSE = 12
ACTION_STOP = 13
ACTION_SHOW_GUI = 18
ACTION_SHOW_OSD = 24
ACTION_PLAYER_PLAY = 79
ACTION_VOLUME_UP = 88
ACTION_VOLUME_DOWN = 89
ACTION_MUTE = 91
ACTION_NAV_BACK = 92
ACTION_CHAPTER_OR_BIG_STEP_FORWARD = 97
ACTION_CHAPTER_OR_BIG_STEP_BACK = 98
ACTION_MOUSE_LEFT_CLICK = 100
ACTION_ENTER = 135
ACTION_PLAYER_PLAYPAUSE = 229
ACTION_TRIGGER_OSD = 243

_WATCHABLE_TYPES = {"ContentEpisode", "ContentSpecial", "ContentMovie"}
_CONTENT_TYPES = {
    "ContentEpisode": "series",
    "ContentSpecial": "specials",
    "ContentMovie": "movies",
}
_CHOOSE_ACTIONS = {ACTION_SELECT_ITEM, ACTION_MOUSE_LEFT_CLICK, ACTION_ENTER}
_OSD_ACTIONS = {ACTION_SELECT_ITEM, ACTION_SHOW_OSD, ACTION_ENTER, ACTION_TRIGGER_OSD}
_PAUSE_ACTIONS = {ACTION_PAUSE, ACTION_PLAYER_PLAY, ACTION_PLAYER_PLAYPAUSE}
_BACK_ACTIONS = {ACTION_PREVIOUS_MENU, ACTION_NAV_BACK, ACTION_SHOW_GUI}
_UNFOCUS_ACTIONS = {ACTION_MOVE_DOWN, ACTION_PREVIOUS_MENU, ACTION_NAV_BACK}


class NextEpisodeState(NamedTuple):
    """What the player should show at one playhead position."""

    player_control: bool
    end_card: bool
    title: str


def show_time(credits: Optional[float], duration: Optional[float]) -> float:
    """Return the site's showTime in seconds.

    credits + 8 when credits is set, and never later than 15 seconds before
    the end. When credits is missing, showTime is 15 seconds before the end.
    The result is never below 0. A result of 0 means no end card.
    """
    end_limit = None if duration is None else duration - 15
    if credits is None:
        value = 0.0 if end_limit is None else end_limit
    else:
        value = credits + 8
        if end_limit is not None:
            value = min(value, end_limit)
    if value < 0:
        return 0.0
    return float(value)


def end_card_visible(position: float, show_time_seconds: float) -> bool:
    """The end card starts one second before showTime and stays through the end."""
    if show_time_seconds <= 0:
        return False
    return position >= (show_time_seconds - 1)


def inside_intro(position: float, start: Optional[float], end: Optional[float]) -> bool:
    """True for the intro window, including both ends. Both times must be set."""
    if start is None or end is None:
        return False
    return start <= position <= end


def intro_bounds(episode: object) -> tuple:
    """Return intro start and end, or (None, None) unless both are present."""
    if not isinstance(episode, dict):
        return None, None
    start = coerce_seconds(episode.get("introStartTime"))
    end = coerce_seconds(episode.get("introEndTime"))
    if start is None or end is None:
        return None, None
    return start, end


def credits_and_duration(episode: object) -> tuple:
    """Read credits and duration. A missing credits value stays missing.

    Catalog episodes store both on source. Continue Watching stores credits
    on the content record. Zero is a real value. Null is missing.
    """
    if not isinstance(episode, dict):
        return None, None
    credits = None
    duration = None
    source = episode.get("source")
    if isinstance(source, dict):
        if source.get("credits") is not None:
            credits = coerce_seconds(source.get("credits"))
        if source.get("duration") is not None:
            duration = coerce_seconds(source.get("duration"))
    if credits is None and episode.get("credits") is not None:
        credits = coerce_seconds(episode.get("credits"))
    if duration is None and episode.get("duration") is not None:
        duration = coerce_seconds(episode.get("duration"))
    return credits, duration


def _parse_utc(value: object) -> Optional[datetime]:
    """Parse an Angel timestamp. Z is the UTC suffix used by the API."""
    if not isinstance(value, str) or not value:
        return None
    text = value.replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def watchable_now(content: object, now: datetime) -> bool:
    """True when Angel would keep this next title.

    WATCHABLE counts. So does a Guild availability action whose start time
    has already passed. Anything else is dropped, including a future Guild start.
    """
    if not isinstance(content, dict):
        return False
    if content.get("__typename") not in _WATCHABLE_TYPES:
        return False
    if content.get("watchableAvailabilityStatus") == "WATCHABLE":
        return True
    actions = content.get("actionsToWatch")
    if not isinstance(actions, list):
        return False
    moment = now if now.tzinfo is not None else now.replace(tzinfo=timezone.utc)
    for action in actions:
        if not isinstance(action, dict):
            continue
        if action.get("__typename") != "GuildAvailabilityAction":
            continue
        start = _parse_utc(action.get("startDatetime"))
        if start is not None and start <= moment:
            return True
    return False


def next_title(content: object) -> str:
    """Return the name to show on the end card."""
    if not isinstance(content, dict):
        return ""
    for key in ("title", "subtitle", "name"):
        value = content.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def playback_target(content: object) -> Optional[dict]:
    """Return the fields needed to open this title, or None when they are missing."""
    if not isinstance(content, dict):
        return None
    typename = content.get("__typename")
    content_type = _CONTENT_TYPES.get(typename) if isinstance(typename, str) else None
    if content_type is None:
        return None
    guid = content.get("id")
    project = content.get("project")
    slug = project.get("slug") if isinstance(project, dict) else None
    if not isinstance(guid, str) or not guid or not isinstance(slug, str) or not slug:
        return None
    return {
        "id": guid,
        "slug": slug,
        "content_type": content_type,
        "title": next_title(content),
        "__typename": typename,
    }


def next_play_command(content: object) -> Optional[str]:
    """Return the PlayMedia call that starts this title at the beginning.

    noresume keeps Kodi's resume dialog closed. from_beginning tells the
    addon not to seek to a saved position.
    """
    target = None
    if isinstance(content, dict):
        guid = content.get("id")
        slug = content.get("slug")
        content_type = content.get("content_type")
        if (
            isinstance(guid, str)
            and guid
            and isinstance(slug, str)
            and slug
            and isinstance(content_type, str)
            and content_type
        ):
            target = content
    if target is None:
        target = playback_target(content)
    if not isinstance(target, dict):
        return None
    query = urlencode(
        (
            ("action", "play_episode"),
            ("content_type", target["content_type"]),
            ("project_slug", target["slug"]),
            ("episode_guid", target["id"]),
            ("from_beginning", "1"),
        )
    )
    url = f"plugin://plugin.video.angelstudios/?{query}"
    return f'PlayMedia("{url}",noresume)'


def handle_playback_action(action_id: int, focused_on_button: bool) -> Optional[str]:
    """Map a remote action to one overlay command.

    Up moves onto the Next Episode button. Select on that button plays it.
    Select otherwise opens the player controls. Left and right still seek.
    """
    if focused_on_button and action_id in _CHOOSE_ACTIONS:
        return "choose"
    if not focused_on_button and action_id == ACTION_MOVE_UP:
        return "focus"
    if focused_on_button and action_id in _UNFOCUS_ACTIONS:
        return "unfocus"
    if action_id in _OSD_ACTIONS:
        return "osd"
    if action_id == ACTION_MOVE_LEFT:
        return "smallbackward"
    if action_id == ACTION_MOVE_RIGHT:
        return "smallforward"
    if action_id == ACTION_CHAPTER_OR_BIG_STEP_FORWARD:
        return "bigforward"
    if action_id in (ACTION_MOVE_DOWN, ACTION_CHAPTER_OR_BIG_STEP_BACK):
        return "bigbackward"
    if action_id in _PAUSE_ACTIONS:
        return "pause"
    if action_id == ACTION_STOP:
        return "stop"
    if action_id in _BACK_ACTIONS:
        return "back"
    if action_id == ACTION_SHOW_INFO:
        return "info"
    if action_id == ACTION_VOLUME_UP:
        return "volumeup"
    if action_id == ACTION_VOLUME_DOWN:
        return "volumedown"
    if action_id == ACTION_MUTE:
        return "mute"
    return None


class NextEpisodeSession:
    """The next title for one playback, and what to show at each position."""

    def __init__(self, episode: object, content: object, offer_enabled: bool, autostart_enabled: bool, now=None):
        self.offer_enabled = bool(offer_enabled)
        self.autostart_enabled = self.offer_enabled and bool(autostart_enabled)
        self.intro_start, self.intro_end = intro_bounds(episode)
        credits, duration = credits_and_duration(episode)
        self.show_time = show_time(credits, duration)
        moment = now if isinstance(now, datetime) else datetime.now(timezone.utc)
        if moment.tzinfo is None:
            moment = moment.replace(tzinfo=timezone.utc)
        self.target = playback_target(content) if self.offer_enabled and watchable_now(content, moment) else None
        self.title = next_title(self.target)

    def view_at(self, position: object) -> NextEpisodeState:
        """Return the player control and end card for this playhead position."""
        seconds = coerce_seconds(position)
        if not self.offer_enabled or self.target is None or seconds is None:
            return NextEpisodeState(False, False, "")
        if inside_intro(seconds, self.intro_start, self.intro_end):
            return NextEpisodeState(False, False, "")
        card = end_card_visible(seconds, self.show_time)
        return NextEpisodeState(True, card, self.title if card else "")

    def should_start(self, ended: bool, chosen: bool) -> bool:
        """Start the next title when the viewer chose it, or when it should auto-start.

        Auto-start runs only when both settings are on and the episode ends.
        A stop does not auto-start. Choosing the offer still starts it when
        auto-start is off.
        """
        if self.target is None or not self.offer_enabled:
            return False
        if chosen:
            return True
        return bool(ended) and self.autostart_enabled
