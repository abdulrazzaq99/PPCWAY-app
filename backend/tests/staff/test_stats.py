"""What the platform looks like from the inside, and the figures' honesty.

Two properties carry most of this file. Every figure names the window it was
measured over, because "412 changes" means nothing and "412 changes in the last
7 days" is a fact. And zero is not the same as unknown: no proposals last night
because the rules found nothing is a healthy platform, and no proposals because
the job did not run is an incident.
"""

from __future__ import annotations

import uuid
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta

import pytest
import sqlalchemy as sa
from sqlalchemy.orm import Session as DbSession
from sqlalchemy.orm import sessionmaker

from ppcway.ads.mirror import SyncRun
from ppcway.ads.models import AdsConnection
from ppcway.auth.models import UserAccount
from ppcway.db.base import Base
from ppcway.model.log import PromptLog
from ppcway.opt.models import OptimizationAction, Status
from ppcway.org.places import home_for
from ppcway.staff.stats import (
    STUCK_AFTER,
    WINDOWS,
    Count,
    Money,
    merchants,
    platform,
)

NOW = datetime(2026, 11, 3, 12, 0, tzinfo=UTC)
CUSTOMER = "2580586343"


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


def a_business(session: DbSession, email: str, name: str, *, connected: bool = True) -> uuid.UUID:
    owner = person(session, email)
    place = home_for(session, owner)
    place.name = name
    if connected:
        session.add(
            AdsConnection(
                id=uuid.uuid4(),
                account_id=owner.id,
                organization_id=place.id,
                ciphertext="locked",
                customer_id=CUSTOMER,
                customer_name=name,
                currency="CAD",
                account_status="ENABLED",
            )
        )
    session.flush()
    return place.id


def an_action(session: DbSession, place: uuid.UUID, status: Status, *, ago: int = 1) -> None:
    session.add(
        OptimizationAction(
            id=uuid.uuid4(),
            organization_id=place,
            customer_id=CUSTOMER,
            kind="add_negative_keyword",
            target_id="t",
            status=status.value,
            created_at=NOW - timedelta(days=ago),
        )
    )
    session.flush()


# --- a figure says what it measured -----------------------------------------


def test_a_count_reads_as_a_sentence() -> None:
    """The owner's rule is a sentence before a number, and an internal screen
    has the same obligation: the reader is about to decide from it."""
    one = Count(label="Changes proposed", value=412, window="7d")
    assert one.words == "412 changes proposed in the last 7d."


def test_a_count_with_no_window_does_not_pretend_to_have_one() -> None:
    assert Count(label="Businesses", value=9).words == "9 businesses."


def test_an_unknown_figure_is_not_reported_as_zero() -> None:
    """ "No proposals last night" and "we do not know whether the job ran" lead
    to opposite actions."""
    unknown = Count(label="Changes proposed", known=False)
    assert unknown.value == 0
    assert "cannot tell" in unknown.words
    assert unknown.change is None


def test_a_count_says_how_much_it_moved() -> None:
    assert Count(label="x", value=10, before=4).change == 6
    assert Count(label="x", value=10).change is None


def test_money_always_carries_its_currency() -> None:
    """A bare number is a trap: 90 is very different in CAD and in EUR."""
    assert "90.00 CAD" in Money(label="spent", amount=90.0, currency="CAD").words


def test_thousands_are_grouped_because_somebody_has_to_read_it() -> None:
    assert "1,234,567" in Count(label="Tokens used", value=1_234_567).words


# --- the platform view -------------------------------------------------------


def test_an_empty_platform_counts_zero_and_says_it_is_healthy(
    factory: sessionmaker[DbSession],
) -> None:
    """Nothing wrong is the honest state, and the screen should say so rather
    than show an empty panel."""
    with factory() as session:
        said = platform(session, now=NOW)
        assert said.merchants.value == 0
        assert said.healthy
        assert said.trouble == ()


def test_businesses_and_connections_are_counted_separately(
    factory: sessionmaker[DbSession],
) -> None:
    """A business that signed up and never connected is a different problem
    from one that did."""
    with factory() as session:
        a_business(session, "a@one.ie", "Alpha", connected=True)
        a_business(session, "b@two.ie", "Beta", connected=False)
        session.commit()
        said = platform(session, now=NOW)
        assert said.merchants.value == 2
        assert said.connected.value == 1


def test_the_window_bounds_what_is_counted(factory: sessionmaker[DbSession]) -> None:
    with factory() as session:
        place = a_business(session, "a@one.ie", "Alpha")
        an_action(session, place, Status.APPLIED, ago=2)
        an_action(session, place, Status.APPLIED, ago=40)
        session.commit()
        assert platform(session, window="7d", now=NOW).applied.value == 1
        assert platform(session, window="90d", now=NOW).applied.value == 2


