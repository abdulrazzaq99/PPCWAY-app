"""Who works for PPCWay, and the one confusion that must never be possible.

`org.Role.ADMIN` is the admin of one merchant's own account -- somebody that
merchant invited. Staff access is PPCWay's own people. Wiring the internal
panel to the first would hand every merchant's admin a window into every other
merchant's business, so the first test in this file is that the two cannot
touch, and several others approach the same property from different angles.
"""

from __future__ import annotations

import uuid
from collections.abc import Iterator
from itertools import pairwise

import pytest
import sqlalchemy as sa
from sqlalchemy.orm import Session as DbSession
from sqlalchemy.orm import sessionmaker

from ppcway.auth.models import UserAccount
from ppcway.db.base import Base
from ppcway.org.models import Role
from ppcway.org.places import accept, change_role, home_for, invite
from ppcway.staff.guard import (
    NotAllowed,
    NotStaff,
    grant,
    level_of,
    note_look,
    require,
    require_level,
    who_looked,
    withdraw,
)
from ppcway.staff.models import LADDER, MAY, Level, StaffGrant, at_least, may


@pytest.fixture
def factory() -> Iterator[sessionmaker[DbSession]]:
    engine = sa.create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=sa.pool.StaticPool
    )
    Base.metadata.create_all(engine)
    yield sessionmaker(bind=engine, expire_on_commit=False, future=True)
    Base.metadata.drop_all(engine)


def person(session: DbSession, email: str, name: str = "") -> UserAccount:
    account = UserAccount(google_sub=f"google-{email}", email=email, name=name)
    session.add(account)
    session.flush()
    return account


# --- the confusion that must not be possible ---------------------------------


def test_a_merchants_own_admin_is_not_ppcway_staff(factory: sessionmaker[DbSession]) -> None:
    """The whole reason staff is a separate table.

    This person is `Role.ADMIN` of their own business, which is a real and
    ordinary thing to be. It must give them nothing here.
    """
    with factory() as session:
        owner = person(session, "owner@alpha.ie")
        place = home_for(session, owner)
        theirs = person(session, "admin@alpha.ie")
        token = invite(session, place, by=owner, email="admin@alpha.ie", role=Role.ADMIN)
        accept(session, token, theirs)
        session.commit()

        assert change_role is not None  # the org-side machinery really exists
        assert level_of(session, theirs) is None
        with pytest.raises(NotStaff):
            require(session, theirs, "read_merchant")


def test_an_owner_of_their_own_business_is_not_staff_either(
    factory: sessionmaker[DbSession],
) -> None:
    with factory() as session:
        owner = person(session, "owner@beta.ie")
        home_for(session, owner)
        session.commit()
        assert level_of(session, owner) is None


def test_nobody_is_staff_by_default(factory: sessionmaker[DbSession]) -> None:
    with factory() as session:
        assert level_of(session, person(session, "nobody@example.com")) is None


def test_no_account_is_not_staff(factory: sessionmaker[DbSession]) -> None:
    """A missing caller is refused rather than crashing the endpoint."""
    with factory() as session:
        assert level_of(session, None) is None
        with pytest.raises(NotStaff):
            require(session, None, "read_merchant")


# --- granting, and taking away ----------------------------------------------


def test_a_grant_gives_exactly_its_level(factory: sessionmaker[DbSession]) -> None:
    with factory() as session:
        boss = person(session, "boss@ppcway.com")
        helper = person(session, "help@ppcway.com")
        grant(
            session,
            account_id=helper.id,
            level=Level.SUPPORT,
            by_account_id=boss.id,
            because="answers support tickets",
        )
        session.commit()
        assert level_of(session, helper) is Level.SUPPORT
        assert require(session, helper, "read_merchant") is Level.SUPPORT
        with pytest.raises(NotAllowed, match="cannot stop writes"):
            require(session, helper, "stop_writes")


def test_a_grant_without_a_reason_is_refused(factory: sessionmaker[DbSession]) -> None:
    """A grant nobody can review is the one kind this table cannot tolerate."""
    with factory() as session:
        helper = person(session, "help@ppcway.com")
        for nothing in ("", "   ", "\n"):
            with pytest.raises(ValueError, match="stated reason"):
                grant(
                    session,
                    account_id=helper.id,
                    level=Level.SUPPORT,
                    by_account_id=None,
                    because=nothing,
                )


