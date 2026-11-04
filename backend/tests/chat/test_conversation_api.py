"""Carrying a conversation on, through the HTTP layer.

The loop has always accepted earlier messages; the endpoint never passed
them, so every question to Otto started from nothing and "and the week
before?" had nothing to refer to. These go through the real endpoint, with
the answering loop replaced by one that records what it was given, so the
tests can see exactly which history reached it.

The endpoint writes each turn with its own session after the stream ends, so
`session_factory` is pointed at this file's database. Without that it would
open whatever `DATABASE_URL` names, and a test suite has no business there.
"""

from __future__ import annotations

import json
import uuid
from collections.abc import Iterator
from typing import Any

import pytest
import sqlalchemy as sa
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker

import ppcway.api.app as api_module
from ppcway.ads.models import AdsConnection
from ppcway.api.app import create_app
from ppcway.auth.models import UserAccount
from ppcway.auth.sessions import sign_in_existing
from ppcway.chat import ask as asking
from ppcway.chat.ask import Said
from ppcway.chat.transcript import Turn, this_month
from ppcway.config import Settings
from ppcway.db.base import Base
from ppcway.db.session import get_session
from ppcway.model.service import Answer
from ppcway.org.models import Organization
from ppcway.org.places import home_for
from ppcway.staff import models as _staff_tables  # noqa: F401 - home_for reads staff_grant

CUSTOMER = "2580586343"


@pytest.fixture
def world(
    monkeypatch: pytest.MonkeyPatch,
) -> Iterator[tuple[FastAPI, sessionmaker[Session], list[dict[str, Any]]]]:
    engine = sa.create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=sa.pool.StaticPool
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False, future=True)
    monkeypatch.setattr(api_module, "session_factory", lambda: factory)

    seen: list[dict[str, Any]] = []

    def recording(
        models: Any,
        session: Any,
        question: str,
        *,
        history: Any = (),
        spent: Any = None,
        **_: Any,
    ) -> Iterator[Said]:
        seen.append({"question": question, "history": list(history)})
        if spent is not None:
            # What one real call reports, in OpenRouter's spelling. A question
            # can ask for a costlier one by saying "expensive".
            spent.add(
                Answer(
                    text="",
                    model="anthropic/claude-sonnet-5.5",
                    prompt_version="otto-test",
                    input_tokens=7_000_000 if "expensive" in question else 4_000,
                    output_tokens=200,
                    took_ms=1_200,
                )
            )
        yield Said(kind="answer", words=f"About: {question}")

    monkeypatch.setattr(asking, "answer", recording)

    # Configured as a deployment with Otto switched on; no real model is
    # reached, because the loop above never calls one.
    app = create_app(
        Settings(
            environment="test",
            openrouter_api_key="sk-not-a-real-key",  # type: ignore[arg-type]
            model_prompt_version="otto-test",
        )
    )

    def one_session() -> Iterator[Session]:
        session = factory()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_session] = one_session
    yield app, factory, seen
    Base.metadata.drop_all(engine)


def a_merchant(factory: sessionmaker[Session], email: str) -> str:
    """A signed-in owner of a business with Google Ads connected."""
    with factory() as session:
        owner = UserAccount(google_sub=f"google-{email}", email=email)
        session.add(owner)
        session.flush()
        place = home_for(session, owner)
        session.add(
            AdsConnection(
                id=uuid.uuid4(),
                account_id=owner.id,
                organization_id=place.id,
                ciphertext="locked",
                customer_id=CUSTOMER,
                customer_name="Alpha Plumbing",
                currency="EUR",
                account_status="ENABLED",
            )
        )
        token = sign_in_existing(session, owner)
        session.commit()
        return token


def ask(client: TestClient, token: str, **body: Any) -> list[dict[str, Any]]:
    said = client.post("/v1/otto/ask", headers={"x-session-token": token}, json=body)
    assert said.status_code == 200, said.text
    return [json.loads(line[6:]) for line in said.text.splitlines() if line.startswith("data: ")]


