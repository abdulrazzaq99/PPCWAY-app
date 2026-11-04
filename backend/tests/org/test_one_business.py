"""One business per person, even when the first page load asks several times.

`home_for` reads and then writes, and a dashboard opening fires several
requests together. In production that produced two businesses for one account,
which is how the internal panel came to list the same name twice.

This runs the race for real against Postgres rather than asserting that a lock
is present: a test that checks for `FOR UPDATE` in the SQL would pass just as
happily if the lock were taken on the wrong row.
"""

from __future__ import annotations

import uuid
from concurrent.futures import ThreadPoolExecutor

import pytest
import sqlalchemy as sa
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from ppcway.auth.models import UserAccount
from ppcway.org.models import Membership, Organization
from ppcway.org.places import home_for


@pytest.fixture
def factory(pg_engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=pg_engine, expire_on_commit=False, future=True)


def test_four_requests_at_once_still_make_one_business(
    factory: sessionmaker[Session],
) -> None:
    """The exact shape of the bug: a page load firing several calls together."""
    email = f"race-{uuid.uuid4().hex[:8]}@example.com"
    with factory() as session:
        account = UserAccount(google_sub=f"google-{email}", email=email, name="Race Test")
        session.add(account)
        session.commit()
        account_id = account.id

    def open_the_app() -> uuid.UUID:
        with factory() as session:
            them = session.get(UserAccount, account_id)
            assert them is not None
            return home_for(session, them).id

    with ThreadPoolExecutor(max_workers=4) as pool:
        made = [one.result() for one in [pool.submit(open_the_app) for _ in range(4)]]

    assert len(set(made)) == 1, f"four callers made {len(set(made))} businesses"

    with factory() as session:
        how_many = session.scalar(
            sa.select(sa.func.count())
            .select_from(Organization)
            .join(Membership, Membership.organization_id == Organization.id)
            .where(Membership.account_id == account_id)
        )
        assert how_many == 1

        # Clean up after ourselves: this runs against a shared throwaway
        # database and leaving rows behind would make the next test's counts
        # wrong.
        session.execute(sa.delete(Membership).where(Membership.account_id == account_id))
        session.execute(sa.delete(Organization).where(Organization.id == made[0]))
        session.execute(sa.delete(UserAccount).where(UserAccount.id == account_id))
        session.commit()
