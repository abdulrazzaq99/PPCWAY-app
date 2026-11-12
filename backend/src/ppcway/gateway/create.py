"""Creating several things in Google at once: a new campaign, through the one door.

`apply_now` makes one approved change. This makes a whole new campaign, which
is a different shape -- a budget, a campaign, its places, ad groups, keywords
and ads, all pointing at each other -- and Google takes it as one request that
lands whole or not at all. The order here is the same discipline:

1. **The switches**, read now: the write gate and both kill switches. A launch
   refused here created nothing and can simply be pressed again later.
2. **Room in the day's quota**, read before anything is sent.
3. **Google checks it first.** The whole request goes once with
   `validateOnly`, so a refused headline, an unknown place or a duplicate name
   is found while nothing exists. Every launch does this; it costs one request
   and spares the merchant a campaign that half-happened in their head.
4. **Counted, then created.** The operations are counted against the day
   before the real request, for the reason `quota` gives: the honest error is
   to believe we used slightly more than we did.

A campaign the merchant built and launched is not an automated change, so the
guardrails' rules for changes Otto proposes -- the weekly cap, the spend
ceilings -- do not decide whether it goes. The merchant does. The switches
still apply, because "stop every write" has to mean every write.
"""

from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from ppcway.gateway import quota, switch
from ppcway.gateway.apply import CannotApply
from ppcway.gateway.port import Applied, Batch, Builds, Created, Door, Together


def create_together(
    session: Session,
    together: Together,
    *,
    door: Builds,
    gate_open: bool,
    now: datetime | None = None,
) -> Created:
    """Check, count and create. Raises `CannotApply` when it must not be sent,
    and `GoogleRefused` with Google's reason when Google will not have it."""
    at = now or datetime.now(UTC)

    standing = switch.may_write(session, customer_id=together.customer_id, gate_open=gate_open)
    if not standing.may_write:
        raise CannotApply(standing.because)

    if quota.room_today(session, together.customer_id, today=at.date()).left < together.how_many:
        raise CannotApply(
            "This account has used its Google Ads allowance for today. Try again tomorrow."
        )

    door.mutate_together(replace(together, validate_only=True))

    quota.spend(session, together.customer_id, together.how_many, today=at.date())
    session.commit()
    return door.mutate_together(replace(together, validate_only=False))


def check_together(together: Together, *, door: Builds) -> Created:
    """Google's check of a whole request, creating nothing.

    The review step's "is this ready?" before the merchant presses publish.
    Nothing is written, so neither the switches nor the quota stop it; a
    refusal comes back as `GoogleRefused`, with every problem Google named.
    """
    return door.mutate_together(replace(together, validate_only=True))


def create_alone(
    session: Session,
    batch: Batch,
    *,
    door: Door,
    gate_open: bool,
    now: datetime | None = None,
) -> Applied:
    """One kind of thing created at its own service, behind the same switches.

    For what Google keeps out of the all-or-nothing request: the goals behind
    new-customer bidding exist only at `GoalService` and
    `CampaignGoalConfigService`, and only once the campaign does.
    """
    at = now or datetime.now(UTC)
    standing = switch.may_write(session, customer_id=batch.customer_id, gate_open=gate_open)
    if not standing.may_write:
        raise CannotApply(standing.because)
    if quota.room_today(session, batch.customer_id, today=at.date()).left < batch.how_many:
        raise CannotApply(
            "This account has used its Google Ads allowance for today. Try again tomorrow."
        )
    quota.spend(session, batch.customer_id, batch.how_many, today=at.date())
    session.commit()
    return door.mutate(batch)
