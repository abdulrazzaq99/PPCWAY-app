"""One live permission per account.

A merchant who starts the trip to Google twice leaves two rows behind. The app
read the newest, which could be the one that never got as far as choosing an
account: it then reported "connected" and could read nothing, with no way on
the screen to put it right. That happened to a real account.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import sqlalchemy as sa
from sqlalchemy.orm import Session, sessionmaker

from ppcway.ads import models as ads_models
from ppcway.auth.models import UserAccount
from ppcway.db.base import Base


def a_db() -> sessionmaker[Session]:
    engine = sa.create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=sa.pool.StaticPool
    )
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, expire_on_commit=False, future=True)


def pick(session: Session, account_id: uuid.UUID) -> ads_models.AdsConnection | None:
    """The same order the API uses to choose which permission is theirs."""
    return session.scalar(
        sa.select(ads_models.AdsConnection)
        .where(
            ads_models.AdsConnection.account_id == account_id,
            ads_models.AdsConnection.revoked_at.is_(None),
        )
        .order_by(
            (ads_models.AdsConnection.customer_id.is_(None)).asc(),
            (ads_models.AdsConnection.customer_id == "").asc(),
            ads_models.AdsConnection.created_at.desc(),
        )
    )


def test_a_half_finished_connection_does_not_hide_the_working_one() -> None:
    factory = a_db()
    with factory() as session:
        person = UserAccount(google_sub="g", email="dana@alphaplumbing.ca", name="Dana")
        session.add(person)
        session.flush()
        session.add_all(
            [
                ads_models.AdsConnection(
                    account_id=person.id,
                    ciphertext="locked",
                    customer_id="2580586343",
                    created_at=datetime(2026, 10, 7, tzinfo=UTC),
                ),
                # Started again, went no further than Google's screen.
                ads_models.AdsConnection(
                    account_id=person.id,
                    ciphertext="locked",
                    customer_id="",
                    created_at=datetime(2026, 10, 12, tzinfo=UTC),
                ),
            ]
        )
        session.commit()
        chosen = pick(session, person.id)
        assert chosen is not None
        assert chosen.customer_id == "2580586343", "the newest row names no account"


def test_the_newest_wins_when_both_name_an_account() -> None:
    factory = a_db()
    with factory() as session:
        person = UserAccount(google_sub="g", email="dana@alphaplumbing.ca", name="Dana")
        session.add(person)
        session.flush()
        session.add_all(
            [
                ads_models.AdsConnection(
                    account_id=person.id,
                    ciphertext="old",
                    customer_id="1111111111",
                    created_at=datetime(2026, 10, 1, tzinfo=UTC),
                ),
                ads_models.AdsConnection(
                    account_id=person.id,
                    ciphertext="new",
                    customer_id="2222222222",
                    created_at=datetime(2026, 10, 12, tzinfo=UTC),
                ),
            ]
        )
        session.commit()
        chosen = pick(session, person.id)
        assert chosen is not None
        assert chosen.customer_id == "2222222222"
