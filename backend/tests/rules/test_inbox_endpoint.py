"""`GET /v1/otto/inbox`, through the interface a merchant's browser uses.

The endpoint is where phase 1's promise is kept or broken: shown, not applied.
So these check the whole path -- signed in, connected, cards with everything on
them -- and that nothing was written to Google or to the log on the way.
"""

from __future__ import annotations

import uuid
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta

import pytest
import sqlalchemy as sa
from cryptography.fernet import Fernet
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import SecretStr
from sqlalchemy.orm import Session, sessionmaker

from ppcway.ads import models as ads_models
from ppcway.ads.mirror import (
    MICRO,
    CampaignDay,
    MirrorAd,
    MirrorCampaign,
    SearchTermDay,
    SyncRun,
    term_key,
)
from ppcway.api.app import create_app
from ppcway.auth import google
from ppcway.auth.models import UserAccount
from ppcway.chat import transcript as _transcript  # noqa: F401 - registers its table
from ppcway.config import Settings
from ppcway.db.base import Base
from ppcway.db.session import get_session
from ppcway.model import log as _prompt_log  # noqa: F401 - registers its table
from ppcway.opt import consent as _consent  # noqa: F401 - registers its table
from ppcway.opt.models import OptimizationAction
from ppcway.org.places import home_for

KEY = Fernet.generate_key()
CUSTOMER = "2580586343"
TODAY = datetime.now(UTC).date()


@pytest.fixture
def app_and_db(monkeypatch: pytest.MonkeyPatch) -> Iterator[tuple[FastAPI, sessionmaker[Session]]]:
    engine = sa.create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=sa.pool.StaticPool
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False, future=True)

    monkeypatch.setattr(
        google.id_token,  # type: ignore[attr-defined]
        "verify_oauth2_token",
        lambda credential, *a, **k: {
            "sub": "google-dana",
            "email": "dana@alphaplumbing.ca",
            "email_verified": True,
            "name": "Dana",
        },
    )
    settings = Settings(
        google_signin_client_id="test-client",
        google_oauth_client_id="test-client",
        google_oauth_client_secret=SecretStr("test-secret"),
        google_ads_developer_token=SecretStr("test-token"),
        google_oauth_token_key=SecretStr(KEY.decode()),
    )
    app = create_app(settings)

    def one_session() -> Iterator[Session]:
        session = factory()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_session] = one_session
    yield app, factory
    Base.metadata.drop_all(engine)


def connected(client: TestClient, factory: sessionmaker[Session]) -> str:
    token = client.post("/v1/auth/google", json={"credential": "d" * 40}).json()["token"]
    with factory() as session:
        dana = session.scalars(sa.select(UserAccount)).one()
        session.add(
            ads_models.AdsConnection(
                account_id=dana.id,
                organization_id=home_for(session, dana).id,
                ciphertext=Fernet(KEY).encrypt(b"a-permission").decode(),
                customer_id=CUSTOMER,
                customer_name="Alpha Plumbing",
                currency="CAD",
                # Without this the second guardrail refuses every proposal
                # with "we cannot tell what state this account is in", which
                # is correct and is also what production looks like until a
                # structure sync has read `customer.status`.
                account_status="ENABLED",
                status_read_at=datetime.now(UTC) - timedelta(hours=2),
            )
        )
        session.commit()
    return str(token)


def mirror(factory: sessionmaker[Session], *, term: str = "boiler repair jobs") -> None:
    """A read that went fine, a month of leads, and one wasteful search."""
    now = datetime.now(UTC)
    with factory() as session:
        session.add(
            MirrorCampaign(
                id=uuid.uuid4(),
                customer_id=CUSTOMER,
                resource_name=f"customers/{CUSTOMER}/campaigns/11",
                campaign_id="11",
                name="Emergency",
                status="ENABLED",
                channel="SEARCH",
                budget_micros=round(30.0 * MICRO),
                seen_at=now - timedelta(hours=2),
            )
        )
        session.add(
            SyncRun(
                id=uuid.uuid4(),
                customer_id=CUSTOMER,
                kind="today",
                status="done",
                started_at=now - timedelta(hours=3),
                finished_at=now - timedelta(hours=2),
            )
        )
        # Enough leads and spend that the account has its own cost per lead,
        # which is what the endpoint uses as the target to measure waste.
        for back in range(1, 29):
            session.add(
                CampaignDay(
                    id=uuid.uuid4(),
                    customer_id=CUSTOMER,
                    campaign_id="11",
                    day=TODAY - timedelta(days=back),
                    impressions=400,
                    clicks=20,
                    cost_micros=round(30.0 * MICRO),
                    conversions=1.0,
                    # `leads` is calls plus forms, not `conversions`, so an
                    # account whose conversions are not split into those
                    # categories has no cost per lead at all. Set here because
                    # this test is about an account that does.
                    calls=1.0,
                    refreshed_at=now - timedelta(hours=2),
                )
            )
        session.add(
            SearchTermDay(
                id=uuid.uuid4(),
                customer_id=CUSTOMER,
                campaign_id="11",
                ad_group_id="21",
                day=TODAY - timedelta(days=3),
                term=term,
                term_hash=term_key(term),
                status="NONE",
                clicks=140,
                cost_micros=round(240.0 * MICRO),
                conversions=0.0,
                refreshed_at=now - timedelta(hours=2),
            )
        )
        session.commit()


