"""What somebody agreed to, and the five things that must agree before Otto acts.

The record's fields are the client's specification, and each exists because
"they agreed" answers none of the questions somebody asks later: agreed to
what, under which words, up to what limits, when, and from where.
"""

from __future__ import annotations

import uuid
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta

import pytest
import sqlalchemy as sa
from sqlalchemy.orm import Session, sessionmaker

from ppcway.auth.models import UserAccount
from ppcway.db.base import Base
from ppcway.opt.consent import (
    THE_WORDS,
    WORDING,
    AutoApplyConsent,
    NotTheirs,
    current,
    eligible_kinds,
    give,
    may_apply_unasked,
    withdraw,
)
from ppcway.opt.guardrails import Limits
from ppcway.opt.models import Autonomy
from ppcway.org.models import Organization, Role

NOW = datetime(2026, 11, 2, 12, 0, tzinfo=UTC)


@pytest.fixture
def db() -> Iterator[sessionmaker[Session]]:
    engine = sa.create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=sa.pool.StaticPool
    )
    Base.metadata.create_all(engine)
    yield sessionmaker(bind=engine, expire_on_commit=False, future=True)
    Base.metadata.drop_all(engine)


@pytest.fixture
def world(db: sessionmaker[Session]) -> tuple[sessionmaker[Session], uuid.UUID, uuid.UUID]:
    with db() as session:
        place = Organization(name="Alpha Plumbing")
        person = UserAccount(email="dana@alphaplumbing.ca", name="Dana")
        session.add_all([place, person])
        session.commit()
        return db, place.id, person.id


def test_only_the_two_types_the_client_named_are_eligible() -> None:
    """Read from the rules rather than restated: two lists would disagree."""
    assert eligible_kinds() == ("add_negative_keyword", "pause_ad")


def test_the_record_says_what_was_agreed_and_under_which_words(
    world: tuple[sessionmaker[Session], uuid.UUID, uuid.UUID],
) -> None:
    db, place, person = world
    with db() as session:
        record = give(
            session,
            organization_id=place,
            account_id=person,
            role=Role.OWNER,
            ip="203.0.113.7",
            limits=Limits(version=4, max_change_pct=20.0),
            now=NOW,
        )
    assert record.wording == WORDING
    assert record.words == THE_WORDS, "the text, not only its version number"
    assert record.ip == "203.0.113.7"
    assert record.given_at == NOW
    assert record.account_id == person
    assert record.change_types == {"kinds": ["add_negative_keyword", "pause_ad"]}
    assert record.limits is not None
    assert record.limits["version"] == 4
    assert record.limits["max_change_pct"] == 20.0


def test_the_words_name_both_types_and_rule_out_the_rest() -> None:
    """A merchant reading this should not be surprised by what happens next."""
    assert "excluding searches" in THE_WORDS
    assert "pausing ads that Google has refused" in THE_WORDS
    assert "will not change your budgets, your bids or your ad text" in THE_WORDS
    assert "thirty days" in THE_WORDS
    assert "turn this off at any moment" in THE_WORDS


def test_only_the_owner_may_agree(
    world: tuple[sessionmaker[Session], uuid.UUID, uuid.UUID],
) -> None:
    """An admin cannot sign away the owner's money."""
    db, place, person = world
    for role in (Role.ADMIN, Role.MEMBER, Role.EXPERT, None):
        with db() as session, pytest.raises(NotTheirs, match="Only the owner"):
            give(session, organization_id=place, account_id=person, role=role, now=NOW)


def test_an_admin_may_turn_it_off_even_though_they_could_not_turn_it_on(
    world: tuple[sessionmaker[Session], uuid.UUID, uuid.UUID],
) -> None:
    """Making it harder to stop than to start would be the wrong way round."""
    db, place, person = world
    with db() as session:
        give(session, organization_id=place, account_id=person, role=Role.OWNER, now=NOW)
        gone = withdraw(session, organization_id=place, account_id=person, role=Role.ADMIN, now=NOW)
    assert gone is not None and gone.withdrawn_at == NOW
    with db() as session:
        assert current(session, place) is None


def test_a_member_may_not_turn_it_off(
    world: tuple[sessionmaker[Session], uuid.UUID, uuid.UUID],
) -> None:
    db, place, person = world
    with db() as session:
        give(session, organization_id=place, account_id=person, role=Role.OWNER, now=NOW)
        with pytest.raises(NotTheirs):
            withdraw(session, organization_id=place, account_id=person, role=Role.MEMBER, now=NOW)


def test_withdrawing_keeps_the_record(
    world: tuple[sessionmaker[Session], uuid.UUID, uuid.UUID],
) -> None:
    """That somebody once agreed, when, and to what is the record."""
    db, place, person = world
    with db() as session:
        give(session, organization_id=place, account_id=person, role=Role.OWNER, now=NOW)
        withdraw(session, organization_id=place, account_id=person, role=Role.OWNER, now=NOW)
        rows = session.scalars(sa.select(AutoApplyConsent)).all()
    assert len(rows) == 1
    assert rows[0].withdrawn_at is not None
    assert rows[0].words == THE_WORDS, "and what they agreed to is still there"


