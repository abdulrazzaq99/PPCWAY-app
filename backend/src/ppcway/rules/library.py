"""The two rules the client has specified, and nothing invented beside them.

R1 and R4. See `catalogue` for why R2, R3 and R5 are declared and empty.

Both read the mirror and never Google. That is the point of the mirror: a rule
that called the API would be a rule whose answer depended on quota, and a
nightly pass over every account would spend the day's quota deciding whether to
spend it.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, date, datetime
from typing import Final

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ppcway.ads.mirror import MICRO, MirrorAd, SearchTermDay
from ppcway.metric.figures import Figure, Period, Scope, Unit
from ppcway.rules.catalogue import rule
from ppcway.rules.recommend import Impact, Recommendation

#: Google's own average month, for turning a window's waste into a monthly
#: figure a merchant can weigh against their budget.
MONTH: Final = 30.4

#: Approval states in which an ad is actually capable of being shown.
SERVING: Final = frozenset({"APPROVED", "APPROVED_LIMITED", ""})


@dataclass(frozen=True, slots=True)
class Wasteful:
    """One search term, summed over the window."""

    term: str
    term_hash: str
    campaign_id: str
    ad_group_id: str
    status: str
    clicks: int
    spend: float
    conversions: float
    as_of: datetime


def _confidence(ratio: float) -> float:
    """How sure a finding is, from how far past the minimum its data goes.

    At the brief's own minimum -- 1.5 times the target cost per lead in spend,
    or a hundred clicks -- this is 0.6, not 1.0. Meeting the minimum is what
    makes a finding allowed, not what makes it certain, and a card that claimed
    certainty from the least data that qualifies would be overstating itself on
    exactly the findings most likely to be wrong.
    """
    return min(1.0, 0.6 + 0.4 * max(0.0, ratio - 1.0))


def wasteful_terms(
    session: Session,
    customer_id: str,
    *,
    currency: str,
    target_cost_per_lead: float,
    today: date | None = None,
    protected: Sequence[str] = (),
    blocked: Sequence[str] = (),
) -> list[Recommendation]:
    """R1: searches that cost money and never led to anybody getting in touch.

    `target_cost_per_lead` is the account's own target. The client owes us these
    per plan; until they arrive a caller passes the account's own average, which
    is a weaker threshold in the safe direction -- it takes more waste to
    qualify, not less.

    `protected` is the brand terms a merchant never wants excluded, and
    `blocked` the client's own list. Both are matched loosely, as substrings of
    the search term, because "alpha plumbing ennis" has to be protected by
    "alpha plumbing" and an exact match would protect nothing.
    """
    spec = rule("R1")
    at = today or datetime.now(UTC).date()
    window = Period.last(int(spec.limits["window_days"]), until=at)

    rows = session.execute(
        select(
            SearchTermDay.term_hash,
            func.max(SearchTermDay.term).label("term"),
            func.max(SearchTermDay.campaign_id).label("campaign_id"),
            func.max(SearchTermDay.ad_group_id).label("ad_group_id"),
            func.sum(SearchTermDay.clicks).label("clicks"),
            func.sum(SearchTermDay.cost_micros).label("cost_micros"),
            func.sum(SearchTermDay.conversions).label("conversions"),
            func.max(SearchTermDay.refreshed_at).label("as_of"),
        )
        .where(
            SearchTermDay.customer_id == customer_id,
            SearchTermDay.day >= window.start,
            SearchTermDay.day <= window.end,
        )
        .group_by(SearchTermDay.term_hash)
    ).all()

    # The status of the most recent day, not of any day: a term added as a
    # keyword last week is handled now, whatever it was a fortnight ago.
    latest = {
        term_hash: status
        for term_hash, status in session.execute(
            select(SearchTermDay.term_hash, SearchTermDay.status)
            .where(
                SearchTermDay.customer_id == customer_id,
                SearchTermDay.day >= window.start,
                SearchTermDay.day <= window.end,
            )
            .order_by(SearchTermDay.day.asc())
        ).all()
    }

    enough_clicks = spec.limits["enough_clicks"]
    multiple = spec.limits["wasted_multiple_of_target"]
    least = spec.limits["least_wasted"]
    worth_losing = multiple * target_cost_per_lead if target_cost_per_lead > 0 else 0.0

    found: list[Recommendation] = []
    for row in rows:
        spend = round((row.cost_micros or 0) / MICRO, 2)
        clicks = int(row.clicks or 0)
        conversions = float(row.conversions or 0)
        term = str(row.term or "")

        if conversions > 0:
            continue
        if latest.get(row.term_hash, "") in {"ADDED", "EXCLUDED", "ADDED_EXCLUDED"}:
            continue
        if spend < least:
            continue
        if _is_protected(term, protected, blocked):
            continue

        by_clicks = clicks / enough_clicks if enough_clicks else 0.0
        by_spend = spend / worth_losing if worth_losing else 0.0
        ratio = max(by_clicks, by_spend)
        if ratio < 1.0:
            continue

        as_of = _aware(row.as_of)
        scope = Scope(kind="search_term", id=row.term_hash[:12])
        evidence = tuple(
            figure.cite()
            for figure in (
                Figure(
                    name="search_term_spend",
                    value=spend,
                    unit=Unit.MONEY,
                    currency=currency,
                    period=window,
                    scope=scope,
                    as_of=as_of,
                ),
                Figure(
                    name="search_term_clicks",
                    value=float(clicks),
                    unit=Unit.COUNT,
                    period=window,
                    scope=scope,
                    as_of=as_of,
                ),
                Figure(
                    name="search_term_leads",
                    value=0.0,
                    unit=Unit.COUNT,
                    period=window,
                    scope=scope,
                    as_of=as_of,
                ),
            )
        )
        a_month = round(spend * (MONTH / window.days), 2)
        found.append(
            Recommendation(
                rule=spec,
                customer_id=customer_id,
                target_kind="search_term",
                target_id=row.term_hash,
                target_label=term,
                reason=(
                    f'People searching for "{term}" clicked {clicks} '
                    f"{'time' if clicks == 1 else 'times'} in the last "
                    f"{window.days} days and cost you {spend:,.2f} {currency}. "
                    f"None of them got in touch."
                ),
                impact=Impact(
                    money_a_month=a_month,
                    currency=currency,
                    confidence=_confidence(ratio),
                    words=(
                        f"Excluding it stops about {a_month:,.2f} {currency} a month "
                        f"going on this search. Some of that spend may move to better "
                        f"searches rather than disappear."
                    ),
                ),
                evidence=evidence,
                undo=(
                    "Remove the negative keyword and this search can match your ads "
                    "again from that moment. The clicks you did not pay for in between "
                    "do not come back."
                ),
                before={"excluded": False},
                after={"excluded": True, "match_type": "EXACT", "level": "ad_group"},
                reversible=True,
                as_of=as_of,
                resources=(f"customers/{customer_id}/adGroups/{row.ad_group_id}",),
            )
        )
    return found


def _is_protected(term: str, protected: Sequence[str], blocked: Sequence[str]) -> bool:
    """Whether this term must be left alone, or must never be proposed at all.

    Loose, on purpose: "alpha plumbing" has to protect "alpha plumbing ennis",
    and an exact match would protect nothing anybody actually searched for.
    """
    lowered = term.lower()
    return any(word.lower() in lowered for word in (*protected, *blocked) if word)


def disapproved_ads(
    session: Session,
    customer_id: str,
    *,
    currency: str,
    today: date | None = None,
) -> list[Recommendation]:
    """R4: ads Google has refused, which are costing nothing and doing nothing.

    Pause only, per the client's brief. A disapproved ad is already not being
    shown, which is exactly why pausing it is low risk: it cannot cost traffic
    that was being got. What it can do is hide a real problem -- an ad group
    whose only ad has been refused is an ad group showing nothing at all -- so
    that case is marked blocking and sorts ahead of any saving.
    """
    spec = rule("R4")
    at = today or datetime.now(UTC).date()
    window = Period.last(1, until=at)

    live = session.scalars(
        select(MirrorAd).where(MirrorAd.customer_id == customer_id, MirrorAd.gone_at.is_(None))
    ).all()
    serving_in: dict[str, int] = {}
    for ad in live:
        if ad.status == "ENABLED" and ad.approval in SERVING:
            serving_in[ad.ad_group_id] = serving_in.get(ad.ad_group_id, 0) + 1

    found: list[Recommendation] = []
    for ad in live:
        if ad.approval != "DISAPPROVED" or ad.status != "ENABLED":
            continue
        alone = serving_in.get(ad.ad_group_id, 0) == 0
        as_of = _aware(ad.seen_at)
        headline = (ad.headlines or [""])[0] if ad.headlines else ""
        label = headline or f"Ad {ad.ad_id}"
        found.append(
            Recommendation(
                rule=spec,
                customer_id=customer_id,
                target_kind="ad",
                target_id=ad.ad_id,
                target_label=label,
                reason=(
                    "Google has refused this ad, so it is not being shown to anybody."
                    + (
                        " It is the only ad in its group, so that group is showing nothing at all."
                        if alone
                        else " Your other ads in the group are still running."
                    )
                ),
                impact=Impact(
                    money_a_month=0.0,
                    currency=currency,
                    # Google told us it is refused. That is a fact rather than
                    # an inference, so there is nothing to be unsure about.
                    confidence=1.0,
                    words=(
                        "This group cannot show an ad until one is approved, so it is"
                        " getting none of the traffic it is budgeted for."
                        if alone
                        else "Nothing is being lost. Pausing it keeps the account tidy"
                        " and stops it looking live."
                    ),
                    blocking=alone,
                ),
                evidence=(
                    Figure(
                        name="ad_approval",
                        value=0.0,
                        unit=Unit.COUNT,
                        period=window,
                        scope=Scope(kind="ad", id=ad.ad_id),
                        as_of=as_of,
                        notes={"approval": ad.approval, "status": ad.status},
                    ).cite(),
                ),
                undo=(
                    "Turn the ad back on. It stays refused until its wording is"
                    " changed, so it still will not be shown."
                ),
                before={"status": ad.status},
                after={"status": "PAUSED"},
                reversible=True,
                as_of=as_of,
                pauses=1,
                resources=(ad.resource_name,),
            )
        )
    return found


def _aware(when: datetime | None) -> datetime:
    """A timestamp with a zone, because SQLite hands back naive ones."""
    if when is None:
        return datetime.now(UTC)
    return when if when.tzinfo else when.replace(tzinfo=UTC)
