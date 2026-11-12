"""Names for one caption condition, a bundle of them, or every condition.

A leaf is one play. A bundle runs its leaves in order. all runs every leaf once.
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

GROUPS = {
    "all": LEAVES,
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
    return sorted(set(LEAVES) | set(GROUPS) | {SIGN_IN})