def test_the_window_is_named_on_the_answer(factory: sessionmaker[DbSession]) -> None:
    with factory() as session:
        assert platform(session, window="30d", now=NOW).window == "30d"
        assert platform(session, window="30d", now=NOW).applied.window == "30d"


def test_an_unknown_window_falls_back_rather_than_crashing(
    factory: sessionmaker[DbSession],
) -> None:
    """A URL somebody typed must not take the panel down."""
    with factory() as session:
        assert platform(session, window="all-time", now=NOW).window == "7d"
        assert set(WINDOWS) == {"today", "7d", "30d", "90d"}


def test_proposed_is_compared_with_the_window_before_it(
    factory: sessionmaker[DbSession],
) -> None:
    with factory() as session:
        place = a_business(session, "a@one.ie", "Alpha")
        an_action(session, place, Status.PROPOSED, ago=1)
        an_action(session, place, Status.PROPOSED, ago=2)
        an_action(session, place, Status.PROPOSED, ago=9)
        session.commit()
        said = platform(session, window="7d", now=NOW)
        assert said.proposed.value == 2
        assert said.proposed.before == 1
        assert said.proposed.change == 1


def test_waiting_is_a_state_now_and_is_not_bounded_by_the_window(
    factory: sessionmaker[DbSession],
) -> None:
    """Bounding it would hide the oldest ones, which are the only ones that
    matter."""
    with factory() as session:
        place = a_business(session, "a@one.ie", "Alpha")
        an_action(session, place, Status.AWAITING_APPROVAL, ago=200)
        session.commit()
        said = platform(session, window="7d", now=NOW)
        assert said.waiting.value == 1
        assert said.waiting.window == ""


def test_each_status_is_counted_into_its_own_figure(
    factory: sessionmaker[DbSession],
) -> None:
    with factory() as session:
        place = a_business(session, "a@one.ie", "Alpha")
        for status in (Status.APPLIED, Status.REVERTED, Status.REJECTED):
            an_action(session, place, status)
        session.commit()
        said = platform(session, now=NOW)
        assert (said.applied.value, said.reverted.value, said.refused.value) == (1, 1, 1)


# --- what needs attention ----------------------------------------------------


def test_a_sync_that_never_finished_is_called_stuck(
    factory: sessionmaker[DbSession],
) -> None:
    """The structure sync runs every 15 minutes, so an hour is four missed
    turns -- stuck rather than slow."""
    with factory() as session:
        a_business(session, "a@one.ie", "Alpha")
        session.add(
            SyncRun(
                id=uuid.uuid4(),
                customer_id=CUSTOMER,
                kind="structure",
                status="running",
                started_at=NOW - STUCK_AFTER - timedelta(minutes=5),
            )
        )
        session.commit()
        said = platform(session, now=NOW)
        assert said.syncs_stuck.value == 1
        assert not said.healthy
        assert "never finished" in said.trouble[0]
        assert "old figures" in said.trouble[0]


def test_a_sync_still_running_but_young_is_not_stuck(
    factory: sessionmaker[DbSession],
) -> None:
    with factory() as session:
        a_business(session, "a@one.ie", "Alpha")
        session.add(
            SyncRun(
                id=uuid.uuid4(),
                customer_id=CUSTOMER,
                status="running",
                started_at=NOW - timedelta(minutes=5),
            )
        )
        session.commit()
        assert platform(session, now=NOW).syncs_stuck.value == 0


def test_a_failed_model_call_is_surfaced(factory: sessionmaker[DbSession]) -> None:
    with factory() as session:
        session.add(
            PromptLog(
                id=uuid.uuid4(),
                job="chat",
                model="claude-sonnet-5-5",
                prompt_version="v1",
                trouble="the model could not be reached",
                created_at=NOW - timedelta(hours=1),
            )
        )
        session.commit()
        said = platform(session, now=NOW)
        assert said.model_trouble.value == 1
        assert any("came back with nothing" in one for one in said.trouble)


def test_tokens_are_summed_across_input_and_output(
    factory: sessionmaker[DbSession],
) -> None:
    with factory() as session:
        for one in range(2):
            session.add(
                PromptLog(
                    id=uuid.uuid4(),
                    job="chat",
                    model="m",
                    prompt_version="v",
                    input_tokens=100,
                    output_tokens=50,
                    created_at=NOW - timedelta(hours=one + 1),
                )
            )
        session.commit()
        assert platform(session, now=NOW).model_tokens.value == 300


