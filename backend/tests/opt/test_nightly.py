"""The pass that makes everything else happen.

Until this existed, phases 1 and 2 were a working engine nobody started: each
piece had tests and none of them ran in production. These check the order, and
check that one broken account does not cost the others their night.
"""

from __future__ import annotations

import uuid
from collections.abc import Iterator
from datetime import UTC, date, datetime, timedelta
from typing import Any

import pytest
import sqlalchemy as sa
from sqlalchemy.orm import Session, sessionmaker

from ppcway.ads.mirror import MICRO, CampaignDay, MirrorCampaign, SearchTermDay, SyncRun, term_key
from ppcway.ads.models import AdsConnection
from ppcway.auth.models import UserAccount
from ppcway.config import Settings
from ppcway.db.base import Base
from ppcway.model.jobs import SONNET
from ppcway.model.log import PromptLog
from ppcway.opt.models import OptimizationAction, Status
from ppcway.opt.nightly import tonight
from ppcway.org.models import Organization

TODAY = date(2026, 11, 3)
NOW = datetime(2026, 11, 3, 2, 0, tzinfo=UTC)


@pytest.fixture
def db() -> Iterator[sessionmaker[Session]]:
    engine = sa.create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=sa.pool.StaticPool
    )
    Base.metadata.create_all(engine)
    yield sessionmaker(bind=engine, expire_on_commit=False, future=True)
    Base.metadata.drop_all(engine)


def settings() -> Settings:
    return Settings(environment="test")


def an_account(
    db: sessionmaker[Session],
    *,
    customer_id: str = "2580586343",
    wasteful: str | None = "boiler repair jobs",
    read_ok: bool = True,
) -> uuid.UUID:
    with db() as session:
        place = Organization(name=f"Business {customer_id}", plan="starter")
        person = UserAccount(email=f"{customer_id}@example.test", name="Dana")
        session.add_all([place, person])
        session.flush()
        session.add(
            AdsConnection(
                account_id=person.id,
                organization_id=place.id,
                ciphertext="locked",
                customer_id=customer_id,
                customer_name=f"Business {customer_id}",
                currency="CAD",
                account_status="ENABLED",
                status_read_at=NOW - timedelta(hours=2),
            )
        )
        session.add(
            SyncRun(
                id=uuid.uuid4(),
                customer_id=customer_id,
                kind="today",
                status="done" if read_ok else "failed",
                started_at=NOW - timedelta(hours=3),
                finished_at=NOW - timedelta(hours=2) if read_ok else None,
                trouble="" if read_ok else "quota exhausted",
            )
        )
        session.add(
            MirrorCampaign(
                id=uuid.uuid4(),
                customer_id=customer_id,
                resource_name=f"customers/{customer_id}/campaigns/11",
                campaign_id="11",
                name="Emergency",
                status="ENABLED",
                channel="SEARCH",
                budget_micros=round(20.0 * MICRO),
                seen_at=NOW,
            )
        )
        for back in range(1, 32):
            session.add(
                CampaignDay(
                    id=uuid.uuid4(),
                    customer_id=customer_id,
                    campaign_id="11",
                    day=TODAY - timedelta(days=back),
                    impressions=400,
                    clicks=20,
                    cost_micros=round(18.0 * MICRO),
                    conversions=1.0,
                    calls=1.0,
                    refreshed_at=NOW,
                )
            )
        if wasteful:
            session.add(
                SearchTermDay(
                    id=uuid.uuid4(),
                    customer_id=customer_id,
                    campaign_id="11",
                    ad_group_id="21",
                    day=TODAY - timedelta(days=3),
                    term=wasteful,
                    term_hash=term_key(wasteful),
                    status="NONE",
                    clicks=140,
                    cost_micros=round(90.0 * MICRO),
                    conversions=0.0,
                    refreshed_at=NOW,
                )
            )
        session.commit()
        return place.id


class Saying:
    """A model service that always rewrites cleanly."""

    def __init__(self, text: str) -> None:
        self.text = text
        self.asked = 0

    def ask(self, job: Any, **kwargs: Any) -> Any:
        from ppcway.model.service import Answer

        self.asked += 1
        return Answer(text=self.text, model=SONNET, prompt_version="otto-test")


