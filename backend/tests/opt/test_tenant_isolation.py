"""Fix F1: one organisation cannot read another, proven against Postgres.

The brief's test is precise about what counts: *a query run as one organisation
returns 0 rows from another, with the WHERE clause removed in the test*. So
none of the reads below filter by organisation. They say `select(Thing)` and
nothing else, which is the mistake the policy exists to survive, and then
assert that the mistake is harmless.
"""

from __future__ import annotations

import uuid
from collections.abc import Iterator

import pytest
import sqlalchemy as sa
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from ppcway.ads.mirror import MirrorCampaign
from ppcway.ads.models import AdsConnection
from ppcway.audit.models import AuditRequest, AuditRun
from ppcway.auth.models import UserAccount
from ppcway.db.session import org_scope
from ppcway.opt.models import OptimizationAction, Status
from ppcway.org.models import Membership, Organization, Role


class Business:
    """One business, with one of everything that should be invisible next door."""

    def __init__(self, name: str, customer_id: str) -> None:
        self.name = name
        self.customer_id = customer_id
        self.org_id: uuid.UUID
        self.action_id: uuid.UUID
        self.run_id: uuid.UUID


def _plant(session: Session, which: Business) -> None:
    """Written as the owner, which bypasses the policies, as the app does today."""
    place = Organization(name=which.name)
    session.add(place)
    session.flush()
    which.org_id = place.id

    person = UserAccount(email=f"{which.customer_id}@example.test", name=which.name)
    session.add(person)
    session.flush()
    session.add(Membership(organization_id=place.id, account_id=person.id, role=Role.OWNER.value))
    session.add(
        AdsConnection(
            account_id=person.id,
            organization_id=place.id,
            ciphertext="not-a-real-token",
            customer_id=which.customer_id,
            customer_name=which.name,
        )
    )
    session.add(
        MirrorCampaign(
            customer_id=which.customer_id,
            resource_name=f"customers/{which.customer_id}/campaigns/1",
            campaign_id="1",
            name=f"{which.name} search",
            budget_micros=40_000_000,
        )
    )
    action = OptimizationAction(
        organization_id=place.id,
        customer_id=which.customer_id,
        kind="decrease_daily_budget",
        status=Status.PENDING.value,
        before={"daily_budget": 40.0},
        after={"daily_budget": 32.0},
    )
    session.add(action)
    session.flush()
    which.action_id = action.id

    asked = AuditRequest(
        organization_id=place.id,
        user_id=person.id,
        name=which.name,
        business_name=which.name,
        email=f"{which.customer_id}@example.test",
        phone="+353 1 234 5678",
        consent_text="agreed",
        site=f"https://{which.customer_id}.example.test",
    )
    session.add(asked)
    session.flush()
    run = AuditRun(request_id=asked.id, site=asked.site)
    session.add(run)
    session.flush()
    which.run_id = run.id
    session.commit()


@pytest.fixture
def two(pg_engine: Engine) -> Iterator[tuple[sessionmaker[Session], Business, Business]]:
    """Two businesses, each new, and nothing cleaned up afterwards.

    There is no teardown on purpose, and the reason is itself a result: the
    first version of this fixture ended with `DELETE FROM optimization_action`
    and could not, because F2's trigger forbids DELETE on that table with no
    exception and no privileged path. So each test plants its own businesses
    under ids nobody else uses, and the throwaway database is dropped whole.

    Rows left behind by earlier tests do not weaken the assertions below. A
    read scoped to this test's Alpha is filtered to this test's Alpha; every
    other business in the database, left over or not, is exactly what the
    policy is being asked to hide.
    """
    factory = sessionmaker(bind=pg_engine, expire_on_commit=False, future=True)
    mine = uuid.uuid4().int % 10**6
    alpha = Business("Alpha Plumbing", f"111{mine:06d}")
    beta = Business("Beta Dental", f"222{mine:06d}")
    with factory() as session:
        _plant(session, alpha)
        _plant(session, beta)
    yield factory, alpha, beta