def test_signing_out_is_refused(app_and_db: tuple[FastAPI, sessionmaker[Session]]) -> None:
    app, _ = app_and_db
    with TestClient(app) as client:
        assert client.get("/v1/otto/inbox").status_code in (401, 422)


def test_without_a_connection_it_says_to_connect(
    app_and_db: tuple[FastAPI, sessionmaker[Session]],
) -> None:
    app, _factory = app_and_db
    with TestClient(app) as client:
        token = client.post("/v1/auth/google", json={"credential": "d" * 40}).json()["token"]
        said = client.get("/v1/otto/inbox", headers={"x-session-token": token}).json()
    assert said["connected"] is False
    assert said["cards"] == []
    assert "Connect your Google Ads account" in said["nothing_because"]


def test_a_card_comes_back_with_everything_the_brief_asks_for(
    app_and_db: tuple[FastAPI, sessionmaker[Session]],
) -> None:
    app, factory = app_and_db
    with TestClient(app) as client:
        token = connected(client, factory)
        mirror(factory)
        reply = client.get("/v1/otto/inbox", headers={"x-session-token": token})
    assert reply.status_code == 200, reply.text
    said = reply.json()
    assert said["connected"] is True
    assert said["target_cost_per_lead"] > 0
    assert len(said["cards"]) == 1

    card = said["cards"][0]
    assert card["rule_id"] == "R1"
    assert card["reason"] and "boiler repair jobs" in card["reason"]
    assert card["evidence"] and all(cite["id"] and cite["as_of"] for cite in card["evidence"])
    assert card["impact"]["money_a_month"] > 0
    assert card["risk"] == "low" and card["route"] == "owner"
    assert card["undo"]
    assert card["reason_is_ours"] is True, "no model was called on this path"


def test_the_business_own_name_is_never_proposed_for_exclusion(
    app_and_db: tuple[FastAPI, sessionmaker[Session]],
) -> None:
    """The mistake that would cost the most: a plumber stops showing for their own name."""
    app, factory = app_and_db
    with TestClient(app) as client:
        token = connected(client, factory)
        mirror(factory, term="alpha plumbing emergency")
        said = client.get("/v1/otto/inbox", headers={"x-session-token": token}).json()
    assert said["cards"] == []


def test_the_inbox_says_which_rules_are_still_missing(
    app_and_db: tuple[FastAPI, sessionmaker[Session]],
) -> None:
    app, factory = app_and_db
    with TestClient(app) as client:
        token = connected(client, factory)
        mirror(factory)
        said = client.get("/v1/otto/inbox", headers={"x-session-token": token}).json()
    assert said["ran"] == ["R1", "R4"]
    assert said["not_specified"] == ["R2", "R3", "R5"]


def test_reading_the_inbox_changes_nothing(
    app_and_db: tuple[FastAPI, sessionmaker[Session]],
) -> None:
    """Phase 1 is shown, not applied. Opening it must not be a decision."""
    app, factory = app_and_db
    with TestClient(app) as client:
        token = connected(client, factory)
        mirror(factory)
        client.get("/v1/otto/inbox", headers={"x-session-token": token})
        client.get("/v1/otto/inbox", headers={"x-session-token": token})
    with factory() as session:
        assert session.scalars(sa.select(OptimizationAction)).all() == []
        assert session.scalars(sa.select(MirrorAd)).all() == []


def test_a_colleague_sees_the_same_inbox(
    app_and_db: tuple[FastAPI, sessionmaker[Session]],
) -> None:
    """The connection belongs to the business, so the cards do too."""
    app, factory = app_and_db
    with TestClient(app) as client:
        token = connected(client, factory)
        mirror(factory)
        mine = client.get("/v1/otto/inbox", headers={"x-session-token": token}).json()
    assert mine["connected"] is True and len(mine["cards"]) == 1


# --- the auto-apply consent screen (phase 2.4) ---


def test_the_consent_screen_serves_its_own_words(
    app_and_db: tuple[FastAPI, sessionmaker[Session]],
) -> None:
    """From the server, so what was shown and what was recorded cannot drift."""
    app, factory = app_and_db
    with TestClient(app) as client:
        token = connected(client, factory)
        said = client.get("/v1/otto/auto-apply", headers={"x-session-token": token}).json()
    assert said["on"] is False
    assert said["wording"]
    assert "excluding searches" in said["words"]
    assert said["change_types"] == ["add_negative_keyword", "pause_ad"]
    assert said["may_turn_on"] is True, "the first person in a business is its owner"
    assert said["live"] is False, "the flag ships off"


