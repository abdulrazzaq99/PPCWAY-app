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

from fastapi import BackgroundTasks, Depends, FastAPI, Header, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, EmailStr, Field, field_validator, model_validator
from sqlalchemy import select
from sqlalchemy.orm import Session

from ppcway.audit.models import AuditRequest, AuditRun
from ppcway.audit.places import (
    Listing,
    PlacesError,
    find_businesses,
    nearby_rivals,
    place_details,
)
from ppcway.audit.runner import normalise_site, run_audit
from ppcway.auth.google import SignInRefused, verify_google_token
from ppcway.auth.models import UserAccount
from ppcway.auth.sessions import sign_in, sign_out, whoever_holds
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
    """What the public forms send. The business and its website are enough to run the
    checks; the person's details arrive when they ask for the report by email."""

    business_name: str = Field(min_length=1, max_length=200)
    site: str = Field(min_length=3, max_length=500)
    city: str = Field(default="", max_length=120)
    trade: str = Field(default="", max_length=120)
    name: str = Field(default="", max_length=200)
    email: EmailStr | None = None
    phone: str = Field(default="", max_length=40)
    consent: bool = False
    #: "yes", "no" or "unsure": whether they already run Google Ads.
    advertising: str = Field(default="", pattern="^(yes|no|unsure|)$")
    source: str = Field(default="landing", pattern="^(landing|onboarding)$")
    #: The Google listing they picked, when they came through Find my business.
    #: The id is the one part of a listing Google lets us keep.
    place_id: str = Field(default="", max_length=200)

    @field_validator("site")
    @classmethod
    def _looks_like_a_site(cls, value: str) -> str:
        bare = re.sub(r"^https?://", "", value.strip())
        if not SITE.match(bare):
            raise ValueError("Type your website address, like alphaplumbing.ca")
        return bare

    @model_validator(mode="after")
    def _consent_when_we_would_contact(self) -> AuditRequestIn:
        if self.email and not self.consent:
            raise ValueError("Tick the box so we can send you the report.")
        return self


class AuditOut(BaseModel):
    id: UUID
    site: str
    status: str
    report: dict[str, Any] | None = None
    error: str | None = None
    #: What the run is doing now: crawling, rendering, speed, checks, done.
    stage: str = ""
    #: Pages read so far, which climbs while the crawl runs.
    pages_read: int = 0
    #: The Google listing they confirmed, so the report can read it again.
    place_id: str = ""
    #: The town they typed, the anchor for the businesses nearby.
    city: str = ""


class SignInIn(BaseModel):
    """What Google's button hands the browser, passed straight through once."""

    credential: str = Field(min_length=20, max_length=4000)


class PersonOut(BaseModel):
    """Who is signed in, as a screen needs to greet them."""

    email: str
    name: str
    picture: str


class SignedInOut(BaseModel):
    person: PersonOut
    #: The session token. The web app puts this in an httpOnly cookie and the
    #: browser never reads it; it is returned once, here, and nowhere else.
    token: str


