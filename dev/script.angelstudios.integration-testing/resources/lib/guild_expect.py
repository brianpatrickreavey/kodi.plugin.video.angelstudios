"""Decide what a Guild Voting directory listing means.

These functions do not call Angel or Kodi. nextInCategory can name a different
torch for a category on the next read, so a folder check looks at the shape
of the Kodi rows rather than matching titles to a second read.
"""

from urllib.parse import parse_qsl, urlsplit


def parse_member(payload):
    """Return True, False, or None when the membership field is missing."""
    if not isinstance(payload, dict):
        return None
    user = payload.get("user")
    if not isinstance(user, dict) or "isGuildMember" not in user:
        return None
    return user.get("isGuildMember") is True


def parse_torches(payload):
    """Return the torches Angel is offering, or None when the response has no list.

    An empty list means there is nothing to vote on. None means the read failed.
    Rows with no torch id are skipped. A blank title becomes "Torch".
    """
    if not isinstance(payload, dict):
        return None
    categories = payload.get("guildVotingCategories")
    if not isinstance(categories, dict):
        return None
    rows = categories.get("nextInCategory")
    if not isinstance(rows, list):
        return None
    torches = []
    for row in rows:
        torch = _torch(row)
        if torch is not None:
            torches.append(torch)
    return torches


def directory_rows(files):
    """Return the label, action, and torch id for each Kodi directory item."""
    rows = []
    for item in files or []:
        if not isinstance(item, dict):
            continue
        file_url = item.get("file")
        if not isinstance(file_url, str):
            file_url = ""
        params = dict(parse_qsl(urlsplit(file_url).query))
        label = item.get("label")
        rows.append(
            {
                "label": label if isinstance(label, str) else "",
                "action": params.get("action", ""),
                "torch_id": params.get("torch_id", ""),
            }
        )
    return rows


def menu_problem(rows):
    """Return a sentence when Guild Voting is missing or is not above Settings.

    An empty string means the main menu has one Guild Voting item and Settings
    is the next item.
    """
    guild = [
        index
        for index, row in enumerate(rows)
        if row["action"] == "guild_voting_menu" or row["label"] == "Guild Voting"
    ]
    if len(guild) != 1:
        return f"The main menu showed {len(guild)} Guild Voting items."
    row = rows[guild[0]]
    if row["label"] != "Guild Voting" or row["action"] != "guild_voting_menu":
        return "The Guild Voting item does not open Guild Voting."
    if guild[0] + 1 >= len(rows):
        return "Guild Voting is not above Settings."
    settings = rows[guild[0] + 1]
    if settings["label"] != "Settings" or settings["action"] != "settings":
        shown = settings["label"] or "a blank item"
        return f"The item under Guild Voting is {shown}."
    return ""


def folder_problem(rows):
    """Return a sentence when Guild Voting is not the ballot list.

    An empty string means the first row opens Already voted on, and every
    later row has a title, a torch id, and the play_torch action. A second
    Angel read can name different torches. nextInCategory changes some
    categories between calls, so this does not compare titles.
    """
    if not rows:
        return "Kodi opened Guild Voting and listed nothing."
    first = rows[0]
    if first["label"] != "Already voted on" or first["action"] != "guild_voted_menu":
        return "Guild Voting does not open with Already voted on."
    if first["torch_id"]:
        return "Already voted on has a torch id."
    for index, row in enumerate(rows[1:], start=1):
        if not row["label"]:
            return f"Torch {index} has no title."
        if row["action"] != "play_torch":
            opened = row["action"] or "nothing"
            return f"Torch {index} opens {opened} instead of the torch."
        if not row["torch_id"]:
            return f"Torch {index} has no torch id."
    return ""


def _torch(row):
    if not isinstance(row, dict):
        return None
    torch = row.get("torch")
    if not isinstance(torch, dict):
        return None
    torch_id = torch.get("id")
    if not isinstance(torch_id, str) or not torch_id:
        return None
    title = torch.get("title")
    if not isinstance(title, str) or not title:
        title = "Torch"
    return {"id": torch_id, "title": title}
