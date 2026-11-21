"""Read Continue Watching, then resume one in-progress title.

Continue Watching's own link leaves content_type empty. The addon does not
seek on that link. Resume uses the catalog link for the same title, which is
the link that seeks to Angel's saved seconds. The play stops as soon as the
position is confirmed.
"""

from urllib.parse import urlencode

from angel_read import graphql
from listing import directory, plugin_url, public_error, rows
from resume_expect import parse_resume, resume_candidate
from runner import register

_QUERY = """
query resumeSample($first: Int) {
  resumeWatching(first: $first) {
    edges {
      node {
        watchableGuid
        position
        content {
          __typename
          ... on ContentMovie {
            name
            duration
            project { slug name }
          }
          ... on ContentEpisode {
            name
            duration
            project { slug name }
          }
          ... on ContentSpecial {
            name
            duration
            project { slug name }
          }
        }
      }
    }
  }
}
"""
_NEAR_SECONDS = 45


@register("continue-list")
def continue_list(kodi):
    """The Continue Watching folder lists Angel's in-progress titles, in Angel's order."""
    try:
        expected, error = _saved()
        if error:
            kodi.check("continue-list", False, error)
            return
        files, error = directory(kodi, plugin_url(action="continue_watching_menu"))
        if error:
            kodi.check("continue-list", False, "Kodi did not open Continue Watching. " + error)
            return
        listed = [row["params"].get("episode_guid", "") for row in rows(files) if row["action"] == "play_episode"]
        wanted = [item["guid"] for item in expected]
        if listed != wanted:
            kodi.check(
                "continue-list",
                False,
                f"Continue Watching listed {len(listed)} titles. Angel has {len(wanted)}.",
            )
            return
        if not wanted:
            kodi.check("continue-list", True, "Continue Watching is empty.")
            return
        kodi.check("continue-list", True, f"Continue Watching listed {len(wanted)} titles in Angel's order.")
    except Exception as exc:
        kodi.check("continue-list", False, public_error(exc))


@register("resume-saved")
def resume_saved(kodi):
    """Resume seeks to Angel's saved seconds, then playback stops."""
    try:
        expected, error = _saved()
        if error:
            kodi.check("resume-saved", False, error)
            return
        chosen = resume_candidate(expected)
        if chosen is None:
            kodi.check(
                "resume-saved",
                True,
                "No in-progress title is far enough from the start and the end to resume.",
            )
            return
        _play_resume(kodi, chosen)
    except Exception as exc:
        kodi.check("resume-saved", False, public_error(exc))
    finally:
        try:
            kodi.stop()
        except Exception as exc:
            kodi.check("resume-saved-stop", False, "Could not stop playback. " + public_error(exc))


def _play_resume(kodi, chosen):
    url = "plugin://plugin.video.angelstudios/?" + urlencode(
        {
            "action": "play_episode",
            "content_type": chosen["content_type"],
            "project_slug": chosen["project_slug"],
            "episode_guid": chosen["guid"],
        }
    )
    target = int(chosen["position"])
    kodi.stop()
    kodi.open_video(url, resume=True)
    clock = kodi.wait(lambda: _near(kodi, target), 40)
    if kodi.blocking_dialog():
        kodi.check("resume-saved", False, f"{chosen['name']} opened a dialog. Playback was stopped.")
        return
    if clock is None:
        seen = kodi.play_time()
        if seen is None:
            kodi.check("resume-saved", False, f"{chosen['name']} did not start playing.")
            return
        kodi.check(
            "resume-saved",
            False,
            f"{chosen['name']} was at {int(seen)} seconds. Angel had saved {target} seconds.",
        )
        return
    kodi.check("resume-saved", True, f"{chosen['name']} resumed at {int(clock)} seconds. Angel had saved {target}.")


def _near(kodi, target):
    if kodi.blocking_dialog():
        return True
    clock = kodi.play_time()
    if clock is None:
        return None
    if abs(clock - target) <= _NEAR_SECONDS:
        return clock
    return None


def _saved():
    data, error = graphql(_QUERY, {"first": 10})
    if error:
        return None, error
    items = parse_resume(data)
    if items is None:
        return None, "Angel did not return Continue Watching."
    return items, ""
