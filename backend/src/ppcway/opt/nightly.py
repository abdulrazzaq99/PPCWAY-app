"""The pass that makes everything else happen: once a night, every account.

Until this existed, phases 1 and 2 were a working engine nobody started. Each
piece had tests and none of them ran in production, which is the quietest way
for six weeks of work to be worth nothing.

**The order matters and is the order below.**

1. **Expire first.** An offer past its week is expired before anything new is
   written, because the ten-a-week cap counts what is waiting -- so leaving
   stale offers in place would use up a merchant's allowance with cards nobody
   is going to answer.
2. **Run the rules, write what they found.** Each recommendation is judged by
   the guardrails and written to the log before anything is applied. Nothing is
   applied here at all: the write gate is a separate decision and is shut.
3. **Write the words before the row, not after.** The model turns each card's
   computed sentence into something warmer and the number check throws it away
   if it invents a figure -- but this happens *before* the row is written,
   because `reason` is write-once at the database and a card polished
   afterwards would be refused by our own append-only trigger. Which is the
   trigger working: what a merchant was told is not a thing to rewrite later.
   Done in this pass rather than when the inbox is opened, so opening the
   inbox never waits on a model.
4. **Forget what is past keeping.** Prompt logs at thirty days, transcripts at
   twelve months.

**One account's failure must not stop the rest.** A hundred accounts are read
in a loop and one merchant with a revoked permission must not cost the other
ninety-nine their night. Every account is wrapped, and what went wrong is
recorded against that account rather than raised.

**Nothing here applies a change.** Phase 2.3's gateway is the only thing that
can, and this does not call it: applying is gated on the write gate, the kill
switches and a consent record, and a nightly job that quietly started writing
to Google the day a flag flipped would be the wrong shape entirely. When writes
open, applying becomes its own pass with its own report.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field, replace
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from ppcway.ads.models import AdsConnection
from ppcway.ads.numbers import account_numbers
from ppcway.chat.transcript import forget_old as forget_transcripts
from ppcway.config import Settings
from ppcway.model.log import forget_old as forget_prompts
from ppcway.model.service import Models
from ppcway.opt.context import limits_for, standing_for
from ppcway.opt.guardrails import judge
from ppcway.opt.models import ProposedBy
from ppcway.opt.record import expire_old, write_proposal
from ppcway.rules.engine import run as run_rules
from ppcway.rules.words import reason_for

log = logging.getLogger(__name__)


@dataclass
class Night:
    """What one pass did, in the words a log reader and a screen both need."""

    ran_at: datetime
    accounts: int = 0
    expired: int = 0
    proposed: int = 0
    refused: int = 0
    #: Which guardrail refused, and how many times. A bare count hides the one
    #: thing an operator needs: "every proposal on every account was refused by
    #: account_serviceable" is a deployment problem, and "three were refused by
    #: delta_limits" is the system working.
    refused_because: dict[str, int] = field(default_factory=dict)
    worded: int = 0
    forgot_prompts: int = 0
    forgot_transcripts: int = 0
    #: One line per account that went wrong, so a failure is attributable
    #: rather than a count.
    trouble: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {
            "ran_at": self.ran_at.isoformat(),
            "accounts": self.accounts,
            "expired": self.expired,
            "proposed": self.proposed,
            "refused": self.refused,
            "refused_because": dict(self.refused_because),
            "worded": self.worded,
            "forgot_prompts": self.forgot_prompts,
            "forgot_transcripts": self.forgot_transcripts,
            "trouble": list(self.trouble),
        }


def tonight(
    factory: sessionmaker[Session],
    settings: Settings,
    *,
    models: Models | None = None,
    now: datetime | None = None,
) -> Night:
    """One pass over every connected account. Writes proposals, applies nothing."""
    at = now or datetime.now(UTC)
    night = Night(ran_at=at)

    with factory() as session:
        night.expired = expire_old(session, now=at)
        session.commit()

        connections = session.scalars(
            select(AdsConnection).where(
                AdsConnection.revoked_at.is_(None),
                AdsConnection.customer_id != "",
                AdsConnection.organization_id.is_not(None),
            )
        ).all()

    seen: set[tuple[UUID, str]] = set()
    for connection in connections:
        place = connection.organization_id
        if place is None or (place, connection.customer_id) in seen:
            continue
        seen.add((place, connection.customer_id))
        night.accounts += 1
        try:
            _one_account(factory, settings, connection, place, night, models, at)
        except Exception as exc:
            # Deliberately broad. One merchant's broken permission must not
            # cost the other ninety-nine their night, and the account it
            # happened to is named rather than counted.
            log.exception("the nightly pass failed for %s", connection.customer_id)
            night.trouble.append(f"{connection.customer_id}: {exc}")

    with factory() as session:
        night.forgot_prompts = forget_prompts(session, now=at)
        night.forgot_transcripts = forget_transcripts(session, now=at)
        session.commit()

    log.info("nightly pass: %s", night.as_dict())
    return night


def _one_account(
    factory: sessionmaker[Session],
    settings: Settings,
    connection: AdsConnection,
    place: UUID,
    night: Night,
    models: Models | None,
    at: datetime,
) -> None:
    """Find, judge and write for one account. Its own session, so a failure
    here rolls back this account and leaves the others alone."""
    with factory() as session:
        held = account_numbers(
            session, connection.customer_id, currency=connection.currency, today=at.date()
        )
        found = run_rules(
            session,
            connection.customer_id,
            currency=connection.currency,
            target_cost_per_lead=held.cost_per_lead,
            today=at.date(),
            now=at,
            protected=tuple(word for word in (connection.customer_name,) if word and len(word) > 2),
        )
        if not found.ok:
            night.trouble.append(f"{connection.customer_id}: {found.stopped}")
            return

        limits = limits_for(session, place)
        for found_card in found.offered:
            # The words first, then the row. `reason` is write-once at the
            # database -- the append-only trigger refuses a second write to it
            # -- so a card polished after being written would be refused by
            # our own guard. Which is the guard working: what a merchant was
            # told is not something to be rewritten later.
            card = found_card
            if models is not None:
                written = reason_for(models, found_card)
                if not written.is_ours:
                    card = replace(found_card, reason=written.text)
                    night.worded += 1

            said = judge(
                card.to_proposal(),
                standing_for(
                    session,
                    connection,
                    organization_id=place,
                    target_id=card.target_id,
                    now=at,
                ),
                limits,
                now=at,
            )
            row = write_proposal(
                session,
                card,
                said,
                organization_id=place,
                guardrail_config_version=limits.version,
                proposed_by=ProposedBy.RULE.value,
                job_run=f"nightly-{at.date().isoformat()}",
                auto_apply_flag=settings.otto_auto_apply,
                now=at,
            )
            if row.status == "rejected":
                night.refused += 1
                which = said.ruling.check or "unknown"
                night.refused_because[which] = night.refused_because.get(which, 0) + 1
            else:
                night.proposed += 1
        session.commit()
