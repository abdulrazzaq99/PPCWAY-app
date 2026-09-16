"""The API. Today: the free website audit. Tomorrow: sign-in, onboarding, the dashboard.

Runs the audit in a background task for now. When the crawler and browser move
to their own worker, this endpoint only enqueues.
"""

from __future__ import annotations

import logging
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated, Any
from uuid import UUID

from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, EmailStr, Field, field_validator
from sqlalchemy import select
from sqlalchemy.orm import Session

from ppcway.audit.models import AuditRequest, AuditRun
from ppcway.audit.runner import normalise_site, run_audit
from ppcway.config import Settings, load_settings
from ppcway.db.session import get_session, session_factory

log = logging.getLogger(__name__)

CONSENT_TEXT = (
    "PPCWay may email and call me about this audit. No newsletters, and I can ask you "
    "to stop at any time. PPCWay reads my website to write the report and may send what "
    "it says to its AI provider, Anthropic."
)

SITE = re.compile(r"^[a-z0-9-]+(\.[a-z0-9-]+)+(/.*)?$", re.IGNORECASE)


class AuditRequestIn(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    email: EmailStr
    phone: str = Field(min_length=7, max_length=40)
    business_name: str = Field(min_length=1, max_length=200)
    site: str = Field(min_length=3, max_length=500)
    consent: bool
    source: str = Field(default="landing", pattern="^(landing|onboarding)$")

    @field_validator("site")
    @classmethod
    def _looks_like_a_site(cls, value: str) -> str:
        bare = re.sub(r"^https?://", "", value.strip())
        if not SITE.match(bare):
            raise ValueError("Type your website address, like alphaplumbing.ca")
        return bare

    @field_validator("consent")
    @classmethod
    def _must_consent(cls, value: bool) -> bool:
        if not value:
            raise ValueError("Tick the box so we can send you the report.")
        return value


class AuditOut(BaseModel):
    id: UUID
    site: str
    status: str
    report: dict[str, Any] | None = None
    error: str | None = None


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or load_settings()
    app = FastAPI(title="PPCWay API", version="0.1.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[settings.web_url, "http://localhost:3000"],
        allow_methods=["GET", "POST"],
        allow_headers=["*"],
    )

    @app.get("/healthz")
    def healthz() -> dict[str, str]:
        return {"status": "ok", "environment": settings.environment}

    @app.post("/v1/audits", response_model=AuditOut, status_code=202)
    def request_audit(
        body: AuditRequestIn, tasks: BackgroundTasks, session: Annotated[Session, Depends(get_session)]
    ) -> AuditOut:
        req = AuditRequest(
            name=body.name.strip(),
            email=str(body.email).lower(),
            phone=body.phone.strip(),
            business_name=body.business_name.strip(),
            site=body.site,
            source=body.source,
            consent_text=CONSENT_TEXT,
        )
        run = AuditRun(site=normalise_site(body.site), status="queued")
        session.add(req)
        session.flush()
        run.request_id = req.id
        session.add(run)
        session.commit()
        tasks.add_task(_run, run.id, settings)
        return AuditOut(id=run.id, site=run.site, status=run.status)

    @app.get("/v1/audits/{run_id}", response_model=AuditOut)
    def read_audit(run_id: UUID, session: Annotated[Session, Depends(get_session)]) -> AuditOut:
        run = session.get(AuditRun, run_id)
        if run is None:
            raise HTTPException(404, "No audit with that id.")
        return AuditOut(id=run.id, site=run.site, status=run.status, report=run.report, error=run.error)

    @app.get("/v1/audits/{run_id}/screenshot/{kind}")
    def screenshot(run_id: UUID, kind: str) -> FileResponse:
        if kind not in ("phone", "laptop"):
            raise HTTPException(404, "No such screenshot.")
        path = Path(settings.audit_shots_dir) / str(run_id) / f"{kind}.jpg"
        if not path.exists():
            raise HTTPException(404, "No screenshot for this audit.")
        return FileResponse(path, media_type="image/jpeg", headers={"Cache-Control": "public, max-age=86400"})

    @app.get("/v1/audits", response_model=list[AuditOut])
    def list_audits(session: Annotated[Session, Depends(get_session)], limit: int = 20) -> list[AuditOut]:
        rows = session.scalars(select(AuditRun).order_by(AuditRun.created_at.desc()).limit(min(limit, 100))).all()
        return [AuditOut(id=r.id, site=r.site, status=r.status, error=r.error) for r in rows]

    return app


def _run(run_id: UUID, settings: Settings) -> None:
    factory = session_factory()
    with factory() as session:
        run = session.get(AuditRun, run_id)
        if run is None:
            return
        run.status = "running"
        run.started_at = datetime.now(UTC)
        session.commit()
        site = run.site
    try:
        report = run_audit(site, settings)
        folder = Path(settings.audit_shots_dir) / str(run_id)
        for kind, data in report.screenshots.items():
            folder.mkdir(parents=True, exist_ok=True)
            (folder / f"{kind}.jpg").write_bytes(data)
            report.screenshot_urls[kind] = f"/v1/audits/{run_id}/screenshot/{kind}"
        with factory() as session:
            run = session.get(AuditRun, run_id)
            if run is None:
                return
            run.report = report.as_dict()
            run.status = "done"
            run.finished_at = datetime.now(UTC)
            session.commit()
    except Exception as exc:
        log.exception("audit %s failed", run_id)
        with factory() as session:
            run = session.get(AuditRun, run_id)
            if run is not None:
                run.status = "failed"
                run.error = f"{type(exc).__name__}: {exc}"[:2000]
                run.finished_at = datetime.now(UTC)
                session.commit()


app = create_app()
