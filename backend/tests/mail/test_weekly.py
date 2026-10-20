"""The Monday post: what it says, and the ways it must not go twice.

The words matter as much as the sending here. This is the only part of PPCway
that reaches somebody who is not looking at it, so a week with nothing in it has
to read as a week with nothing in it, and the account's own figures have to
agree with the dashboard because both are read from the same mirror.
"""

from __future__ import annotations

import json
from datetime import UTC, date, datetime, timedelta

import httpx
import pytest
import sqlalchemy as sa
from sqlalchemy.orm import Session as DbSession

from ppcway.ads.mirror import MICRO, CampaignDay, ExternalChange, MirrorAd, MirrorCampaign
from ppcway.ads.models import AdsConnection
from ppcway.ads.numbers import account_numbers
from ppcway.auth.models import UserAccount
from ppcway.config import Settings
from ppcway.db.base import Base

# A connection points at the business it belongs to, so that table has to exist
# before this one can be created.
from ppcway.mail.models import WeeklyPost
from ppcway.mail.send import Post
from ppcway.org.models import Organization  # noqa: F401
from ppcway.mail.weekly import post_weekly, weekly_letter

#: A Monday, which is when the post goes out.
NOW = datetime(2026, 10, 19, 8, 0, tzinfo=UTC)
TODAY = NOW.date()

LIVE = Post(sender="PPCway <hello@ppcway.com>", provider="resend", api_key="key")


@pytest.fixture
def db() -> DbSession:
    engine = sa.create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with DbSession(engine) as session:
        yield session


def provider(status: int = 200) -> tuple[httpx.Client, list[dict[str, object]]]:
    sent: list[dict[str, object]] = []

    def handle(request: httpx.Request) -> httpx.Response:
        sent.append(json.loads(request.content))
        return httpx.Response(status, json={"id": "abc"} if status < 300 else {"message": "no"})

    return httpx.Client(transport=httpx.MockTransport(handle)), sent


def settings() -> Settings:
    return Settings(
        email_provider="resend",
        email_from="PPCway <hello@ppcway.com>",
        app_base_url="https://app.ppcway.com",
    )


def account(db: DbSession, *, confirmed: bool = True) -> UserAccount:
    person = UserAccount(
        email="dana@alphaplumbing.ca",
        name="Dana Reyes",
        email_verified_at=NOW if confirmed else None,
    )
    db.add(person)
    db.commit()
    return person


def connect(db: DbSession, person: UserAccount) -> AdsConnection:
    row = AdsConnection(
        account_id=person.id,
        ciphertext="x",
        customer_id="1",
        customer_name="Alpha Plumbing",
        currency="CAD",
    )
    db.add(row)
    db.commit()
    return row


def campaign(db: DbSession, name: str = "Emergency plumbing", budget: float = 20.0) -> None:
    db.add(
        MirrorCampaign(
            customer_id="1",
            resource_name=f"customers/1/campaigns/{name}",
            campaign_id="11",
            name=name,
            status="ENABLED",
            budget_micros=round(budget * MICRO),
        )
    )
    db.commit()


def day(
    db: DbSession,
    on: date,
    *,
    cost: float = 0.0,
    calls: float = 0.0,
    forms: float = 0.0,
    campaign_id: str = "11",
) -> None:
    db.add(
        CampaignDay(
            customer_id="1",
            campaign_id=campaign_id,
            day=on,
            cost_micros=round(cost * MICRO),
            calls=calls,
            forms=forms,
            conversions=calls + forms,
        )
    )
    db.commit()


def letter_for(db: DbSession) -> tuple[str, str]:
    held = account_numbers(db, "1", days=7, currency="CAD", today=TODAY)
    written = weekly_letter(
        held,
        to="dana@alphaplumbing.ca",
        name="Dana Reyes",
        business="Alpha Plumbing",
        link="https://app.ppcway.com/home",
        now=NOW,
    )
    return written.subject, written.text


def test_it_says_what_came_in_and_how_that_compares(db: DbSession) -> None:
    campaign(db)
    day(db, date(2026, 10, 15), cost=180.0, calls=5, forms=3)
    day(db, date(2026, 10, 8), cost=180.0, forms=5)

    subject, text = letter_for(db)

    assert subject == "Last week: 8 leads at $22.50 each"
    assert "You got 8 leads last week — 5 phone calls and 3 forms." in text
    assert "That is 3 more than the week before." in text
    assert "Each one cost $22.50." in text
    assert "$13.50 cheaper than the week before" in text
    assert "You spent $180.00." in text
    assert "about $140.00 a week" in text


def test_a_week_the_ads_did_not_run_says_that_rather_than_printing_zeros(
    db: DbSession,
) -> None:
    campaign(db)
    day(db, date(2026, 10, 15), cost=0.0)

    subject, text = letter_for(db)

    assert subject == "Last week: your ads did not run"
    assert "Your ads did not run last week" in text
    assert "0 leads" not in text


def test_money_spent_with_nothing_counted_points_at_the_tracking(db: DbSession) -> None:
    campaign(db)
    day(db, date(2026, 10, 15), cost=240.0)

    subject, text = letter_for(db)

    assert subject == "Last week: $240.00 spent and nothing came in"
    assert "Nothing came in last week, and you spent $240.00." in text
    assert "the tracking may not be counting it" in text


def test_the_first_week_does_not_pretend_to_compare(db: DbSession) -> None:
    campaign(db)
    day(db, date(2026, 10, 15), cost=50.0, forms=2)

    _, text = letter_for(db)

    assert "There is nothing to compare it with yet." in text
    assert "than the week before" not in text


