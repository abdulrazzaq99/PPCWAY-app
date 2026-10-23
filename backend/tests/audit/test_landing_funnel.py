"""The free audit page: run it, see the score, prove the address, see the rest.

The test that matters most is the plain one — that a finding never appears in
anything a stranger can read. Everything else here is about the code being a
credential: it expires, it runs out of guesses, and a newer one retires the
older one.
"""

from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
import sqlalchemy as sa
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker

from ppcway.api import app as api_module
from ppcway.api.app import create_app
from ppcway.audit import lead as lead_module
from ppcway.audit.models import AuditRequest, AuditRun, EmailCode
from ppcway.config import Settings
from ppcway.db.base import Base
from ppcway.db.session import get_session
from ppcway.mail.send import Letter

REPORT: dict[str, Any] = {
    "findings": [
        {
            "key": "counting",
            "title": "Counting calls and forms",
            "status": "needs_you",
            "summary": "Nothing on this site tells Google when somebody calls.",
            "detail": [],
            "fix": "Add the conversion tag to the thank-you page.",
        },
        {
            "key": "speed",
            "title": "Speed on a phone",
            "status": "needs_you",
            "summary": "The home page takes nine seconds on a phone.",
            "detail": [],
            "fix": "Compress the hero image.",
        },
        {
            "key": "wording",
            "title": "Words Google may object to",
            "status": "ours",
            "summary": "We keep those out of your ads.",
            "detail": [],
            "fix": "",
        },
        {
            "key": "mobile",
            "title": "Works on a phone",
            "status": "good",
            "summary": "The site works on a phone.",
            "detail": [],
            "fix": "",
        },
    ]
}

#: Every word a stranger must never see before proving the address.
SECRETS = ["Counting calls", "nine seconds", "thank-you page", "Compress the hero"]


@pytest.fixture
def page(
    monkeypatch: pytest.MonkeyPatch,
) -> Iterator[tuple[FastAPI, sessionmaker[Session], list[Letter]]]:
    engine = sa.create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=sa.pool.StaticPool
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False, future=True)

    posted: list[Letter] = []
    monkeypatch.setattr(api_module, "send", lambda post, letter, **k: posted.append(letter))

    # The audit itself is tested elsewhere; here it only has to finish.
    def finish(run_id: Any, settings: Settings, **k: Any) -> None:
        with factory() as session:
            run = session.get(AuditRun, run_id)
            assert run is not None
            run.report = REPORT
            run.status = "done"
            run.stage = "done"
            run.finished_at = datetime.now(UTC)
            session.commit()

    monkeypatch.setattr(api_module, "_run", finish)

    app = create_app(Settings(app_base_url="https://app.ppcway.com", environment="test"))

    def one_session() -> Iterator[Session]:
        session = factory()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_session] = one_session
    yield app, factory, posted
    Base.metadata.drop_all(engine)


def an_audit(client: TestClient, **over: Any) -> str:
    body = {
        "business_name": "Alpha Plumbing",
        "site": "alphaplumbing.ca",
        "runner": "me",
        "goal": "calls",
        "spend_band": "1k_5k",
        "came_from": {"gclid": "abc123", "utm_source": "google"},
    }
    body.update(over)
    said = client.post("/v1/public/audits", json=body)
    assert said.status_code == 202, said.text
    return str(said.json()["audit_id"])


def give_details(client: TestClient, run_id: str) -> None:
    said = client.post(
        f"/v1/public/audits/{run_id}/lead",
        json={
            "name": "Dana Reid",
            "email": "dana@alphaplumbing.ca",
            "phone": "+1 416 555 0123",
            "tips_opt_in": True,
        },
    )
    assert said.status_code == 200, said.text


