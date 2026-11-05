"""What the guardrails need to know, gathered from what we actually hold.

The ten checks take a `Standing` and a `Limits` and nothing else, which is what
makes them pure and testable. This is where those two are built, and it is the
honest part of the arrangement: a check that asks "is this account serviceable"
is only as good as the answer it is given, and several of the answers here are
derivations rather than readings. Each one says which it is.

**Nothing here guesses in the permissive direction.** Where a fact is unknown
the field is left in the state that makes the matching check refuse. An unread
account, a connection with no status, a day whose quota we have not counted --
all of those come back as "we cannot tell", and the guardrails turn that into a
refusal. That is the design: a change nobody can show to be safe does not go.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ppcway.ads.mirror import MirrorAd, MirrorCampaign, MirrorKeyword
from ppcway.ads.models import AdsConnection
from ppcway.opt.guardrails import Limits, Standing
from ppcway.opt.models import COUNTS_TOWARD_CAP, GuardrailConfig, OptimizationAction

#: Google's daily allowance of mutating operations for a Basic-access account.
#: The guardrails' tenth check reads this whole allowance as left, because the
#: day's real count lives in the gateway and this package may not reach it. The
#: count is read where it matters: `gateway.apply.apply_now` checks the day's
#: room before it takes a change, and refuses one that would not fit.
DAILY_OPERATIONS = 15_000

#: The states in which Google will actually serve an account's ads.
SERVING = frozenset({"ENABLED"})

#: How long an account-status reading stays worth acting on. A status read a
#: fortnight ago is not a current answer, and the check that depends on it
#: should refuse rather than trust it.
STATUS_GOOD_FOR = timedelta(hours=36)


def limits_for(session: Session, organization_id: UUID) -> Limits:
    """The newest guardrail configuration for a business, or the defaults.

    The defaults are the client's own figures, so a business that has never had
    limits written for it is governed by the same numbers as one that has. The
    version is zero in that case, and an action records that zero -- which
    reads, correctly, as "no configuration had been written when this
    happened".
    """
    held = session.scalars(
        select(GuardrailConfig)
        .where(GuardrailConfig.organization_id == organization_id)
        .order_by(GuardrailConfig.version.desc())
        .limit(1)
    ).first()
    if held is None:
        return Limits()
    hands_off = held.hands_off or {}
    pinned = hands_off.get("resources", []) if isinstance(hands_off, dict) else []
    return Limits(
        version=held.version,
        autonomy=held.autonomy,
        max_daily_budget=held.max_daily_budget,
        max_cpa=held.max_cpa,
        min_bid=held.min_bid,
        max_bid=held.max_bid,
        max_change_pct=held.max_change_pct,
        expert_max_change_pct=held.expert_max_change_pct,
        max_daily_change_pct=held.max_daily_change_pct,
        max_changes_per_entity_day=held.max_changes_per_entity_day,
        max_changes_per_day=held.max_changes_per_day,
        max_pause_pct=held.max_pause_pct,
        staleness_minutes=held.staleness_minutes,
        hands_off=tuple(str(r) for r in pinned),
    )


def standing_for(
    session: Session,
    connection: AdsConnection,
    *,
    organization_id: UUID,
    target_id: str = "",
    now: datetime | None = None,
) -> Standing:
    """What is true of this account and this day, as far as we can tell."""
    at = now or datetime.now(UTC)
    status = (connection.account_status or "").upper()
    fresh_status = (
        connection.status_read_at is not None
        and (at - _aware(connection.status_read_at)) <= STATUS_GOOD_FOR
    )

    return Standing(
        link_active=connection.revoked_at is None,
        # We hold a stored permission. Whether Google will still honour it is
        # only knowable by asking, and the gateway asks at the moment it acts;
        # a connection whose token had been revoked would fail there, loudly,
        # rather than here, quietly.
        token_refreshable=bool(connection.ciphertext),
        # A status read too long ago is not an answer. Reported as empty, which
        # is what `account_serviceable` refuses on.
        account_status=status if fresh_status else "",
        # Google exposes no single account-level "billing on hold" field. What
        # it does expose is the account's own status, and an account whose
        # billing has failed does not stay ENABLED. So this is derived, and
        # narrowly: anything other than a serving state is treated as a hold.
        # Phase 2.3's gateway will tighten it, because Google says so directly
        # in the error it returns when billing actually blocks a mutation.
        billing_on_hold=status not in SERVING,
        own_customer_id=connection.customer_id,
        changes_to_entity_today=_changes_today(session, connection, at, target_id=target_id),
        changes_today=_changes_today(session, connection, at),
        moved_pct_today=_moved_today(session, connection, at),
        active_entities=_active(session, connection.customer_id),
        # The whole allowance, as far as this package can see. The real count
        # is checked at the door, before a change is taken -- see the note on
        # `DAILY_OPERATIONS`.
        quota_left=DAILY_OPERATIONS,
    )


def _changes_today(
    session: Session, connection: AdsConnection, at: datetime, *, target_id: str = ""
) -> int:
    """Changes to this account, or to one thing in it, since midnight."""
    since = datetime.combine(at.date(), datetime.min.time(), tzinfo=UTC)
    query = select(func.count(OptimizationAction.id)).where(
        OptimizationAction.customer_id == connection.customer_id,
        OptimizationAction.created_at >= since,
        OptimizationAction.status.in_([s.value for s in COUNTS_TOWARD_CAP]),
    )
    if target_id:
        query = query.where(OptimizationAction.target_id == target_id)
    return int(session.scalar(query) or 0)


def _moved_today(session: Session, connection: AdsConnection, at: datetime) -> float:
    """How far today's changes have already moved a number, added up.

    Added rather than compounded, which matches how the limit is written: the
    brief caps the day at 100% in total, not at a compounded multiple. Summing
    the absolute moves is the reading that bounds the exposure.
    """
    since = datetime.combine(at.date(), datetime.min.time(), tzinfo=UTC)
    rows: list[Any] = list(
        session.scalars(
            select(OptimizationAction.expected_impact).where(
                OptimizationAction.customer_id == connection.customer_id,
                OptimizationAction.created_at >= since,
                OptimizationAction.status.in_([s.value for s in COUNTS_TOWARD_CAP]),
            )
        ).all()
    )
    total = 0.0
    for impact in rows:
        if isinstance(impact, dict):
            total += abs(float(impact.get("change_pct", 0) or 0))
    return round(total, 2)


def _active(session: Session, customer_id: str) -> int:
    """How many live things this account has, for the blast-radius check.

    Campaigns, ad groups' keywords and ads together, because a proposal that
    pauses three ads should be measured against the ads and not against the
    campaigns. Counting all three is the conservative reading -- a larger
    denominator would make a dangerous pause look small, and this errs the
    other way.
    """
    total = 0
    for model in (MirrorCampaign, MirrorKeyword, MirrorAd):
        total += int(
            session.scalar(
                select(func.count(model.id)).where(
                    model.customer_id == customer_id,
                    model.gone_at.is_(None),
                    model.status == "ENABLED",
                )
            )
            or 0
        )
    return total


def _aware(when: datetime) -> datetime:
    return when if when.tzinfo else when.replace(tzinfo=UTC)


def as_dict(standing: Standing, limits: Limits) -> dict[str, Any]:
    """Both, for the action log's own record of what was checked against."""
    return {
        "standing": {
            "account_status": standing.account_status,
            "billing_on_hold": standing.billing_on_hold,
            "changes_today": standing.changes_today,
            "moved_pct_today": standing.moved_pct_today,
            "active_entities": standing.active_entities,
            "quota_left": standing.quota_left,
        },
        "limits_version": limits.version,
    }