def test_what_needs_them_is_in_the_letter(db: DbSession) -> None:
    campaign(db, "Drain cleaning")
    day(db, date(2026, 10, 15), cost=120.0)
    db.add(
        MirrorAd(
            customer_id="1",
            resource_name="customers/1/adGroupAds/21~41",
            ad_id="41",
            ad_group_id="21",
            campaign_id="11",
            status="ENABLED",
            approval="DISAPPROVED",
            headlines=["24 hour plumber"],
        )
    )
    db.commit()

    _, text = letter_for(db)

    assert "2 things needs you:" in text or "2 things need you:" in text
    assert "Drain cleaning: Spent $120.00" in text
    assert "24 hour plumber" in text


def test_a_change_made_in_google_ads_is_listed_once_and_only_if_it_is_recent(
    db: DbSession,
) -> None:
    campaign(db)
    day(db, date(2026, 10, 15), cost=50.0, forms=2)
    db.add(
        ExternalChange(
            customer_id="1",
            kind="campaign",
            resource_name="customers/1/campaigns/11",
            label="Emergency plumbing",
            summary="Daily budget raised from 5.00 CAD to 12.00 CAD",
            noticed_at=NOW - timedelta(days=2),
        )
    )
    db.add(
        ExternalChange(
            customer_id="1",
            kind="campaign",
            resource_name="customers/1/campaigns/11",
            label="Emergency plumbing",
            summary="Status changed from PAUSED to ENABLED",
            noticed_at=NOW - timedelta(days=40),
        )
    )
    db.commit()

    _, text = letter_for(db)

    assert "1 change was made in Google Ads itself last week:" in text
    assert "Daily budget raised from 5.00 CAD to 12.00 CAD" in text
    assert "Status changed from PAUSED" not in text
    # The same fact must not appear twice, as a count and as a list.
    assert "were made directly in Google" not in text


def test_every_letter_says_what_ppcway_touched(db: DbSession) -> None:
    campaign(db)
    day(db, date(2026, 10, 15), cost=50.0, forms=2)

    _, text = letter_for(db)

    assert "PPCway has not changed anything in your account." in text


def test_one_post_a_week_however_often_the_clock_calls(db: DbSession) -> None:
    person = account(db)
    connect(db, person)
    campaign(db)
    day(db, date(2026, 10, 15), cost=50.0, forms=2)
    client, sent = provider()

    with client:
        first = post_weekly(db, settings(), now=NOW, post=LIVE, client=client)
        second = post_weekly(db, settings(), now=NOW + timedelta(hours=6), post=LIVE, client=client)

    assert first == {"sent": 1, "failed": 0, "skipped": 0}
    assert second == {"sent": 0, "failed": 0, "skipped": 0}
    assert len(sent) == 1
    assert sent[0]["to"] == ["dana@alphaplumbing.ca"]
    rows = db.scalars(sa.select(WeeklyPost)).all()
    assert len(rows) == 1
    assert rows[0].week_start == date(2026, 10, 19)
    assert rows[0].status == "sent"


def test_an_unconfirmed_address_is_not_written_to(db: DbSession) -> None:
    person = account(db, confirmed=False)
    connect(db, person)
    campaign(db)
    day(db, date(2026, 10, 15), cost=50.0, forms=2)
    client, sent = provider()

    with client:
        counts = post_weekly(db, settings(), now=NOW, post=LIVE, client=client)

    assert counts == {"sent": 0, "failed": 0, "skipped": 1}
    assert sent == []
    assert db.scalars(sa.select(WeeklyPost)).all() == []


def test_an_account_we_have_not_read_yet_is_left_for_next_week(db: DbSession) -> None:
    person = account(db)
    connect(db, person)
    client, sent = provider()

    with client:
        counts = post_weekly(db, settings(), now=NOW, post=LIVE, client=client)

    assert counts == {"sent": 0, "failed": 0, "skipped": 1}
    assert sent == []
    # No row, so the next run tries again rather than counting a week as done.
    assert db.scalars(sa.select(WeeklyPost)).all() == []


def test_a_refusal_is_written_down_and_tried_again(db: DbSession) -> None:
    person = account(db)
    connect(db, person)
    campaign(db)
    day(db, date(2026, 10, 15), cost=50.0, forms=2)
    broken, _ = provider(status=422)
    working, sent = provider()

    with broken:
        first = post_weekly(db, settings(), now=NOW, post=LIVE, client=broken)
    rows = db.scalars(sa.select(WeeklyPost)).all()
    assert first == {"sent": 0, "failed": 1, "skipped": 0}
    assert rows[0].status == "failed"
    assert rows[0].trouble

    with working:
        second = post_weekly(
            db, settings(), now=NOW + timedelta(hours=2), post=LIVE, client=working
        )

    assert second == {"sent": 1, "failed": 0, "skipped": 0}
    assert len(sent) == 1
    rows = db.scalars(sa.select(WeeklyPost)).all()
    assert len(rows) == 1
    assert rows[0].status == "sent"


def test_a_revoked_connection_gets_no_post(db: DbSession) -> None:
    person = account(db)
    connection = connect(db, person)
    connection.revoked_at = NOW
    db.commit()
    campaign(db)
    day(db, date(2026, 10, 15), cost=50.0, forms=2)
    client, sent = provider()

    with client:
        counts = post_weekly(db, settings(), now=NOW, post=LIVE, client=client)

    assert counts == {"sent": 0, "failed": 0, "skipped": 0}
    assert sent == []
