"""Putting a campaign live: checked here, checked by Google, created whole.

The client's brief for phase 4.2: *pre-launch checks, one-batch launch with
rollback*. Since 6 November this creates the whole campaign. Until then it
created only the keywords, because the client's eight builder steps (`v0.1
§3.2`) were never supplied; the owner asked for the whole flow, and the
designs (Figma 87:10926 and 17:2048) say what it is.

**One request, and nothing to roll back.** The budget, the campaign, its
places and excluded searches, the ad groups, keywords and ads go to
Google as one request that applies whole or not at all (`gateway.create`). The
brief asked for rollback because a launch sent piece by piece can half-land;
sent as one request it cannot, which is better than any rollback.

**Checked twice before anything exists.** `campaign.missing` lists everything
PPCWay can see is wrong, together. Then Google checks the whole request
without creating anything, so a refused headline or a duplicate name is said
while there is still nothing to undo.

**What a merchant is told is what happened.** Live means Google created it;
refused means nothing was created, with Google's reason, and the draft stays
as it was to be changed and tried again.
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from ppcway.builder.campaign import CampaignPlan, campaign_of, missing, operations_for
from ppcway.builder.models import CampaignDraft
from ppcway.gateway.apply import CannotApply
from ppcway.gateway.create import create_together
from ppcway.gateway.port import Builds, GoogleRefused

log = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class Launched:
    """What became of pressing Launch."""

    live: bool
    words: str
    campaign: str = ""


def launch_draft(
    session: Session,
    draft: CampaignDraft,
    *,
    door: Builds,
    gate_open: bool,
    account_id: uuid.UUID | None,
    now: datetime | None = None,
) -> Launched:
    """Create the drafted campaign in Google, or say exactly why not."""
    at = now or datetime.now(UTC)
    if draft.status == "launched":
        return Launched(
            live=True, words="That campaign is already live.", campaign=draft.campaign_resource
        )

    plan = CampaignPlan.from_dict(draft.plan or {})
    problems = missing(plan)
    if problems:
        return Launched(live=False, words=" ".join(problems))

    together = operations_for(plan, draft.customer_id, tag=str(draft.id)[:8])
    try:
        made = create_together(session, together, door=door, gate_open=gate_open, now=at)
    except CannotApply as exc:
        return Launched(live=False, words=f"Nothing was created. {exc}")
    except GoogleRefused as exc:
        draft.outcome = {"at": at.isoformat(), "refused": str(exc)}
        session.commit()
        log.warning("launch of draft %s refused: %s", draft.id, exc)
        return Launched(
            live=False,
            words=f"{exc}. Nothing was created; change that and launch again.",
        )

    draft.status = "launched"
    draft.launched_at = at
    draft.launched_by = account_id
    draft.campaign_resource = campaign_of(made.names)
    draft.outcome = {"at": at.isoformat(), "created": list(made.names)}
    session.commit()
    words = (
        f'"{plan.name}" is live in Google Ads. It shows on your Campaigns page within a'
        " few minutes. Google needs about a week of its own data before its cost per"
        " lead means much."
    )
    if plan.ai_written:
        words += " The ad text was drafted by Otto and checked by PPCWay's rules."
    return Launched(live=True, words=words, campaign=draft.campaign_resource)
