"""A run can be one condition, a bundle, or every condition."""

import sys
from pathlib import Path

sys.path.insert(
    0, str(Path(__file__).resolve().parents[2] / "dev/script.angelstudios.integration-testing/resources/lib")
)

from notices import step_notice  # noqa: E402
from selection import LEAVES, expand, run_order  # noqa: E402


def test_one_condition_is_that_condition_only():
    assert expand("captions-spanish") == ["captions-spanish"]


def test_every_run_refreshes_sign_in_first():
    assert run_order("captions-spanish") == ["sign-in", "captions-spanish"]
    assert run_order("all") == ["sign-in"] + list(LEAVES)
    assert run_order("sign-in") == ["sign-in"]


def test_sign_in_is_not_a_watched_play():
    assert expand("all") == list(LEAVES)
    assert expand("sign-in") == []


def test_preferences_bundle_includes_spanish():
    assert expand("preferences") == ["captions-none", "captions-spanish", "captions-forced-only"]


def test_captions_bundle_is_the_tuttle_conditions():
    assert expand("captions") == [
        "captions-english",
        "captions-off",
        "captions-none",
        "captions-spanish",
        "captions-forced-only",
    ]


def test_hearing_impaired_bundle_is_the_pair():
    assert expand("hearing-impaired") == ["hearing-impaired-on", "hearing-impaired-off"]


def test_all_runs_every_leaf_once():
    selected = expand("all")
    assert selected == list(LEAVES)
    assert len(selected) == len(set(selected))


def test_unknown_name_is_rejected():
    assert expand("captions-spain") is None


def test_step_notice_counts_this_run():
    title, message = step_notice(2, 3, "Spanish. Spanish captions should be on.")
    assert title == "Test 2 of 3"
    assert message == "2. Spanish. Spanish captions should be on."
