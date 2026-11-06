"""Which campaign a change acts in, read from the account's own structure.

A change names the ad groups or the ad it touches, as Google does, never the
campaign. These pin the lookup that lets one campaign's panel show its own
suggestions.
"""

from __future__ import annotations

import uuid
from collections.abc import Iterator
from datetime import UTC, datetime

import pytest
import sqlalchemy as sa
from sqlalchemy.orm import Session

from ppcway.ads.mirror import MirrorAd, MirrorAdGroup, SearchTermDay, term_key
from ppcway.db.base import Base
from ppcway.rules.offered import campaigns_of

C = "2580586343"


@pytest.fixture
def session() -> Iterator[Session]:
    engine = sa.create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with Session(engine) as one:
        one.add_all(
            [
                MirrorAdGroup(
                    id=uuid.uuid4(),
                    customer_id=C,
                    resource_name=f"customers/{C}/adGroups/21",
                    ad_group_id="21",
                    campaign_id="11",
                ),
                MirrorAdGroup(
                    id=uuid.uuid4(),
                    customer_id=C,
                    resource_name=f"customers/{C}/adGroups/22",
                    ad_group_id="22",
                    campaign_id="12",
                ),
                # An ad whose ad group was never mirrored on its own.
                MirrorAd(
                    id=uuid.uuid4(),
                    customer_id=C,
                    resource_name=f"customers/{C}/adGroupAds/23~5",
                    ad_id="5",
                    ad_group_id="23",
                    campaign_id="13",
                ),
                # A search answered in an ad group known only from the report.
                SearchTermDay(
                    id=uuid.uuid4(),
                    customer_id=C,
                    campaign_id="14",
                    ad_group_id="24",
                    day=datetime.now(UTC).date(),
                    term="pdf jobs",
                    term_hash=term_key("pdf jobs"),
                ),
            ]
        )
        one.commit()
        yield one


def test_each_payload_gets_the_campaigns_it_acts_in(session: Session) -> None:
    said = campaigns_of(
        session,
        [
            # A search excluded in two ad groups, in two campaigns.
            {
                "change": "exclude_search",
                "ad_groups": [f"customers/{C}/adGroups/22", f"customers/{C}/adGroups/21"],
            },
            {"change": "set_ad_status", "ad": f"customers/{C}/adGroupAds/23~5"},
            {"change": "exclude_search", "ad_groups": [f"customers/{C}/adGroups/24"]},
            # An undo names the exclusions it removes.
            {"change": "remove_exclusions", "criteria": [f"customers/{C}/adGroupCriteria/21~901"]},
            {"change": "set_budget", "campaign": f"customers/{C}/campaigns/15"},
        ],
    )
    assert said == [("11", "12"), ("13",), ("14",), ("11",), ("15",)]


def test_what_cannot_be_placed_is_in_no_campaign(session: Session) -> None:
    said = campaigns_of(session, [None, {}, {"ad_groups": [f"customers/{C}/adGroups/99"]}])
    assert said == [(), (), ()]


def test_nothing_asked_reads_nothing(session: Session) -> None:
    assert campaigns_of(session, []) == []