def test_withdrawing_is_a_row_and_not_a_deletion(factory: sessionmaker[DbSession]) -> None:
    """ "Who could see this account in March" is a question somebody will have
    to answer."""
    with factory() as session:
        boss = person(session, "boss@ppcway.com")
        helper = person(session, "help@ppcway.com")
        grant(
            session,
            account_id=helper.id,
            level=Level.ENGINEER,
            by_account_id=boss.id,
            because="on call",
        )
        session.commit()
        assert level_of(session, helper) is Level.ENGINEER

        withdraw(session, account_id=helper.id, by_account_id=boss.id, because="left the company")
        session.commit()

        assert level_of(session, helper) is None
        rows = list(session.scalars(sa.select(StaffGrant).order_by(StaffGrant.at)))
        assert len(rows) == 2, "the grant is still there"
        assert [r.granted for r in rows] == [True, False]
        # The withdrawal records what was taken away, not merely that something was.
        assert rows[1].level == Level.ENGINEER.value
        assert rows[1].because == "left the company"


def test_withdrawing_from_somebody_who_had_nothing_is_safe(
    factory: sessionmaker[DbSession],
) -> None:
    """Asking twice should not be an error; the second ask has nothing to record."""
    with factory() as session:
        helper = person(session, "help@ppcway.com")
        assert withdraw(session, account_id=helper.id, by_account_id=None, because="x") is None


def test_a_re_grant_after_a_withdrawal_works(factory: sessionmaker[DbSession]) -> None:
    """People come back. The latest row decides, so this needs no special case."""
    with factory() as session:
        helper = person(session, "help@ppcway.com")
        grant(
            session,
            account_id=helper.id,
            level=Level.SUPPORT,
            by_account_id=None,
            because="first stint",
        )
        session.commit()
        withdraw(session, account_id=helper.id, by_account_id=None, because="left")
        session.commit()
        grant(
            session,
            account_id=helper.id,
            level=Level.PRINCIPAL,
            by_account_id=None,
            because="came back, and runs it now",
        )
        session.commit()
        assert level_of(session, helper) is Level.PRINCIPAL


def test_an_unknown_level_on_a_row_reads_as_no_access(
    factory: sessionmaker[DbSession],
) -> None:
    """Fail closed. A typo in a grant must not become more authority than was
    intended."""
    with factory() as session:
        helper = person(session, "help@ppcway.com")
        session.add(
            StaffGrant(
                account_id=helper.id,
                level="superadmin",
                granted=True,
                because="typed by hand",
            )
        )
        session.commit()
        assert level_of(session, helper) is None


# --- the ladder --------------------------------------------------------------


def test_the_three_levels_are_ordered(factory: sessionmaker[DbSession]) -> None:
    assert LADDER == (Level.SUPPORT, Level.ENGINEER, Level.PRINCIPAL)
    assert at_least(Level.PRINCIPAL, Level.SUPPORT)
    assert at_least(Level.SUPPORT, Level.SUPPORT)
    assert not at_least(Level.SUPPORT, Level.ENGINEER)


def test_reading_someones_figures_and_stopping_their_writes_need_different_authority() -> None:
    """Blueprint §8.3 makes the same argument about autonomy: these are not the
    same act and should not need the same authority."""
    assert may(Level.SUPPORT, "read_merchant")
    assert not may(Level.SUPPORT, "stop_writes")
    assert not may(Level.ENGINEER, "stop_writes")
    assert may(Level.PRINCIPAL, "stop_writes")


def test_only_a_principal_can_make_more_staff() -> None:
    """Otherwise the weakest level can promote itself to the strongest."""
    assert not may(Level.SUPPORT, "grant_staff")
    assert not may(Level.ENGINEER, "grant_staff")
    assert may(Level.PRINCIPAL, "grant_staff")


def test_support_cannot_reach_the_platform_or_the_errors() -> None:
    """Somebody answering a ticket has no business in the error stream."""
    assert not may(Level.SUPPORT, "read_platform")
    assert not may(Level.SUPPORT, "read_errors")
    assert may(Level.ENGINEER, "read_platform")


def test_every_capability_a_weaker_level_has_a_stronger_one_has_too() -> None:
    """A ladder with a hole in it is not a ladder, and the hole would show up
    as a principal unable to do something support can."""
    for lower, higher in pairwise(LADDER):
        assert MAY[lower] <= MAY[higher], f"{higher.value} is missing something {lower.value} has"


def test_require_level_refuses_a_weaker_level(factory: sessionmaker[DbSession]) -> None:
    with factory() as session:
        helper = person(session, "help@ppcway.com")
        grant(
            session,
            account_id=helper.id,
            level=Level.SUPPORT,
            by_account_id=None,
            because="tickets",
        )
        session.commit()
        assert require_level(session, helper, Level.SUPPORT) is Level.SUPPORT
        with pytest.raises(NotAllowed, match="needs principal access"):
            require_level(session, helper, Level.PRINCIPAL)


