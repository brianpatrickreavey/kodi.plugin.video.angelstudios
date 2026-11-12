"""Names for one check, a bundle of them, or every caption check.

A leaf is one check. A bundle runs its leaves in order. all runs every caption
leaf once. The watchlist bundle is separate, so all does not open the watchlist.
sign-in runs first on every selection and is not one of the watched plays.
The leaf names here match the @register names in resources/lib/tests.
"""

SIGN_IN = "sign-in"

LEAVES = (
    "captions-english",
    "captions-off",
    "captions-none",
    "captions-spanish",
    "captions-forced-only",
    "no-captions",
    "hearing-impaired-on",
    "hearing-impaired-off",
)

# Not part of LEAVES. all stays the caption run.
WATCHLIST = (
    "watchlist-hidden",
    "watchlist-shown",
    "watchlist-matches",
    "watchlist-open",
    "watchlist-add-remove",
)

GROUPS = {
    "all": LEAVES,
    "watchlist": WATCHLIST,
    "captions": (
        "captions-english",
        "captions-off",
        "captions-none",
        "captions-spanish",
        "captions-forced-only",
    ),
    "preferences": (
        "captions-none",
        "captions-spanish",
        "captions-forced-only",
    ),
    "hearing-impaired": (
        "hearing-impaired-on",
        "hearing-impaired-off",
    ),
}


def expand(name):
    """Return the plays for a name, or None when the name is unknown.

    sign-in has no play. The runner still runs that check before the plays.
    """
    if name == SIGN_IN:
        return []
    if name in GROUPS:
        return list(GROUPS[name])
    if name in LEAVES:
        return [name]
    for leaves in GROUPS.values():
        if name in leaves:
            return [name]
    return None


def run_order(name):
    """Return sign-in plus the plays, or None when the name is unknown."""
    if name == SIGN_IN:
        return [SIGN_IN]
    plays = expand(name)
    if plays is None:
        return None
    return [SIGN_IN] + list(plays)


def known_names():
    """Return every name a run can ask for, in alphabetical order."""
    names = set(LEAVES) | set(GROUPS) | {SIGN_IN}
    for leaves in GROUPS.values():
        names.update(leaves)
    return sorted(names)