def test_a_pass_writes_what_the_rules_found(db: sessionmaker[Session]) -> None:
    an_account(db)
    night = tonight(db, settings(), now=NOW)
    assert night.accounts == 1
    assert night.proposed == 1
    with db() as session:
        row = session.scalars(sa.select(OptimizationAction)).one()
    assert row.status == Status.AWAITING_APPROVAL.value
    assert row.job_run == "nightly-2026-11-03"
    assert row.rule_id == "R1"


def test_nothing_is_applied(db: sessionmaker[Session]) -> None:
    """The write gate, the kill switches and a consent record all have to
    agree, and none of that is decided here."""
    an_account(db)
    tonight(db, settings(), now=NOW)
    with db() as session:
        rows = session.scalars(sa.select(OptimizationAction)).all()
    assert all(row.status != Status.APPLIED.value for row in rows)
    assert all(row.applied_at is None for row in rows)


def test_an_account_that_could_not_be_read_is_named_not_counted(
    db: sessionmaker[Session],
) -> None:
    an_account(db, read_ok=False)
    night = tonight(db, settings(), now=NOW)
    assert night.proposed == 0
    assert night.trouble and "2580586343" in night.trouble[0]
    assert "last read of this account failed" in night.trouble[0]


def test_one_broken_account_does_not_cost_the_others_their_night(
    db: sessionmaker[Session],
) -> None:
    """A hundred accounts in a loop, and one revoked permission."""
    an_account(db, customer_id="1110000001", read_ok=False)
    an_account(db, customer_id="2220000002")
    an_account(db, customer_id="3330000003")
    night = tonight(db, settings(), now=NOW)
    assert night.accounts == 3
    assert night.proposed == 2, "the two good ones still got their cards"
    assert len(night.trouble) == 1


def test_offers_are_expired_before_anything_new_is_written(
    db: sessionmaker[Session],
) -> None:
    """The ten-a-week cap counts what is waiting, so a stale offer left in
    place would use up a merchant's allowance with a card nobody will answer."""
    place = an_account(db)
    with db() as session:
        for n in range(10):
            session.add(
                OptimizationAction(
                    id=uuid.uuid4(),
                    organization_id=place,
                    customer_id="2580586343",
                    kind="add_negative_keyword",
                    target_id=f"old-{n}",
                    status=Status.AWAITING_APPROVAL.value,
                    created_at=NOW - timedelta(days=10),
                    expires_at=NOW - timedelta(days=3),
                )
            )
        session.commit()

    night = tonight(db, settings(), now=NOW)
    assert night.expired == 10
    assert night.proposed == 1, "and the allowance was free again"


def test_without_a_model_the_computed_words_ship(db: sessionmaker[Session]) -> None:
    """Which is what production looks like until Vertex is enabled."""
    an_account(db)
    night = tonight(db, settings(), models=None, now=NOW)
    assert night.worded == 0
    with db() as session:
        row = session.scalars(sa.select(OptimizationAction)).one()
    assert "boiler repair jobs" in row.reason
    assert row.reason


def test_with_a_model_the_words_are_rewritten_before_the_row_is_written(
    db: sessionmaker[Session],
) -> None:
    """`reason` is write-once at the database, so polishing after writing would
    be refused by our own append-only trigger."""
    an_account(db)
    models = Saying("140 clicks on that search cost you 90.00 CAD and nobody rang.")
    night = tonight(db, settings(), models=models, now=NOW)
    assert night.worded == 1
    with db() as session:
        row = session.scalars(sa.select(OptimizationAction)).one()
    assert row.reason == "140 clicks on that search cost you 90.00 CAD and nobody rang."


def test_an_invented_figure_never_reaches_the_card(db: sessionmaker[Session]) -> None:
    an_account(db)
    models = Saying("That search cost 90.00 CAD and lost you 14 leads.")
    night = tonight(db, settings(), models=models, now=NOW)
    assert night.worded == 0
    with db() as session:
        row = session.scalars(sa.select(OptimizationAction)).one()
    assert "14 leads" not in row.reason