# --- the record of what was looked at ----------------------------------------


def test_opening_a_business_is_written_down(factory: sessionmaker[DbSession]) -> None:
    """The brief promises a merchant their data is theirs. The internal panel
    is where that is routinely bent, so it is where the bending is visible."""
    with factory() as session:
        owner = person(session, "owner@alpha.ie")
        place = home_for(session, owner)
        place.name = "Alpha Plumbing"
        helper = person(session, "help@ppcway.com")
        grant(
            session,
            account_id=helper.id,
            level=Level.SUPPORT,
            by_account_id=None,
            because="ticket 41",
        )
        session.commit()

        note_look(session, account=helper, level=Level.SUPPORT, place=place)
        session.commit()

        looks = who_looked(session, organization_id=place.id)
        assert len(looks) == 1
        assert looks[0].account_id == helper.id
        assert looks[0].organization_name == "Alpha Plumbing"
        assert looks[0].level == "support"
        assert looks[0].looked_at == "merchant"


def test_the_record_still_names_the_business_if_the_row_is_gone(
    factory: sessionmaker[DbSession],
) -> None:
    """The name is kept as text as well as a key: if an organisation is
    removed, the fact that staff looked at it does not stop being true."""
    with factory() as session:
        owner = person(session, "owner@gamma.ie")
        place = home_for(session, owner)
        place.name = "Gamma Roofing"
        helper = person(session, "help@ppcway.com")
        session.commit()
        row = note_look(session, account=helper, level=Level.ENGINEER, place=place)
        session.commit()
        assert row.organization_name == "Gamma Roofing"


def test_looks_come_back_newest_first(factory: sessionmaker[DbSession]) -> None:
    with factory() as session:
        owner = person(session, "owner@alpha.ie")
        place = home_for(session, owner)
        helper = person(session, "help@ppcway.com")
        session.commit()
        for what in ("merchant", "change-log", "support"):
            note_look(session, account=helper, level=Level.SUPPORT, place=place, looked_at=what)
            session.commit()
        looks = who_looked(session, organization_id=place.id)
        assert looks[0].looked_at == "support"
        assert len(looks) == 3


def test_a_look_with_no_business_is_still_recorded(factory: sessionmaker[DbSession]) -> None:
    """Somebody browsing the list rather than one account. Recorded without an
    organisation rather than not at all."""
    with factory() as session:
        helper = person(session, "help@ppcway.com")
        session.commit()
        row = note_look(session, account=helper, level=Level.SUPPORT, place=None)
        session.commit()
        assert row.organization_id is None
        assert row.organization_name == ""


def test_two_rows_written_in_one_transaction_are_still_ordered(
    factory: sessionmaker[DbSession],
) -> None:
    """The bug this file was written badly enough to find.

    `at` used to come from `server_default=func.now()`. In Postgres that is the
    *transaction's* start time -- the same value for every row written in one
    transaction -- and in SQLite `CURRENT_TIMESTAMP` has one-second
    granularity. So a grant and the withdrawal meant to revoke it could share
    a timestamp, and "the latest row" fell through to a tiebreak on a random
    UUID. The withdrawal lost a coin toss and the access stayed live.

    Written in Python to the microsecond now. This test writes both rows in one
    transaction with no commit between, which is exactly the case that broke.
    """
    with factory() as session:
        helper = person(session, "help@ppcway.com")
        grant(
            session,
            account_id=helper.id,
            level=Level.PRINCIPAL,
            by_account_id=None,
            because="granted and revoked in one breath",
        )
        withdraw(session, account_id=helper.id, by_account_id=None, because="immediately")
        session.commit()

        assert level_of(session, helper) is None, "the withdrawal must win"
        rows = list(session.scalars(sa.select(StaffGrant).order_by(StaffGrant.at)))
        assert rows[0].at < rows[1].at, "two rows in one transaction need distinct times"


def test_looks_are_scoped_to_the_business_asked_about(
    factory: sessionmaker[DbSession],
) -> None:
    """A merchant shown who looked at them must not be shown another merchant."""
    with factory() as session:
        one = person(session, "a@one.ie")
        two = person(session, "b@two.ie")
        first = home_for(session, one)
        second = home_for(session, two)
        helper = person(session, "help@ppcway.com")
        session.commit()
        note_look(session, account=helper, level=Level.SUPPORT, place=first)
        note_look(session, account=helper, level=Level.SUPPORT, place=second)
        session.commit()
        assert len(who_looked(session, organization_id=first.id)) == 1
        assert len(who_looked(session, organization_id=uuid.uuid4())) == 0
