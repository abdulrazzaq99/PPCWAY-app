"""The switches the panel can throw, and who is allowed to throw them.

Two properties carry this file. Reading the platform and changing it need
different authority -- stopping writes is the one control that changes what
happens to a merchant's money. And nothing here can *start* writes the
deployment has not enabled, because a panel button that appeared to turn on
live writing to Google Ads would be the most dangerous control in the product.
"""

from __future__ import annotations

from collections.abc import Iterator
from datetime import date

import pytest
import sqlalchemy as sa
from sqlalchemy.orm import Session as DbSession
from sqlalchemy.orm import sessionmaker

from ppcway.auth.models import UserAccount
from ppcway.db.base import Base
from ppcway.gateway import quota, switch
from ppcway.staff.controls import (
    EVERYTHING,
    LEAST_REASON,
    Room,
    flags,
    levels_for_screen,
    may_stop_writes,
    quota_today,
    release_writes,
    standing,
    stop_writes,
)
from ppcway.staff.guard import NotAllowed, NotStaff, grant
from ppcway.staff.models import Level

CUSTOMER = "2580586343"
TODAY = date(2026, 11, 3)


@pytest.fixture
def factory() -> Iterator[sessionmaker[DbSession]]:
    engine = sa.create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=sa.pool.StaticPool
    )
    Base.metadata.create_all(engine)
    yield sessionmaker(bind=engine, expire_on_commit=False, future=True)
    Base.metadata.drop_all(engine)


def person(session: DbSession, email: str) -> UserAccount:
    account = UserAccount(google_sub=f"google-{email}", email=email)
    session.add(account)
    session.flush()
    return account


def staff(session: DbSession, email: str, level: Level) -> UserAccount:
    account = person(session, email)
    grant(
        session,
        account_id=account.id,
        level=level,
        by_account_id=None,
        because=f"test fixture at {level.value}",
    )
    session.commit()
    return account


def says(session: DbSession, account: UserAccount, **over: bool) -> object:
    settings: dict[str, bool] = {"writes_enabled": False, "auto_apply_enabled": False}
    settings.update(over)
    return standing(session, account, **settings)  # type: ignore[arg-type]


# --- who may read, and who may throw ----------------------------------------


def test_a_stranger_cannot_read_the_platform(factory: sessionmaker[DbSession]) -> None:
    with factory() as session:
        nobody = person(session, "nobody@example.com")
        session.commit()
        with pytest.raises(NotStaff):
            says(session, nobody)


def test_support_cannot_read_the_platform_either(factory: sessionmaker[DbSession]) -> None:
    """Somebody answering a ticket has no business in the platform's health."""
    with factory() as session:
        helper = staff(session, "help@ppcway.com", Level.SUPPORT)
        with pytest.raises(NotAllowed):
            says(session, helper)


def test_an_engineer_can_read_but_not_stop(factory: sessionmaker[DbSession]) -> None:
    """The line that matters: reading the platform and changing what happens to
    a merchant's money are not the same authority."""
    with factory() as session:
        engineer = staff(session, "eng@ppcway.com", Level.ENGINEER)
        assert says(session, engineer) is not None
        with pytest.raises(NotAllowed, match="cannot stop writes"):
            stop_writes(session, engineer, because="trying it on anyway")


def test_only_a_principal_can_stop_writes(factory: sessionmaker[DbSession]) -> None:
    with factory() as session:
        boss = staff(session, "boss@ppcway.com", Level.PRINCIPAL)
        stopped = stop_writes(session, boss, because="the rules are misbehaving")
        assert stopped.ours is True
        assert stopped.customer_id == EVERYTHING


def test_a_stop_needs_a_real_reason(factory: sessionmaker[DbSession]) -> None:
    """Whoever picks up the incident reads this line."""
    with factory() as session:
        boss = staff(session, "boss@ppcway.com", Level.PRINCIPAL)
        for nothing in ("", "x", "bad", "   "):
            with pytest.raises(ValueError, match="say why"):
                stop_writes(session, boss, because=nothing)
        assert LEAST_REASON >= 12


