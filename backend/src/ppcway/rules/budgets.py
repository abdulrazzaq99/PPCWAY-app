"""R6 and R7: moving money between campaigns by what their leads cost.

R1 judges one search at a time and needs a search that brought nobody. On an
account whose conversion tracking counts nearly every click, no such search
exists, so on 10 November Otto had nothing to say to an owner whose campaigns
plainly differed: one brought leads at 0.40, another at 2.69. These two rules
compare a campaign with the rest of its own account instead, which works
wherever leads are counted at all, however generously.

  R7  a campaign whose leads cost at least twice what the rest of the account
      pays: lower its daily budget by a fifth. Spending less cannot cost more,
      so it is low risk; it can cost leads, so it is a suggestion and says so.

  R6  a campaign whose leads cost at most six tenths of the rest, and which
      Google says loses a fifth or more of its searches to its budget: raise
      the budget by a fifth, never past the account's own daily ceiling. More
      spend is a person's decision, every time.

Both leave alone a campaign still learning (under a week old, or with fewer
than a week of spend), a campaign on a shared budget -- changing it would move
other campaigns' money too -- and any comparison resting on fewer than ten
leads either side. The thresholds are written on the rules in
`rules.catalogue` and recorded in
docs/decisions/2026-11-10-otto-moves-money-between-campaigns.md.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, date, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from ppcway.ads.clock import account_today
from ppcway.ads.mirror import MICRO, CampaignDay, MirrorCampaign
from ppcway.metric.figures import Figure, Period, Scope, Unit
from ppcway.rules.catalogue import Rule, rule
from ppcway.rules.recommend import Impact, Recommendation

#: How far back "loses searches to its budget" is averaged.
RECENT_DAYS = 14
#: A month of days, for "a month" in money.
MONTH = 30.4


@dataclass(slots=True)
class _Spent:
    """One campaign over the window."""

    cost: float = 0.0
    leads: float = 0.0
    days_spent: int = 0
    lost: list[float] = field(default_factory=list)
    as_of: datetime | None = None

    @property
    def cost_per_lead(self) -> float:
        return self.cost / self.leads if self.leads else 0.0


def _aware(when: datetime | None) -> datetime:
    if when is None:
        return datetime.now(UTC)
    return when if when.tzinfo else when.replace(tzinfo=UTC)


def _window(
    session: Session, customer_id: str, today: date, days: int
) -> tuple[Period, dict[str, _Spent]]:
    period = Period.last(days, until=today)
    recent = today - timedelta(days=RECENT_DAYS)
    out: dict[str, _Spent] = {}
    for row in session.scalars(
        select(CampaignDay).where(
            CampaignDay.customer_id == customer_id,
            CampaignDay.day >= period.start,
            CampaignDay.day <= period.end,
        )
    ):
        spent = out.setdefault(row.campaign_id, _Spent())
        spent.cost += (row.cost_micros or 0) / MICRO
        spent.leads += (row.calls or 0.0) + (row.forms or 0.0)
        if (row.cost_micros or 0) > 0:
            spent.days_spent += 1
        if row.day > recent and row.lost_to_budget is not None:
            spent.lost.append(float(row.lost_to_budget))
        when = _aware(row.refreshed_at)
        spent.as_of = max(spent.as_of, when) if spent.as_of else when
    return period, out


def _settled(campaign: MirrorCampaign, spent: _Spent, today: date, need: int) -> bool:
    """Out of Google's learning period: a week old, with a week of spend."""
    if spent.days_spent < need:
        return False
    try:
        started = date.fromisoformat(campaign.starts_at[:10])
    except ValueError:
        return True
    return (today - started).days >= need


def _changeable(session: Session, customer_id: str) -> list[MirrorCampaign]:
    """Live campaigns whose own budget PPCWay can name and change alone."""
    return list(
        session.scalars(
            select(MirrorCampaign).where(
                MirrorCampaign.customer_id == customer_id,
                MirrorCampaign.gone_at.is_(None),
                MirrorCampaign.status == "ENABLED",
                MirrorCampaign.budget_resource != "",
                MirrorCampaign.budget_shared.is_(False),
                MirrorCampaign.budget_micros > 0,
            )
        )
    )


def _ceiling(session: Session, customer_id: str) -> float:
    """The most any campaign may spend a day, as this business set it. Zero if unset."""
    from ppcway.ads.models import AdsConnection
    from ppcway.opt.context import limits_for

    organization_id = session.scalar(
        select(AdsConnection.organization_id)
        .where(AdsConnection.customer_id == customer_id, AdsConnection.revoked_at.is_(None))
        .limit(1)
    )
    if organization_id is None:
        return 0.0
    return float(limits_for(session, organization_id).max_daily_budget or 0.0)


