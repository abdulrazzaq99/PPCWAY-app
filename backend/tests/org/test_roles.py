"""Who may do what, decided here rather than by the interface.

The requirements are explicit: plan limits and roles are enforced in the
backend, not hidden in the screens. A member who knows the URL is still a
member.
"""

from __future__ import annotations

from collections.abc import Iterator

import pytest
import sqlalchemy as sa
from sqlalchemy.orm import Session as DbSession
from sqlalchemy.orm import sessionmaker

from ppcway.auth.models import UserAccount
from ppcway.db.base import Base
from ppcway.org.models import Role
from ppcway.org.places import (
    NotAllowed,
    accept,
    change_role,
    home_for,
    invite,
    may,
    people_in,
    remove,
    role_of,
)


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
    session.commit()
    return account


def test_a_new_person_owns_a_business_of_one(factory: sessionmaker[DbSession]) -> None:
    """Nobody fills in a form to get an organisation; using the app makes one."""
    with factory() as session:
        dana = person(session, "dana@alphaplumbing.ca", "Dana Reid")
        place = home_for(session, dana)
        assert place.name == "Dana Reid"
        assert role_of(session, dana, place) is Role.OWNER
        assert home_for(session, dana).id == place.id, "a second visit made a second business"


def test_what_each_role_may_do(factory: sessionmaker[DbSession]) -> None:
    with factory() as session:
        dana = person(session, "dana@alphaplumbing.ca")
        place = home_for(session, dana)
        sam = person(session, "sam@alphaplumbing.ca")
        token = invite(session, place, by=dana, email="sam@alphaplumbing.ca", role=Role.MEMBER)
        assert accept(session, token, sam) is not None

        # A member may look and suggest, and nothing else.
        assert may(session, sam, place, "view")
        assert may(session, sam, place, "propose")
        assert not may(session, sam, place, "approve")
        assert not may(session, sam, place, "connect")
        assert not may(session, sam, place, "disconnect")
        assert not may(session, sam, place, "invite")

        # The owner may do all of it.
        for what in ("view", "approve", "connect", "disconnect", "invite", "billing"):
            assert may(session, dana, place, what), what


def test_somebody_from_another_business_may_do_nothing(
    factory: sessionmaker[DbSession],
) -> None:
    with factory() as session:
        dana = person(session, "dana@alphaplumbing.ca")
        place = home_for(session, dana)
        stranger = person(session, "nobody@example.com")
        home_for(session, stranger)  # their own business, not this one
        for what in ("view", "propose", "approve", "connect"):
            assert not may(session, stranger, place, what), what


def test_an_invitation_is_to_a_person_not_a_link_to_pass_around(
    factory: sessionmaker[DbSession],
) -> None:
    with factory() as session:
        dana = person(session, "dana@alphaplumbing.ca")
        place = home_for(session, dana)
        token = invite(session, place, by=dana, email="sam@alphaplumbing.ca", role=Role.MEMBER)

        someone_else = person(session, "other@example.com")
        assert accept(session, token, someone_else) is None, "the wrong person got in"
        assert len(people_in(session, place)) == 1


def test_an_invitation_works_once(factory: sessionmaker[DbSession]) -> None:
    with factory() as session:
        dana = person(session, "dana@alphaplumbing.ca")
        place = home_for(session, dana)
        sam = person(session, "sam@alphaplumbing.ca")
        token = invite(session, place, by=dana, email="sam@alphaplumbing.ca", role=Role.EXPERT)
        assert accept(session, token, sam) is not None
        assert accept(session, token, sam) is None, "an invitation was reusable"


def test_nobody_may_invite_an_owner(factory: sessionmaker[DbSession]) -> None:
    """There is one owner, and it is whoever pays."""
    with factory() as session:
        dana = person(session, "dana@alphaplumbing.ca")
        place = home_for(session, dana)
        with pytest.raises(NotAllowed):
            invite(session, place, by=dana, email="sam@alphaplumbing.ca", role=Role.OWNER)


def test_the_last_owner_cannot_be_demoted_or_removed(
    factory: sessionmaker[DbSession],
) -> None:
    """Otherwise a business exists that nobody can pay for or disconnect."""
    with factory() as session:
        dana = person(session, "dana@alphaplumbing.ca")
        place = home_for(session, dana)
        with pytest.raises(NotAllowed):
            change_role(session, place, dana, Role.MEMBER)
        with pytest.raises(NotAllowed):
            remove(session, place, dana)
        assert role_of(session, dana, place) is Role.OWNER


def test_an_owner_can_go_once_there_is_another(factory: sessionmaker[DbSession]) -> None:
    with factory() as session:
        dana = person(session, "dana@alphaplumbing.ca")
        place = home_for(session, dana)
        sam = person(session, "sam@alphaplumbing.ca")
        token = invite(session, place, by=dana, email="sam@alphaplumbing.ca", role=Role.ADMIN)
        accept(session, token, sam)
        change_role(session, place, sam, Role.OWNER)

        remove(session, place, dana)
        assert role_of(session, dana, place) is None
        assert role_of(session, sam, place) is Role.OWNER


def test_an_expert_signs_off_but_does_not_own(factory: sessionmaker[DbSession]) -> None:
    with factory() as session:
        dana = person(session, "dana@alphaplumbing.ca")
        place = home_for(session, dana)
        maya = person(session, "maya@ppcway.com")
        token = invite(session, place, by=dana, email="maya@ppcway.com", role=Role.EXPERT)
        accept(session, token, maya)

        assert may(session, maya, place, "sign_off")
        assert may(session, maya, place, "log_hours")
        assert may(session, maya, place, "approve")
        assert not may(session, maya, place, "disconnect")
        assert not may(session, maya, place, "billing")


def test_a_client_viewer_only_looks(factory: sessionmaker[DbSession]) -> None:
    with factory() as session:
        agency = person(session, "agency@example.com")
        place = home_for(session, agency)
        client = person(session, "client@example.com")
        token = invite(
            session, place, by=agency, email="client@example.com", role=Role.CLIENT_VIEWER
        )
        accept(session, token, client)

        assert may(session, client, place, "view")
        for what in ("propose", "approve", "connect", "invite", "billing"):
            assert not may(session, client, place, what), what