def test_the_unfiltered_query_sees_only_its_own_business(
    two: tuple[sessionmaker[Session], Business, Business],
) -> None:
    """Every read here is missing its WHERE clause on purpose."""
    factory, alpha, _beta = two
    with factory() as session, org_scope(session, alpha.org_id):
        places = session.scalars(sa.select(Organization)).all()
        assert [p.name for p in places] == ["Alpha Plumbing"]

        connections = session.scalars(sa.select(AdsConnection)).all()
        assert [c.customer_id for c in connections] == [alpha.customer_id]

        # The mirror holds the money. It carries no organisation column at all,
        # so this is the subquery policy through ads_connection doing the work.
        campaigns = session.scalars(sa.select(MirrorCampaign)).all()
        assert [c.name for c in campaigns] == ["Alpha Plumbing search"]

        actions = session.scalars(sa.select(OptimizationAction)).all()
        assert [a.id for a in actions] == [alpha.action_id]

        runs = session.scalars(sa.select(AuditRun)).all()
        assert [r.id for r in runs] == [alpha.run_id]


def test_the_other_business_is_not_merely_filtered_but_unreachable(
    two: tuple[sessionmaker[Session], Business, Business],
) -> None:
    """Asking for Beta's row by its primary key, from inside Alpha, finds nothing."""
    factory, alpha, beta = two
    with factory() as session, org_scope(session, alpha.org_id):
        assert session.get(OptimizationAction, beta.action_id) is None
        assert session.get(Organization, beta.org_id) is None
        found = session.scalars(
            sa.select(MirrorCampaign).where(MirrorCampaign.customer_id == beta.customer_id)
        ).all()
        assert found == []


def test_a_write_cannot_be_addressed_to_another_business(
    two: tuple[sessionmaker[Session], Business, Business],
) -> None:
    """WITH CHECK, not only USING: scoped to Alpha, a row for Beta is refused."""
    factory, alpha, beta = two
    with factory() as session, org_scope(session, alpha.org_id):
        session.add(
            OptimizationAction(
                organization_id=beta.org_id,
                customer_id=beta.customer_id,
                kind="increase_daily_budget",
                status=Status.PENDING.value,
            )
        )
        with pytest.raises(sa.exc.ProgrammingError, match="row-level security"):
            session.flush()


def test_no_organisation_set_means_no_rows_rather_than_every_row(
    two: tuple[sessionmaker[Session], Business, Business],
) -> None:
    """Fail closed. The role is stepped into without the setting ever being written."""
    factory, _alpha, _beta = two
    with factory() as session:
        session.execute(sa.text("SET LOCAL ROLE ppcway_app"))
        assert session.scalars(sa.select(Organization)).all() == []
        assert session.scalars(sa.select(MirrorCampaign)).all() == []
        assert session.scalars(sa.select(OptimizationAction)).all() == []


def test_the_application_itself_is_not_blanked_by_the_policies(
    two: tuple[sessionmaker[Session], Business, Business],
) -> None:
    """A guard against re-adding FORCE ROW LEVEL SECURITY.

    The services connect as the owner and scope almost nothing yet. FORCE binds
    the owner too, and would turn every unfiltered read into an empty result
    rather than an error -- a silent, total outage. Measured, not assumed: see
    the note in `20261030_tenant_isolation.py`. If somebody adds FORCE for
    tidiness, this test is what tells them what it costs.
    """
    factory, alpha, beta = two
    with factory() as session:
        seen = {p.id for p in session.scalars(sa.select(Organization)).all()}
        assert {alpha.org_id, beta.org_id} <= seen
        mirrored = {c.customer_id for c in session.scalars(sa.select(MirrorCampaign)).all()}
        assert {alpha.customer_id, beta.customer_id} <= mirrored