def _money(amount: float, currency: str) -> str:
    return f"{amount:,.2f} {currency}".strip()


def _figures(
    campaign: MirrorCampaign,
    spent: _Spent,
    rest: float,
    period: Period,
    currency: str,
    *,
    lost: float | None = None,
) -> tuple[Figure, ...]:
    scope = Scope(kind="campaign", id=campaign.campaign_id)
    as_of = _aware(spent.as_of)
    found = [
        Figure("campaign_spend", round(spent.cost, 2), Unit.MONEY, period, scope, as_of, currency),
        Figure("campaign_leads", round(spent.leads, 2), Unit.COUNT, period, scope, as_of),
        Figure(
            "campaign_cost_per_lead",
            round(spent.cost_per_lead, 2),
            Unit.MONEY,
            period,
            scope,
            as_of,
            currency,
        ),
        Figure(
            "rest_of_account_cost_per_lead",
            round(rest, 2),
            Unit.MONEY,
            period,
            Scope(kind="account"),
            as_of,
            currency,
        ),
    ]
    if lost is not None:
        found.append(Figure("lost_to_budget", round(lost, 3), Unit.RATIO, period, scope, as_of))
    return tuple(found)


@dataclass(frozen=True, slots=True)
class _Compared:
    campaign: MirrorCampaign
    spent: _Spent
    rest: float


def _compared(
    session: Session, customer_id: str, spec: Rule, today: date
) -> tuple[Period, list[_Compared]]:
    """Every changeable, settled campaign beside what the rest of the account pays."""
    period, spent = _window(session, customer_id, today, int(spec.limits["window_days"]))
    total_cost = sum(s.cost for s in spent.values())
    total_leads = sum(s.leads for s in spent.values())
    least = spec.limits["least_leads"]
    settled = int(spec.limits["settled_days"])
    out: list[_Compared] = []
    for campaign in _changeable(session, customer_id):
        mine = spent.get(campaign.campaign_id)
        if mine is None or mine.leads < least or mine.cost <= 0:
            continue
        if not _settled(campaign, mine, today, settled):
            continue
        rest_leads = total_leads - mine.leads
        if rest_leads < least:
            continue
        out.append(_Compared(campaign, mine, (total_cost - mine.cost) / rest_leads))
    return period, out


def dearest(
    session: Session,
    customer_id: str,
    *,
    currency: str,
    today: date | None = None,
) -> list[Recommendation]:
    """R7: lower the budget of a campaign whose leads cost far more than the rest."""
    spec = rule("R7")
    at = today or account_today(session, customer_id)
    period, compared = _compared(session, customer_id, spec, at)
    step = spec.limits["step_pct"] / 100
    found: list[Recommendation] = []
    for one in compared:
        mine, campaign = one.spent, one.campaign
        if one.rest <= 0 or mine.cost_per_lead < spec.limits["dearer_than"] * one.rest:
            continue
        budget = campaign.budget_micros / MICRO
        new = max(spec.limits["least_budget"], round(budget * (1 - step), 2))
        if new >= budget:
            continue
        times = mine.cost_per_lead / one.rest
        daily = min(budget, mine.cost / period.days)
        saving = round(max(0.0, daily - new) * MONTH, 2)
        name = campaign.name or f"Campaign {campaign.campaign_id}"
        found.append(
            Recommendation(
                rule=spec,
                customer_id=customer_id,
                target_kind="campaign",
                target_id=campaign.campaign_id,
                target_label=name,
                reason=(
                    f"{name}'s leads cost {_money(mine.cost_per_lead, currency)} each over the"
                    f" last {period.days} days, {times:.1f} times the"
                    f" {_money(one.rest, currency)} the rest of your account pays. Lowering its"
                    f" daily budget from {_money(budget, currency)} to {_money(new, currency)}"
                    f" puts less money where leads cost most."
                ),
                impact=Impact(
                    money_a_month=saving,
                    currency=currency,
                    confidence=min(1.0, 0.6 + 0.4 * min(1.0, mine.leads / 50)),
                    words=(
                        f"About {_money(saving, currency)} a month less spent there. Expect"
                        f" fewer leads from this campaign; the ones it still brings should cost"
                        f" about the same or less."
                    ),
                ),
                figures=_figures(campaign, mine, one.rest, period, currency),
                undo=(
                    f"Set the daily budget back to {_money(budget, currency)}. Google uses the"
                    f" amount from the moment it is changed."
                ),
                before={"daily_budget": budget},
                after={"daily_budget": new},
                reversible=True,
                as_of=_aware(mine.as_of),
                new_daily_budget=new,
                change_pct=round((new - budget) / budget * 100, 1),
                resources=(campaign.resource_name, campaign.budget_resource),
                payload={
                    "change": "set_budget",
                    "budget": campaign.budget_resource,
                    "campaign": campaign.resource_name,
                    "amount_micros": round(new * MICRO),
                    "was_micros": int(campaign.budget_micros),
                    "resources": [campaign.resource_name, campaign.budget_resource],
                },
            )
        )
    return found