def test_businesses_with_no_connection_at_all_is_called_out(
    factory: sessionmaker[DbSession],
) -> None:
    """Nothing can be read or proposed for anybody, which is worth a sentence."""
    with factory() as session:
        a_business(session, "a@one.ie", "Alpha", connected=False)
        session.commit()
        said = platform(session, now=NOW)
        assert any("No business has a connected" in one for one in said.trouble)


def test_no_businesses_at_all_is_not_reported_as_trouble(
    factory: sessionmaker[DbSession],
) -> None:
    """A new deployment is not broken. Saying it is would train staff to ignore
    the panel."""
    with factory() as session:
        assert platform(session, now=NOW).trouble == ()


def test_a_pile_of_unanswered_proposals_is_worth_saying(
    factory: sessionmaker[DbSession],
) -> None:
    with factory() as session:
        place = a_business(session, "a@one.ie", "Alpha")
        for _ in range(50):
            an_action(session, place, Status.AWAITING_APPROVAL)
        session.commit()
        said = platform(session, now=NOW)
        assert any("waiting for a merchant" in one for one in said.trouble)


# --- the merchant list -------------------------------------------------------


def test_the_list_carries_enough_to_decide_who_needs_attention(
    factory: sessionmaker[DbSession],
) -> None:
    with factory() as session:
        place = a_business(session, "a@one.ie", "Alpha Plumbing")
        an_action(session, place, Status.AWAITING_APPROVAL)
        an_action(session, place, Status.APPLIED)
        session.commit()
        rows = merchants(session)
        assert len(rows) == 1
        assert rows[0].name == "Alpha Plumbing"
        assert rows[0].connected
        assert rows[0].waiting == 1
        assert rows[0].applied == 1
        assert rows[0].people == 1


def test_a_business_with_no_connection_says_so_in_one_sentence(
    factory: sessionmaker[DbSession],
) -> None:
    with factory() as session:
        a_business(session, "b@two.ie", "Beta", connected=False)
        session.commit()
        assert merchants(session)[0].trouble == "No Google Ads account connected."


def test_a_suspended_google_account_is_the_trouble_worth_showing(
    factory: sessionmaker[DbSession],
) -> None:
    with factory() as session:
        place = a_business(session, "a@one.ie", "Alpha")
        connection = session.scalars(
            sa.select(AdsConnection).where(AdsConnection.organization_id == place)
        ).one()
        connection.account_status = "SUSPENDED"
        session.commit()
        assert "suspended" in merchants(session)[0].trouble


def test_a_connected_account_that_never_synced_says_so(
    factory: sessionmaker[DbSession],
) -> None:
    with factory() as session:
        a_business(session, "a@one.ie", "Alpha")
        session.commit()
        assert merchants(session)[0].trouble == "Never synced."


def test_a_healthy_business_has_nothing_to_say(factory: sessionmaker[DbSession]) -> None:
    with factory() as session:
        a_business(session, "a@one.ie", "Alpha")
        session.add(
            SyncRun(
                id=uuid.uuid4(),
                customer_id=CUSTOMER,
                status="ok",
                started_at=NOW - timedelta(minutes=20),
                finished_at=NOW - timedelta(minutes=19),
            )
        )
        session.commit()
        assert merchants(session)[0].trouble == ""


def test_the_list_can_be_searched_by_name(factory: sessionmaker[DbSession]) -> None:
    with factory() as session:
        a_business(session, "a@one.ie", "Alpha Plumbing")
        a_business(session, "b@two.ie", "Beta Roofing")
        session.commit()
        assert [r.name for r in merchants(session, look_for="roof")] == ["Beta Roofing"]
        assert [r.name for r in merchants(session, look_for="ALPHA")] == ["Alpha Plumbing"]
        assert merchants(session, look_for="nothing here") == []


def test_an_unnamed_business_is_still_listed(factory: sessionmaker[DbSession]) -> None:
    """It exists, somebody has to deal with it, and a blank row is unclickable."""
    with factory() as session:
        owner = person(session, "a@one.ie")
        place = home_for(session, owner)
        place.name = ""
        session.commit()
        assert merchants(session)[0].name == "(unnamed)"


# --- jobs and faults ---------------------------------------------------------