def test_agreeing_is_recorded_and_can_be_turned_off(
    app_and_db: tuple[FastAPI, sessionmaker[Session]],
) -> None:
    app, factory = app_and_db
    with TestClient(app) as client:
        token = connected(client, factory)
        gave = client.post("/v1/otto/auto-apply", headers={"x-session-token": token})
        assert gave.status_code == 201, gave.text
        assert gave.json()["on"] is True
        assert gave.json()["change_types"] == ["add_negative_keyword", "pause_ad"]

        now_on = client.get("/v1/otto/auto-apply", headers={"x-session-token": token}).json()
        assert now_on["on"] is True
        assert now_on["agreed_at"] and now_on["agreed_wording"]

        off = client.delete("/v1/otto/auto-apply", headers={"x-session-token": token})
        assert off.status_code == 200
        assert off.json() == {
            "on": False,
            "was_on": True,
            "stopped_at": off.json()["stopped_at"],
        }

        after = client.get("/v1/otto/auto-apply", headers={"x-session-token": token}).json()
        assert after["on"] is False


def test_the_record_keeps_the_ip_and_the_words(
    app_and_db: tuple[FastAPI, sessionmaker[Session]],
) -> None:
    """What makes it evidence rather than a note."""
    from ppcway.opt.consent import THE_WORDS, AutoApplyConsent

    app, factory = app_and_db
    with TestClient(app) as client:
        token = connected(client, factory)
        client.post("/v1/otto/auto-apply", headers={"x-session-token": token})
    with factory() as session:
        row = session.scalars(sa.select(AutoApplyConsent)).one()
    assert row.ip, "the address it came from"
    assert row.words == THE_WORDS
    assert row.limits is not None and "max_change_pct" in row.limits


def test_turning_off_something_never_on_says_so(
    app_and_db: tuple[FastAPI, sessionmaker[Session]],
) -> None:
    app, factory = app_and_db
    with TestClient(app) as client:
        token = connected(client, factory)
        off = client.delete("/v1/otto/auto-apply", headers={"x-session-token": token}).json()
    assert off["on"] is False and off["was_on"] is False


# --- the inbox reads the log, so a card can be answered (the 1.2/2.2 join) ---


def test_a_written_proposal_appears_with_an_id_and_can_be_answered(
    app_and_db: tuple[FastAPI, sessionmaker[Session]],
) -> None:
    """The gap this closed: cards computed on read had no id, so nothing in
    the inbox could be approved. A card a merchant cannot answer is not an
    inbox."""
    from ppcway.opt.nightly import tonight

    app, factory = app_and_db
    with TestClient(app) as client:
        token = connected(client, factory)
        mirror(factory)

        # The nightly pass writes what the rules found.
        night = tonight(factory, Settings(environment="test"))
        assert night.proposed == 1, night.trouble

        said = client.get("/v1/otto/inbox", headers={"x-session-token": token}).json()
        card = said["cards"][0]
        assert card["id"], "a written proposal has an id"
        assert card["answerable"] is True
        assert card["status"] == "awaiting_approval"
        assert card["expires_at"], "and a date it stops being on offer"

        # And the id the screen shows is the one the endpoint answers.
        answered = client.post(
            f"/v1/otto/actions/{card['id']}/approve",
            headers={"x-session-token": token},
        )
        assert answered.status_code == 200, answered.text
        assert answered.json()["status"] in {"approved", "rejected"}


def test_what_has_not_been_written_yet_is_shown_without_buttons(
    app_and_db: tuple[FastAPI, sessionmaker[Session]],
) -> None:
    """An account that connected an hour ago has nothing in the log, and an
    empty inbox saying "nothing worth changing" would be a lie about an
    account nobody has looked at."""
    app, factory = app_and_db
    with TestClient(app) as client:
        token = connected(client, factory)
        mirror(factory)
        said = client.get("/v1/otto/inbox", headers={"x-session-token": token}).json()
    card = said["cards"][0]
    assert card["id"] == ""
    assert card["answerable"] is False
    assert card["status"] == "found"
    assert card["reason"], "but it still says what was found and why"


def test_a_card_already_written_is_not_also_previewed(
    app_and_db: tuple[FastAPI, sessionmaker[Session]],
) -> None:
    """Otherwise the same finding appears twice, once answerable and once not."""
    from ppcway.opt.nightly import tonight

    app, factory = app_and_db
    with TestClient(app) as client:
        token = connected(client, factory)
        mirror(factory)
        tonight(factory, Settings(environment="test"))
        said = client.get("/v1/otto/inbox", headers={"x-session-token": token}).json()
    assert len(said["cards"]) == 1