def held_back(
    session: Session,
    customer_id: str,
    *,
    currency: str,
    today: date | None = None,
    notes: list[dict[str, str]] | None = None,
) -> list[Recommendation]:
    """R6: raise the budget of a cheap campaign that runs out of it.

    Never past the business's own daily ceiling. With no ceiling set, nothing
    is offered -- a budget rise without one is refused by the guardrails
    anyway -- and `notes` says which campaign is waiting for one.
    """
    spec = rule("R6")
    at = today or account_today(session, customer_id)
    period, compared = _compared(session, customer_id, spec, at)
    step = spec.limits["step_pct"] / 100
    ceiling: float | None = None
    found: list[Recommendation] = []
    for one in compared:
        mine, campaign = one.spent, one.campaign
        if not mine.lost or one.rest <= 0:
            continue
        lost = sum(mine.lost) / len(mine.lost)
        if lost < spec.limits["lost_to_budget"]:
            continue
        if mine.cost_per_lead > spec.limits["cheaper_than"] * one.rest:
            continue
        name = campaign.name or f"Campaign {campaign.campaign_id}"
        budget = campaign.budget_micros / MICRO
        if ceiling is None:
            ceiling = _ceiling(session, customer_id)
        why = (
            f"{name} loses {lost * 100:.0f}% of its searches to its budget, while its leads"
            f" cost {_money(mine.cost_per_lead, currency)} each against"
            f" {_money(one.rest, currency)} for the rest of your account."
        )
        if ceiling <= 0:
            if notes is not None:
                notes.append(
                    {
                        "campaign": campaign.campaign_id,
                        "words": (
                            f"{why} Otto would suggest a bigger budget for it, but no daily"
                            f" budget ceiling is set for this account. Set one in Settings and"
                            f" Otto will offer it."
                        ),
                    }
                )
            continue
        new = min(round(budget * (1 + step), 2), ceiling)
        if new <= budget:
            if notes is not None:
                notes.append(
                    {
                        "campaign": campaign.campaign_id,
                        "words": (
                            f"{why} Its budget is already at your daily ceiling of"
                            f" {_money(ceiling, currency)}, so Otto is not suggesting more."
                        ),
                    }
                )
            continue
        more = round((new - budget) * MONTH, 2)
        extra_leads = more / mine.cost_per_lead if mine.cost_per_lead else 0.0
        found.append(
            Recommendation(
                rule=spec,
                customer_id=customer_id,
                target_kind="campaign",
                target_id=campaign.campaign_id,
                target_label=name,
                reason=(
                    f"{why} Raising its daily budget from {_money(budget, currency)} to"
                    f" {_money(new, currency)} lets it answer more of those searches."
                ),
                impact=Impact(
                    money_a_month=0.0,
                    currency=currency,
                    confidence=min(1.0, 0.6 + 0.4 * min(1.0, mine.leads / 50)),
                    words=(
                        f"Up to {_money(more, currency)} a month more spend. At this"
                        f" campaign's own price that is about {extra_leads:.0f} more leads a"
                        f" month, if the searches are there."
                    ),
                ),
                figures=_figures(campaign, mine, one.rest, period, currency, lost=lost),
                undo=(
                    f"Set the daily budget back to {_money(budget, currency)}. Google uses the"
                    f" amount from the moment it is changed."
                ),
                before={"daily_budget": budget},
                after={"daily_budget": new},
                reversible=True,
                as_of=_aware(mine.as_of),
                new_daily_budget=new,
                change_pct=round((new - budget) / budget * 100, 1),
                resources=(campaign.resource_name, campaign.budget_resource),
                payload={
                    "change": "set_budget",
                    "budget": campaign.budget_resource,
                    "campaign": campaign.resource_name,
                    "amount_micros": round(new * MICRO),
                    "was_micros": int(campaign.budget_micros),
                    "resources": [campaign.resource_name, campaign.budget_resource],
                },
            )
        )
    return found
