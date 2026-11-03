"""The one thing Otto may write, and every way it cannot be aimed.

The brief: *create_proposal only; target resolved server-side from a
tool-returned id; never a model-supplied budget, bid or target.* Each clause
has a test, and the handle tests are the ones that matter -- a model that could
name its own target would be a model an injected search term could point at
somebody else's account.
"""

from __future__ import annotations

import uuid
from collections.abc import Iterator
from datetime import UTC, date, datetime, timedelta
from typing import Any

import pytest
import sqlalchemy as sa
from sqlalchemy.orm import Session as DbSession

from ppcway.ads.mirror import MICRO, CampaignDay, MirrorCampaign, SearchTermDay, term_key
from ppcway.ads.models import AdsConnection
from ppcway.auth.models import UserAccount
from ppcway.chat import propose
from ppcway.chat.propose import SCHEMA, Handles, create_proposal
from ppcway.chat.tools import TOOLS, Asked
from ppcway.db.base import Base
from ppcway.opt.models import OptimizationAction, ProposedBy, Status
from ppcway.org.models import Organization

CUSTOMER = "2580586343"
TODAY = date(2026, 11, 3)
NOW = datetime(2026, 11, 3, 9, 0, tzinfo=UTC)


@pytest.fixture
def db() -> Iterator[DbSession]:
    engine = sa.create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with DbSession(engine) as session:
        yield session


