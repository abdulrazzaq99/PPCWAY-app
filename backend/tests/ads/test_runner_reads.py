"""Which reads each pass makes, and from when.

Search terms and keyword days were mirrored from 30 October and never read:
the runner called the structure read and the day read and nothing else. Every
account's search terms were empty, Otto could not name one, and rule R1 -- the
one change the client lets run unattended -- had nothing to look at. These
tests hold the runner to calling them, on the passes that reach back.

Google is faked at the edge of each read, so this is about the runner's
choices: which reads, from which day, and what the run then says.
"""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime, timedelta
from types import SimpleNamespace
from typing import Any

import pytest
import sqlalchemy as sa
from pydantic import SecretStr
from sqlalchemy.orm import Session, sessionmaker

from ppcway.ads import models as ads_models
from ppcway.ads import runner
from ppcway.ads.mirror import SearchTermDay, term_key
from ppcway.ads.sync import Report, backfill_since
from ppcway.auth.models import UserAccount
from ppcway.db.base import Base
from ppcway.org.models import Organization  # noqa: F401 - a foreign key target

NOW = datetime.now(UTC)
CUSTOMER = "2580586343"

SETTINGS: Any = SimpleNamespace(
    google_ads_developer_token=SecretStr("developer"),
    google_oauth_client_id="client",
    google_oauth_client_secret=SecretStr("secret"),
    google_oauth_token_key=None,
    google_ads_api_version="v25",
    google_ads_login_customer_id=None,
)


@pytest.fixture
def factory() -> sessionmaker[Session]:
    engine = sa.create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=sa.pool.StaticPool
    )
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, expire_on_commit=False, future=True)


@pytest.fixture
def reads(monkeypatch: pytest.MonkeyPatch) -> dict[str, list[date]]:
    """Every read the runner made, by name, with the day it reached back to."""
    made: dict[str, list[date]] = {}

    def fake(name: str, counts: dict[str, int]) -> Any:
        def read(
            session: Session, customer_id: str, *, since: date | None = None, **_: Any
        ) -> Report:
            made.setdefault(name, []).append(since or NOW.date())
            return Report(counts=dict(counts))

        return read

    monkeypatch.setattr(runner, "sync_structure", fake("structure", {"keywords": 40}))
    monkeypatch.setattr(runner, "sync_days", fake("days", {"days": 3, "rows": 6}))
    monkeypatch.setattr(
        runner, "sync_search_terms", fake("search_terms", {"search_terms": 9, "rows": 30})
    )
    monkeypatch.setattr(
        runner, "sync_keyword_days", fake("keyword_days", {"keywords": 12, "rows": 36})
    )

    class Vault:
        def __init__(self, key: Any) -> None:
            pass

        def unlock(self, ciphertext: str) -> str:
            return "refresh"

    monkeypatch.setattr(runner, "TokenVault", Vault)
    monkeypatch.setattr(runner, "fresh_access_token", lambda *a, **k: "access")
    return made


def _connection(session: Session) -> ads_models.AdsConnection:
    person = UserAccount(google_sub=str(uuid.uuid4()), email="dana@alphaplumbing.ca", name="Dana")
    session.add(person)
    session.flush()
    held = ads_models.AdsConnection(account_id=person.id, ciphertext="locked", customer_id=CUSTOMER)
    session.add(held)
    session.commit()
    return held


def _pass(factory: sessionmaker[Session], kind: str) -> Any:
    with factory() as session:
        held = session.scalar(sa.select(ads_models.AdsConnection)) or _connection(session)
        return runner.sync_connection(session, held, SETTINGS, kind=kind, now=NOW)


def test_the_nightly_pass_reads_search_terms_and_keyword_days(
    factory: sessionmaker[Session], reads: dict[str, list[date]]
) -> None:
    run = _pass(factory, "backfill")
    assert run.status == "done"
    assert set(reads) == {"days", "search_terms", "keyword_days"}


def test_an_account_holding_no_search_terms_gets_the_whole_first_window(
    factory: sessionmaker[Session], reads: dict[str, list[date]]
) -> None:
    """Every account connected before these were read has none. Three nights
    of terms would leave a 30-day question with three days to answer from."""
    _pass(factory, "backfill")
    reached = NOW.date() - timedelta(days=runner.FIRST_DAYS)
    assert reads["search_terms"] == [reached]
    assert reads["keyword_days"] == [reached]
    assert reads["days"] == [backfill_since(NOW.date())], "the days are read as before"


def test_once_it_holds_some_the_nightly_pass_reaches_back_three_days(
    factory: sessionmaker[Session], reads: dict[str, list[date]]
) -> None:
    with factory() as session:
        _connection(session)
        session.add(
            SearchTermDay(
                customer_id=CUSTOMER,
                term_hash=term_key("pdf to word"),
                day=NOW.date() - timedelta(days=2),
                term="pdf to word",
                campaign_id="31",
                ad_group_id="41",
                refreshed_at=NOW,
            )
        )
        session.commit()
    _pass(factory, "backfill")
    assert reads["search_terms"] == [backfill_since(NOW.date())]
    assert reads["keyword_days"] == [NOW.date() - timedelta(days=runner.FIRST_DAYS)], (
        "each mirror decides for itself"
    )


