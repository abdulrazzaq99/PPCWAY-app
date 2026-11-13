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


def test_someone_with_a_business_is_never_kept_waiting_by_their_own_other_request(
    factory: sessionmaker[Session],
) -> None:
    """The lock is for making a business, not for finding one.

    A report PDF waits up to a minute for a browser that opens the report page
    signed in as the same person. While the first request still held the row
    lock taken here, that page's own request queued behind it, the browser gave
    up after sixty seconds and the PDF failed; a "Share this report" pressed
    meanwhile sat on "Making a link…" for the whole minute (13 Nov 2026).
    """
    email = f"wait-{uuid.uuid4().hex[:8]}@example.com"
    with factory() as session:
        account = UserAccount(google_sub=f"google-{email}", email=email, name="Wait Test")
        session.add(account)
        session.commit()
        account_id = account.id
        made = home_for(session, account).id

    with factory() as first, factory() as second:
        them = first.get(UserAccount, account_id)
        assert them is not None
        # A long request: it has found the business and its transaction is
        # still open while it waits on something else.
        assert home_for(first, them).id == made

        second.execute(sa.text("SET lock_timeout = '2s'"))
        again = second.get(UserAccount, account_id)
        assert again is not None
        assert home_for(second, again).id == made, "the second request had to wait for the first"
        first.rollback()
        second.rollback()

    with factory() as session:
        session.execute(sa.delete(Membership).where(Membership.account_id == account_id))
        session.execute(sa.delete(Organization).where(Organization.id == made))
        session.execute(sa.delete(UserAccount).where(UserAccount.id == account_id))
        session.commit()