def test_what_is_past_keeping_is_forgotten(db: sessionmaker[Session]) -> None:
    an_account(db)
    with db() as session:
        session.add(
            PromptLog(
                id=uuid.uuid4(),
                job="card_reason",
                model=SONNET,
                prompt_version="otto-1",
                created_at=NOW - timedelta(days=45),
            )
        )
        session.commit()
    night = tonight(db, settings(), now=NOW)
    assert night.forgot_prompts == 1


def test_an_account_with_nothing_wrong_proposes_nothing(
    db: sessionmaker[Session],
) -> None:
    an_account(db, wasteful=None)
    night = tonight(db, settings(), now=NOW)
    assert night.accounts == 1 and night.proposed == 0 and night.trouble == []


def test_two_connections_to_one_account_are_read_once(
    db: sessionmaker[Session],
) -> None:
    """A merchant who connected twice should not get two sets of cards."""
    place = an_account(db)
    with db() as session:
        person = session.scalars(sa.select(UserAccount)).first()
        assert person is not None
        session.add(
            AdsConnection(
                account_id=person.id,
                organization_id=place,
                ciphertext="locked",
                customer_id="2580586343",
                currency="CAD",
                account_status="ENABLED",
                status_read_at=NOW - timedelta(hours=2),
            )
        )
        session.commit()
    night = tonight(db, settings(), now=NOW)
    assert night.accounts == 1
    assert night.proposed == 1


def test_a_pass_reports_what_it_did(db: sessionmaker[Session]) -> None:
    an_account(db)
    said = tonight(db, settings(), now=NOW).as_dict()
    assert set(said) == {
        "ran_at",
        "accounts",
        "expired",
        "proposed",
        "refused",
        "refused_because",
        "worded",
        "forgot_prompts",
        "forgot_transcripts",
        "trouble",
    }


def test_why_things_were_refused_is_in_the_report(db: sessionmaker[Session]) -> None:
    """A bare count hides the one thing an operator needs. "Every proposal on
    every account refused by account_serviceable" is a deployment problem;
    "three refused by delta_limits" is the system working."""
    with db() as session:
        place = Organization(name="Unread", plan="starter")
        person = UserAccount(email="unread@example.test", name="X")
        session.add_all([place, person])
        session.flush()
        # No account_status: the second guardrail cannot tell what state this
        # account is in, which is what production looks like until a structure
        # sync has read it.
        session.add(
            AdsConnection(
                account_id=person.id,
                organization_id=place.id,
                ciphertext="locked",
                customer_id="9990000009",
                currency="CAD",
            )
        )
        session.add(
            SyncRun(
                id=uuid.uuid4(),
                customer_id="9990000009",
                kind="today",
                status="done",
                started_at=NOW - timedelta(hours=3),
                finished_at=NOW - timedelta(hours=2),
            )
        )
        session.add(
            MirrorCampaign(
                id=uuid.uuid4(),
                customer_id="9990000009",
                resource_name="customers/9990000009/campaigns/11",
                campaign_id="11",
                name="Emergency",
                status="ENABLED",
                channel="SEARCH",
                budget_micros=round(20.0 * MICRO),
                seen_at=NOW,
            )
        )
        for back in range(1, 32):
            session.add(
                CampaignDay(
                    id=uuid.uuid4(),
                    customer_id="9990000009",
                    campaign_id="11",
                    day=TODAY - timedelta(days=back),
                    impressions=400,
                    clicks=20,
                    cost_micros=round(18.0 * MICRO),
                    conversions=1.0,
                    calls=1.0,
                    refreshed_at=NOW,
                )
            )
        session.add(
            SearchTermDay(
                id=uuid.uuid4(),
                customer_id="9990000009",
                campaign_id="11",
                ad_group_id="21",
                day=TODAY - timedelta(days=3),
                term="boiler repair jobs",
                term_hash=term_key("boiler repair jobs"),
                status="NONE",
                clicks=140,
                cost_micros=round(90.0 * MICRO),
                conversions=0.0,
                refreshed_at=NOW,
            )
        )
        session.commit()

    night = tonight(db, settings(), now=NOW)
    assert night.refused == 1
    assert night.refused_because == {"account_serviceable": 1}