@pytest.fixture
def world(db: DbSession) -> tuple[DbSession, uuid.UUID, AdsConnection]:
    place = Organization(name="Alpha Plumbing", plan="starter")
    person = UserAccount(email="dana@alphaplumbing.ca", name="Dana")
    db.add_all([place, person])
    db.flush()
    connection = AdsConnection(
        account_id=person.id,
        organization_id=place.id,
        ciphertext="locked",
        customer_id=CUSTOMER,
        currency="CAD",
        account_status="ENABLED",
        status_read_at=NOW - timedelta(hours=2),
    )
    db.add(connection)
    db.add(
        MirrorCampaign(
            id=uuid.uuid4(),
            customer_id=CUSTOMER,
            resource_name=f"customers/{CUSTOMER}/campaigns/11",
            campaign_id="11",
            name="Emergency plumbing",
            status="ENABLED",
            channel="SEARCH",
            budget_micros=round(20.0 * MICRO),
            seen_at=NOW,
        )
    )
    for back in range(1, 40):
        db.add(
            CampaignDay(
                id=uuid.uuid4(),
                customer_id=CUSTOMER,
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
    db.commit()
    return db, place.id, connection


def a_wasteful_term(db: DbSession, term: str = "boiler repair jobs", *, clicks: int = 140) -> None:
    db.add(
        SearchTermDay(
            id=uuid.uuid4(),
            customer_id=CUSTOMER,
            campaign_id="11",
            ad_group_id="21",
            day=TODAY - timedelta(days=4),
            term=term,
            term_hash=term_key(term),
            status="NONE",
            clicks=clicks,
            cost_micros=round(90.0 * MICRO),
            conversions=0.0,
            refreshed_at=NOW,
        )
    )
    db.commit()


def _asked(
    world: tuple[DbSession, uuid.UUID, AdsConnection],
    handles: Handles | None = None,
    **args: Any,
) -> Asked:
    db, place, connection = world
    return Asked(
        session=db,
        organization_id=place,
        customer_id=CUSTOMER,
        currency="CAD",
        args=dict(args),
        today=TODAY,
        handles=handles,
        connection=connection,
    )


def _a_handle(world: tuple[DbSession, uuid.UUID, AdsConnection]) -> tuple[Handles, str]:
    """Look terms up the way a turn does, and take the handle that comes back."""
    handles = Handles()
    found = TOOLS["get_search_terms"](_asked(world, handles, days=30))
    return handles, found.data["terms"][0]["handle"]


def test_the_schema_has_nothing_to_aim() -> None:
    """No target, no amount, no account. The brief's rule, as a schema."""
    fields = set(SCHEMA["input_schema"]["properties"])
    assert fields == {"handle", "change"}
    assert SCHEMA["input_schema"]["additionalProperties"] is False
    assert SCHEMA["input_schema"]["properties"]["change"]["enum"] == ["add_negative_keyword"]


def test_the_description_tells_the_model_it_is_not_making_a_change() -> None:
    assert "does not make one" in SCHEMA["description"]
    assert "cannot name a target or" in SCHEMA["description"]
    assert "Do not use it to be helpful unprompted" in SCHEMA["description"]


def test_a_term_a_read_tool_showed_can_be_proposed_on(
    world: tuple[DbSession, uuid.UUID, AdsConnection],
) -> None:
    db, place, _connection = world
    a_wasteful_term(db)
    handles, handle = _a_handle(world)

    said = create_proposal(_asked(world, handles, handle=handle, change="add_negative_keyword"))
    assert said["proposed"] is True
    assert said["in_their_inbox"] is True
    assert said["about"] == "boiler repair jobs"
    assert said["expected_saving_a_month"] > 0
    assert said["undo"]

    row = db.scalars(sa.select(OptimizationAction)).one()
    assert row.status == Status.AWAITING_APPROVAL.value
    assert row.proposed_by == ProposedBy.CHAT.value
    assert row.organization_id == place
    assert row.job_run == "chat"


def test_what_is_written_waits_for_a_person(
    world: tuple[DbSession, uuid.UUID, AdsConnection],
) -> None:
    """The model cannot approve. Proposing is not approving."""
    db, _place, _connection = world
    a_wasteful_term(db)
    handles, handle = _a_handle(world)
    create_proposal(_asked(world, handles, handle=handle, change="add_negative_keyword"))
    row = db.scalars(sa.select(OptimizationAction)).one()
    assert row.status == Status.AWAITING_APPROVAL.value
    assert row.approved_by is None and row.approved_at is None


def test_a_handle_nobody_issued_resolves_to_nothing(
    world: tuple[DbSession, uuid.UUID, AdsConnection],
) -> None:
    """An invented handle is the obvious attack, and it writes nothing."""
    db, _place, _connection = world
    a_wasteful_term(db)
    said = create_proposal(
        _asked(world, Handles(), handle="h_madeitup", change="add_negative_keyword")
    )
    assert said["proposed"] is False
    assert "not something I showed you" in said["why"]
    assert db.scalars(sa.select(OptimizationAction)).all() == []


def test_a_handle_from_another_turn_is_gone(
    world: tuple[DbSession, uuid.UUID, AdsConnection],
) -> None:
    """Deliberate: a proposal should rest on figures just shown, not on
    something remembered about an account that has moved since."""
    db, _place, _connection = world
    a_wasteful_term(db)
    _handles, handle = _a_handle(world)
    # A new turn. New dictionary, and the old handle means nothing in it.
    said = create_proposal(_asked(world, Handles(), handle=handle, change="add_negative_keyword"))
    assert said["proposed"] is False
    assert db.scalars(sa.select(OptimizationAction)).all() == []


def test_no_handle_at_all_writes_nothing(
    world: tuple[DbSession, uuid.UUID, AdsConnection],
) -> None:
    db, _place, _connection = world
    a_wasteful_term(db)
    said = create_proposal(_asked(world, Handles(), change="add_negative_keyword"))
    assert said["proposed"] is False
    assert db.scalars(sa.select(OptimizationAction)).all() == []


def test_a_search_term_handle_cannot_be_used_to_pause_an_ad(
    world: tuple[DbSession, uuid.UUID, AdsConnection],
) -> None:
    """The server decides what a given target is even eligible for."""
    db, _place, _connection = world
    a_wasteful_term(db)
    handles, handle = _a_handle(world)
    said = create_proposal(_asked(world, handles, handle=handle, change="pause_ad"))
    assert said["proposed"] is False
    assert "cannot be used to propose" in said["why"]
    assert db.scalars(sa.select(OptimizationAction)).all() == []


def test_a_term_already_excluded_is_offered_no_handle(
    world: tuple[DbSession, uuid.UUID, AdsConnection],
) -> None:
    """Offering one would invite a proposal the rule would then refuse."""
    db, _place, _connection = world
    db.add(
        SearchTermDay(
            id=uuid.uuid4(),
            customer_id=CUSTOMER,
            campaign_id="11",
            ad_group_id="21",
            day=TODAY - timedelta(days=4),
            term="plumber jobs",
            term_hash=term_key("plumber jobs"),
            status="EXCLUDED",
            clicks=140,
            cost_micros=round(90.0 * MICRO),
            conversions=0.0,
            refreshed_at=NOW,
        )
    )
    db.commit()
    handles = Handles()
    found = TOOLS["get_search_terms"](_asked(world, handles, days=30))
    assert "handle" not in found.data["terms"][0]


def test_a_term_not_wasteful_enough_is_refused_rather_than_proposed(
    world: tuple[DbSession, uuid.UUID, AdsConnection],
) -> None:
    """The rule's own thresholds, not the model's judgement."""
    db, _place, _connection = world
    a_wasteful_term(db, "plumbing advice", clicks=4)
    handles, handle = _a_handle(world)
    said = create_proposal(_asked(world, handles, handle=handle, change="add_negative_keyword"))
    assert said["proposed"] is False
    assert "not cost enough" in said["why"]
    assert db.scalars(sa.select(OptimizationAction)).all() == []


def test_the_figures_are_recomputed_not_taken_from_the_handle(
    world: tuple[DbSession, uuid.UUID, AdsConnection],
) -> None:
    """A figure that travelled through a prompt is one that could have been
    rewritten on the way, so the handle carries no numbers at all."""
    db, _place, _connection = world
    a_wasteful_term(db)
    handles, handle = _a_handle(world)
    held = handles.resolve(handle)
    assert held is not None
    assert set(held.what) == {"term_hash", "ad_group_id"}
    assert not any(isinstance(v, (int, float)) for v in held.what.values())


def test_a_proposal_from_chat_cites_the_same_figures_as_the_nightly_pass(
    world: tuple[DbSession, uuid.UUID, AdsConnection],
) -> None:
    """The rule that would have found it anyway is the one that builds it, so
    the two cannot drift into two sets of thresholds."""
    db, _place, _connection = world
    a_wasteful_term(db)
    handles, handle = _a_handle(world)
    create_proposal(_asked(world, handles, handle=handle, change="add_negative_keyword"))
    row = db.scalars(sa.select(OptimizationAction)).one()
    assert row.rule_id == "R1" and row.rule_version == 1
    assert row.evidence is not None
    assert row.evidence["figures"][0]["id"].startswith("search_term_spend:")
    assert row.undo_plan


def test_a_broken_proposal_says_so_rather_than_claiming_success(
    world: tuple[DbSession, uuid.UUID, AdsConnection],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db, _place, _connection = world
    a_wasteful_term(db)
    handles, handle = _a_handle(world)

    def explode(*_a: object, **_k: object) -> None:
        raise RuntimeError("the mirror is on fire")

    monkeypatch.setattr(propose, "wasteful_terms", explode)
    said = create_proposal(_asked(world, handles, handle=handle, change="add_negative_keyword"))
    assert said["proposed"] is False
    assert "rather than claiming it worked" in said["why"]


def test_handles_are_not_guessable() -> None:
    handles = Handles()
    made = {handles.offer("search_term", term_hash=str(n)) for n in range(200)}
    assert len(made) == 200, "no collisions"
    assert all(h.startswith("h_") and len(h) > 10 for h in made)
