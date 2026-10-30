"""The prompt log: written whatever happened, redacted on the way in, forgotten."""

from __future__ import annotations

import uuid
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta

import pytest
import sqlalchemy as sa
from sqlalchemy.orm import Session, sessionmaker

from ppcway.db.base import Base
from ppcway.model.jobs import SONNET, Job
from ppcway.model.log import KEEP_DAYS, PromptLog, forget_old, record

NOW = datetime(2026, 10, 30, 12, 0, tzinfo=UTC)


@pytest.fixture
def db() -> Iterator[sessionmaker[Session]]:
    engine = sa.create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=sa.pool.StaticPool
    )
    Base.metadata.create_all(engine)
    yield sessionmaker(bind=engine, expire_on_commit=False, future=True)
    Base.metadata.drop_all(engine)


def test_the_text_is_redacted_before_it_is_stored(db: sessionmaker[Session]) -> None:
    """Not on the way out: a redaction applied at read time never reached the backup."""
    with db() as session:
        record(
            session,
            job=Job.CHAT.value,
            model=SONNET,
            prompt_version="otto-1",
            system="You explain Google Ads.",
            asked="I am dana@alphaplumbing.ca, ring me on +353 1 234 5678",
            answered="I will not share that.",
        )
        session.commit()
        row = session.scalars(sa.select(PromptLog)).one()

    assert "dana@alphaplumbing.ca" not in row.input_text
    assert "[email]" in row.input_text and "[phone]" in row.input_text


def test_a_failed_call_is_written_too(db: sessionmaker[Session]) -> None:
    """A log of successes answers no question worth asking."""
    with db() as session:
        record(
            session,
            job=Job.AD_DRAFT.value,
            model=SONNET,
            prompt_version="otto-1",
            asked="draft ads",
            stop_reason="",
            trouble="the model could not be reached: 502",
        )
        session.commit()
        row = session.scalars(sa.select(PromptLog)).one()

    assert row.trouble.startswith("the model could not be reached")
    assert row.output_text == ""


def test_a_refusal_is_legible(db: sessionmaker[Session]) -> None:
    with db() as session:
        record(
            session,
            job=Job.CHAT.value,
            model=SONNET,
            prompt_version="otto-1",
            stop_reason="refusal",
            armor="clean",
        )
        session.commit()
        assert session.scalars(sa.select(PromptLog)).one().stop_reason == "refusal"


def test_what_it_cost_and_what_cached_are_kept(db: sessionmaker[Session]) -> None:
    """Zero cached tokens across a run of requests is how a broken prefix shows up."""
    with db() as session:
        record(
            session,
            job=Job.CHAT.value,
            model=SONNET,
            prompt_version="otto-1",
            input_tokens=1200,
            output_tokens=90,
            cached_tokens=1024,
            took_ms=1430,
        )
        session.commit()
        row = session.scalars(sa.select(PromptLog)).one()

    assert (row.input_tokens, row.output_tokens, row.cached_tokens, row.took_ms) == (
        1200,
        90,
        1024,
        1430,
    )


def test_everything_past_the_window_is_forgotten(db: sessionmaker[Session]) -> None:
    """Thirty days, by a job rather than by intention."""
    with db() as session:
        for days in (0, 1, KEEP_DAYS - 1, KEEP_DAYS + 1, KEEP_DAYS * 2):
            session.add(
                PromptLog(
                    id=uuid.uuid4(),
                    job=Job.INTERNAL.value,
                    model=SONNET,
                    prompt_version="otto-1",
                    created_at=NOW - timedelta(days=days),
                )
            )
        session.commit()

        gone = forget_old(session, now=NOW)
        session.commit()
        left = session.scalars(sa.select(PromptLog)).all()

    assert gone == 2, "the two older than thirty days, and only those"
    assert len(left) == 3


def test_the_boundary_is_not_off_by_a_day(db: sessionmaker[Session]) -> None:
    with db() as session:
        session.add(
            PromptLog(
                id=uuid.uuid4(),
                job=Job.INTERNAL.value,
                model=SONNET,
                prompt_version="otto-1",
                created_at=NOW - timedelta(days=KEEP_DAYS) + timedelta(minutes=1),
            )
        )
        session.commit()
        assert forget_old(session, now=NOW) == 0, "a row one minute inside the window stays"
