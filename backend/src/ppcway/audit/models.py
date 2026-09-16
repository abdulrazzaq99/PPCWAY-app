"""The audit request and its run. Portable types: SQLite locally, Postgres (JSONB) deployed."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import JSON, DateTime, ForeignKey, String, Text, Uuid, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from ppcway.db.base import Base


def _pk() -> Mapped[uuid.UUID]:
    return mapped_column(Uuid(), primary_key=True, default=uuid.uuid4)


class AuditRequest(Base):
    """Who asked for the free audit, and the consent they gave."""

    __tablename__ = "audit_request"
    id: Mapped[uuid.UUID] = _pk()
    name: Mapped[str] = mapped_column(String(200))
    email: Mapped[str] = mapped_column(String(320), index=True)
    phone: Mapped[str] = mapped_column(String(40))
    business_name: Mapped[str] = mapped_column(String(200))
    site: Mapped[str] = mapped_column(String(500))
    #: "landing" for the public form, "onboarding" for step 4.
    source: Mapped[str] = mapped_column(String(20), default="landing")
    consent_text: Mapped[str] = mapped_column(Text)
    consented_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class AuditRun(Base):
    """One run of the eight checks. Status: queued, running, done, failed."""

    __tablename__ = "audit_run"
    id: Mapped[uuid.UUID] = _pk()
    request_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("audit_request.id"), index=True, nullable=True)
    site: Mapped[str] = mapped_column(String(500), index=True)
    status: Mapped[str] = mapped_column(String(20), default="queued", index=True)
    report: Mapped[dict[str, Any] | None] = mapped_column(
        JSON().with_variant(JSONB(), "postgresql"), nullable=True
    )
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
