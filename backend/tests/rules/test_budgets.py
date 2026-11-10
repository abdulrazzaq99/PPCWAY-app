"""R6 and R7: money moved between campaigns by what their leads cost.

On 10 November Otto had nothing to say on an account whose tracking counts
nearly every click, though one campaign's leads cost 0.40 and another's 2.69.
These hold the two budget rules to that comparison, to what they leave alone,
and to the budget change they send and the one that puts it back.

Dates come from the clock: a pinned day stops being inside the window as soon
as the calendar passes it.
"""

from __future__ import annotations

import uuid
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta

import pytest
import sqlalchemy as sa
from sqlalchemy.orm import Session as DbSession

from ppcway.ads.mirror import MICRO, CampaignDay, MirrorCampaign, SyncRun
from ppcway.ads.models import AdsConnection
from ppcway.auth.models import UserAccount
from ppcway.db.base import Base
from ppcway.gateway.changes import batch_for, done_words
from ppcway.gateway.port import Doing
from ppcway.opt.answer import _reverse
from ppcway.opt.models import GuardrailConfig, OptimizationAction
from ppcway.org.models import Organization
from ppcway.rules.budgets import dearest, held_back
from ppcway.rules.engine import run

NOW = datetime.now(UTC)
TODAY = NOW.date()
C = "2580586343"


@pytest.fixture
def db() -> Iterator[DbSession]:
    engine = sa.create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with DbSession(engine) as session:
        session.add(
            SyncRun(
                id=uuid.uuid4(),
                customer_id=C,
                kind="today",
                status="done",
                started_at=NOW - timedelta(hours=3),
                finished_at=NOW - timedelta(hours=2),
            )
        )
        session.commit()
        yield session


def campaign(
    db: DbSession,
    campaign_id: str,
    name: str,
    *,
    budget: float,
    cost_a_day: float,
    leads_a_day: float,
    lost_to_budget: float | None = None,
    days: int = 30,
    shared: bool = False,
    started_days_ago: int = 60,
) -> None:
    started = (TODAY - timedelta(days=started_days_ago)).isoformat()
    db.add(
        MirrorCampaign(
            id=uuid.uuid4(),
            customer_id=C,
            resource_name=f"customers/{C}/campaigns/{campaign_id}",
            campaign_id=campaign_id,
            name=name,
            status="ENABLED",
            budget_micros=round(budget * MICRO),
            budget_resource=f"customers/{C}/campaignBudgets/9{campaign_id}",
            budget_shared=shared,
            starts_at=f"{started} 00:00:00",
        )
    )
    for back in range(1, days + 1):
        db.add(
            CampaignDay(
                id=uuid.uuid4(),
                customer_id=C,
                campaign_id=campaign_id,
                day=TODAY - timedelta(days=back),
                clicks=20,
                cost_micros=round(cost_a_day * MICRO),
                forms=leads_a_day,
                not_leads=0.0,
                lost_to_budget=lost_to_budget,
                refreshed_at=NOW - timedelta(hours=2),
            )
        )
    db.commit()


def a_ceiling(db: DbSession, amount: float) -> None:
    person = UserAccount(google_sub=str(uuid.uuid4()), email="owner@pdfezy.com", name="Owner")
    place = Organization(name="PDFezy")
    db.add_all([person, place])
    db.flush()
    db.add(
        AdsConnection(account_id=person.id, organization_id=place.id, ciphertext="x", customer_id=C)
    )
    db.add(GuardrailConfig(organization_id=place.id, version=1, max_daily_budget=amount))
    db.commit()


def the_account(db: DbSession, *, search_lost: float | None = 0.6) -> None:
    """PDFezy as it stood: one dear campaign, one cheap one held back by budget."""
    campaign(db, "11", "pdfezy", budget=5.0, cost_a_day=5.0, leads_a_day=1.8)  # 2.78 a lead
    campaign(
        db,
        "12",
        "PDFezy | Search",
        budget=20.0,
        cost_a_day=4.0,
        leads_a_day=10.0,  # 0.40 a lead
        lost_to_budget=search_lost,
    )


# ---------- R7 ----------


def test_a_campaign_whose_leads_cost_far_more_is_offered_a_smaller_budget(
    db: DbSession,
) -> None:
    the_account(db)
    (found,) = dearest(db, C, currency="USD", today=TODAY)
    assert found.target_label == "pdfezy"
    assert found.before == {"daily_budget": 5.0} and found.after == {"daily_budget": 4.0}
    assert found.change_pct == -20.0
    assert found.payload["change"] == "set_budget"
    assert found.payload["amount_micros"] == 4_000_000
    assert found.payload["was_micros"] == 5_000_000
    assert "times the" in found.reason and "the rest of your account pays" in found.reason