def test_the_summary_says_how_much_is_wrong_without_saying_what(
    page: tuple[FastAPI, sessionmaker[Session], list[Letter]],
) -> None:
    """The whole bargain of the page, in one assertion."""
    app, _, _ = page
    with TestClient(app) as client:
        run_id = an_audit(client)
        said = client.get(f"/v1/public/audits/{run_id}")

    assert said.status_code == 200, said.text
    body = said.json()
    assert body["status"] == "done"
    summary = body["summary"]
    assert summary["score"] > 0
    assert (summary["to_fix"], summary["to_improve"], summary["working"]) == (2, 1, 1)
    assert summary["business"] == "Alpha Plumbing"
    assert summary["goal"] == "Calls and bookings"
    assert summary["verdict"]
    assert "findings" not in body
    whole = said.text
    for secret in SECRETS:
        assert secret not in whole, f"a finding leaked before the address was proved: {secret}"


def test_the_waiting_screen_names_six_stages(
    page: tuple[FastAPI, sessionmaker[Session], list[Letter]],
) -> None:
    app, factory, _ = page
    with TestClient(app) as client:
        run_id = an_audit(client)
        with factory() as session:
            run = session.get(AuditRun, __import__("uuid").UUID(run_id))
            assert run is not None
            run.status = "running"
            run.stage = "crawling"
            session.commit()
        body = client.get(f"/v1/public/audits/{run_id}").json()

    assert [one["label"] for one in body["stages"]] == [
        "Reading your website",
        "Checking conversion tracking",
        "Checking speed and security on a phone",
        "Checking your search presence",
        "Checking ad readiness",
        "Comparing with similar businesses",
    ]
    assert body["stages"][0]["state"] == "running"
    assert body["stages"][-1]["state"] == "todo"
    assert 0 <= body["percent"] < 100


def test_the_lead_is_kept_before_the_address_is_proved(
    page: tuple[FastAPI, sessionmaker[Session], list[Letter]],
) -> None:
    """Somebody who gives their details and stops is still somebody who asked."""
    app, factory, posted = page
    with TestClient(app) as client:
        run_id = an_audit(client)
        give_details(client, run_id)

    with factory() as session:
        asked = session.scalars(sa.select(AuditRequest)).one()
        assert asked.name == "Dana Reid"
        assert asked.email == "dana@alphaplumbing.ca"
        assert asked.phone == "+1 416 555 0123"
        assert asked.runner == "me"
        assert asked.goal == "calls"
        assert asked.spend_band == "1k_5k"
        assert asked.came_from == {"gclid": "abc123", "utm_source": "google"}
        assert asked.tips_opt_in is True
        assert asked.tips_opt_in_at is not None
        # Kept, but not yet claimed as a verified lead.
        assert asked.verified_at is None

    assert len(posted) == 1
    assert "is your PPCway code" in posted[0].subject


def test_the_right_code_opens_everything(
    page: tuple[FastAPI, sessionmaker[Session], list[Letter]],
) -> None:
    app, factory, posted = page
    with TestClient(app) as client:
        run_id = an_audit(client)
        give_details(client, run_id)
        code = posted[0].subject.split(" ")[0]

        said = client.post(f"/v1/public/audits/{run_id}/verify", json={"code": code})

    assert said.status_code == 200, said.text
    body = said.json()
    assert body["verified"] is True
    titles = [f["title"] for f in body["findings"]]
    assert "Counting calls and forms" in titles
    # Costly first, then what we fix, then what is already fine.
    assert [f["severity"] for f in body["findings"]] == ["fix", "fix", "improve", "good"]
    assert body["waste"]["said"] == "$400–$1,100 a month"
    assert body["open_again"].startswith("https://app.ppcway.com/audit/open/")

    with factory() as session:
        assert session.scalars(sa.select(AuditRequest)).one().verified_at is not None


def test_a_wrong_code_is_told_apart_from_an_expired_one(
    page: tuple[FastAPI, sessionmaker[Session], list[Letter]],
) -> None:
    """They call for different actions, so they are different sentences."""
    app, factory, _ = page
    with TestClient(app) as client:
        run_id = an_audit(client)
        give_details(client, run_id)

        wrong = client.post(f"/v1/public/audits/{run_id}/verify", json={"code": "000000"})
        assert wrong.status_code == 400
        assert "not right" in wrong.json()["detail"]

        with factory() as session:
            code = session.scalars(sa.select(EmailCode)).one()
            code.expires_at = datetime.now(UTC) - timedelta(minutes=1)
            session.commit()

        stale = client.post(f"/v1/public/audits/{run_id}/verify", json={"code": "111111"})
        assert stale.status_code == 400
        assert "expired" in stale.json()["detail"]


