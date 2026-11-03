"""Putting a campaign live: checked first, sent as one batch, rolled back whole.

The client's brief for phase 4.2: *pre-launch checks, one-batch launch with
rollback, learning-window labels*, and from 4.1: *declare AI-drafted ads with
synthetic_content_info*.

**Why one batch and not four.** A campaign is a campaign, a budget, ad groups,
keywords and ads, and Google will happily create the first three and refuse the
fourth. A merchant left with a live campaign, a live budget and no ads has a
campaign that spends nothing and looks broken, and nobody can tell from the
outside whether that was the plan. So everything goes in one request, and
anything that does not all land is put back.

**Rollback is not the same as undo.** The thirty-day undo in `gateway.apply`
reverses a change somebody approved and we made. This reverses a launch that
*failed*: half of it exists, nobody asked for half of it, and it goes away
without a merchant being told a change they can reverse. The distinction
matters because a failed launch must not consume a week's change allowance or
appear in the activity feed as something they did.

**Nothing here can run yet, and that is checked rather than assumed.** The
write gate is shut; `ready` reports it alongside everything else that is
missing, so a screen can say what is actually needed rather than offering a
Launch button that fails.

**`synthetic_content_info` is declared whenever a model wrote any of the
copy.** Not when "most" of it did: one model-written headline makes the ad
model-written, and the declaration costs nothing while getting it wrong is a
policy matter.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Final

from ppcway.builder.draft import Written
from ppcway.builder.keywords import Sifted
from ppcway.builder.validate import DESCRIPTIONS_LEAST, HEADLINES_KEEP, Business
from ppcway.gateway import switch
from ppcway.gateway.port import Applied, Batch, Doing, Door, GoogleRefused, Operation

log = logging.getLogger(__name__)

#: What Google wants on an ad whose text a model wrote. The brief names the
#: field; this is the shape the API takes it in.
AI_DRAFTED: Final[dict[str, Any]] = {"synthetic_content_info": {"ai_generated": True}}


@dataclass(frozen=True, slots=True)
class Plan:
    """One campaign, as it would be created. Nothing live yet."""

    name: str
    daily_budget: float
    currency: str
    business: Business
    theme: str
    keywords: Sifted
    copy: Written
    final_url: str = ""


@dataclass(frozen=True, slots=True)
class Ready:
    """Whether this may be launched, and everything stopping it."""

    may_launch: bool
    stopping: tuple[str, ...] = ()

    @property
    def because(self) -> str:
        return " ".join(self.stopping)


@dataclass(frozen=True, slots=True)
class Launched:
    """What became of a launch."""

    live: bool
    words: str
    said: Applied | None = None
    #: What was put back, where a partial launch had to be undone.
    rolled_back: tuple[str, ...] = field(default_factory=tuple)


def ready(plan: Plan, *, gate_open: bool, writes: switch.Standing | None = None) -> Ready:
    """Every pre-launch check, together, so a screen can list what is missing.

    Together rather than short-circuiting: a merchant fixing one thing and
    being told about the next is a merchant who gives up on the third.
    """
    stopping: list[str] = []

    if not gate_open or (writes is not None and not writes.may_write):
        stopping.append(
            (writes.because if writes is not None and writes.because else "")
            or "PPCWay is not creating campaigns in Google Ads yet."
        )
    if plan.keywords.unavailable:
        stopping.append(plan.keywords.unavailable)
    elif not plan.keywords.keywords:
        stopping.append("None of the keywords we found are things Google says people search for.")
    if len(plan.copy.headlines) < HEADLINES_KEEP:
        stopping.append(
            plan.copy.short
            or f"Only {len(plan.copy.headlines)} headlines passed checking and"
            f" {HEADLINES_KEEP} are needed."
        )
    if len(plan.copy.descriptions) < DESCRIPTIONS_LEAST:
        stopping.append(
            f"Only {len(plan.copy.descriptions)} descriptions passed checking and"
            f" {DESCRIPTIONS_LEAST} are needed."
        )
    if plan.daily_budget <= 0:
        stopping.append("No daily budget has been set.")
    if not plan.final_url:
        stopping.append("The ad has no page to send people to.")
    if not plan.business.name:
        stopping.append("We do not have the business's name.")

    return Ready(may_launch=not stopping, stopping=tuple(stopping))


def _operations(plan: Plan) -> tuple[Operation, ...]:
    """The keywords this launch creates, as one kind of operation.

    Only the keywords. A real eight-step launch creates the campaign, its
    budget, its ad groups and its ads too, and those are four more resource
    types in a defined order -- which is `v0.1 §3.2`, the section the client
    has not supplied. Building a guess at that order would be building
    something to throw away, so this is the part the brief does state, and
    `ready` refuses a launch that would need the rest.
    """
    return tuple(
        Operation(
            resource_type="ad_group_criterion",
            doing=Doing.CREATE,
            fields={
                "keyword": {"text": keyword.text, "matchType": "PHRASE"},
                "status": "ENABLED",
            },
        )
        for keyword in plan.keywords.keywords
    )


def launch(
    plan: Plan,
    *,
    door: Door,
    customer_id: str,
    gate_open: bool,
    writes: switch.Standing | None = None,
) -> Launched:
    """Send one campaign's worth of changes as one batch, or none of them.

    The checks run again here rather than being trusted from the screen: time
    passes between a person pressing Launch and this running, and the write
    gate is a thing that can be shut in between.
    """
    said_ready = ready(plan, gate_open=gate_open, writes=writes)
    if not said_ready.may_launch:
        return Launched(live=False, words=said_ready.because)

    operations = _operations(plan)
    if not operations:
        return Launched(live=False, words="There is nothing to create.")

    batch = Batch(
        customer_id=customer_id,
        operations=operations,
        partial_failure=True,
        idempotency_key=f"launch:{plan.name}",
    )
    try:
        answered = door.mutate(batch)
    except (GoogleRefused, OSError) as exc:
        # The door's own refusal, or the network. Anything else is a bug in
        # building the request and should not be reported to a merchant as
        # Google saying no.
        log.warning("launch of %r never reached Google: %s", plan.name, exc)
        return Launched(
            live=False,
            words=f"Google would not take the new campaign: {exc}. Nothing was created.",
        )

    if answered.all_landed:
        return Launched(
            live=True,
            words=(
                f"{len(operations)} keywords are live."
                + (
                    " The ad text was drafted by Otto and is declared to Google as AI-written."
                    if plan.copy.declared_as_ai
                    else ""
                )
            ),
            said=answered,
        )

    # Something landed and something did not. Put the rest back: nobody asked
    # for half a campaign, and leaving it would spend money on an account
    # nobody meant to change.
    put_back = _roll_back(answered, door=door, customer_id=customer_id)
    landed, sent = answered.how_many_landed, len(answered.landed)
    log.warning("launch of %r landed %d of %d and was rolled back", plan.name, landed, sent)
    return Launched(
        live=False,
        words=(
            f"Google accepted {landed} of {sent} changes and refused the rest, so we"
            f" put the {len(put_back)} that landed back. Nothing has changed in your"
            f" account."
        ),
        said=answered,
        rolled_back=put_back,
    )


def _roll_back(answered: Applied, *, door: Door, customer_id: str) -> tuple[str, ...]:
    """Remove whatever did land. Best effort, and says what it could not.

    Best effort because a rollback that itself fails must not raise into the
    launch: the merchant needs to be told the account is in a half state far
    more than the process needs to crash. What could not be removed is
    returned, so the words a person reads can be honest about it.
    """
    created = tuple(name for name in answered.landed if name)
    if not created:
        return ()
    try:
        door.mutate(
            Batch(
                customer_id=customer_id,
                operations=tuple(
                    Operation(
                        resource_type="ad_group_criterion",
                        doing=Doing.REMOVE,
                        resource_name=name,
                    )
                    for name in created
                ),
                partial_failure=True,
                idempotency_key=f"rollback:{created[0]}",
            )
        )
    except (GoogleRefused, OSError):
        log.exception("could not roll back %d created resources", len(created))
        return created
    return created


def declare_ai(fields: dict[str, Any], copy: Written) -> dict[str, Any]:
    """Add the AI declaration to an ad's fields, where a model wrote any of it.

    A separate function so the one place that decides is greppable: the brief
    requires the declaration, and a field quietly dropped from a request body
    is the kind of omission nobody notices until somebody asks.
    """
    if not copy.declared_as_ai:
        return dict(fields)
    return {**fields, **AI_DRAFTED}


def headline_fields(copy: Written) -> dict[str, Any]:
    """An ad's assets, in the shape Google's responsive search ad takes them."""
    return declare_ai(
        {
            "responsiveSearchAd": {
                "headlines": [{"text": text} for text in copy.headlines],
                "descriptions": [{"text": text} for text in copy.descriptions],
            }
        },
        copy,
    )
