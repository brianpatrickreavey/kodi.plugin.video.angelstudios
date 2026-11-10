"""Decide when a playback position is worth sending to Angel.

Positions are seconds. Angel already stores one position per title.
Starting playback must not replace that position with the beginning.
"""

# A position under this many seconds is the beginning of the title.
# Stopping there must leave an earlier Angel position in place.
BEGINNING_SECONDS = 10

# While playback continues, report at least this often.
REPORT_INTERVAL_SECONDS = 60


def coerce_seconds(value):
    """Return a float number of seconds, or None when the value is not a position."""
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value)
        except ValueError:
            return None
    return None


def position_from_episode(episode):
    """Read watchPosition.position, then the older watch_position field."""
    if not isinstance(episode, dict):
        return None
    watch_position = episode.get("watchPosition")
    if isinstance(watch_position, dict):
        seconds = coerce_seconds(watch_position.get("position"))
        if seconds is not None:
            return seconds
    return coerce_seconds(episode.get("watch_position"))


def apply_saved_position(episode, seconds):
    """Write a saved position onto one episode. Return True when it sticks.

    The value is whole seconds, matching what Angel stores. An existing
    watch_position field is updated too. A missing one is left missing.
    """
    if not isinstance(episode, dict):
        return False
    coerced = coerce_seconds(seconds)
    if coerced is None or coerced < 0:
        return False
    whole = int(round(coerced))
    watch_position = episode.get("watchPosition")
    if isinstance(watch_position, dict):
        watch_position["position"] = whole
    else:
        episode["watchPosition"] = {"position": whole}
    if "watch_position" in episode:
        episode["watch_position"] = whole
    return True


def patch_project_watch_position(project, guid, seconds):
    """Write a saved position onto every matching episode in a cached project."""
    if not isinstance(project, dict) or not guid:
        return False
    changed = False
    for season in project.get("seasons") or []:
        if not isinstance(season, dict):
            continue
        for episode in season.get("episodes") or []:
            if isinstance(episode, dict) and episode.get("guid") == guid:
                changed = apply_saved_position(episode, seconds) or changed
    return changed


def native_resume_point(episode):
    """Return (seconds, total_seconds) for a catalog row, or None.

    Kodi shows Resume from / Play from beginning only when both numbers are
    greater than zero. The numbers are seconds, not a fraction of the title.

    A known position under one second is returned as 0 with a total above 0.
    Kodi treats that as a set resume point and does not fill in the bookmark
    it stored the last time this title was stopped. Leaving the resume point
    unset is what lets that old bookmark appear after a restart.
    """
    seconds = position_from_episode(episode)
    if seconds is None or seconds < 0:
        return None
    if seconds < 1:
        seconds = 0.0
    total = None
    if isinstance(episode, dict):
        source = episode.get("source")
        if isinstance(source, dict):
            total = coerce_seconds(source.get("duration"))
        if total is None or total <= 0:
            total = coerce_seconds(episode.get("duration"))
    if total is None or total <= 0:
        total = seconds + 1 if seconds >= 1 else 1.0
    return seconds, total


def should_report_position(position, saved_position):
    """Return True when this position should be sent to Angel.

    A position in the opening seconds is the beginning. Do not send it when
    Angel already has a later position. A later pause or the once-a-minute
    report still sends the real position.
    """
    seconds = coerce_seconds(position)
    if seconds is None or seconds < 1:
        return False
    saved = coerce_seconds(saved_position)
    if seconds < BEGINNING_SECONDS and saved is not None and saved >= BEGINNING_SECONDS:
        return False
    return True


class WatchProgressSession:
    """Track one playback and decide which samples to send."""

    def __init__(self, saved_position, interval=REPORT_INTERVAL_SECONDS):
        self.saved_position = coerce_seconds(saved_position)
        self.interval = interval
        self.started_at = None
        self.last_report_at = None
        self.last_position = None

    def start(self, now):
        """Mark the moment playback is actually running."""
        self.started_at = now
        self.last_report_at = now

    def observe(self, position, now, paused=False):
        """Return a position to send for the once-a-minute report, or None."""
        seconds = coerce_seconds(position)
        if seconds is not None:
            self.last_position = seconds
        if paused or self.last_report_at is None or seconds is None:
            return None
        if now - self.last_report_at < self.interval:
            return None
        if not should_report_position(seconds, self.saved_position):
            return None
        self.last_report_at = now
        return seconds

    def on_pause_or_stop(self, position):
        """Return a position to send for pause or stop, or None."""
        seconds = coerce_seconds(position)
        if seconds is None:
            seconds = self.last_position
        if seconds is not None:
            self.last_position = seconds
        if not should_report_position(seconds, self.saved_position):
            return None
        return seconds

    def note_saved(self, position):
        """Remember a position Angel accepted, so a later beginning does not replace it."""
        seconds = coerce_seconds(position)
        if seconds is not None:
            self.saved_position = seconds
