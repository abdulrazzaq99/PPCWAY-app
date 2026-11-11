"""An ad Google has not reviewed yet is not an ad Google refused.

On 11 November a campaign launched that morning had its ad listed under Needs
you as "Ad refused: Google will not show this ad until it is fixed", with a red
"unknown" on its Ads tab. Google had simply not reviewed it yet: a new ad's
approval is UNKNOWN until the review is done. These hold every place that
reads an ad's approval to the difference.
"""

from __future__ import annotations

from datetime import UTC, date, datetime

import httpx
import pytest
import sqlalchemy as sa
from sqlalchemy.orm import Session as DbSession

from ppcway.ads.approval import standing
from ppcway.ads.mirror import MICRO, MirrorAd, MirrorCampaign
from ppcway.ads.numbers import account_numbers, campaign_numbers
from ppcway.ads.sync import sync_structure
from ppcway.auth import models as _auth  # noqa: F401 - registers the account table
from ppcway.db.base import Base
from ppcway.org import models as _org  # noqa: F401
from ppcway.staff import models as _staff  # noqa: F401

TODAY = date(2026, 11, 11)
NOW = datetime(2026, 11, 11, 9, 0, tzinfo=UTC)


@pytest.fixture
def db() -> DbSession:
    engine = sa.create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with DbSession(engine) as session:
        yield session


def campaign(db: DbSession, *, gone: bool = False) -> None:
    db.add(
        MirrorCampaign(
            customer_id="1",
            resource_name="customers/1/campaigns/11",
            campaign_id="11",
            name="ai pdf tools",
            status="ENABLED",
            budget_micros=20 * MICRO,
            gone_at=NOW if gone else None,
        )
    )
    db.commit()


def an_ad(db: DbSession, *, approval: str, review: str = "", status: str = "ENABLED") -> None:
    db.add(
        MirrorAd(
            customer_id="1",
            resource_name="customers/1/adGroupAds/21~41",
            ad_id="41",
            ad_group_id="21",
            campaign_id="11",
            status=status,
            approval=approval,
            review=review,
            headlines=["Summarise Long Documents"],
        )
    )
    db.commit()


def refused(db: DbSession) -> list[str]:
    held = account_numbers(db, "1", days=30, today=TODAY)
    return [n.label for n in held.needs if n.kind == "ad_refused"]


# ---------- the words ----------


@pytest.mark.parametrize(
    ("approval", "review", "key", "label"),
    [
        ("UNKNOWN", "REVIEW_IN_PROGRESS", "review", "Under review"),
        ("UNKNOWN", "", "review", "Under review"),
        ("", "", "review", "Under review"),
        ("UNSPECIFIED", "", "review", "Under review"),
        ("UNKNOWN", "ELIGIBLE_MAY_SERVE", "review", "Showing, still in review"),
        ("APPROVED", "REVIEWED", "approved", "Approved"),
        ("APPROVED_LIMITED", "REVIEWED", "limited", "Approved, with limits"),
        ("AREA_OF_INTEREST_ONLY", "REVIEWED", "limited", "Approved, with limits"),
        ("DISAPPROVED", "REVIEWED", "refused", "Refused by Google"),
        ("DISAPPROVED", "UNDER_APPEAL", "appeal", "Appeal under review"),
    ],
)
def test_each_of_google_s_answers_has_its_own_words(
    approval: str, review: str, key: str, label: str
) -> None:
    said = standing(approval, review)
    assert (said.key, said.label) == (key, label)
    assert said.words


# ---------- Needs you ----------


def test_a_new_ad_google_has_not_reviewed_is_not_refused(db: DbSession) -> None:
    campaign(db)
    an_ad(db, approval="UNKNOWN", review="REVIEW_IN_PROGRESS")
    assert refused(db) == []


def test_an_unknown_approval_with_no_review_word_is_not_refused_either(db: DbSession) -> None:
    campaign(db)
    an_ad(db, approval="UNKNOWN")
    assert refused(db) == []


def test_an_ad_google_disapproved_still_needs_you(db: DbSession) -> None:
    campaign(db)
    an_ad(db, approval="DISAPPROVED", review="REVIEWED")
    assert refused(db) == ["Summarise Long Documents"]


def test_an_ad_under_appeal_is_waiting_on_google_not_on_you(db: DbSession) -> None:
    campaign(db)
    an_ad(db, approval="DISAPPROVED", review="UNDER_APPEAL")
    assert refused(db) == []


def test_a_refused_ad_that_is_paused_stops_nothing(db: DbSession) -> None:
    campaign(db)
    an_ad(db, approval="DISAPPROVED", review="REVIEWED", status="PAUSED")
    assert refused(db) == []


# ---------- the campaign panel ----------


def test_the_ads_tab_says_under_review_rather_than_unknown(db: DbSession) -> None:
    campaign(db)
    an_ad(db, approval="UNKNOWN", review="REVIEW_IN_PROGRESS")
    held = campaign_numbers(db, "1", "11", days=30, today=TODAY)
    (ad,) = held.ads
    assert ad["standing"]["key"] == "review"
    assert ad["standing"]["label"] == "Under review"


def test_a_deleted_campaign_says_when_it_was_found_deleted(db: DbSession) -> None:
    campaign(db, gone=True)
    held = campaign_numbers(db, "1", "11", days=30, today=TODAY)
    said = held.as_dict()
    assert said["gone"] is True
    assert said["gone_on"] == "2026-11-11"


# ---------- the sync ----------


def _ad_row(review: str) -> dict[str, object]:
    return {
        "adGroupAd": {
            "resourceName": "customers/1/adGroupAds/21~41",
            "ad": {
                "id": "41",
                "type": "RESPONSIVE_SEARCH_AD",
                "responsiveSearchAd": {"headlines": [{"text": "Summarise Long Documents"}]},
                "finalUrls": ["https://pdfezy.com/en/ai-tools"],
            },
            "status": "ENABLED",
            "policySummary": {"approvalStatus": "UNKNOWN", "reviewStatus": review},
        },
        "adGroup": {"id": "21"},
        "campaign": {"id": "11"},
    }


def _account(ad: dict[str, object]) -> httpx.Client:
    def handle(request: httpx.Request) -> httpx.Response:
        query = request.content.decode()
        rows = [ad] if "ad_group_ad" in query else []
        return httpx.Response(200, json={"results": rows})

    return httpx.Client(transport=httpx.MockTransport(handle), base_url="https://x")


def test_the_review_is_read_and_its_progress_is_not_a_change_somebody_made(
    db: DbSession,
) -> None:
    sync_structure(
        db,
        "1",
        access_token="a",
        developer_token="d",
        client=_account(_ad_row("REVIEW_IN_PROGRESS")),
        now=NOW,
    )
    held = db.scalar(sa.select(MirrorAd))
    assert held is not None and held.review == "REVIEW_IN_PROGRESS"

    report = sync_structure(
        db,
        "1",
        access_token="a",
        developer_token="d",
        client=_account(_ad_row("ELIGIBLE_MAY_SERVE")),
        now=NOW,
    )
    db.refresh(held)
    assert held.review == "ELIGIBLE_MAY_SERVE"
    assert report.changes == [], "a review moving on is Google's doing, not a change in the account"