def test_a_code_runs_out_of_guesses(
    page: tuple[FastAPI, sessionmaker[Session], list[Letter]],
) -> None:
    app, _, posted = page
    with TestClient(app) as client:
        run_id = an_audit(client)
        give_details(client, run_id)
        right = posted[0].subject.split(" ")[0]

        for _ in range(lead_module.MOST_TRIES):
            client.post(f"/v1/public/audits/{run_id}/verify", json={"code": "000000"})

        # Even the right code is no good once the guesses are spent.
        said = client.post(f"/v1/public/audits/{run_id}/verify", json={"code": right})

    assert said.status_code == 400
    assert "Too many tries" in said.json()["detail"]


def test_asking_again_too_soon_is_refused_politely(
    page: tuple[FastAPI, sessionmaker[Session], list[Letter]],
) -> None:
    app, _, posted = page
    with TestClient(app) as client:
        run_id = an_audit(client)
        give_details(client, run_id)
        said = client.post(f"/v1/public/audits/{run_id}/resend")

    assert said.status_code == 200
    assert said.json()["sent"] is False
    assert said.json()["wait_seconds"] > 0
    assert len(posted) == 1


def test_the_link_in_the_email_opens_it_on_any_device(
    page: tuple[FastAPI, sessionmaker[Session], list[Letter]],
) -> None:
    app, _, posted = page
    with TestClient(app) as client:
        run_id = an_audit(client)
        give_details(client, run_id)
        token = posted[0].text.split("/audit/open/")[1].split()[0]

        said = client.get(f"/v1/public/audits/open/{token}")

    assert said.status_code == 200, said.text
    assert said.json()["verified"] is True
    assert [f["title"] for f in said.json()["findings"]]


def test_an_unknown_link_is_refused_like_any_other(
    page: tuple[FastAPI, sessionmaker[Session], list[Letter]],
) -> None:
    app, _, _ = page
    with TestClient(app) as client:
        assert client.get("/v1/public/audits/open/not-a-real-token").status_code == 404


def test_nothing_is_wasted_when_nothing_is_spent(
    page: tuple[FastAPI, sessionmaker[Session], list[Letter]],
) -> None:
    """ "Not yet" is an answer, and it gets a green box rather than a number."""
    app, _, posted = page
    with TestClient(app) as client:
        run_id = an_audit(client, spend_band="none")
        give_details(client, run_id)
        code = posted[0].subject.split(" ")[0]
        body = client.post(f"/v1/public/audits/{run_id}/verify", json={"code": code}).json()

    assert body["waste"] is None


def test_a_website_cannot_be_audited_over_and_over(
    page: tuple[FastAPI, sessionmaker[Session], list[Letter]],
) -> None:
    app, _, _ = page
    with TestClient(app) as client:
        for _ in range(6):
            an_audit(client)
        said = client.post(
            "/v1/public/audits",
            json={"business_name": "Alpha Plumbing", "site": "alphaplumbing.ca"},
        )
    assert said.status_code == 429


def test_the_form_refuses_what_it_cannot_use(
    page: tuple[FastAPI, sessionmaker[Session], list[Letter]],
) -> None:
    app, _, _ = page
    with TestClient(app) as client:
        bad_site = client.post(
            "/v1/public/audits", json={"business_name": "Alpha", "site": "not a website"}
        )
        assert bad_site.status_code == 422

        run_id = an_audit(client)
        short_phone = client.post(
            f"/v1/public/audits/{run_id}/lead",
            json={"name": "Dana Reid", "email": "dana@alphaplumbing.ca", "phone": "123"},
        )
        assert short_phone.status_code == 422