def test_agreeing_again_leaves_exactly_one_live_permission(
    world: tuple[sessionmaker[Session], uuid.UUID, uuid.UUID],
) -> None:
    """So the live one is always the most recent words somebody actually read."""
    db, place, person = world
    with db() as session:
        give(session, organization_id=place, account_id=person, role=Role.OWNER, now=NOW)
        second = give(
            session,
            organization_id=place,
            account_id=person,
            role=Role.OWNER,
            now=NOW + timedelta(days=1),
        )
        live = session.scalars(
            sa.select(AutoApplyConsent).where(AutoApplyConsent.withdrawn_at.is_(None))
        ).all()
        everything = session.scalars(sa.select(AutoApplyConsent)).all()
    assert len(live) == 1 and live[0].id == second.id
    assert len(everything) == 2, "and the first is kept"


def test_a_permission_covers_only_the_types_it_named(
    world: tuple[sessionmaker[Session], uuid.UUID, uuid.UUID],
) -> None:
    """Adding a rule to the eligible list must not widen last March's consent."""
    db, place, person = world
    with db() as session:
        record = give(session, organization_id=place, account_id=person, role=Role.OWNER, now=NOW)
        # A permission given before a third type existed.
        record.change_types = {"kinds": ["add_negative_keyword"]}
        session.commit()

        allowed = may_apply_unasked(
            session,
            organization_id=place,
            kind="add_negative_keyword",
            autonomy=Autonomy.FULL_AUTO.value,
            flag_on=True,
        )
        not_allowed = may_apply_unasked(
            session,
            organization_id=place,
            kind="pause_ad",
            autonomy=Autonomy.FULL_AUTO.value,
            flag_on=True,
        )
    assert allowed.may
    assert not not_allowed.may
    assert not_allowed.stopped_by == "consent_scope"


@pytest.mark.parametrize(
    ("kind", "autonomy", "flag", "consent", "stopped_by"),
    [
        ("add_negative_keyword", Autonomy.FULL_AUTO.value, False, True, "flag"),
        ("increase_daily_budget", Autonomy.FULL_AUTO.value, True, True, "kind"),
        ("add_negative_keyword", Autonomy.APPROVE_FIRST.value, True, True, "autonomy"),
        ("add_negative_keyword", Autonomy.ALERTS_ONLY.value, True, True, "autonomy"),
        ("add_negative_keyword", Autonomy.FULL_AUTO.value, True, False, "consent"),
    ],
)
def test_each_of_the_five_can_say_no_on_its_own(
    world: tuple[sessionmaker[Session], uuid.UUID, uuid.UUID],
    kind: str,
    autonomy: str,
    flag: bool,
    consent: bool,
    stopped_by: str,
) -> None:
    db, place, person = world
    with db() as session:
        if consent:
            give(session, organization_id=place, account_id=person, role=Role.OWNER, now=NOW)
        said = may_apply_unasked(
            session,
            organization_id=place,
            kind=kind,
            autonomy=autonomy,
            flag_on=flag,
        )
    assert not said.may
    assert said.stopped_by == stopped_by
    assert said.because, "and says so in words a merchant could be shown"


def test_all_five_agreeing_is_the_only_way_through(
    world: tuple[sessionmaker[Session], uuid.UUID, uuid.UUID],
) -> None:
    db, place, person = world
    with db() as session:
        give(session, organization_id=place, account_id=person, role=Role.OWNER, now=NOW)
        said = may_apply_unasked(
            session,
            organization_id=place,
            kind="add_negative_keyword",
            autonomy=Autonomy.FULL_AUTO.value,
            flag_on=True,
        )
    assert said.may
    assert said.stopped_by == ""


def test_turning_it_off_takes_effect_at_once(
    world: tuple[sessionmaker[Session], uuid.UUID, uuid.UUID],
) -> None:
    db, place, person = world
    with db() as session:
        give(session, organization_id=place, account_id=person, role=Role.OWNER, now=NOW)
        withdraw(session, organization_id=place, account_id=person, role=Role.OWNER, now=NOW)
        said = may_apply_unasked(
            session,
            organization_id=place,
            kind="add_negative_keyword",
            autonomy=Autonomy.FULL_AUTO.value,
            flag_on=True,
        )
    assert not said.may and said.stopped_by == "consent"


def test_the_flag_ships_off(
    world: tuple[sessionmaker[Session], uuid.UUID, uuid.UUID],
) -> None:
    """The brief: `otto_auto_apply` stays off in production until we confirm."""
    from ppcway.config import Settings

    settings = Settings()
    assert settings.otto_auto_apply is False
    assert settings.ads_writes_enabled is False
