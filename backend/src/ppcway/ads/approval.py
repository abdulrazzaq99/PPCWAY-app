"""What Google's policy review made of an ad, in the words a person would use.

Google says two things about every ad. Its approval status is the verdict:
approved, approved with limits, or disapproved. Its review status is where the
review stands: in progress, done, under appeal, or "eligible, may serve" while
it finishes. A new ad's verdict is UNKNOWN until the review is done, which
used to be read here as "refused": a merchant who launched a campaign that
morning was told Google would not show their ad, when Google simply had not
looked at it yet.

So the verdict is read together with where the review stands, and only a real
disapproval is called a refusal.
"""

from __future__ import annotations

from dataclasses import dataclass

#: Google's verdicts that come before or without a review, all of which mean
#: "not decided yet".
UNDECIDED = frozenset({"", "UNKNOWN", "UNSPECIFIED"})


@dataclass(frozen=True)
class Standing:
    """Where one ad stands with Google."""

    #: "approved", "limited", "review", "appeal" or "refused".
    key: str
    #: The chip's word or two.
    label: str
    #: One sentence saying what it means for the merchant.
    words: str


def standing(approval: str, review: str = "") -> Standing:
    """The ad's standing, from Google's verdict and where its review is."""
    verdict = (approval or "").upper()
    stage = (review or "").upper()
    if stage == "UNDER_APPEAL":
        return Standing(
            "appeal",
            "Appeal under review",
            "Google is looking at the appeal against its decision on this ad.",
        )
    if verdict == "DISAPPROVED":
        return Standing(
            "refused",
            "Refused by Google",
            "Google will not show this ad until it is fixed.",
        )
    if stage == "ELIGIBLE_MAY_SERVE":
        return Standing(
            "review",
            "Showing, still in review",
            "Google lets this ad show while it finishes reviewing it.",
        )
    if stage == "REVIEW_IN_PROGRESS" or verdict in UNDECIDED:
        return Standing(
            "review",
            "Under review",
            "Google is still reviewing this ad. New and edited ads are usually "
            "reviewed within a working day, and it shows once approved.",
        )
    if verdict == "APPROVED":
        return Standing("approved", "Approved", "Google approved this ad.")
    if verdict in ("APPROVED_LIMITED", "AREA_OF_INTEREST_ONLY"):
        return Standing(
            "limited",
            "Approved, with limits",
            "Google approved this ad but limits where, or to whom, it is shown.",
        )
    return Standing(
        "review",
        "Under review",
        "Google has not given a verdict on this ad yet.",
    )