class ListingOut(BaseModel):
    """A Google listing as the screens show it. Only `place_id` may be stored."""

    place_id: str
    name: str
    address: str
    category: str
    rating: float | None
    reviews: int
    website: str
    phone: str
    open_now: bool | None
    service_area_only: bool
    status: str
    maps_url: str
    photos: int
    hours_set: bool
    open_24h: bool
    name_match: bool

    @classmethod
    def of(cls, li: Listing) -> ListingOut:
        return cls(
            place_id=li.place_id,
            name=li.name,
            address=li.short_address or li.address,
            category=li.category,
            rating=li.rating,
            reviews=li.reviews,
            website=li.website,
            phone=li.phone,
            open_now=li.open_now,
            service_area_only=li.service_area_only,
            status=li.status,
            maps_url=li.maps_url,
            photos=li.photos,
            hours_set=li.hours_set,
            open_24h=li.open_24h,
            name_match=li.name_match,
        )


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
    @app.get("/v1/healthz")
    def healthz() -> dict[str, str]:
        """Two paths for one answer: Google's front end swallows /healthz on Cloud Run."""
        return {"status": "ok", "environment": settings.environment}

    @app.post("/v1/audits", response_model=AuditOut, status_code=202)
    def request_audit(
        body: AuditRequestIn,
        tasks: BackgroundTasks,
        session: Annotated[Session, Depends(get_session)],
        x_session_token: Annotated[str | None, Header()] = None,
    ) -> AuditOut:
        # Signed in, the audit is kept against the account; signed out, it is not.
        asked_by = _person(session, x_session_token)
        req = AuditRequest(
            name=body.name.strip(),
            email=str(body.email).lower() if body.email else "",
            phone=body.phone.strip(),
            business_name=body.business_name.strip(),
            site=body.site,
            source=body.source,
            place_id=body.place_id.strip(),
            city=body.city.strip(),
            user_id=asked_by.id if asked_by else None,
            consent_text=CONSENT_TEXT if body.consent else "",
        )
        run = AuditRun(site=normalise_site(body.site), status="queued")
        session.add(req)
        session.flush()
        run.request_id = req.id
        session.add(run)
        session.commit()
        tasks.add_task(_run, run.id, settings)
        return AuditOut(id=run.id, site=run.site, status=run.status)

    @app.get("/v1/audits/mine", response_model=list[AuditOut])
    def my_audits(
        session: Annotated[Session, Depends(get_session)],
        x_session_token: Annotated[str | None, Header()] = None,
        limit: int = 20,
    ) -> list[AuditOut]:
        """Every audit this person ran while signed in, newest first."""
        account = _person(session, x_session_token)
        if account is None:
            raise HTTPException(401, "Nobody is signed in.")
        rows = session.scalars(
            select(AuditRun)
            .join(AuditRequest, AuditRun.request_id == AuditRequest.id)
            .where(AuditRequest.user_id == account.id)
            .order_by(AuditRun.created_at.desc())
            .limit(min(limit, 100))
        ).all()
        return [
            AuditOut(id=r.id, site=r.site, status=r.status, error=r.error, stage=r.stage)
            for r in rows
        ]

    @app.get("/v1/audits/{run_id}", response_model=AuditOut)
    def read_audit(run_id: UUID, session: Annotated[Session, Depends(get_session)]) -> AuditOut:
        run = session.get(AuditRun, run_id)
        if run is None:
            raise HTTPException(404, "No audit with that id.")
        asked = session.get(AuditRequest, run.request_id) if run.request_id else None
        return AuditOut(
            id=run.id,
            site=run.site,
            status=run.status,
            report=run.report,
            error=run.error,
            stage=run.stage,
            pages_read=run.pages_read,
            place_id=asked.place_id if asked else "",
            city=asked.city if asked else "",
        )

    @app.get("/v1/audits/{run_id}/screenshot/{kind}")
    def screenshot(run_id: UUID, kind: str) -> FileResponse:
        if kind not in ("phone", "laptop"):
            raise HTTPException(404, "No such screenshot.")
        path = Path(settings.audit_shots_dir) / str(run_id) / f"{kind}.jpg"
        if not path.exists():
            raise HTTPException(404, "No screenshot for this audit.")
        return FileResponse(
            path, media_type="image/jpeg", headers={"Cache-Control": "public, max-age=86400"}
        )

    def _maps_key() -> str:
        if settings.google_maps_api_key is None:
            raise HTTPException(503, "Business search is not set up yet.")
        return settings.google_maps_api_key.get_secret_value()

    def _person(session: Session, token: str | None) -> UserAccount | None:
        return whoever_holds(session, token)

    @app.post("/v1/auth/google", response_model=SignedInOut)
    def sign_in_with_google(
        body: SignInIn, session: Annotated[Session, Depends(get_session)]
    ) -> SignedInOut:
        """Check Google's token, then start a session. See `auth.google`."""
        if not settings.google_signin_client_id:
            raise HTTPException(503, "Signing in with Google is not set up yet.")
        try:
            who = verify_google_token(body.credential, client_id=settings.google_signin_client_id)
        except SignInRefused as exc:
            log.warning("sign-in refused: %s", exc)
            raise HTTPException(401, str(exc)) from None
        account, token = sign_in(session, who)
        return SignedInOut(
            person=PersonOut(email=account.email, name=account.name, picture=account.picture),
            token=token,
        )

    @app.get("/v1/auth/me", response_model=PersonOut)
    def who_am_i(
        session: Annotated[Session, Depends(get_session)],
        x_session_token: Annotated[str | None, Header()] = None,
    ) -> PersonOut:
        account = _person(session, x_session_token)
        if account is None:
            raise HTTPException(401, "Nobody is signed in.")
        return PersonOut(email=account.email, name=account.name, picture=account.picture)

    @app.post("/v1/auth/signout", status_code=204)
    def sign_out_here(
        session: Annotated[Session, Depends(get_session)],
        x_session_token: Annotated[str | None, Header()] = None,
    ) -> None:
        sign_out(session, x_session_token)

    @app.get("/v1/places/suggest", response_model=list[ListingOut])
    def suggest_businesses(
        q: Annotated[str, Query(min_length=2, max_length=200)],
        city: Annotated[str, Query(max_length=200)] = "",
        region: Annotated[str, Query(min_length=2, max_length=2)] = "ca",
        limit: Annotated[int, Query(ge=1, le=10)] = 6,
    ) -> list[ListingOut]:
        """What to offer while someone is still typing.

        The same search as the button, not Autocomplete. Autocomplete is cheaper and
        built for a key at a time, but it only offers prominent listings: measured
        against this project's own test business, a service-area plumber with seven
        reviews, it never returned it at any radius, while this search returns it
        first. A list that cannot find the person typing is not worth its discount.
        """
        try:
            found = find_businesses(
                q.strip(), api_key=_maps_key(), city=city.strip(), region=region, max_results=limit
            )
        except PlacesError as exc:
            log.warning("places suggest failed: %s", exc)
            # A dead list must not stop someone typing: the button still works.
            return []
        return [ListingOut.of(li) for li in found]

    @app.get("/v1/places/search", response_model=list[ListingOut])
    def search_businesses(
        name: Annotated[str, Query(min_length=2, max_length=200)],
        city: Annotated[str, Query(max_length=200)] = "",
        region: Annotated[str, Query(min_length=2, max_length=2)] = "ca",
        limit: Annotated[int, Query(ge=1, le=60)] = 20,
    ) -> list[ListingOut]:
        """Every listing of that name, the given town's first. See `audit.places`."""
        try:
            found = find_businesses(
                name.strip(),
                api_key=_maps_key(),
                city=city.strip(),
                region=region,
                max_results=limit,
            )
        except PlacesError as exc:
            log.warning("places search failed: %s", exc)
            if exc.out_of_quota:
                raise HTTPException(
                    429, "The day's allowance for business lookups is used up."
                ) from None
            raise HTTPException(502, "Google did not answer the business search.") from None
        return [ListingOut.of(li) for li in found]

    @app.get("/v1/places/{place_id}", response_model=ListingOut)
    def read_business(place_id: str) -> ListingOut:
        try:
            found = place_details(place_id, api_key=_maps_key())
        except PlacesError as exc:
            log.warning("places details failed: %s", exc)
            raise HTTPException(502, "Google did not answer for that listing.") from None
        if found is None:
            raise HTTPException(404, "Google no longer has that listing.")
        return ListingOut.of(found)

    @app.get("/v1/places/{place_id}/nearby", response_model=list[ListingOut])
    def read_nearby(place_id: str, city: str = "", limit: int = 6) -> list[ListingOut]:
        """The same trade around that business: the honest half of "who you are up against"."""
        key = _maps_key()
        try:
            listing = place_details(place_id, api_key=key)
            if listing is None:
                raise HTTPException(404, "Google no longer has that listing.")
            rivals = nearby_rivals(listing, api_key=key, city=city, limit=min(max(limit, 1), 20))
        except PlacesError as exc:
            log.warning("places nearby failed: %s", exc)
            raise HTTPException(502, "Google did not answer for the businesses nearby.") from None
        return [ListingOut.of(li) for li in rivals]

    @app.get("/v1/audits", response_model=list[AuditOut])
    def list_audits(
        session: Annotated[Session, Depends(get_session)], limit: int = 20
    ) -> list[AuditOut]:
        rows = session.scalars(
            select(AuditRun).order_by(AuditRun.created_at.desc()).limit(min(limit, 100))
        ).all()
        return [AuditOut(id=r.id, site=r.site, status=r.status, error=r.error) for r in rows]

    return app


def _run(run_id: UUID, settings: Settings) -> None:
    factory = session_factory()
    with factory() as session:
        run = session.get(AuditRun, run_id)
        if run is None:
            return
        run.status = "running"
        run.stage = "crawling"
        run.started_at = datetime.now(UTC)
        session.commit()
        site = run.site

    def say(stage: str, pages_read: int) -> None:
        """Write where the run has got to, so the waiting screen can show it."""
        with factory() as session:
            now = session.get(AuditRun, run_id)
            if now is not None:
                now.stage = stage
                now.pages_read = pages_read
                session.commit()

    try:
        report = run_audit(site, settings, on_stage=say)
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
            run.stage = "done"
            run.pages_read = report.pages_read
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