def a_run(
    session: DbSession,
    *,
    status: str = "ok",
    kind: str = "structure",
    ago_min: int = 20,
    took_min: int | None = 1,
    trouble: str = "",
) -> None:
    started = NOW - timedelta(minutes=ago_min)
    session.add(
        SyncRun(
            id=uuid.uuid4(),
            customer_id=CUSTOMER,
            kind=kind,
            status=status,
            stage="campaigns",
            trouble=trouble,
            started_at=started,
            finished_at=None if took_min is None else started + timedelta(minutes=took_min),
        )
    )
    session.flush()


def test_the_newest_run_comes_first(factory: sessionmaker[DbSession]) -> None:
    """The question somebody brings to this screen is "what just happened"."""
    from ppcway.staff.stats import jobs

    with factory() as session:
        a_run(session, kind="backfill", ago_min=300)
        a_run(session, kind="today", ago_min=5)
        session.commit()
        assert [one.kind for one in jobs(session, now=NOW)] == ["today", "backfill"]


def test_a_run_still_going_has_no_duration_rather_than_zero(
    factory: sessionmaker[DbSession],
) -> None:
    """Still running is not the same as instant."""
    from ppcway.staff.stats import jobs

    with factory() as session:
        a_run(session, took_min=None, ago_min=5)
        session.commit()
        one = jobs(session, now=NOW)[0]
        assert one.took_seconds is None
        assert one.words(NOW) == "Still running."
        assert not one.stuck(NOW)


def test_a_run_that_never_finished_is_called_stuck_with_its_age(
    factory: sessionmaker[DbSession],
) -> None:
    from ppcway.staff.stats import jobs

    with factory() as session:
        a_run(session, took_min=None, ago_min=200)
        session.commit()
        one = jobs(session, now=NOW)[0]
        assert one.stuck(NOW)
        assert "never finished" in one.words(NOW)
        assert "3 h ago" in one.words(NOW)


def test_runs_can_be_narrowed_to_the_failures(factory: sessionmaker[DbSession]) -> None:
    from ppcway.staff.stats import jobs

    with factory() as session:
        a_run(session, status="ok")
        a_run(session, status="failed", trouble="Google refused the request", ago_min=10)
        session.commit()
        assert len(jobs(session, now=NOW)) == 2
        only = jobs(session, failed_only=True, now=NOW)
        assert [one.status for one in only] == ["failed"]
        assert only[0].words(NOW) == "Google refused the request"


def test_a_failure_with_nothing_to_say_still_says_something(
    factory: sessionmaker[DbSession],
) -> None:
    """A blank cell tells a reader the screen is broken."""
    from ppcway.staff.stats import faults

    with factory() as session:
        a_run(session, status="failed", trouble="")
        session.commit()
        assert "said nothing" in faults(session, now=NOW)[0].what


def test_job_and_model_failures_arrive_in_one_list(
    factory: sessionmaker[DbSession],
) -> None:
    """Two tables would make somebody read both to find out whether anything is
    wrong."""
    from ppcway.staff.stats import faults

    with factory() as session:
        a_run(session, status="failed", trouble="the sync broke", ago_min=30)
        session.add(
            PromptLog(
                id=uuid.uuid4(),
                job="chat",
                model="m",
                prompt_version="v",
                customer_id=CUSTOMER,
                trouble="the model timed out",
                created_at=NOW - timedelta(minutes=10),
            )
        )
        session.commit()
        found = faults(session, now=NOW)
        assert len(found) == 2
        # Newest first, whichever source it came from.
        assert found[0].where.startswith("model")
        assert found[1].where.startswith("sync")


def test_faults_outside_the_window_are_left_out(factory: sessionmaker[DbSession]) -> None:
    from ppcway.staff.stats import faults

    with factory() as session:
        a_run(session, status="failed", trouble="old news", ago_min=60 * 24 * 40)
        session.commit()
        assert faults(session, window="7d", now=NOW) == []
        assert len(faults(session, window="90d", now=NOW)) == 1


def test_a_naive_timestamp_from_the_driver_does_not_crash_the_screen(
    factory: sessionmaker[DbSession],
) -> None:
    """SQLite hands back naive datetimes even for a `DateTime(timezone=True)`
    column, so arithmetic against an aware `now` raises TypeError.

    Found by these tests rather than in production, where Postgres would have
    hidden it until somebody ran the suite against SQLite -- or until a driver
    changed. `opt.guardrails` already normalises for the same reason.
    """
    from ppcway.staff.stats import jobs

    with factory() as session:
        a_run(session, took_min=None, ago_min=5)
        session.commit()
        one = jobs(session, now=NOW)[0]
        assert one.started_at.tzinfo is None, "the driver really did return naive"
        # None of these may raise.
        assert one.words(NOW)
        assert one.stuck(NOW) is False
        assert one.took_seconds is None