def test_the_authority_is_checked_here_not_only_in_the_endpoint(
    factory: sessionmaker[DbSession],
) -> None:
    """An endpoint is one caller. The second caller -- a CLI, a task, a test
    somebody writes in a hurry -- would otherwise arrive unchecked."""
    with factory() as session:
        nobody = person(session, "nobody@example.com")
        session.commit()
        with pytest.raises(NotStaff):
            stop_writes(session, nobody, because="a perfectly good reason here")
        with pytest.raises(NotStaff):
            release_writes(session, nobody)
        with pytest.raises(NotStaff):
            quota_today(session, nobody, customer_id=CUSTOMER)


# --- a stop PPCWay set is not a stop a merchant can lift --------------------


def test_a_staff_stop_is_marked_as_ours(factory: sessionmaker[DbSession]) -> None:
    """The one case this exists for is "we found a problem and are stopping
    while we look". That must not be a case the merchant can overrule."""
    with factory() as session:
        boss = staff(session, "boss@ppcway.com", Level.PRINCIPAL)
        stop_writes(session, boss, customer_id=CUSTOMER, because="investigating a bad rule")
        row = session.scalars(
            sa.select(switch.KillSwitch).where(switch.KillSwitch.released_at.is_(None))
        ).one()
        assert row.ours is True

        # And the merchant's own path refuses to lift it.
        with pytest.raises(switch.WritesStopped):
            switch.release(session, customer_id=CUSTOMER, staff=False)


def test_a_principal_can_lift_their_own_stop(factory: sessionmaker[DbSession]) -> None:
    with factory() as session:
        boss = staff(session, "boss@ppcway.com", Level.PRINCIPAL)
        stop_writes(session, boss, customer_id=CUSTOMER, because="investigating a bad rule")
        lifted = release_writes(session, boss, customer_id=CUSTOMER)
        assert lifted is not None
        assert says(session, boss, writes_enabled=True).stops == ()  # type: ignore[attr-defined]


def test_lifting_nothing_is_not_an_error(factory: sessionmaker[DbSession]) -> None:
    with factory() as session:
        boss = staff(session, "boss@ppcway.com", Level.PRINCIPAL)
        assert release_writes(session, boss, customer_id=CUSTOMER) is None


# --- the two reasons writes can be off, which need different fixes ----------


def test_a_setting_that_is_off_is_reported_as_a_setting_not_a_switch(
    factory: sessionmaker[DbSession],
) -> None:
    """ "Writes are off" has two causes and the fix differs: one is a deploy,
    the other is a button. A screen that conflates them sends somebody to press
    a button that cannot help."""
    with factory() as session:
        boss = staff(session, "boss@ppcway.com", Level.PRINCIPAL)
        said = says(session, boss, writes_enabled=False)
        assert "takes a deploy" in said.words  # type: ignore[attr-defined]
        assert not said.anything_can_be_written  # type: ignore[attr-defined]


def test_a_platform_stop_is_reported_as_a_stop(factory: sessionmaker[DbSession]) -> None:
    with factory() as session:
        boss = staff(session, "boss@ppcway.com", Level.PRINCIPAL)
        stop_writes(session, boss, because="a rule proposed nonsense overnight")
        said = says(session, boss, writes_enabled=True)
        assert "the whole platform" in said.words  # type: ignore[attr-defined]
        assert "nonsense overnight" in said.words  # type: ignore[attr-defined]
        assert not said.anything_can_be_written  # type: ignore[attr-defined]


def test_everything_on_and_nothing_stopped_says_so_plainly(
    factory: sessionmaker[DbSession],
) -> None:
    with factory() as session:
        boss = staff(session, "boss@ppcway.com", Level.PRINCIPAL)
        said = says(session, boss, writes_enabled=True)
        assert said.words == "Writes are on and nothing is stopped."  # type: ignore[attr-defined]
        assert said.anything_can_be_written  # type: ignore[attr-defined]


def test_accounts_stopped_one_by_one_are_counted_not_confused_with_the_platform(
    factory: sessionmaker[DbSession],
) -> None:
    with factory() as session:
        boss = staff(session, "boss@ppcway.com", Level.PRINCIPAL)
        stop_writes(session, boss, customer_id=CUSTOMER, because="one account looks wrong")
        stop_writes(session, boss, customer_id="999", because="this one too, separately")
        said = says(session, boss, writes_enabled=True)
        assert said.platform_stopped is None  # type: ignore[attr-defined]
        assert "2 accounts stopped individually" in said.words  # type: ignore[attr-defined]
        assert said.anything_can_be_written  # type: ignore[attr-defined]


