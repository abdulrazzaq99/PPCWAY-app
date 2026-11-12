"""Checking and publishing a campaign built on Google's own steps.

The review step of Google's flow lists every problem with a way to fix it,
then publishes. Here that is three things, in order:

1. **PPCWay's checks** (`checks.problems`), everything it can see is wrong
   without asking anyone, filed against the step it belongs to.
2. **Google's check**: the whole request sent once with `validateOnly`, which
   creates nothing and returns every error Google has, each filed against a
   step the same way (`checks.step_of`), so "Fix it" goes to the right place.
3. **Publish**: the same request for real, all or nothing (`gateway.create`).
   Then the one thing Google will not take inside that request, new-customer
   bidding, which lives at its goal services and needs the campaign's id.

What a merchant is told is what happened: published means Google created it;
refused means nothing was created, with Google's reasons, and the draft stays
as it was.
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from typing import Any

from sqlalchemy.orm import Session

from ppcway.builder.checks import blocking, problems, step_of
from ppcway.builder.models import CampaignDraft
from ppcway.builder.ops import build, campaign_of
from ppcway.builder.spec import CampaignSpec
from ppcway.gateway.apply import CannotApply
from ppcway.gateway.create import check_together, create_alone, create_together
from ppcway.gateway.port import Batch, Builds, Doing, Door, GoogleRefused, Operation

log = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class Outcome:
    ok: bool
    words: str
    problems: list[dict[str, Any]] = field(default_factory=list)
    campaign: str = ""


def _google_problems(exc: GoogleRefused, spec: CampaignSpec) -> list[dict[str, Any]]:
    found = [
        {
            "step": step_of(p.get("resource_type", ""), p.get("field", ""), spec.type),
            "words": f"Google: {p.get('message', '')}"
            + (
                f" ({p.get('about')})"
                if p.get("about") and p.get("about") != "the campaign"
                else ""
            ),
            "blocks": True,
            "code": p.get("code", ""),
        }
        for p in exc.problems
    ]
    return found or [{"step": "review", "words": str(exc), "blocks": True, "code": ""}]


def check(spec: CampaignSpec, *, customer_id: str, door: Builds, today: date, tag: str) -> Outcome:
    """Everything wrong, PPCWay's first and then Google's. Creates nothing."""
    found = problems(spec, today=today)
    if blocking(found):
        return Outcome(False, "Fix these before publishing.", [p.as_dict() for p in found])
    built = build(spec, customer_id, tag=tag, today=today)
    advice = [p.as_dict() for p in found]
    try:
        check_together(built.together, door=door)
    except GoogleRefused as exc:
        return Outcome(
            False, "Google would not publish it yet.", advice + _google_problems(exc, spec)
        )
    return Outcome(True, "Google checked the whole campaign and would publish it.", advice)


def publish(
    session: Session,
    draft: CampaignDraft,
    *,
    door: Builds,
    gate_open: bool,
    account_id: uuid.UUID | None,
    today: date,
    now: datetime | None = None,
) -> Outcome:
    """Create the campaign in Google, or say exactly why not."""
    at = now or datetime.now(UTC)
    if draft.status == "launched":
        return Outcome(
            True, "That campaign is already published.", campaign=draft.campaign_resource
        )
    spec = CampaignSpec.model_validate(draft.plan or {})
    found = problems(spec, today=today)
    if blocking(found):
        return Outcome(False, "Fix these before publishing.", [p.as_dict() for p in found])

    built = build(spec, draft.customer_id, tag=str(draft.id)[:8], today=today)
    try:
        made = create_together(session, built.together, door=door, gate_open=gate_open, now=at)
    except CannotApply as exc:
        return Outcome(False, f"Nothing was created. {exc}")
    except GoogleRefused as exc:
        draft.outcome = {"at": at.isoformat(), "refused": str(exc), "problems": exc.problems}
        session.commit()
        log.warning("publish of draft %s refused: %s", draft.id, exc)
        return Outcome(
            False,
            "Google would not publish it, so nothing was created. Fix these and publish again.",
            _google_problems(exc, spec),
        )

    draft.status = "launched"
    draft.launched_at = at
    draft.launched_by = account_id
    draft.campaign_resource = campaign_of(made.names)
    draft.outcome = {"at": at.isoformat(), "created": list(made.names)}
    session.commit()
    return Outcome(
        True,
        f'"{spec.name}" is published in Google Ads. Google reviews new ads, usually within'
        " one business day, and its bidding needs a week or two of its own data to settle.",
        campaign=draft.campaign_resource,
    )


def new_customer_goal(
    session: Session,
    *,
    customer_id: str,
    campaign: str,
    mode: str,
    value: float | None,
    existing_goal: str,
    door: Door,
    gate_open: bool,
) -> str:
    """Set new-customer bidding on a campaign that now exists. "" when done.

    Google keeps this out of the creation request: one account-level `Goal`
    for new-customer acquisition, then a `CampaignGoalConfig` joining it to
    the campaign, "Bid only for new customers" being `TARGET_SPECIFIC`. A
    failure here leaves the campaign published and is said, not hidden.
    """
    if mode == "off" or not campaign:
        return ""
    try:
        goal = existing_goal
        if not goal:
            settings: dict[str, Any] = {}
            if value:
                settings = {"valueSettings": {"additionalValue": float(value)}}
            made = create_alone(
                session,
                Batch(
                    customer_id=customer_id,
                    operations=(
                        Operation(
                            resource_type="goal",
                            doing=Doing.CREATE,
                            fields={"newCustomerAcquisitionGoalSettings": settings},
                        ),
                    ),
                    partial_failure=False,
                ),
                door=door,
                gate_open=gate_open,
            )
            goal = next((n for n in made.landed if n), "") or ""
            if not goal:
                return (
                    made.refused[0].message if made.refused else "Google did not create the goal."
                )
        applied = create_alone(
            session,
            Batch(
                customer_id=customer_id,
                operations=(
                    Operation(
                        resource_type="campaign_goal_config",
                        doing=Doing.CREATE,
                        fields={
                            "campaign": campaign,
                            "goal": goal,
                            "campaignNewCustomerAcquisitionSettings": {
                                "targetOption": "TARGET_SPECIFIC"
                                if mode == "only"
                                else "TARGET_ALL"
                            },
                        },
                    ),
                ),
                partial_failure=False,
            ),
            door=door,
            gate_open=gate_open,
        )
        if not applied.all_landed:
            return applied.refused[0].message if applied.refused else "Google did not set it."
    except (CannotApply, GoogleRefused) as exc:
        return str(exc)
    return ""
