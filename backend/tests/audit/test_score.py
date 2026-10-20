"""The score a run carries on a listing.

The sidebar badge, the home card and the audit tool all show it, and all three
showed nothing because the listing left it out. The arithmetic belongs in one
place, with a test, rather than in each screen.
"""

from __future__ import annotations

from ppcway.api.app import _score_of
from ppcway.audit.models import AuditRun


def run_with(findings: list[dict[str, str]] | None) -> AuditRun:
    return AuditRun(
        site="https://alpha-plumbing.ca/",
        status="done",
        report={"findings": findings} if findings is not None else None,
    )


def test_the_score_is_the_share_of_checks_that_passed() -> None:
    run = run_with(
        [{"status": "good"}, {"status": "good"}, {"status": "needs_you"}, {"status": "ours"}]
    )
    assert _score_of(run) == 50


def test_a_check_with_no_answer_counts_against_nobody() -> None:
    """A business is not marked down because Google would not tell us something."""
    run = run_with([{"status": "good"}, {"status": "unknown"}, {"status": "unknown"}])
    assert _score_of(run) == 100


def test_a_run_with_nothing_to_judge_has_no_score() -> None:
    assert _score_of(run_with(None)) is None
    assert _score_of(run_with([])) is None
    assert _score_of(run_with([{"status": "unknown"}])) is None


def test_the_same_run_scores_the_same_on_its_own_as_in_a_listing() -> None:
    # `/v1/audits/{id}` left the score out, so a finished audit read on its own
    # answered null while the listing answered a number.
    run = run_with(
        [
            {"status": "good", "key": "a"},
            {"status": "needs_you", "key": "b"},
            {"status": "unknown", "key": "c"},
        ]
    )

    assert _score_of(run) == 50