# --- the flags are honest about not being switches --------------------------


def test_no_flag_pretends_to_be_changeable_from_the_panel(
    factory: sessionmaker[DbSession],
) -> None:
    """A screen that shows a toggle for something only a deploy can change
    teaches people the panel is lying to them."""
    with factory() as session:
        boss = staff(session, "boss@ppcway.com", Level.PRINCIPAL)
        every = flags(
            session,
            boss,
            writes_enabled=False,
            auto_apply_enabled=False,
            open_to="invited",
            model_provider="openrouter",
            armor_template="projects/p/locations/us-central1/templates/t",
        )
        assert every, "there is something to show"
        assert all(not one.changeable for one in every)
        assert all(one.why_not for one in every), "each says why it cannot be changed"


def test_the_two_dangerous_settings_are_reported_and_not_offered(
    factory: sessionmaker[DbSession],
) -> None:
    """A button that could turn on live writing to a merchant's account would
    be the most dangerous control in the product, so it does not exist."""
    with factory() as session:
        boss = staff(session, "boss@ppcway.com", Level.PRINCIPAL)
        every = {
            one.name: one
            for one in flags(
                session,
                boss,
                writes_enabled=False,
                auto_apply_enabled=False,
                open_to="invited",
                model_provider="openrouter",
                armor_template="t",
            )
        }
        assert not every["Writing to Google Ads"].on
        assert not every["Writing to Google Ads"].changeable
        assert not every["Applying without asking"].on
        assert not every["Applying without asking"].changeable


def test_chat_screening_shows_as_off_when_no_template_is_set(
    factory: sessionmaker[DbSession],
) -> None:
    with factory() as session:
        boss = staff(session, "boss@ppcway.com", Level.PRINCIPAL)
        every = {
            one.name: one
            for one in flags(
                session,
                boss,
                writes_enabled=False,
                auto_apply_enabled=False,
                open_to="invited",
                model_provider="openrouter",
                armor_template="",
            )
        }
        assert not every["Chat is screened"].on
        assert "refuses" in every["Chat is screened"].what_it_does


# --- quota -------------------------------------------------------------------


def test_quota_reports_what_is_left(factory: sessionmaker[DbSession]) -> None:
    with factory() as session:
        engineer = staff(session, "eng@ppcway.com", Level.ENGINEER)
        quota.spend(session, CUSTOMER, 400, today=TODAY)
        session.commit()
        room = quota_today(session, engineer, customer_id=CUSTOMER, today=TODAY)
        assert room.used == 400
        assert room.left == room.allowance - 400
        assert "400 of" in room.words
        assert not room.tight


def test_quota_calls_itself_tight_before_it_runs_out(factory: sessionmaker[DbSession]) -> None:
    """Shouting at the point it is exhausted is shouting too late."""
    room = Room(customer_id=CUSTOMER, used=12_000, allowance=15_000, day=TODAY)
    assert room.share_used == pytest.approx(0.8)
    assert room.tight


def test_an_account_with_no_allowance_does_not_divide_by_zero() -> None:
    assert Room(customer_id=CUSTOMER, used=0, allowance=0, day=TODAY).share_used == 0.0


# --- what the screen should show ---------------------------------------------


def test_the_screen_can_ask_whether_to_show_the_stop_button(
    factory: sessionmaker[DbSession],
) -> None:
    """A disabled button is a better screen than a button that fails, and a far
    better one than a button that is missing with no explanation."""
    with factory() as session:
        boss = staff(session, "boss@ppcway.com", Level.PRINCIPAL)
        engineer = staff(session, "eng@ppcway.com", Level.ENGINEER)
        nobody = person(session, "nobody@example.com")
        session.commit()
        assert may_stop_writes(session, boss)
        assert not may_stop_writes(session, engineer)
        assert not may_stop_writes(session, nobody)
        assert not may_stop_writes(session, None)


def test_the_three_levels_are_described_for_whoever_grants_them() -> None:
    """Somebody choosing a level needs to know what they are handing over."""
    described = dict(levels_for_screen())
    assert set(described) == {"support", "engineer", "principal"}
    assert "Changes nothing" in described["support"]
    assert "kill switch" in described["principal"]
