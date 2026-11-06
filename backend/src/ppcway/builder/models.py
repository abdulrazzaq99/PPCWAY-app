"""A campaign being built, between "start writing" and "launch".

One row per campaign somebody started building: the plan as the builder
wrote it and the merchant edited it, and, once launched, what Google said it
created. It is the record of a launch as well as its workspace -- who pressed
launch, when, and the resource name of the campaign that came of it -- so
"where did this campaign come from?" has an answer in PPCWay as well as in
Google's change history.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import JSON, DateTime, ForeignKey, String, Uuid, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from ppcway.db.base import Base


class CampaignDraft(Base):
    """One new campaign, before and after it reaches Google."""

    __tablename__ = "campaign_draft"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organization.id"), index=True)
    customer_id: Mapped[str] = mapped_column(String(20), default="", index=True)
    created_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("account.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )
    #: "draft" while it is being read and edited; "launched" once Google has it.
    status: Mapped[str] = mapped_column(String(20), default="draft", index=True)
    #: The `CampaignPlan`, as data.
    plan: Mapped[dict[str, Any] | None] = mapped_column(
        JSON().with_variant(JSONB(), "postgresql"), nullable=True
    )
    launched_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    launched_by: Mapped[uuid.UUID | None] = mapped_column(Uuid(), nullable=True)
    #: The campaign Google created, as it names it.
    campaign_resource: Mapped[str] = mapped_column(String(120), default="")
    #: The last thing Google said: what it created, or why it refused.
    outcome: Mapped[dict[str, Any] | None] = mapped_column(
        JSON().with_variant(JSONB(), "postgresql"), nullable=True
    )
