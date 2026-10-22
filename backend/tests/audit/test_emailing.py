"""Emailing a finished audit, which is the post and not the audit.

The button that asks for this used to be a link to the waiting screen: it
started the whole check again and threw away the address. These tests hold the
new shape — one finished run, one letter, nobody's inbox but the right one.
"""

from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

import pytest
import sqlalchemy as sa
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker

from ppcway.api import app as api_module
from ppcway.api.app import create_app
from ppcway.audit.models import AuditRequest, AuditRun
from ppcway.auth import google
from ppcway.config import Settings
from ppcway.db.base import Base
from ppcway.db.session import get_session
from ppcway.mail.send import Letter

#: What the stubbed printer hands back, and every page it was asked to print.
PDF = b"%PDF-1.4 a report"
printed: list[str] = []

REPORT = {
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
            "key": "mobile",
            "title": "Works on a phone",
            "status": "good",
            "summary": "The site works on a phone.",
            "detail": [],
            "fix": "",
        },
    ]
}


@pytest.fixture
def app_db_post(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> Iterator[tuple[FastAPI, sessionmaker[Session], list[Letter]]]:
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

    # Nothing leaves the building; we keep what would have.
    posted: list[Letter] = []
    monkeypatch.setattr(api_module, "send", lambda post, letter, **k: posted.append(letter))

    # No browser in a test. What matters here is which page it is asked to
    # print and that what comes back travels; the printing is Chromium's job.
    printed.clear()

    def pretend(url: str, **k: object) -> bytes:
        printed.append(url)
        return PDF

    monkeypatch.setattr(api_module, "to_pdf", pretend)

    settings = Settings(
        google_signin_client_id="test-client",
        app_base_url="https://app.ppcway.com",
        audit_shots_dir=str(tmp_path),
    )
    app = create_app(settings)

    def one_session() -> Iterator[Session]:
        session = factory()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_session] = one_session
    yield app, factory, posted
    Base.metadata.drop_all(engine)


def an_audit(factory: sessionmaker[Session], *, status: str = "done", email: str = "") -> str:
    with factory() as session:
        asked = AuditRequest(
            name="Dana",
            phone="",
            business_name="Alpha Plumbing",
            site="alphaplumbing.ca",
            email=email,
            source="landing",
            consent_text="They ticked the box.",
        )
        session.add(asked)
        session.flush()
        run = AuditRun(
            site="alphaplumbing.ca",
            status=status,
            request_id=asked.id,
            report=REPORT if status == "done" else None,
            finished_at=datetime.now(UTC) if status == "done" else None,
        )
        session.add(run)
        session.commit()
        return str(run.id)


def test_it_emails_the_person_signed_in_without_asking_where(
    app_db_post: tuple[FastAPI, sessionmaker[Session], list[Letter]],
) -> None:
    app, factory, posted = app_db_post
    with TestClient(app) as client:
        token = client.post("/v1/auth/google", json={"credential": "d" * 40}).json()["token"]
        run_id = an_audit(factory)

        said = client.post(
            f"/v1/audits/{run_id}/email", json={}, headers={"x-session-token": token}
        )

        assert said.status_code == 200, said.text
        assert said.json()["sent_to"] == "dana@alphaplumbing.ca"
        assert len(posted) == 1
        letter = posted[0]
        assert letter.to == "dana@alphaplumbing.ca"
        assert "Alpha Plumbing" in letter.subject
        # The link is the report itself, so nothing has to be run again to read it.
        assert f"https://app.ppcway.com/audit/{run_id}" in letter.text


def test_a_session_beats_any_address_in_the_body(
    app_db_post: tuple[FastAPI, sessionmaker[Session], list[Letter]],
) -> None:
    """The most anybody can do with a session is email themselves."""
    app, factory, posted = app_db_post
    with TestClient(app) as client:
        token = client.post("/v1/auth/google", json={"credential": "d" * 40}).json()["token"]
        run_id = an_audit(factory)

        said = client.post(
            f"/v1/audits/{run_id}/email",
            json={"email": "somebody.else@example.com"},
            headers={"x-session-token": token},
        )

        assert said.status_code == 200, said.text
        assert said.json()["sent_to"] == "dana@alphaplumbing.ca"
        assert posted[0].to == "dana@alphaplumbing.ca"


def test_an_unfinished_audit_is_not_emailed(
    app_db_post: tuple[FastAPI, sessionmaker[Session], list[Letter]],
) -> None:
    app, factory, posted = app_db_post
    with TestClient(app) as client:
        token = client.post("/v1/auth/google", json={"credential": "d" * 40}).json()["token"]
        run_id = an_audit(factory, status="running")

        said = client.post(
            f"/v1/audits/{run_id}/email", json={}, headers={"x-session-token": token}
        )

        assert said.status_code == 409
        assert "finished" in said.json()["detail"]
        assert posted == []