def test_a_campaign_with_few_leads_is_not_judged(db: DbSession) -> None:
    the_account(db)
    campaign(db, "13", "Translate PDF", budget=5.0, cost_a_day=3.0, leads_a_day=0.2)
    labels = [one.target_label for one in dearest(db, C, currency="USD", today=TODAY)]
    assert "Translate PDF" not in labels, "six leads is luck, not a price"


def test_a_shared_budget_is_never_changed_for_one_campaign(db: DbSession) -> None:
    campaign(db, "11", "pdfezy", budget=5.0, cost_a_day=5.0, leads_a_day=1.8, shared=True)
    campaign(db, "12", "PDFezy | Search", budget=20.0, cost_a_day=4.0, leads_a_day=10.0)
    assert dearest(db, C, currency="USD", today=TODAY) == []


def test_a_campaign_still_learning_is_left_alone(db: DbSession) -> None:
    campaign(db, "11", "pdfezy", budget=5.0, cost_a_day=5.0, leads_a_day=3, days=4)
    campaign(db, "12", "PDFezy | Search", budget=20.0, cost_a_day=4.0, leads_a_day=10.0)
    assert dearest(db, C, currency="USD", today=TODAY) == []


# ---------- R6 ----------


def test_without_a_ceiling_a_cheap_campaign_waits_and_says_why(db: DbSession) -> None:
    the_account(db)
    notes: list[dict[str, str]] = []
    assert held_back(db, C, currency="USD", today=TODAY, notes=notes) == []
    (note,) = notes
    assert note["campaign"] == "12"
    assert note["words"].startswith("PDFezy | Search loses 60% of its searches to its budget")
    assert "no daily budget ceiling is set" in note["words"]


def test_with_a_ceiling_a_cheap_campaign_held_back_is_offered_more(db: DbSession) -> None:
    the_account(db)
    a_ceiling(db, 30.0)
    (found,) = held_back(db, C, currency="USD", today=TODAY)
    assert found.target_label == "PDFezy | Search"
    assert found.after == {"daily_budget": 24.0}
    assert found.change_pct == 20.0
    assert found.impact.money_a_month == 0.0, "more spend is not shown as a saving"


def test_never_past_the_ceiling(db: DbSession) -> None:
    the_account(db)
    a_ceiling(db, 22.0)
    (found,) = held_back(db, C, currency="USD", today=TODAY)
    assert found.after == {"daily_budget": 22.0}


def test_a_campaign_not_held_back_by_its_budget_is_not_offered_more(db: DbSession) -> None:
    the_account(db, search_lost=0.05)
    a_ceiling(db, 30.0)
    assert held_back(db, C, currency="USD", today=TODAY) == []


# ---------- in the pass ----------


def test_the_nightly_pass_offers_the_cut_and_carries_the_note(db: DbSession) -> None:
    the_account(db)
    said = run(db, C, currency="USD", target_cost_per_lead=0.8, today=TODAY, now=NOW)
    assert [(one.rule.id, one.target_label) for one in said.offered] == [("R7", "pdfezy")]
    assert any("no daily budget ceiling" in note["words"] for note in said.notes)


# ---------- the change, and putting it back ----------


def _action(payload: dict[str, object]) -> OptimizationAction:
    return OptimizationAction(
        id=uuid.uuid4(),
        organization_id=uuid.uuid4(),
        customer_id=C,
        kind="decrease_daily_budget",
        target_kind="campaign",
        target_id="11",
        target_label="pdfezy",
        payload=payload,
        before={"daily_budget": 5.0},
        after={"daily_budget": 4.0},
    )


def test_the_change_sent_is_the_budget_s_amount_and_nothing_else(db: DbSession) -> None:
    the_account(db)
    (found,) = dearest(db, C, currency="USD", today=TODAY)
    action = _action(dict(found.payload))
    (op,) = batch_for(action).operations
    assert op.resource_type == "campaign_budget" and op.doing is Doing.UPDATE
    assert op.resource_name == f"customers/{C}/campaignBudgets/911"
    assert op.fields == {"amountMicros": 4_000_000}
    assert op.update_mask == ("amountMicros",), "an update without its mask is ignored"
    assert done_words(action) == "The daily budget of pdfezy is now 4.00."


def test_putting_it_back_sends_the_amount_it_had(db: DbSession) -> None:
    the_account(db)
    (found,) = dearest(db, C, currency="USD", today=TODAY)
    back = _reverse(_action(dict(found.payload)))
    assert back["change"] == "set_budget"
    assert back["amount_micros"] == 5_000_000
    assert back["budget"] == f"customers/{C}/campaignBudgets/911"