def test_the_hourly_and_fifteen_minute_passes_do_not_read_them(
    factory: sessionmaker[Session], reads: dict[str, list[date]]
) -> None:
    """Google settles them a day behind, and every window ends yesterday."""
    _pass(factory, "today")
    _pass(factory, "structure")
    assert "search_terms" not in reads
    assert "keyword_days" not in reads


def test_a_first_pass_and_a_refresh_read_them_too(
    factory: sessionmaker[Session], reads: dict[str, list[date]]
) -> None:
    _pass(factory, "first")
    _pass(factory, "manual")
    assert len(reads["search_terms"]) == 2
    assert len(reads["keyword_days"]) == 2


def test_each_read_keeps_its_own_counts(
    factory: sessionmaker[Session], reads: dict[str, list[date]]
) -> None:
    """Three reads each count "rows", and the keyword read's "keywords" is
    also what the structure read calls the keywords in the account."""
    run = _pass(factory, "manual")
    assert run.counts["keywords"] == 40, "the structure's count survives"
    assert run.counts["rows"] == 6, "the days' rows survive"
    assert run.counts["search_terms"] == 9
    assert run.counts["search_term_rows"] == 30
    assert run.counts["keywords_with_days"] == 12
    assert run.counts["keyword_day_rows"] == 36


def test_a_refused_search_term_read_fails_the_run_and_says_why(
    factory: sessionmaker[Session], reads: dict[str, list[date]], monkeypatch: pytest.MonkeyPatch
) -> None:
    """The same as a refused day read: the jobs screen has to show it."""
    monkeypatch.setattr(
        runner,
        "sync_search_terms",
        lambda *a, **k: Report(ok=False, trouble="Google refused the search term report."),
    )
    run = _pass(factory, "backfill")
    assert run.status == "failed"
    assert run.trouble == "Google refused the search term report."
    assert "keyword_days" in reads, (
        "the two mirrors do not depend on each other, so one refused report"
        " does not leave the other empty for another night"
    )


def _dated(monkeypatch: pytest.MonkeyPatch) -> dict[str, list[tuple[date, date | None]]]:
    """Every read, with the first and last day it asked Google for."""
    asked: dict[str, list[tuple[date, date | None]]] = {}

    def fake(name: str) -> Any:
        def read(
            session: Session,
            customer_id: str,
            *,
            since: date | None = None,
            until: date | None = None,
            **_: Any,
        ) -> Report:
            asked.setdefault(name, []).append((since or NOW.date(), until))
            return Report()

        return read

    for name, attr in (
        ("days", "sync_days"),
        ("search_terms", "sync_search_terms"),
        ("keyword_days", "sync_keyword_days"),
    ):
        monkeypatch.setattr(runner, attr, fake(name))
    return asked


def test_the_hourly_read_asks_for_the_account_s_today_not_utc_s(
    factory: sessionmaker[Session], reads: dict[str, list[date]], monkeypatch: pytest.MonkeyPatch
) -> None:
    """At 02:00 UTC it is still yesterday evening in Toronto. Asking Google for
    the UTC date asked for a day that had not started in the account."""
    asked = _dated(monkeypatch)
    two_utc = datetime.combine(NOW.date(), datetime.min.time(), tzinfo=UTC) + timedelta(hours=2)
    with factory() as session:
        held = _connection(session)
        held.time_zone = "America/Toronto"
        session.commit()
        runner.sync_connection(session, held, SETTINGS, kind="today", now=two_utc)
    toronto_today = NOW.date() - timedelta(days=1)
    assert asked["days"] == [(toronto_today, toronto_today)]


def test_a_zone_read_by_the_structure_pass_is_kept_and_used_at_once(
    factory: sessionmaker[Session], reads: dict[str, list[date]], monkeypatch: pytest.MonkeyPatch
) -> None:
    """A first pass has no zone held yet; the structure read supplies it, and
    the same pass dates its history reads by it."""
    asked = _dated(monkeypatch)
    monkeypatch.setattr(
        runner,
        "sync_structure",
        lambda *a, **k: Report(counts={"campaigns": 2}, time_zone="Asia/Karachi"),
    )
    late_utc = datetime.combine(NOW.date(), datetime.min.time(), tzinfo=UTC) + timedelta(hours=21)
    with factory() as session:
        held = _connection(session)
        runner.sync_connection(session, held, SETTINGS, kind="first", now=late_utc)
        session.refresh(held)
        assert held.time_zone == "Asia/Karachi"
    karachi_today = NOW.date() + timedelta(days=1)
    assert asked["days"] == [(karachi_today - timedelta(days=runner.FIRST_DAYS), karachi_today)]
    assert asked["search_terms"][0][1] == karachi_today