def test_signed_out_it_takes_an_address_once_and_then_only_that_one(
    app_db_post: tuple[FastAPI, sessionmaker[Session], list[Letter]],
) -> None:
    """Otherwise this would be a way of posting mail to strangers."""
    app, factory, posted = app_db_post
    with TestClient(app) as client:
        run_id = an_audit(factory)

        first = client.post(f"/v1/audits/{run_id}/email", json={"email": "Dana@Alpha.ca"})
        assert first.status_code == 200, first.text
        assert first.json()["sent_to"] == "dana@alpha.ca"

        again = client.post(f"/v1/audits/{run_id}/email", json={"email": "stranger@example.com"})
        assert again.status_code == 403
        assert len(posted) == 1

        # The same address again is simply the person pressing twice.
        same = client.post(f"/v1/audits/{run_id}/email", json={"email": "dana@alpha.ca"})
        assert same.status_code == 200
        assert len(posted) == 2


def test_signed_out_with_no_address_anywhere_it_asks(
    app_db_post: tuple[FastAPI, sessionmaker[Session], list[Letter]],
) -> None:
    app, factory, posted = app_db_post
    with TestClient(app) as client:
        run_id = an_audit(factory)
        said = client.post(f"/v1/audits/{run_id}/email", json={})
        assert said.status_code == 400
        assert posted == []


def test_the_run_posts_the_report_to_whoever_asked_for_it(
    app_db_post: tuple[FastAPI, sessionmaker[Session], list[Letter]],
) -> None:
    """The waiting screen's promise: an address, and the report when it is ready."""
    _, factory, posted = app_db_post
    run_id = an_audit(factory, email="dana@alphaplumbing.ca")
    settings = Settings(app_base_url="https://app.ppcway.com")

    with factory() as session:
        run = session.get(AuditRun, UUID(run_id))
        assert run is not None
        api_module._tell_them(run, session, settings)

    assert len(posted) == 1
    assert posted[0].to == "dana@alphaplumbing.ca"
    assert "out of 100" in posted[0].text


def test_a_run_nobody_left_an_address_for_posts_nothing(
    app_db_post: tuple[FastAPI, sessionmaker[Session], list[Letter]],
) -> None:
    _, factory, posted = app_db_post
    run_id = an_audit(factory)
    settings = Settings(app_base_url="https://app.ppcway.com")

    with factory() as session:
        run = session.get(AuditRun, UUID(run_id))
        assert run is not None
        api_module._tell_them(run, session, settings)

    assert posted == []


def test_the_letter_carries_the_report_as_a_pdf(
    app_db_post: tuple[FastAPI, sessionmaker[Session], list[Letter]],
) -> None:
    """A link is no use to somebody who wants to print it or keep it."""
    app, factory, posted = app_db_post
    with TestClient(app) as client:
        token = client.post("/v1/auth/google", json={"credential": "d" * 40}).json()["token"]
        run_id = an_audit(factory)

        client.post(f"/v1/audits/{run_id}/email", json={}, headers={"x-session-token": token})

        assert len(posted[0].attachments) == 1
        paper = posted[0].attachments[0]
        assert paper.filename == "PPCWay audit - Alpha Plumbing.pdf"
        assert paper.content == PDF
        assert paper.media_type == "application/pdf"
        assert "attached as a PDF" in posted[0].text


def test_the_printed_page_is_the_one_without_the_furniture(
    app_db_post: tuple[FastAPI, sessionmaker[Session], list[Letter]],
) -> None:
    app, factory, _ = app_db_post
    with TestClient(app) as client:
        run_id = an_audit(factory)

        said = client.get(f"/v1/audits/{run_id}/pdf")

        assert said.status_code == 200, said.text
        assert said.headers["content-type"] == "application/pdf"
        assert said.content == PDF
        assert printed == [f"https://app.ppcway.com/audit/{run_id}?paper=1"]


def test_a_pdf_is_printed_once_and_then_kept(
    app_db_post: tuple[FastAPI, sessionmaker[Session], list[Letter]],
) -> None:
    app, factory, _ = app_db_post
    with TestClient(app) as client:
        run_id = an_audit(factory)
        client.get(f"/v1/audits/{run_id}/pdf")
        client.get(f"/v1/audits/{run_id}/pdf")
        assert len(printed) == 1


def test_an_unfinished_audit_has_no_pdf(
    app_db_post: tuple[FastAPI, sessionmaker[Session], list[Letter]],
) -> None:
    app, factory, _ = app_db_post
    with TestClient(app) as client:
        run_id = an_audit(factory, status="running")
        said = client.get(f"/v1/audits/{run_id}/pdf")
        assert said.status_code == 404
        assert printed == []