def conversation_of(events: list[dict[str, Any]]) -> str:
    first = events[0]
    assert first["kind"] == "conversation", "the stream says which conversation first"
    return str(first["id"])


def test_a_follow_up_arrives_with_what_came_before(
    world: tuple[FastAPI, sessionmaker[Session], list[dict[str, Any]]],
) -> None:
    app, factory, seen = world
    token = a_merchant(factory, "dana@alphaplumbing.ie")
    with TestClient(app) as client:
        first = ask(client, token, question="How many leads did I get last week?")
        held = conversation_of(first)
        second = ask(client, token, question="And the week before?", conversation_id=held)
    assert conversation_of(second) == held
    assert seen[0]["history"] == []
    assert seen[1]["history"] == [
        {"role": "user", "content": "How many leads did I get last week?"},
        {"role": "assistant", "content": "About: How many leads did I get last week?"},
    ]


def test_without_a_conversation_every_question_starts_fresh(
    world: tuple[FastAPI, sessionmaker[Session], list[dict[str, Any]]],
) -> None:
    """As before, for a screen that sends no conversation."""
    app, factory, seen = world
    token = a_merchant(factory, "dana@alphaplumbing.ie")
    with TestClient(app) as client:
        one = conversation_of(ask(client, token, question="How did last week go?"))
        two = conversation_of(ask(client, token, question="And this week?"))
    assert one != two
    assert seen[1]["history"] == []


def test_somebody_elses_conversation_is_not_read(
    world: tuple[FastAPI, sessionmaker[Session], list[dict[str, Any]]],
) -> None:
    """An id from another merchant's conversation starts a new one, and none
    of their questions or answers reaches the model."""
    app, factory, seen = world
    dana = a_merchant(factory, "dana@alphaplumbing.ie")
    sean = a_merchant(factory, "sean@beaconroofing.ie")
    with TestClient(app) as client:
        theirs = conversation_of(ask(client, dana, question="What did Beacon Roofing spend?"))
        mine = conversation_of(
            ask(client, sean, question="How am I doing?", conversation_id=theirs)
        )
    assert mine != theirs
    assert seen[1]["history"] == []


def test_what_a_question_cost_is_written_down_and_counted(
    world: tuple[FastAPI, sessionmaker[Session], list[dict[str, Any]]],
) -> None:
    """It used to be written down as nothing, so the ceiling never moved."""
    app, factory, _seen = world
    token = a_merchant(factory, "dana@alphaplumbing.ie")
    with TestClient(app) as client:
        ask(client, token, question="How did last week go?")
    with factory() as session:
        turn = session.query(Turn).one()
        assert (turn.input_tokens, turn.output_tokens) == (4_000, 200)
        assert turn.cost_usd > 0
        assert this_month(session, turn.organization_id).used_usd == turn.cost_usd


def test_the_ceiling_refuses_the_next_question_once_it_is_reached(
    world: tuple[FastAPI, sessionmaker[Session], list[dict[str, Any]]],
    caplog: pytest.LogCaptureFixture,
) -> None:
    """One very long question spends past the Starter plan's provisional
    ceiling. The next is refused before a token is spent, in words that do not
    blame the merchant, and the crossing is logged for whoever is on call."""
    app, factory, seen = world
    token = a_merchant(factory, "dana@alphaplumbing.ie")
    with TestClient(app) as client, caplog.at_level("WARNING"):
        ask(client, token, question="An expensive question about a whole year")
        refused = client.post(
            "/v1/otto/ask", headers={"x-session-token": token}, json={"question": "And now?"}
        )
    assert refused.status_code == 429
    assert "limit of what PPCWay spends" in refused.json()["detail"]
    assert "you have spent" not in refused.json()["detail"].lower()
    assert len(seen) == 1, "the refused question never reached the model"
    logged = [one.getMessage() for one in caplog.records]
    assert any("reached its monthly ceiling" in one for one in logged)
    assert any("crossed 80% of its monthly ceiling" in one for one in logged)
    with factory() as session:
        place = session.query(Organization).one()
        assert this_month(session, place.id).spent_out
