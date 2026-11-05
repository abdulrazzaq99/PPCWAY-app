"""Running a sync for one connected account, start to finish.

The sync itself knows nothing about our database of people, and the endpoints
should not know about refresh tokens. This is the piece between: it opens the
run, unlocks the permission, asks Google, and closes the run with what it found.

Four kinds, which are the cadence the requirements set:

  first      everything, plus ninety days of history, when an account is connected
  structure  what the account is made of, every fifteen minutes
  today      this day's numbers, hourly
  backfill   the previous three days, nightly, because conversions arrive late
  manual     structure and the last three days, when somebody presses refresh

The passes that reach back -- first, backfill and manual -- also read the two
mirrors the rules and Otto read: the words people actually typed, and what each
keyword did each day. They were built on 30 October and never read: nothing
called them, so every account's search terms were empty, Otto could not name a
single one, and the one rule the client lets run unattended had nothing to look
at. Not hourly: Google settles them a day behind, and every window that reads
them ends yesterday.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from ppcway.ads.mirror import KeywordDay, SearchTermDay, SyncRun
from ppcway.ads.models import AdsConnection
from ppcway.ads.oauth import (
    AdsConnectionRefused,
    TokenVault,
    VaultUnavailable,
    fresh_access_token,
)
from ppcway.ads.sync import (
    Report,
    backfill_since,
    finish,
    record,
    sync_days,
    sync_keyword_days,
    sync_search_terms,
    sync_structure,
)
from ppcway.config import Settings

log = logging.getLogger(__name__)

#: What a new account gets: enough history for "against the previous period" and
#: the year-on-year column, without asking Google for years nobody will look at.
FIRST_DAYS = 90

#: The passes that also read search terms and keyword days.
REACHING_BACK = ("first", "backfill", "manual")

#: What those two reads are called in a run's counts. Each read counts its own
#: "rows", and the keyword read its "keywords", which is also what the
#: structure read calls the keywords in the account; kept under their own
#: names so one does not quietly overwrite another on the jobs screen.
_COUNTED_AS = {
    "search_terms": {"search_terms": "search_terms", "rows": "search_term_rows"},
    "keyword_days": {"keywords": "keywords_with_days", "rows": "keyword_day_rows"},
}

#: What each kind is called while it runs, in the words the waiting screen shows.
STAGES = {
    "structure": "Reading your campaigns, keywords and ads",
    "history": "Reading your history, day by day",
}


def live_connections(session: Session) -> list[AdsConnection]:
    """Every connection we may read: granted, not revoked, and told which account."""
    return list(
        session.scalars(
            select(AdsConnection).where(
                AdsConnection.revoked_at.is_(None),
                AdsConnection.customer_id != "",
            )
        )
    )


def sync_connection(
    session: Session,
    connection: AdsConnection,
    settings: Settings,
    *,
    kind: str = "structure",
    now: datetime | None = None,
    run: SyncRun | None = None,
) -> SyncRun:
    """One pass over one account, recorded whether it works or not.

    A refusal is written on the run rather than raised. The scheduler reads a
    hundred accounts in a loop, and one merchant who has withdrawn their
    permission must not stop the other ninety-nine from syncing.

    `run` is for the endpoint that opened a row before answering, so somebody
    polling sees one pass rather than two.
    """
    at = now or datetime.now(UTC)
    run = run or record(session, connection.customer_id, kind, STAGES["structure"])

    if settings.google_ads_developer_token is None:
        return finish(session, run, Report(ok=False, trouble="Reading Google Ads is not set up."))
    if not (settings.google_oauth_client_id and settings.google_oauth_client_secret):
        return finish(session, run, Report(ok=False, trouble="Reading Google Ads is not set up."))

    try:
        vault = TokenVault(
            settings.google_oauth_token_key.get_secret_value()
            if settings.google_oauth_token_key
            else None
        )
        access = fresh_access_token(
            vault.unlock(connection.ciphertext),
            client_id=settings.google_oauth_client_id,
            client_secret=settings.google_oauth_client_secret.get_secret_value(),
        )
    except (AdsConnectionRefused, VaultUnavailable) as exc:
        log.warning("sync could not open %s: %s", connection.customer_id, exc)
        return finish(session, run, Report(ok=False, trouble=str(exc)))

    keys = {
        "access_token": access,
        "developer_token": settings.google_ads_developer_token.get_secret_value(),
        "api_version": settings.google_ads_api_version,
        "login_customer_id": settings.google_ads_login_customer_id,
    }
    report = Report()
    try:
        if kind in ("first", "structure", "manual"):
            report = sync_structure(session, connection.customer_id, now=at, **keys)  # type: ignore[arg-type]
        if kind in ("first", "today", "backfill", "manual") and report.ok:
            run.stage = STAGES["history"]
            session.commit()
            since = {
                "first": at.date() - timedelta(days=FIRST_DAYS),
                "today": at.date(),
                "backfill": backfill_since(at.date()),
                # A person pressing refresh means "now", but late conversions
                # land on the days behind it, so those are re-read too.
                "manual": backfill_since(at.date()),
            }[kind]
            days = sync_days(session, connection.customer_id, since=since, now=at, **keys)  # type: ignore[arg-type]
            report = Report(
                ok=report.ok and days.ok,
                trouble=report.trouble or days.trouble,
                counts={**report.counts, **days.counts},
                changes=report.changes,
                account_status=report.account_status,
            )
            if kind in REACHING_BACK and report.ok:
                for name, read, held_as in (
                    ("search_terms", sync_search_terms, SearchTermDay),
                    ("keyword_days", sync_keyword_days, KeywordDay),
                ):
                    # An account holding none yet -- every account connected
                    # before these were read at all -- gets the whole first
                    # window, so a 30-day question has 30 days to answer from.
                    holds = (
                        session.scalar(
                            select(held_as.id)
                            .where(held_as.customer_id == connection.customer_id)
                            .limit(1)
                        )
                        is not None
                    )
                    reach = since if holds else at.date() - timedelta(days=FIRST_DAYS)
                    got = read(session, connection.customer_id, since=reach, now=at, **keys)  # type: ignore[arg-type]
                    renamed = _COUNTED_AS[name]
                    report = Report(
                        ok=report.ok and got.ok,
                        trouble=report.trouble or got.trouble,
                        counts={
                            **report.counts,
                            **{renamed.get(key, key): n for key, n in got.counts.items()},
                        },
                        changes=report.changes,
                        account_status=report.account_status,
                    )
    except AdsConnectionRefused as exc:
        log.warning("sync refused for %s: %s", connection.customer_id, exc)
        report = Report(ok=False, trouble=str(exc))

    if report.account_status:
        # Written here rather than in the sync, which does not own this row.
        # Stamped with the time so a guardrail can tell a state we just read
        # from one we happen to still be holding from a fortnight ago.
        connection.account_status = report.account_status
        connection.status_read_at = datetime.now(UTC)

    return finish(session, run, report, now=datetime.now(UTC))


def sync_one(
    connection_id: UUID,
    settings: Settings,
    factory: sessionmaker[Session],
    kind: str = "first",
    run_id: UUID | None = None,
) -> None:
    """The same, in its own session, for a background task to call."""
    with factory() as session:
        connection = session.get(AdsConnection, connection_id)
        if connection is None or not connection.customer_id:
            return
        opened = session.get(SyncRun, run_id) if run_id else None
        sync_connection(session, connection, settings, kind=kind, run=opened)


def sync_everyone(
    settings: Settings, factory: sessionmaker[Session], kind: str = "structure"
) -> dict[str, int]:
    """Every connected account, one after another, for the scheduler."""
    done = {"accounts": 0, "failed": 0, "changes": 0}
    with factory() as session:
        connections = live_connections(session)
    for connection in connections:
        with factory() as session:
            held = session.get(AdsConnection, connection.id)
            if held is None:
                continue
            run = sync_connection(session, held, settings, kind=kind)
            done["accounts"] += 1
            done["failed"] += 1 if run.status == "failed" else 0
            done["changes"] += int(run.counts.get("changes", 0) or 0)
    return done
