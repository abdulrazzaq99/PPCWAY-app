"""The API. Today: the free website audit. Tomorrow: sign-in, onboarding, the dashboard.

Runs the audit in a background task for now. When the crawler and browser move
to their own worker, this endpoint only enqueues.
"""

from __future__ import annotations

import logging
import re
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from hmac import compare_digest
from pathlib import Path
from typing import Annotated, Any
from uuid import UUID

from fastapi import BackgroundTasks, Depends, FastAPI, Header, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, EmailStr, Field, field_validator, model_validator
from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from ppcway.ads.accounts import accessible_accounts
from ppcway.ads.business import known_business
from ppcway.ads.gate import gate_report
from ppcway.ads.mirror import CampaignDay, ExternalChange, MirrorCampaign, SyncRun
from ppcway.ads.models import AdsConnection, ConsentTrip
from ppcway.ads.numbers import account_numbers, campaign_numbers, merge_live
from ppcway.ads.oauth import (
    AdsConnectionRefused,
    TokenVault,
    VaultUnavailable,
    consent_url,
    exchange_code,
    fresh_access_token,
    new_state,
    revoke_permission,
)
from ppcway.ads.planner import demand_for
from ppcway.ads.reports import report_for
from ppcway.ads.runner import sync_everyone, sync_one
from ppcway.ads.stats import read_account
from ppcway.ads.summary import account_summary, campaign_detail
from ppcway.audit.history import score_history, score_of, what_changed
from ppcway.audit.kinds import SAID, Kind, classify, keep
from ppcway.audit.landing import (
    GOALS,
    RUNNERS,
    SPEND_BANDS,
    percent_at,
    report_of,
    stages_at,
    summary_of,
)
from ppcway.audit.lead import Answer, check_code, post_a_code, take_the_lead
from ppcway.audit.listing import listing_findings, rival_findings
from ppcway.audit.models import AuditRequest, AuditRun
from ppcway.audit.pages import check_pages, landing_pages
from ppcway.audit.paper import NotPrinted, to_pdf
from ppcway.audit.places import (
    Listing,
    PlacesError,
    find_businesses,
    listing_for,
    nearby_rivals,
    place_details,
)
from ppcway.audit.runner import normalise_site, run_audit
from ppcway.audit.watch import due_audits
from ppcway.auth.accounts import (
    AlreadyHere,
    finish_reset,
    fresh_verification,
    register,
    sign_in_with_password,
    start_reset,
    verify,
)
from ppcway.auth.google import SignInRefused, verify_google_token
from ppcway.auth.models import UserAccount
from ppcway.auth.opening import NOT_YET, may_come_in, open_to_everybody
from ppcway.auth.passwords import WeakPassword
from ppcway.auth.sessions import (
    sign_in,
    sign_in_existing,
    sign_out,
    sign_out_everywhere,
    whoever_holds,
)
from ppcway.config import Settings, load_settings
from ppcway.db.session import get_session, session_factory
from ppcway.mail.alerts import post_alerts
from ppcway.mail.letters import (
    audit_code,
    audit_ready,
    file_name,
    fix_list,
    invitation,
    reset_password,
    verify_email,
)
from ppcway.mail.send import Letter, NotSent, Post, send
from ppcway.mail.weekly import post_weekly
from ppcway.org.models import CAN, Invitation, Organization, Role
from ppcway.org.places import (
    NotAllowed,
    accept,
    change_role,
    home_for,
    insist,
    invite,
    people_in,
    remove,
    role_of,
)
from ppcway.share.links import make_link, open_link, revoke
from ppcway.share.models import ShareLink

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
    #: The score out of 100, worked out from the checks that have an answer.
    #: Carried on the listing so a screen showing many runs need not fetch each.
    score: int | None = None


class RegisterIn(BaseModel):
    """What the sign-up form sends."""

    email: EmailStr
    password: str = Field(min_length=1, max_length=200)
    name: str = Field(default="", max_length=200)


class PasswordIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=200)


class TokenIn(BaseModel):
    token: str = Field(min_length=10, max_length=200)


class ResetIn(BaseModel):
    token: str = Field(min_length=10, max_length=200)
    password: str = Field(min_length=1, max_length=200)


class SignInIn(BaseModel):
    """What Google's button hands the browser, passed straight through once."""

    credential: str = Field(min_length=20, max_length=4000)


class PersonOut(BaseModel):
    """Who is signed in, as a screen needs to greet them."""

    email: str
    name: str
    picture: str
    #: False until they have followed the link in their email. Google's sign-in
    #: proves the address for us, so those accounts arrive verified.
    email_verified: bool = True

    @classmethod
    def of(cls, account: UserAccount) -> PersonOut:
        return cls(
            email=account.email,
            name=account.name,
            picture=account.picture,
            email_verified=account.email_verified_at is not None,
        )


class SignedInOut(BaseModel):
    person: PersonOut
    #: The session token. The web app puts this in an httpOnly cookie and the
    #: browser never reads it; it is returned once, here, and nowhere else.
    token: str


class ClaimIn(BaseModel):
    """Audits run in this browser before anybody signed in."""

    ids: list[UUID] = Field(default_factory=list, max_length=20)


class ClaimedOut(BaseModel):
    claimed: int


class ConnectStartOut(BaseModel):
    """Where to send the merchant, and the state that ties the trip to them."""

    url: str


class PersonInOrgOut(BaseModel):
    account_id: UUID
    email: str
    name: str
    role: str
    is_you: bool


class OrgOut(BaseModel):
    """The business, and what the person asking may do in it."""

    id: UUID
    name: str
    plan: str
    currency: str
    your_role: str
    can: list[str]
    people: list[PersonInOrgOut]


class RenameIn(BaseModel):
    """What a business is called. It appears in invitations and in every report."""

    name: str = Field(min_length=1, max_length=200)


class InviteIn(BaseModel):
    email: EmailStr
    role: str = Field(default="member")


class RoleIn(BaseModel):
    account_id: UUID
    role: str


class AdsAccountOut(BaseModel):
    customer_id: str
    name: str
    is_manager: bool
    currency: str
    time_zone: str
    #: False when Google refused to read it; `trouble` says why, in plain words.
    readable: bool = True
    trouble: str = ""


class ShareIn(BaseModel):
    """How long a shared link should live."""

    days: int = Field(default=14, ge=1, le=90)


class FixListIn(ShareIn):
    """And who to send it to, when it is being sent rather than copied."""

    email: EmailStr | None = None


class ShareOut(BaseModel):
    id: str
    url: str
    expires_at: datetime
    emailed: bool = False


class PublicAuditIn(BaseModel):
    """Step one and two of the free audit page, posted together."""

    business_name: str = Field(min_length=1, max_length=200)
    site: str = Field(min_length=3, max_length=500)
    runner: str = Field(default="", max_length=20)
    goal: str = Field(default="", max_length=20)
    #: What sort of business this is, as shown to them and possibly corrected.
    kind: str = Field(default="", max_length=20)
    kind_is_theirs: bool = False
    place_id: str = Field(default="", max_length=200)
    spend_band: str = Field(default="", max_length=20)
    #: utm_* and gclid, kept with the lead rather than in the address bar.
    came_from: dict[str, str] = Field(default_factory=dict)

    @field_validator("site")
    @classmethod
    def _looks_like_a_site(cls, value: str) -> str:
        bare = re.sub(r"^https?://", "", value.strip()).split("/")[0]
        if not SITE.match(bare):
            raise ValueError("Enter your website, for example yourbusiness.com")
        return bare

    @field_validator("runner")
    @classmethod
    def _known_runner(cls, value: str) -> str:
        if value and value not in RUNNERS:
            raise ValueError("Pick who runs your Google Ads.")
        return value

    @field_validator("goal")
    @classmethod
    def _known_goal(cls, value: str) -> str:
        if value and value not in GOALS:
            raise ValueError("Pick what your ads should bring you.")
        return value

    @field_validator("spend_band")
    @classmethod
    def _known_band(cls, value: str) -> str:
        if value and value not in SPEND_BANDS:
            raise ValueError("Pick your monthly ad spend.")
        return value


class IdentifyIn(BaseModel):
    """Enough to find them on Google Maps and say what they look like."""

    business_name: str = Field(min_length=1, max_length=200)
    site: str = Field(default="", max_length=500)
    #: Set when they picked their own listing out of Google's suggestions,
    #: which settles which business this is rather than inferring it.
    place_id: str = Field(default="", max_length=200)


class LeadIn(BaseModel):
    """The gate: who they are, so the findings can be opened to them."""

    name: str = Field(min_length=2, max_length=200)
    email: EmailStr
    phone: str = Field(min_length=7, max_length=40)
    tips_opt_in: bool = False
    came_from: dict[str, str] = Field(default_factory=dict)

    @field_validator("phone")
    @classmethod
    def _enough_digits(cls, value: str) -> str:
        if sum(ch.isdigit() for ch in value) < 7:
            raise ValueError("Enter a phone number we can reach you on.")
        return value


class CodeIn(BaseModel):
    """Six digits from the email."""

    code: str = Field(min_length=1, max_length=12)


class EmailAuditIn(BaseModel):
    """Where to send a finished audit. Signed in, we already know."""

    email: EmailStr | None = None


class EmailedOut(BaseModel):
    """Who it went to, so the button can say so rather than guess."""

    sent_to: str


class SyncOut(BaseModel):
    """One pass over the account, as a screen waiting on it needs to see it."""

    id: UUID
    kind: str
    status: str
    stage: str = ""
    counts: dict[str, Any] = Field(default_factory=dict)
    trouble: str = ""
    started_at: datetime
    finished_at: datetime | None = None

    @classmethod
    def of(cls, run: SyncRun) -> SyncOut:
        return cls(
            id=run.id,
            kind=run.kind,
            status=run.status,
            stage=run.stage,
            counts=run.counts or {},
            trouble=run.trouble,
            started_at=run.started_at,
            finished_at=run.finished_at,
        )


class ChangeOut(BaseModel):
    """Something changed in Google Ads rather than here."""

    kind: str
    label: str
    summary: str
    noticed_at: datetime


class SyncStateOut(BaseModel):
    """What the mirror holds, and what the last look found."""

    connected: bool
    customer_name: str = ""
    run: SyncOut | None = None
    last_done_at: datetime | None = None
    held: dict[str, int] = Field(default_factory=dict)
    changes: list[ChangeOut] = Field(default_factory=list)


class ChooseAccountIn(BaseModel):
    """Which of their accounts we should read on the next audit."""

    customer_id: str = Field(min_length=5, max_length=20, pattern=r"^[0-9-]+$")


class AdsStatusOut(BaseModel):
    """What the signed-in home needs to know about their Google Ads."""

    connected: bool
    customer_id: str = ""
    customer_name: str = ""
    #: Set when Google refused to say what the connection can reach.
    trouble: str = ""


class ConnectFinishIn(BaseModel):
    code: str = Field(min_length=10, max_length=2000)
    state: str = Field(min_length=10, max_length=64)


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
            trade=body.trade.strip(),
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

    @app.post("/v1/audits/claim", response_model=ClaimedOut)
    def claim_audits(
        body: ClaimIn,
        session: Annotated[Session, Depends(get_session)],
        x_session_token: Annotated[str | None, Header()] = None,
    ) -> ClaimedOut:
        """Attach audits run before signing in to the account that just signed in.

        Somebody runs the free audit, likes what it says, and makes an account:
        the report they were reading should be waiting for them, not an empty page.
        Only an audit nobody owns can be claimed, and only by a browser that knows
        its id, which is the same secret as the link to the report itself.
        """
        account = _signed_in(session, x_session_token)
        if not body.ids:
            return ClaimedOut(claimed=0)
        runs = session.scalars(select(AuditRun).where(AuditRun.id.in_(body.ids))).all()
        claimed = 0
        for run in runs:
            asked = session.get(AuditRequest, run.request_id) if run.request_id else None
            if asked is not None and asked.user_id is None:
                asked.user_id = account.id
                claimed += 1
        if claimed:
            session.commit()
        return ClaimedOut(claimed=claimed)

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
            AuditOut(
                id=r.id,
                site=r.site,
                status=r.status,
                error=r.error,
                stage=r.stage,
                score=_score_of(r),
            )
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
            # The listing carries the score; one run on its own carried null,
            # which made the same audit answer two different ways.
            score=_score_of(run),
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

    @app.get("/v1/audits/{run_id}/pdf")
    def audit_paper(
        run_id: UUID,
        session: Annotated[Session, Depends(get_session)],
    ) -> FileResponse:
        """The report as a PDF, to keep, print or forward.

        Open to anybody holding the id, exactly as the report itself is: the
        link in the email has to work for the person who asked for it, and a
        PDF of a page they can already read gives nothing away.
        """
        run = session.get(AuditRun, run_id)
        if run is None or run.status != "done":
            raise HTTPException(404, "No finished audit with that id.")
        asked = session.get(AuditRequest, run.request_id) if run.request_id else None
        name = (asked.business_name if asked else "") or run.site
        try:
            path = _paper(run_id, settings)
        except NotPrinted as exc:
            log.warning("audit %s would not print: %s", run_id, exc)
            raise HTTPException(503, "The report could not be made into a PDF just now.") from exc
        return FileResponse(
            path,
            media_type="application/pdf",
            filename=f"PPCWay audit - {file_name(name)}.pdf",
            headers={"Cache-Control": "private, max-age=3600"},
        )

    def _maps_key() -> str:
        if settings.google_maps_api_key is None:
            raise HTTPException(503, "Business search is not set up yet.")
        return settings.google_maps_api_key.get_secret_value()

    def _person(session: Session, token: str | None) -> UserAccount | None:
        return whoever_holds(session, token)

    def _may_sign_in(session: Session, email: str) -> None:
        """Refuse a stranger at the door while PPCWay is not open to everybody.

        Only the doors: the free audit, the shared links and the public pages
        are open to anybody and ask nothing of this. Somebody already invited
        by a person inside is let through without being named in the setting,
        because a business should be able to add its own people.
        """
        if open_to_everybody(settings.open_to):
            return
        address = email.strip().lower()
        invited = (
            session.scalar(
                select(func.count())
                .select_from(Invitation)
                .where(
                    func.lower(Invitation.email) == address,
                    Invitation.accepted_at.is_(None),
                    Invitation.revoked_at.is_(None),
                    Invitation.expires_at > datetime.now(UTC),
                )
            )
            or 0
        )
        if not may_come_in(address, open_to=settings.open_to, invited=bool(invited)):
            log.info("not open yet, so %s was turned away", address.partition("@")[2] or "somebody")
            raise HTTPException(403, NOT_YET)

    @app.get("/v1/open")
    def how_open() -> dict[str, bool]:
        """Whether anybody may make an account, for screens that offer it.

        The free audit never asks this: it is open either way.
        """
        return {"open": open_to_everybody(settings.open_to)}

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
        _may_sign_in(session, who.email)
        account, token = sign_in(session, who)
        return SignedInOut(
            person=PersonOut.of(account),
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
        return PersonOut.of(account)

    def _post() -> Post:
        """How this deployment sends email, built from settings."""
        return _mailer(settings)

    def _home(session: Session, account: UserAccount) -> Organization:
        """The business this person is in, made on first use."""
        return home_for(session, account)

    def _allowed(session: Session, account: UserAccount, place: Organization, what: str) -> None:
        """Refuse plainly. The interface hides what it can; this is what decides."""
        try:
            insist(session, account, place, what)
        except NotAllowed:
            raise HTTPException(
                403, f"Your role does not allow you to {what.replace('_', ' ')}."
            ) from None

    @app.get("/v1/org", response_model=OrgOut)
    def read_org(
        session: Annotated[Session, Depends(get_session)],
        x_session_token: Annotated[str | None, Header()] = None,
    ) -> OrgOut:
        """The business, who is in it, and what the person asking may do."""
        account = _signed_in(session, x_session_token)
        place = _home(session, account)
        mine = role_of(session, account, place)
        return OrgOut(
            id=place.id,
            name=place.name,
            plan=place.plan,
            currency=place.currency,
            your_role=mine.value if mine else "",
            can=sorted(CAN[mine]) if mine else [],
            people=[
                PersonInOrgOut(
                    account_id=person.id,
                    email=person.email,
                    name=person.name,
                    role=role.value,
                    is_you=person.id == account.id,
                )
                for person, role in people_in(session, place)
            ],
        )

    @app.post("/v1/org/name", status_code=204)
    def rename_org(
        body: RenameIn,
        session: Annotated[Session, Depends(get_session)],
        x_session_token: Annotated[str | None, Header()] = None,
    ) -> None:
        """Rename the business. It arrived named after whoever signed up first."""
        account = _signed_in(session, x_session_token)
        place = _home(session, account)
        _allowed(session, account, place, "invite")
        place.name = body.name.strip()
        session.commit()

    @app.post("/v1/org/invite")
    def invite_person(
        body: InviteIn,
        session: Annotated[Session, Depends(get_session)],
        x_session_token: Annotated[str | None, Header()] = None,
    ) -> dict[str, object]:
        """Ask somebody to join, and post it to them.

        The link comes back as well as going out, because an owner whose email is
        not set up yet, or whose invitee never receives it, still has to be able
        to pass it on. It is shown once and not stored.
        """
        account = _signed_in(session, x_session_token)
        place = _home(session, account)
        _allowed(session, account, place, "invite")
        try:
            role = Role(body.role)
        except ValueError:
            raise HTTPException(400, "That is not a role.") from None
        try:
            token = invite(session, place, by=account, email=str(body.email), role=role)
        except NotAllowed as exc:
            raise HTTPException(400, f"You cannot {exc.args[0]}.") from None

        link = f"{settings.app_base_url.rstrip('/')}/invite?token={token}"
        posted = False
        try:
            send(
                _post(),
                invitation(
                    to=str(body.email),
                    business=place.name,
                    inviter=account.name or account.email,
                    role=role.value,
                    link=link,
                ),
            )
            posted = True
        except NotSent as exc:
            # The invitation exists either way; the owner can pass the link on.
            log.warning("invitation to %s not sent: %s", place.id, exc)
        return {
            "token": token,
            "email": str(body.email),
            "role": role.value,
            "link": link,
            "emailed": posted,
        }

    @app.post("/v1/org/accept", response_model=OrgOut)
    def accept_invite(
        body: dict[str, str],
        session: Annotated[Session, Depends(get_session)],
        x_session_token: Annotated[str | None, Header()] = None,
    ) -> OrgOut:
        """Take up an invitation. The address has to match the one invited."""
        account = _signed_in(session, x_session_token)
        place = accept(session, body.get("token", ""), account)
        if place is None:
            raise HTTPException(400, "That invitation is not valid for this account.")
        return read_org(session, x_session_token)

    @app.post("/v1/org/role", status_code=204)
    def set_role(
        body: RoleIn,
        session: Annotated[Session, Depends(get_session)],
        x_session_token: Annotated[str | None, Header()] = None,
    ) -> None:
        account = _signed_in(session, x_session_token)
        place = _home(session, account)
        _allowed(session, account, place, "invite")
        who = session.get(UserAccount, body.account_id)
        if who is None:
            raise HTTPException(404, "No such person.")
        try:
            change_role(session, place, who, Role(body.role))
        except ValueError:
            raise HTTPException(400, "That is not a role.") from None
        except NotAllowed as exc:
            raise HTTPException(400, f"You cannot {exc.args[0]}.") from None

    @app.delete("/v1/org/people/{account_id}", status_code=204)
    def remove_person(
        account_id: UUID,
        session: Annotated[Session, Depends(get_session)],
        x_session_token: Annotated[str | None, Header()] = None,
    ) -> None:
        account = _signed_in(session, x_session_token)
        place = _home(session, account)
        _allowed(session, account, place, "invite")
        who = session.get(UserAccount, account_id)
        if who is None:
            return
        try:
            remove(session, place, who)
        except NotAllowed as exc:
            raise HTTPException(400, f"You cannot {exc.args[0]}.") from None

    def _send_verification(account: UserAccount, secret: str) -> None:
        """Post the confirmation link, and carry on if the post is not set up."""
        if not secret:
            return
        link = f"{settings.app_base_url.rstrip('/')}/verify-email?token={secret}"
        try:
            send(_post(), verify_email(to=account.email, name=account.name, link=link))
        except NotSent as exc:
            log.warning("verification for %s not sent: %s", account.id, exc)

    @app.post("/v1/auth/register", response_model=SignedInOut)
    def register_account(
        body: RegisterIn,
        session: Annotated[Session, Depends(get_session)],
    ) -> SignedInOut:
        """Make an account with an address and a password, and post the link."""
        _may_sign_in(session, str(body.email))
        try:
            account, secret = register(
                session, email=str(body.email), password=body.password, name=body.name
            )
        except WeakPassword as exc:
            raise HTTPException(400, str(exc)) from None
        except AlreadyHere:
            raise HTTPException(
                409, "That address already has an account. Sign in, or reset the password."
            ) from None
        _send_verification(account, secret)
        token = sign_in_existing(session, account)
        return SignedInOut(token=token, person=PersonOut.of(account))

    @app.post("/v1/auth/password", response_model=SignedInOut)
    def sign_in_password(
        body: PasswordIn,
        session: Annotated[Session, Depends(get_session)],
    ) -> SignedInOut:
        """Sign in with an address and a password."""
        _may_sign_in(session, str(body.email))
        account = sign_in_with_password(session, email=str(body.email), password=body.password)
        if account is None:
            # One message for a wrong address and a wrong password: which it was
            # is not a stranger's business.
            raise HTTPException(401, "That address and password do not match.")
        token = sign_in_existing(session, account)
        return SignedInOut(token=token, person=PersonOut.of(account))

    @app.post("/v1/auth/verify", response_model=PersonOut)
    def verify_address(
        body: TokenIn,
        session: Annotated[Session, Depends(get_session)],
    ) -> PersonOut:
        account = verify(session, body.token)
        if account is None:
            raise HTTPException(400, "That link has been used already, or has expired.")
        return PersonOut.of(account)

    @app.post("/v1/auth/verify/resend", status_code=204)
    def resend_verification(
        session: Annotated[Session, Depends(get_session)],
        x_session_token: Annotated[str | None, Header()] = None,
    ) -> None:
        account = _signed_in(session, x_session_token)
        if account.email_verified_at is not None:
            return
        _send_verification(account, fresh_verification(session, account))

    @app.post("/v1/auth/forgot", status_code=204)
    def forgot_password(
        body: dict[str, str],
        session: Annotated[Session, Depends(get_session)],
    ) -> None:
        """Send a reset link, and say nothing about whether there was an account."""
        found = start_reset(session, body.get("email", ""))
        if found is None:
            return
        account, secret = found
        link = f"{settings.app_base_url.rstrip('/')}/reset-password?token={secret}"
        try:
            send(_post(), reset_password(to=account.email, name=account.name, link=link))
        except NotSent as exc:
            log.warning("reset for %s not sent: %s", account.id, exc)

    @app.post("/v1/auth/reset", response_model=SignedInOut)
    def reset_the_password(
        body: ResetIn,
        session: Annotated[Session, Depends(get_session)],
    ) -> SignedInOut:
        try:
            account = finish_reset(session, token=body.token, password=body.password)
        except WeakPassword as exc:
            raise HTTPException(400, str(exc)) from None
        if account is None:
            raise HTTPException(400, "That link has been used already, or has expired.")
        # A new password is still a way in, so it answers to the same latch.
        _may_sign_in(session, account.email)
        token = sign_in_existing(session, account)
        return SignedInOut(token=token, person=PersonOut.of(account))

    @app.post("/v1/auth/signout", status_code=204)
    def sign_out_here(
        session: Annotated[Session, Depends(get_session)],
        x_session_token: Annotated[str | None, Header()] = None,
    ) -> None:
        sign_out(session, x_session_token)

    @app.post("/v1/auth/signout-everywhere")
    def sign_out_all(
        session: Annotated[Session, Depends(get_session)],
        x_session_token: Annotated[str | None, Header()] = None,
    ) -> dict[str, int]:
        """Every session this person has, on every device, ended at once."""
        account = _signed_in(session, x_session_token)
        return {"ended": sign_out_everywhere(session, account)}

    def _permission_is_gone(exc: Exception) -> bool:
        """Google saying the grant no longer exists, in any of its wordings.

        It happens when the merchant revokes us in their Google account, when a
        testing-mode token ages out, and — the one that caught us out — when any
        token in the same grant is revoked, which takes the whole grant with it.
        """
        said = str(exc).lower()
        return "expired or revoked" in said or "invalid_grant" in said

    def _ads_ready() -> tuple[str, str]:
        """The two credentials the trip needs, or a refusal naming what is missing."""
        client_id = settings.google_oauth_client_id
        secret = settings.google_oauth_client_secret
        if not client_id or not secret:
            raise HTTPException(503, "Connecting Google Ads is not set up yet.")
        return client_id, secret.get_secret_value()

    def _signed_in(session: Session, token: str | None) -> UserAccount:
        account = _person(session, token)
        if account is None:
            raise HTTPException(401, "Sign in first.")
        return account

    def _connection(session: Session, account: UserAccount) -> AdsConnection | None:
        """Their live permission, preferring one that names an account.

        A merchant who starts the trip to Google twice leaves two rows behind.
        Picking the newest blindly can pick the one that never got as far as
        choosing an account, which then reports "connected" and reads nothing.
        """
        return session.scalar(
            select(AdsConnection)
            .where(AdsConnection.account_id == account.id, AdsConnection.revoked_at.is_(None))
            .order_by(
                (AdsConnection.customer_id.is_(None)).asc(),
                (AdsConnection.customer_id == "").asc(),
                AdsConnection.created_at.desc(),
            )
        )

    @app.post("/v1/ads/connect", response_model=ConnectStartOut)
    def start_connecting(
        session: Annotated[Session, Depends(get_session)],
        x_session_token: Annotated[str | None, Header()] = None,
    ) -> ConnectStartOut:
        """Where to send the merchant, with a state only this server could have made."""
        account = _signed_in(session, x_session_token)
        _allowed(session, account, _home(session, account), "connect")
        client_id, _ = _ads_ready()
        try:  # refuse before Google is involved, not after they have agreed
            TokenVault(
                settings.google_oauth_token_key.get_secret_value()
                if settings.google_oauth_token_key
                else None
            )
        except VaultUnavailable as exc:
            log.error("%s", exc)
            raise HTTPException(503, "Connecting Google Ads is not set up yet.") from None

        state = new_state()
        session.add(ConsentTrip(state=state, account_id=account.id))
        session.commit()
        return ConnectStartOut(
            url=consent_url(
                client_id=client_id,
                redirect_uri=settings.google_ads_redirect_uri,
                state=state,
            )
        )

    @app.post("/v1/ads/finish", response_model=AdsStatusOut)
    def finish_connecting(
        body: ConnectFinishIn,
        session: Annotated[Session, Depends(get_session)],
        x_session_token: Annotated[str | None, Header()] = None,
    ) -> AdsStatusOut:
        """The code Google sent them back with, for a permission stored encrypted."""
        account = _signed_in(session, x_session_token)
        client_id, secret = _ads_ready()

        trip = session.scalar(select(ConsentTrip).where(ConsentTrip.state == body.state))
        if trip is None or trip.used_at is not None or trip.account_id != account.id:
            # A state that was never issued, already spent, or belongs to somebody
            # else: all three mean this reply is not the one we sent them on.
            raise HTTPException(400, "That sign-in link has already been used. Start again.")

        try:
            grant = exchange_code(
                body.code,
                client_id=client_id,
                client_secret=secret,
                redirect_uri=settings.google_ads_redirect_uri,
            )
            vault = TokenVault(
                settings.google_oauth_token_key.get_secret_value()
                if settings.google_oauth_token_key
                else None
            )
        except (AdsConnectionRefused, VaultUnavailable) as exc:
            log.warning("connecting Google Ads failed: %s", exc)
            raise HTTPException(502, str(exc)) from None

        trip.used_at = datetime.now(UTC)
        for old in session.scalars(
            select(AdsConnection).where(
                AdsConnection.account_id == account.id, AdsConnection.revoked_at.is_(None)
            )
        ):
            # Connecting again replaces the last permission rather than racing it.
            old.revoked_at = datetime.now(UTC)
        place = _home(session, account)
        connection = AdsConnection(
            account_id=account.id,
            organization_id=place.id,
            ciphertext=vault.lock(grant.refresh_token),
        )
        session.add(connection)
        session.commit()
        return AdsStatusOut(connected=True)

    @app.post("/v1/ads/disconnect", status_code=204)
    def disconnect_ads(
        session: Annotated[Session, Depends(get_session)],
        x_session_token: Annotated[str | None, Header()] = None,
    ) -> None:
        """End the permission and destroy the stored key.

        The row stays, so the history shows a connection existed and when it
        ended. What does not stay is the ciphertext: a permission nobody can use
        is not a permission anybody should keep.
        """
        account = _signed_in(session, x_session_token)
        _allowed(session, account, _home(session, account), "disconnect")
        connection = _connection(session, account)
        if connection is None:
            return
        client_id = settings.google_oauth_client_id
        secret = settings.google_oauth_client_secret
        if client_id and secret and settings.google_oauth_token_key:
            # Tell Google too, so the grant ends at their end as well as ours.
            try:
                vault = TokenVault(settings.google_oauth_token_key.get_secret_value())
                revoke_permission(vault.unlock(connection.ciphertext))
            except (AdsConnectionRefused, VaultUnavailable) as exc:
                log.warning("could not tell Google the permission ended: %s", exc)
        connection.revoked_at = datetime.now(UTC)
        connection.ciphertext = ""
        session.commit()

    @app.get("/v1/ads/status", response_model=AdsStatusOut)
    def ads_status(
        session: Annotated[Session, Depends(get_session)],
        x_session_token: Annotated[str | None, Header()] = None,
    ) -> AdsStatusOut:
        account = _signed_in(session, x_session_token)
        connection = _connection(session, account)
        if connection is None:
            return AdsStatusOut(connected=False)
        return AdsStatusOut(
            connected=True,
            customer_id=connection.customer_id,
            customer_name=connection.customer_name,
        )

    @app.get("/v1/ads/business")
    def ads_business(
        session: Annotated[Session, Depends(get_session)],
        x_session_token: Annotated[str | None, Header()] = None,
    ) -> dict[str, Any]:
        """What the connected account tells us about the business it advertises.

        So that the audit stops asking for a name and a website we were handed
        when the account was connected. Everything it answers says where it came
        from, because a screen that fills itself in has to show its working.
        """
        account = _signed_in(session, x_session_token)
        connection = _connection(session, account)
        if connection is None or not connection.customer_id:
            return {"connected": False, "enough": False}
        key = (
            settings.google_maps_api_key.get_secret_value() if settings.google_maps_api_key else ""
        )
        known = known_business(
            session,
            customer_id=connection.customer_id,
            account_name=connection.customer_name,
            maps_key=key,
        )
        return {"connected": True, **known.as_dict()}

    @app.get("/v1/ads/accounts", response_model=list[AdsAccountOut])
    def ads_accounts(
        session: Annotated[Session, Depends(get_session)],
        x_session_token: Annotated[str | None, Header()] = None,
    ) -> list[AdsAccountOut]:
        """Which advertising accounts their permission reaches. See `ads.accounts`."""
        account = _signed_in(session, x_session_token)
        _allowed(session, account, _home(session, account), "connect")
        connection = _connection(session, account)
        if connection is None:
            raise HTTPException(404, "No Google Ads account is connected.")
        if not settings.google_ads_developer_token:
            raise HTTPException(503, "Reading Google Ads is not set up yet.")
        client_id, secret = _ads_ready()
        try:
            vault = TokenVault(
                settings.google_oauth_token_key.get_secret_value()
                if settings.google_oauth_token_key
                else None
            )
            access = fresh_access_token(
                vault.unlock(connection.ciphertext), client_id=client_id, client_secret=secret
            )
            found = accessible_accounts(
                access_token=access,
                developer_token=settings.google_ads_developer_token.get_secret_value(),
                api_version=settings.google_ads_api_version,
                login_customer_id=settings.google_ads_login_customer_id,
            )
        except (AdsConnectionRefused, VaultUnavailable) as exc:
            log.warning("reading Google Ads accounts failed: %s", exc)
            raise HTTPException(502, str(exc)) from None
        return [
            AdsAccountOut(
                customer_id=a.customer_id,
                name=a.name,
                is_manager=a.is_manager,
                currency=a.currency,
                time_zone=a.time_zone,
                readable=a.readable,
                trouble=a.trouble,
            )
            for a in found
        ]

    @app.get("/v1/ads/summary")
    def ads_summary(
        session: Annotated[Session, Depends(get_session)],
        days: int = 30,
        x_session_token: Annotated[str | None, Header()] = None,
    ) -> dict[str, Any]:
        """The numbers the dashboard home is built from, for the chosen account.

        Our own mirror answers this, not Google: one pass over a local table
        instead of four round trips to California, which is what makes the
        two-second dashboard in the requirements reachable and what pays for the
        comparison with the period before.

        Google is asked only when the mirror holds nothing — the minutes between
        connecting an account and the first sync finishing. A merchant with no
        connection or no chosen account gets `read: false` and a sentence, not an
        error: the home screen has plenty to show without it.
        """
        account = _signed_in(session, x_session_token)
        connection = _connection(session, account)
        if connection is None:
            return {"read": False, "trouble": "No Google Ads account is connected yet."}
        if not connection.customer_id:
            return {
                "read": False,
                "choose": True,
                "trouble": "Choose which of your Google Ads accounts we read.",
            }
        window = days if days in (7, 30, 90) else 30
        held = account_numbers(
            session, connection.customer_id, days=window, currency=connection.currency
        )
        if held.read:
            return held.as_dict()
        if settings.google_ads_developer_token is None:
            return {"read": False, "trouble": "Reading Google Ads is not set up yet."}
        client_id, secret = _ads_ready()
        try:
            vault = TokenVault(
                settings.google_oauth_token_key.get_secret_value()
                if settings.google_oauth_token_key
                else None
            )
            access = fresh_access_token(
                vault.unlock(connection.ciphertext), client_id=client_id, client_secret=secret
            )
            found = account_summary(
                connection.customer_id,
                access_token=access,
                developer_token=settings.google_ads_developer_token.get_secret_value(),
                days=window,
                api_version=settings.google_ads_api_version,
                login_customer_id=settings.google_ads_login_customer_id,
            )
        except (AdsConnectionRefused, VaultUnavailable) as exc:
            log.warning("home numbers failed for account %s: %s", account.id, exc)
            if _permission_is_gone(exc):
                # The grant is gone at Google's end, so stop claiming it is here.
                connection.revoked_at = datetime.now(UTC)
                session.commit()
                return {
                    "read": False,
                    "reconnect": True,
                    "trouble": "Google has ended this permission. Connect again to carry on.",
                }
            return {"read": False, "trouble": "We could not read your Google Ads account."}
        return {**found.as_dict(), "source": "live"}

    @app.get("/v1/ads/campaigns/{campaign_id}")
    def ads_campaign(
        campaign_id: str,
        session: Annotated[Session, Depends(get_session)],
        days: int = 30,
        x_session_token: Annotated[str | None, Header()] = None,
    ) -> dict[str, Any]:
        """One campaign: its numbers, its parts, its change history and its ads.

        Both at once. What the campaign is made of and what it did day by day
        are ours, out of the mirror; what each keyword and each ad did is
        Google's own reporting, read live and laid on top. Either half can fail
        without taking the page with it: a campaign that shows its keywords and
        says it could not read the search terms is more use than an error.
        """
        if not campaign_id.isdigit():
            raise HTTPException(404, "No campaign with that id.")
        account = _signed_in(session, x_session_token)
        connection = _connection(session, account)
        if connection is None:
            return {"read": False, "trouble": "No Google Ads account is connected yet."}
        if not connection.customer_id:
            return {
                "read": False,
                "choose": True,
                "trouble": "Choose which of your Google Ads accounts we read.",
            }
        window = days if days in (7, 30, 90) else 30
        held = campaign_numbers(
            session,
            connection.customer_id,
            campaign_id,
            days=window,
            currency=connection.currency,
        )

        live: dict[str, Any] = {}
        gone = False
        if settings.google_ads_developer_token is not None:
            client_id, secret = _ads_ready()
            try:
                vault = TokenVault(
                    settings.google_oauth_token_key.get_secret_value()
                    if settings.google_oauth_token_key
                    else None
                )
                access = fresh_access_token(
                    vault.unlock(connection.ciphertext), client_id=client_id, client_secret=secret
                )
                live = campaign_detail(
                    connection.customer_id,
                    campaign_id,
                    access_token=access,
                    developer_token=settings.google_ads_developer_token.get_secret_value(),
                    days=window,
                    api_version=settings.google_ads_api_version,
                    login_customer_id=settings.google_ads_login_customer_id,
                ).as_dict()
            except (AdsConnectionRefused, VaultUnavailable) as exc:
                log.warning("campaign %s unreadable for %s: %s", campaign_id, account.id, exc)
                if _permission_is_gone(exc):
                    connection.revoked_at = datetime.now(UTC)
                    session.commit()
                    gone = True

        if held.read:
            answer = merge_live(held, live).as_dict()
        elif live.get("read"):
            answer = {**live, "source": "live", "metrics_read": True}
        else:
            answer = {
                "read": False,
                "campaign_id": campaign_id,
                "trouble": held.trouble or "We could not read that campaign.",
            }
        if gone:
            answer["reconnect"] = True
            answer["trouble"] = "Google has ended this permission."
        return answer

    @app.post("/v1/ads/choose", response_model=AdsStatusOut)
    def choose_account(
        body: ChooseAccountIn,
        session: Annotated[Session, Depends(get_session)],
        x_session_token: Annotated[str | None, Header()] = None,
    ) -> AdsStatusOut:
        """Remember which account to read.

        The id is checked against what Google says this permission reaches, so a
        number typed by hand cannot be stored as though it were theirs.
        """
        account = _signed_in(session, x_session_token)
        _allowed(session, account, _home(session, account), "connect")
        connection = _connection(session, account)
        if connection is None:
            raise HTTPException(404, "No Google Ads account is connected.")
        if not settings.google_ads_developer_token:
            raise HTTPException(503, "Reading Google Ads is not set up yet.")
        client_id, secret = _ads_ready()
        wanted = body.customer_id.replace("-", "")
        try:
            vault = TokenVault(
                settings.google_oauth_token_key.get_secret_value()
                if settings.google_oauth_token_key
                else None
            )
            access = fresh_access_token(
                vault.unlock(connection.ciphertext), client_id=client_id, client_secret=secret
            )
            theirs = accessible_accounts(
                access_token=access,
                developer_token=settings.google_ads_developer_token.get_secret_value(),
                api_version=settings.google_ads_api_version,
                login_customer_id=settings.google_ads_login_customer_id,
            )
        except (AdsConnectionRefused, VaultUnavailable) as exc:
            log.warning("choosing a Google Ads account failed: %s", exc)
            raise HTTPException(502, str(exc)) from None

        picked = next((a for a in theirs if a.customer_id == wanted), None)
        if picked is None:
            raise HTTPException(404, "That account is not one Google says you can reach.")
        connection.customer_id = picked.customer_id
        connection.customer_name = picked.name
        connection.currency = picked.currency
        session.commit()
        return AdsStatusOut(
            connected=True,
            customer_id=picked.customer_id,
            customer_name=picked.name,
            trouble=picked.trouble,
        )

    @app.post("/v1/ads/sync", response_model=SyncOut, status_code=202)
    def refresh_now(
        tasks: BackgroundTasks,
        session: Annotated[Session, Depends(get_session)],
        x_session_token: Annotated[str | None, Header()] = None,
    ) -> SyncOut:
        """Read the account again, now, because somebody asked.

        The requirements ask for a refresh on demand beside the scheduled ones.
        A sync already running is handed back rather than started twice: two
        passes over the same account would race each other to write the same rows.
        """
        account = _signed_in(session, x_session_token)
        connection = _connection(session, account)
        if connection is None or not connection.customer_id:
            raise HTTPException(404, "No Google Ads account is connected.")
        running = session.scalars(
            select(SyncRun)
            .where(SyncRun.customer_id == connection.customer_id, SyncRun.status == "running")
            .order_by(SyncRun.started_at.desc())
        ).first()
        if running is not None:
            return SyncOut.of(running)
        # What decides the kind is what the mirror holds, not what has run. An
        # account connected before the mirror existed has completed syncs and no
        # history at all, and would otherwise never be given any.
        held_days = (
            session.scalar(
                select(func.count(func.distinct(CampaignDay.day))).where(
                    CampaignDay.customer_id == connection.customer_id
                )
            )
            or 0
        )
        kind = "manual" if held_days >= ENOUGH_HISTORY else "first"
        opened = SyncRun(
            customer_id=connection.customer_id,
            kind=kind,
            status="running",
            stage="Asking Google for your account",
        )
        session.add(opened)
        session.commit()
        tasks.add_task(_sync, opened.id, connection.id, settings, kind)
        return SyncOut.of(opened)

    @app.get("/v1/ads/sync", response_model=SyncStateOut)
    def sync_state(
        session: Annotated[Session, Depends(get_session)],
        x_session_token: Annotated[str | None, Header()] = None,
    ) -> SyncStateOut:
        """What the mirror holds, and what the last look at Google found.

        This is what the Get started screen polls while the first sync runs, and
        what every screen will later use to say when it last looked.
        """
        account = _signed_in(session, x_session_token)
        connection = _connection(session, account)
        if connection is None or not connection.customer_id:
            return SyncStateOut(connected=False)
        customer_id = connection.customer_id
        latest = session.scalars(
            select(SyncRun)
            .where(SyncRun.customer_id == customer_id)
            .order_by(SyncRun.started_at.desc())
        ).first()
        done = session.scalars(
            select(SyncRun)
            .where(SyncRun.customer_id == customer_id, SyncRun.status == "done")
            .order_by(SyncRun.started_at.desc())
        ).first()
        held = {
            "campaigns": session.scalar(
                select(func.count())
                .select_from(MirrorCampaign)
                .where(MirrorCampaign.customer_id == customer_id, MirrorCampaign.gone_at.is_(None))
            )
            or 0,
            "days": session.scalar(
                select(func.count(func.distinct(CampaignDay.day))).where(
                    CampaignDay.customer_id == customer_id
                )
            )
            or 0,
        }
        changes = session.scalars(
            select(ExternalChange)
            .where(ExternalChange.customer_id == customer_id)
            .order_by(ExternalChange.noticed_at.desc())
            .limit(10)
        ).all()
        return SyncStateOut(
            connected=True,
            customer_name=connection.customer_name,
            run=SyncOut.of(latest) if latest else None,
            last_done_at=done.finished_at if done else None,
            held=held,
            changes=[
                ChangeOut(kind=c.kind, label=c.label, summary=c.summary, noticed_at=c.noticed_at)
                for c in changes
            ],
        )

    @app.get("/v1/reports")
    def account_report(
        session: Annotated[Session, Depends(get_session)],
        days: int = 30,
        x_session_token: Annotated[str | None, Header()] = None,
    ) -> dict[str, Any]:
        """The report: this period, the one before, and the same period a year ago.

        All three come out of the mirror, so year on year costs a query rather
        than a round trip, and every figure carries a verdict in plain words
        instead of an arrow.
        """
        account = _signed_in(session, x_session_token)
        connection = _connection(session, account)
        if connection is None:
            return {"read": False, "trouble": "No Google Ads account is connected yet."}
        if not connection.customer_id:
            return {
                "read": False,
                "choose": True,
                "trouble": "Choose which of your Google Ads accounts we read.",
            }
        window = days if days in (7, 30, 90) else 30
        report = report_for(
            session, connection.customer_id, days=window, currency=connection.currency
        )
        answer = report.as_dict()
        answer["business"] = connection.customer_name
        answer["shares"] = [
            {
                "id": str(link.id),
                "expires_at": link.expires_at.isoformat(),
                "opened": link.opened,
                "sent_to": link.sent_to,
            }
            for link in session.scalars(
                select(ShareLink).where(
                    ShareLink.kind == "report",
                    ShareLink.subject == connection.customer_id,
                    ShareLink.revoked_at.is_(None),
                )
            )
        ]
        return answer

    @app.post("/v1/reports/share", response_model=ShareOut, status_code=201)
    def share_report(
        body: ShareIn,
        session: Annotated[Session, Depends(get_session)],
        x_session_token: Annotated[str | None, Header()] = None,
    ) -> ShareOut:
        """A link to this account's report that needs no login and expires."""
        account = _signed_in(session, x_session_token)
        place = _home(session, account)
        _allowed(session, account, place, "share")
        connection = _connection(session, account)
        if connection is None or not connection.customer_id:
            raise HTTPException(404, "No Google Ads account is connected.")
        link, token = make_link(
            session,
            kind="report",
            subject=connection.customer_id,
            days=body.days,
            organization_id=place.id,
            made_by=account.id,
        )
        return ShareOut(
            url=f"{settings.app_base_url.rstrip('/')}/r/{token}",
            expires_at=link.expires_at,
            id=str(link.id),
        )

    @app.delete("/v1/reports/share/{link_id}", status_code=204)
    def stop_sharing(
        link_id: UUID,
        session: Annotated[Session, Depends(get_session)],
        x_session_token: Annotated[str | None, Header()] = None,
    ) -> None:
        """Stop a shared link working, keeping the record that it existed."""
        account = _signed_in(session, x_session_token)
        place = _home(session, account)
        _allowed(session, account, place, "share")
        link = session.get(ShareLink, link_id)
        if link is None or link.organization_id != place.id:
            raise HTTPException(404, "No such link.")
        revoke(session, link)

    # ---- The free audit page, which is open to anybody ----------------
    #
    # The score and the counts are shown to whoever runs an audit. The
    # findings wait until the address is proved, which is the page's bargain
    # and the client's requirement: paid traffic in, verified leads out.

    def _lead_run(session: Session, run_id: UUID) -> tuple[AuditRun, AuditRequest | None]:
        run = session.get(AuditRun, run_id)
        if run is None:
            raise HTTPException(404, "No audit with that id.")
        asked = session.get(AuditRequest, run.request_id) if run.request_id else None
        return run, asked

    def _progress(run: AuditRun, asked: AuditRequest | None) -> dict[str, Any]:
        done = run.status == "done"
        out: dict[str, Any] = {
            "audit_id": str(run.id),
            "status": run.status,
            "stages": stages_at(run.stage, done=done),
            "percent": percent_at(run.stage, done=done),
            "pages_read": run.pages_read,
        }
        if run.status == "failed":
            out["error"] = "We could not finish checking that website."
        if done:
            score = _score_of(run) or 0
            out["summary"] = summary_of(run, asked, score=score).as_dict()
            out["verified"] = asked is not None and asked.verified_at is not None
        return out

    def _unlocked(session: Session, run: AuditRun, asked: AuditRequest | None) -> dict[str, Any]:
        """The whole report, plus a link that opens it again on any device."""
        score = _score_of(run) or 0
        full = report_of(run, asked, score=score).as_dict()
        _, token = make_link(session, kind="audit", subject=str(run.id), days=30)
        full["open_again"] = f"{settings.app_base_url.rstrip('/')}/audit/open/{token}"
        return full

    @app.post("/v1/public/identify")
    def identify_business(body: IdentifyIn) -> dict[str, Any]:
        """What sort of business this looks like, for the person to confirm.

        Asked between the first step and the second, so the kind is settled
        before anything is checked. Nothing here is binding: whatever it says,
        the screen shows it and the person can say otherwise.

        It never claims to have read their Google Business Profile category.
        That is a different and far longer list, it is not public, and saying
        we read it would be a lie somebody could catch us in.
        """
        key = (
            settings.google_maps_api_key.get_secret_value() if settings.google_maps_api_key else ""
        )
        listing: Listing | None = None
        matched = False
        if key and body.place_id.strip():
            # They picked it themselves, so there is nothing left to infer.
            try:
                listing = place_details(body.place_id.strip(), api_key=key)
                matched = listing is not None
            except PlacesError as exc:
                log.warning("could not read the listing they picked: %s", exc)
        elif key:
            listing, matched = listing_for(body.business_name, body.site, api_key=key)

        guess = classify(
            primary_type=listing.primary_type if listing else "",
            types=listing.types if listing else (),
            maps_label=listing.maps_label if listing else "",
            business_name=body.business_name,
            open_24h=listing.open_24h if listing else False,
        )
        if listing is not None and not matched:
            # A listing we are not certain belongs to them cannot make us
            # certain of anything it says about them.
            guess = replace(
                guess,
                sure=False,
                because=(
                    f"We found “{listing.name}” on Google, but its website is not the one "
                    "you gave us. Check this is you."
                ),
            )

        return {
            "found": listing is not None,
            "matched": matched,
            "listing_name": listing.name if listing else "",
            "place_id": listing.place_id if listing else "",
            **guess.as_dict(),
            "choices": [
                {"kind": one.value, "label": SAID[one][0], "about": SAID[one][1]} for one in Kind
            ],
        }

    @app.post("/v1/public/audits", status_code=202)
    def start_public_audit(
        body: PublicAuditIn,
        tasks: BackgroundTasks,
        session: Annotated[Session, Depends(get_session)],
        x_session_token: Annotated[str | None, Header()] = None,
    ) -> dict[str, Any]:
        """Start the free audit. Open to anybody; no account, no password."""
        site = normalise_site(body.site)
        recent = (
            session.scalar(
                select(func.count())
                .select_from(AuditRun)
                .where(
                    AuditRun.site == site,
                    AuditRun.created_at >= datetime.now(UTC) - timedelta(hours=1),
                )
            )
            or 0
        )
        if recent >= 6:
            raise HTTPException(429, "That website has been checked several times just now.")

        asked_by = _person(session, x_session_token)
        asked = AuditRequest(
            name="",
            email="",
            phone="",
            business_name=body.business_name.strip(),
            site=body.site,
            source="landing",
            runner=body.runner,
            goal=body.goal,
            kind=body.kind,
            kind_is_theirs=body.kind_is_theirs,
            place_id=body.place_id.strip(),
            spend_band=body.spend_band,
            came_from=body.came_from or None,
            user_id=asked_by.id if asked_by else None,
            consent_text="",
        )
        run = AuditRun(site=site, status="queued")
        session.add(asked)
        session.flush()
        run.request_id = asked.id
        session.add(run)
        session.commit()
        tasks.add_task(_run, run.id, settings)
        return {"audit_id": str(run.id), "status": run.status}

    @app.get("/v1/public/audits/{run_id}")
    def public_audit(
        run_id: UUID,
        session: Annotated[Session, Depends(get_session)],
    ) -> dict[str, Any]:
        """Where the run has got to, and the summary once it is finished.

        Never the findings. Those have their own door.
        """
        run, asked = _lead_run(session, run_id)
        return _progress(run, asked)

    @app.post("/v1/public/audits/{run_id}/lead")
    def public_lead(
        run_id: UUID,
        body: LeadIn,
        session: Annotated[Session, Depends(get_session)],
    ) -> dict[str, Any]:
        """Keep who asked, then post them a code."""
        run, asked = _lead_run(session, run_id)
        if asked is None:
            raise HTTPException(404, "No audit with that id.")
        if run.status != "done":
            raise HTTPException(409, "That audit has not finished yet.")

        take_the_lead(
            session,
            asked,
            name=body.name,
            email=str(body.email),
            phone=body.phone,
            tips_opt_in=body.tips_opt_in,
            came_from=body.came_from or None,
            consent_text=CONSENT_TEXT,
        )
        posted = post_a_code(session, asked, force=True)
        _send_code(session, run, asked, posted.code)
        return {"sent": True, "email": asked.email}

    @app.post("/v1/public/audits/{run_id}/resend")
    def public_resend(
        run_id: UUID,
        session: Annotated[Session, Depends(get_session)],
    ) -> dict[str, Any]:
        """Another code, unless one went out moments ago."""
        run, asked = _lead_run(session, run_id)
        if asked is None or not asked.email:
            raise HTTPException(409, "Ask for a code first.")
        posted = post_a_code(session, asked)
        if posted.too_soon:
            return {"sent": False, "wait_seconds": posted.wait_seconds}
        _send_code(session, run, asked, posted.code)
        return {"sent": True, "email": asked.email}

    @app.post("/v1/public/audits/{run_id}/verify")
    def public_verify(
        run_id: UUID,
        body: CodeIn,
        session: Annotated[Session, Depends(get_session)],
    ) -> dict[str, Any]:
        """Six digits, and then everything."""
        run, asked = _lead_run(session, run_id)
        if asked is None or not asked.email:
            raise HTTPException(409, "Ask for a code first.")
        answer = check_code(session, asked, body.code)
        if answer is not Answer.RIGHT:
            raise HTTPException(400, answer.said)
        log.info("audit %s unlocked by a verified address", run.id)
        return {"verified": True, **_unlocked(session, run, asked)}

    @app.get("/v1/public/audits/open/{token}")
    def public_open(
        token: str,
        session: Annotated[Session, Depends(get_session)],
    ) -> dict[str, Any]:
        """The link in the email, which opens the report on any device."""
        link = open_link(session, token, kind="audit")
        if link is None:
            raise HTTPException(404, "That link does not open anything.")
        run, asked = _lead_run(session, UUID(link.subject))
        if run.status != "done":
            raise HTTPException(409, "That audit has not finished yet.")
        return {"verified": True, **_unlocked(session, run, asked)}

    def _send_code(session: Session, run: AuditRun, asked: AuditRequest, code: str) -> None:
        """Post the code, with a link that does the same job on another device."""
        if not code:
            return
        _, token = make_link(session, kind="audit", subject=str(run.id), days=1)
        url = f"{settings.app_base_url.rstrip('/')}/audit/open/{token}"
        try:
            send(
                _post(),
                audit_code(
                    to=asked.email,
                    business=asked.business_name or run.site,
                    code=code,
                    link=url,
                ),
            )
        except NotSent as exc:
            log.warning("the audit code did not go to %s: %s", asked.email, exc)
            raise HTTPException(502, "We could not send that email just now.") from exc

    @app.get("/v1/public/report/{token}")
    def shared_report(
        token: str,
        session: Annotated[Session, Depends(get_session)],
    ) -> dict[str, Any]:
        """A shared report, to whoever holds the link. Nobody signs in here.

        It answers with the report and the business name and nothing else: no
        addresses, no people, no other accounts. A token that is wrong, expired
        or revoked gets the same flat refusal, because saying which would be
        telling somebody about a link they do not hold.
        """
        link = open_link(session, token, kind="report")
        if link is None:
            raise HTTPException(404, "That link has expired or does not exist.")
        connection = session.scalars(
            select(AdsConnection).where(AdsConnection.customer_id == link.subject).limit(1)
        ).first()
        report = report_for(
            session,
            link.subject,
            days=30,
            currency=connection.currency if connection else "",
        )
        answer = report.as_dict()
        answer["business"] = connection.customer_name if connection else ""
        answer["shared"] = True
        answer["expires_at"] = link.expires_at.isoformat()
        return answer

    @app.post("/v1/audits/{run_id}/share", response_model=ShareOut, status_code=201)
    def share_fixes(
        run_id: UUID,
        body: FixListIn,
        session: Annotated[Session, Depends(get_session)],
        x_session_token: Annotated[str | None, Header()] = None,
    ) -> ShareOut:
        """Send the fix list to whoever looks after the website.

        The person who has to do the work almost never has a PPCway account, so
        this is a link that needs no login, and the letter says plainly that it
        is a list of findings about a website rather than anything to sign into.
        """
        account = _signed_in(session, x_session_token)
        place = _home(session, account)
        _allowed(session, account, place, "share")
        run = session.get(AuditRun, run_id)
        if run is None or run.status != "done":
            raise HTTPException(404, "No finished audit with that id.")
        link, token = make_link(
            session,
            kind="fixes",
            subject=str(run.id),
            days=body.days,
            organization_id=place.id,
            made_by=account.id,
            sent_to=body.email or "",
        )
        url = f"{settings.app_base_url.rstrip('/')}/fixes/{token}"
        emailed = False
        if body.email:
            jobs = _fix_count(run)
            try:
                send(
                    _post(),
                    fix_list(
                        to=body.email,
                        business=place.name,
                        site=run.site,
                        link=url,
                        jobs=jobs,
                        from_name=account.name or account.email,
                    ),
                )
                emailed = True
            except NotSent as exc:
                log.warning("the fix list did not go to %s: %s", body.email, exc)
        return ShareOut(url=url, expires_at=link.expires_at, id=str(link.id), emailed=emailed)

    @app.post("/v1/audits/{run_id}/email", response_model=EmailedOut)
    def email_audit(
        run_id: UUID,
        body: EmailAuditIn,
        session: Annotated[Session, Depends(get_session)],
        x_session_token: Annotated[str | None, Header()] = None,
    ) -> EmailedOut:
        """Send a finished audit to an inbox. It does not run anything.

        The button that asks for this sits on the report, so the work is already
        done and this is the post, not the audit. Which address it may use is
        the whole of the thinking:

        - signed in, their own and nothing the body asks for, so the most
          anybody can do with a session is mail themselves;
        - signed out on a run nobody has given an address for, the one they
          type, which is then kept — that is the free audit's own promise;
        - signed out on a run that already has an address, only that address,
          so this cannot be pointed at a stranger.
        """
        run = session.get(AuditRun, run_id)
        if run is None:
            raise HTTPException(404, "No audit with that id.")
        score = _score_of(run)
        if run.status != "done" or score is None:
            raise HTTPException(409, "That audit has not finished yet.")

        asked = session.get(AuditRequest, run.request_id) if run.request_id else None
        account = _person(session, x_session_token)
        typed = str(body.email).lower().strip() if body.email else ""
        if account is not None:
            to = account.email
        elif asked is not None and asked.email:
            if typed and typed != asked.email:
                raise HTTPException(403, "That audit is already going to another address.")
            to = asked.email
        elif typed:
            to = typed
        else:
            raise HTTPException(400, "Tell us where to send it.")

        try:
            send(_post(), _audit_letter(run, asked, settings, to, score))
        except NotSent as exc:
            log.warning("the audit of %s did not go to %s: %s", run.site, to, exc)
            raise HTTPException(502, "We could not send that email just now.") from exc

        # Signed out and never asked before: remember it, so a second press
        # cannot turn this into a way of mailing somebody else.
        if account is None and asked is not None and not asked.email:
            asked.email = to
            session.commit()
        return EmailedOut(sent_to=to)

    @app.get("/v1/public/fixes/{token}")
    def shared_fixes(
        token: str,
        session: Annotated[Session, Depends(get_session)],
    ) -> dict[str, Any]:
        """The fix list behind a shared link. Nobody signs in here either."""
        link = open_link(session, token, kind="fixes")
        if link is None:
            raise HTTPException(404, "That link has expired or does not exist.")
        run = session.get(AuditRun, UUID(link.subject))
        if run is None or not run.report:
            raise HTTPException(404, "That audit is no longer here.")
        findings = (run.report or {}).get("findings") or []
        return {
            "site": run.site,
            "checked_at": run.finished_at.isoformat() if run.finished_at else None,
            "score": _score_of(run),
            "expires_at": link.expires_at.isoformat(),
            "jobs": [
                {
                    "title": f.get("title", ""),
                    "summary": f.get("summary", ""),
                    "detail": f.get("detail") or [],
                    "fix": f.get("fix", ""),
                }
                for f in findings
                if f.get("status") == "needs_you"
            ],
            "fine": [
                {"title": f.get("title", ""), "summary": f.get("summary", "")}
                for f in findings
                if f.get("status") == "good"
            ],
        }

    @app.get("/v1/audits/history")
    def audit_history(
        session: Annotated[Session, Depends(get_session)],
        site: str = "",
        x_session_token: Annotated[str | None, Header()] = None,
    ) -> dict[str, Any]:
        """Every reading for one site, and what changed since last time.

        Scoped to the business, because two businesses can audit the same
        address — an agency and its client often do — and neither should see the
        other's history.
        """
        account = _signed_in(session, x_session_token)
        place = _home(session, account)
        wanted = normalise_site(site) if site else ""
        if not wanted:
            latest = session.scalars(
                select(AuditRun)
                .join(AuditRequest, AuditRun.request_id == AuditRequest.id)
                .where(
                    AuditRequest.organization_id == place.id,
                    AuditRun.status == "done",
                )
                .order_by(AuditRun.finished_at.desc())
                .limit(1)
            ).first()
            if latest is None:
                return {"site": "", "points": [], "changed": None}
            wanted = latest.site
        points = score_history(session, wanted, organization_id=place.id)
        return {
            "site": wanted,
            "points": [p.as_dict() for p in points],
            "changed": what_changed(session, wanted, organization_id=place.id).as_dict(),
        }

    @app.post("/v1/internal/audit")
    def scheduled_audit(
        tasks: BackgroundTasks,
        x_sync_key: Annotated[str | None, Header()] = None,
    ) -> dict[str, Any]:
        """Re-run every audit that is due, for the nightly scheduler.

        The website is read daily; the parts Google charges for are re-read
        weekly and carried forward in between. A site with a run already in
        flight is left alone, so calling this twice starts nothing twice.
        """
        expected = settings.sync_key.get_secret_value() if settings.sync_key else ""
        if not expected or not x_sync_key or not compare_digest(x_sync_key, expected):
            raise HTTPException(403, "Not for you.")
        factory = session_factory()
        started: list[dict[str, Any]] = []
        with factory() as own:
            for due in due_audits(own):
                run = AuditRun(
                    request_id=due.request_id,
                    site=due.site,
                    status="queued",
                    kind="scheduled",
                )
                own.add(run)
                own.commit()
                tasks.add_task(_run, run.id, settings, with_demand=due.with_demand)
                started.append(
                    {
                        "run_id": str(run.id),
                        "site": due.site,
                        "because": due.because,
                        "with_demand": due.with_demand,
                    }
                )
        return {"started": len(started), "runs": started}

    @app.post("/v1/internal/alerts")
    def scheduled_alerts(
        x_sync_key: Annotated[str | None, Header()] = None,
    ) -> dict[str, int]:
        """The things worth interrupting somebody for, for the hourly watcher.

        One letter per thing per day per business, so calling this every hour
        sends one email about the same refused ad rather than twelve.
        """
        expected = settings.sync_key.get_secret_value() if settings.sync_key else ""
        if not expected or not x_sync_key or not compare_digest(x_sync_key, expected):
            raise HTTPException(403, "Not for you.")
        with session_factory()() as own:
            return post_alerts(own, settings)

    @app.get("/v1/internal/gate")
    def phase_one_gate(
        x_sync_key: Annotated[str | None, Header()] = None,
    ) -> dict[str, Any]:
        """Where the seven-days-on-five-accounts gate stands, counted.

        Behind the sync key rather than open: it names every connected account
        and why its syncing failed, which is nobody's business but ours.
        """
        expected = settings.sync_key.get_secret_value() if settings.sync_key else ""
        if not expected or not x_sync_key or not compare_digest(x_sync_key, expected):
            raise HTTPException(403, "Not for you.")
        with session_factory()() as own:
            return gate_report(own).as_dict()

    @app.post("/v1/internal/sync")
    def scheduled_sync(
        kind: Annotated[str, Query(pattern="^(structure|today|backfill)$")] = "structure",
        x_sync_key: Annotated[str | None, Header()] = None,
    ) -> dict[str, Any]:
        """Every connected account, for the scheduler that calls on the clock.

        Not a public door: without a key in the settings it refuses outright
        rather than running for whoever finds the address, and the key is
        compared in constant time.
        """
        expected = settings.sync_key.get_secret_value() if settings.sync_key else ""
        if not expected or not x_sync_key or not compare_digest(x_sync_key, expected):
            raise HTTPException(403, "Not for you.")
        return {"kind": kind, **sync_everyone(settings, session_factory(), kind=kind)}

    @app.post("/v1/internal/post")
    def scheduled_post(
        x_sync_key: Annotated[str | None, Header()] = None,
    ) -> dict[str, Any]:
        """The weekly summary, for the Monday morning scheduler.

        Safe to call twice: one row a week per account is written, and an
        account that already has this week's post is passed over. The same key
        as the sync, compared in constant time.
        """
        expected = settings.sync_key.get_secret_value() if settings.sync_key else ""
        if not expected or not x_sync_key or not compare_digest(x_sync_key, expected):
            raise HTTPException(403, "Not for you.")
        with session_factory()() as own:
            return post_weekly(own, settings)

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


def _fix_count(run: AuditRun) -> int:
    """How many findings are asking for work, for the letter's first line."""
    findings = (run.report or {}).get("findings") or []
    return sum(1 for f in findings if f.get("status") == "needs_you")


#: The arithmetic lives with the audit rather than with the API, because the
#: history chart and the shared fix list need the same number. Kept under this
#: name because every screen here and its test already asks for it by it.
_score_of = score_of


def _paper(run_id: UUID, settings: Settings) -> Path:
    """The report as a PDF, printed once and kept beside its screenshots.

    Cloud Run gives every instance its own disk, so "kept" means kept here: a
    request that lands on another instance prints it again rather than failing.
    Printing happens when the run finishes, so in the ordinary case it is
    already on the disk of the instance that asked for it.
    """
    path = Path(settings.audit_shots_dir) / str(run_id) / "report.pdf"
    if path.exists() and path.stat().st_size > 0:
        return path
    made = to_pdf(f"{settings.app_base_url.rstrip('/')}/audit/{run_id}?paper=1")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(made)
    return path


def _print_it(run_id: UUID, settings: Settings) -> None:
    """Print now, so that whoever asks for the PDF first does not wait for it."""
    try:
        _paper(run_id, settings)
    except (NotPrinted, OSError) as exc:
        log.warning("audit %s could not be printed: %s", run_id, exc)


def _their_listing(
    run_id: UUID, settings: Settings, factory: sessionmaker[Session]
) -> tuple[Listing | None, list[Listing]]:
    """Their Google listing and the businesses nearby, read fresh.

    Never from anything stored: Google's terms let us keep the place id and
    nothing else, so the listing is read again every time it is used.
    """
    if settings.google_maps_api_key is None:
        return None, []
    key = settings.google_maps_api_key.get_secret_value()

    with factory() as session:
        run = session.get(AuditRun, run_id)
        asked = session.get(AuditRequest, run.request_id) if run and run.request_id else None
        if asked is None:
            return None, []
        place_id, name, city, site = asked.place_id, asked.business_name, asked.city, asked.site

    try:
        mine: Listing | None = None
        if place_id:
            mine = place_details(place_id, api_key=key)
        elif name:
            # No listing was confirmed, so only a website match is good enough
            # to audit somebody's listing by.
            mine, matched = listing_for(name, site, api_key=key)
            if not matched:
                mine = None
        if mine is None:
            return None, []
        return mine, list(nearby_rivals(mine, api_key=key, city=city))
    except PlacesError as exc:
        log.warning("audit %s could not read the Google listing: %s", run_id, exc)
        return None, []


def _kind_of(run_id: UUID, factory: sessionmaker[Session]) -> Kind:
    """What sort of business this run is for.

    Anything we never worked out is OTHER, which asks the questions that are
    true of every business and none of the ones that are not.
    """
    with factory() as session:
        run = session.get(AuditRun, run_id)
        asked = session.get(AuditRequest, run.request_id) if run and run.request_id else None
    named = asked.kind if asked else ""
    try:
        return Kind(named)
    except ValueError:
        return Kind.OTHER


def _mailer(settings: Settings) -> Post:
    """How this deployment sends email, from settings alone.

    Module level because the background run sends too, and it has settings but
    not the application that was built around them.
    """
    return Post(
        sender=settings.email_from,
        provider=settings.email_provider,
        api_key=settings.resend_api_key.get_secret_value() if settings.resend_api_key else "",
        smtp_host=settings.smtp_host,
        smtp_port=settings.smtp_port,
        smtp_user=settings.smtp_user,
        smtp_password=(settings.smtp_password.get_secret_value() if settings.smtp_password else ""),
    )


def _audit_letter(
    run: AuditRun,
    asked: AuditRequest | None,
    settings: Settings,
    to: str,
    score: int,
) -> Letter:
    """One finished audit, as a letter to one person.

    The link is the report's own public address rather than a share token: the
    audit is already readable by anybody holding its id, and a person who asked
    for their own report should not have it expire under them.
    """
    business = (asked.business_name if asked else "") or run.site
    link = f"{settings.app_base_url.rstrip('/')}/audit/{run.id}"
    paper = b""
    try:
        paper = _paper(run.id, settings).read_bytes()
    except (NotPrinted, OSError) as exc:
        # A letter with a link and no attachment is still the report. Losing
        # the email over a printer would be the worse trade.
        log.warning("the audit of %s went without its PDF: %s", run.site, exc)
    return audit_ready(to=to, business=business, score=score, link=link, paper=paper)


def _tell_them(run: AuditRun, session: Session, settings: Settings) -> None:
    """Email the report to whoever asked for it when they started the run.

    "You can stay on this page, or give us an email address and we will send the
    report when it is ready" is on the waiting screen, so this is a promise
    already made. A post that refuses is logged and nothing more: the audit is
    finished and on screen either way, and failing the run over an email would
    throw away work that is already done.
    """
    asked = session.get(AuditRequest, run.request_id) if run.request_id else None
    if asked is None or not asked.email:
        return
    score = _score_of(run)
    if score is None:
        return
    try:
        send(_mailer(settings), _audit_letter(run, asked, settings, asked.email, score))
    except NotSent as exc:
        log.warning("the audit of %s did not go to %s: %s", run.site, asked.email, exc)


def _behind(run_id: UUID, factory: sessionmaker[Session]) -> tuple[str, str] | None:
    """The Google Ads account behind an audit run: its id and stored permission.

    None is the ordinary case rather than a fault: not signed in, not connected,
    or connected without choosing an account yet.
    """
    with factory() as session:
        run = session.get(AuditRun, run_id)
        if run is None or run.request_id is None:
            return None
        asked = session.get(AuditRequest, run.request_id)
        if asked is None or asked.user_id is None:
            return None
        connection = session.scalars(
            select(AdsConnection).where(
                AdsConnection.account_id == asked.user_id,
                AdsConnection.revoked_at.is_(None),
            )
        ).first()
        if connection is None or not connection.customer_id:
            return None
        return connection.customer_id, connection.ciphertext


def _their_pages(
    run_id: UUID, settings: Settings, factory: sessionmaker[Session]
) -> list[dict[str, Any]] | None:
    """Every page their ads send people to, opened and judged.

    The list comes out of the mirror, so these are the pages Google itself sends
    the traffic to rather than a guess about which pages matter. Nothing is read
    from Google here at all.
    """
    behind = _behind(run_id, factory)
    if behind is None:
        return None
    customer_id, _ = behind
    with factory() as session:
        pages = landing_pages(session, customer_id)
    if not pages:
        return None
    try:
        checked = check_pages(pages, settings)
    except Exception:
        # The report goes out without this part rather than failing entirely.
        log.exception("audit %s could not check the landing pages", run_id)
        return None
    return [page.as_dict() for page in checked]


def _their_ads(
    run_id: UUID, settings: Settings, factory: sessionmaker[Session]
) -> dict[str, Any] | None:
    """Their Google Ads account, if they connected one and said which.

    None means there is nothing to read, which is the ordinary case: not signed
    in, not connected, or connected without choosing an account yet. A refusal
    from Google is also None here; the report still goes out, and the reason is
    in the log rather than in a failed audit.
    """
    behind = _behind(run_id, factory)
    if behind is None:
        return None
    customer_id, ciphertext = behind

    if not (settings.google_oauth_client_id and settings.google_oauth_client_secret):
        return None
    if settings.google_ads_developer_token is None:
        return None
    try:
        vault = TokenVault(
            settings.google_oauth_token_key.get_secret_value()
            if settings.google_oauth_token_key
            else None
        )
        access = fresh_access_token(
            vault.unlock(ciphertext),
            client_id=settings.google_oauth_client_id,
            client_secret=settings.google_oauth_client_secret.get_secret_value(),
        )
        developer_token = settings.google_ads_developer_token.get_secret_value()
        reading = read_account(
            customer_id,
            access_token=access,
            developer_token=developer_token,
            api_version=settings.google_ads_api_version,
            login_customer_id=settings.google_ads_login_customer_id,
        )
    except (AdsConnectionRefused, VaultUnavailable) as exc:
        log.warning("audit %s could not read the connected Google Ads account: %s", run_id, exc)
        return None

    return reading.as_dict()


def _last_demand(run_id: UUID, factory: sessionmaker[Session]) -> dict[str, Any] | None:
    """What the searching was worth, from the last run that paid to find out.

    Carried forward rather than dropped: a nightly run that leaves the panel
    empty would read as "we no longer know", when what is true is that we asked
    on Monday and the answer does not change by Tuesday.
    """
    with factory() as session:
        run = session.get(AuditRun, run_id)
        if run is None:
            return None
        for earlier in session.scalars(
            select(AuditRun)
            .where(
                AuditRun.site == run.site,
                AuditRun.status == "done",
                AuditRun.id != run.id,
            )
            .order_by(AuditRun.created_at.desc())
            .limit(10)
        ):
            found = (earlier.report or {}).get("demand")
            if found:
                return dict(found)
    return None


def _worth(
    run_id: UUID, settings: Settings, factory: sessionmaker[Session]
) -> dict[str, Any] | None:
    """What this trade is worth in this town, for anybody who runs the audit.

    Deliberately not tied to a merchant's own account. The free audit is where
    this number does its work, and the person running it has given us nothing.
    So it is asked from PPCWay's own Google Ads account, which exists for this
    one question. Without house credentials configured, the report carries no
    money line rather than a guessed one.
    """
    if not (settings.google_ads_house_customer_id and settings.google_ads_house_refresh_token):
        return None
    if settings.google_ads_developer_token is None:
        return None
    if not (settings.google_oauth_client_id and settings.google_oauth_client_secret):
        return None

    with factory() as session:
        run = session.get(AuditRun, run_id)
        if run is None or run.request_id is None:
            return None
        asked = session.get(AuditRequest, run.request_id)
        if asked is None:
            return None
        trade, city, place_id = asked.trade, asked.city, asked.place_id

    seeds = _seeds(trade, city, place_id, settings)
    if not seeds:
        return None
    try:
        access = fresh_access_token(
            settings.google_ads_house_refresh_token.get_secret_value(),
            client_id=settings.google_oauth_client_id,
            client_secret=settings.google_oauth_client_secret.get_secret_value(),
        )
        found = demand_for(
            seeds,
            city,
            customer_id=settings.google_ads_house_customer_id.replace("-", ""),
            access_token=access,
            developer_token=settings.google_ads_developer_token.get_secret_value(),
            api_version=settings.google_ads_api_version,
        )
    except AdsConnectionRefused as exc:
        log.warning("audit %s could not ask what the trade is worth: %s", run_id, exc)
        return None
    return found.as_dict() if found.read else None


def _seeds(trade: str, city: str, place_id: str, settings: Settings) -> list[str]:
    """The phrases a customer would actually type.

    The trade they gave is best. Failing that, Google's own word for the business
    from its listing, which is why the place id is worth one lookup. Failing both,
    nothing: a guessed trade produces a confident number about the wrong business.
    """
    word = trade.strip().lower()
    if not word and place_id and settings.google_maps_api_key:
        try:
            listing = place_details(
                place_id, api_key=settings.google_maps_api_key.get_secret_value()
            )
            word = (listing.category if listing else "").strip().lower()
        except PlacesError as exc:
            log.warning("could not read the listing for its trade: %s", exc)
    if not word:
        return []
    town = city.strip().lower()
    seeds = [word, f"{word} near me", f"emergency {word}"]
    if town:
        seeds.insert(1, f"{word} {town}")
    # Dedupe, keeping the order, because Google charges by the call not the seed.
    return list(dict.fromkeys(seeds))


#: Days of history that count as "we have their past". Below it, a refresh
#: fetches the ninety days a new account gets rather than only today's.
ENOUGH_HISTORY = 30


def _sync(run_id: UUID, connection_id: UUID, settings: Settings, kind: str) -> None:
    """Run a sync into the row the endpoint already opened and answered with."""
    sync_one(connection_id, settings, session_factory(), kind=kind, run_id=run_id)


def _run(run_id: UUID, settings: Settings, *, with_demand: bool = True) -> None:
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
        # `shot`, not `kind`: in this codebase a kind is what sort of business
        # this is, and reusing the word here would be asking for trouble.
        for shot, data in report.screenshots.items():
            folder.mkdir(parents=True, exist_ok=True)
            (folder / f"{shot}.jpg").write_bytes(data)
            report.screenshot_urls[shot] = f"/v1/audits/{run_id}/screenshot/{shot}"

        # Their Google listing and the same trade nearby. Worked out here
        # rather than on the page that draws the report, so the findings reach
        # the stored report, the counts and the history — and so the kind can
        # drop the ones that were never this business's question.
        say("checks", report.pages_read)
        mine, rivals = _their_listing(run_id, settings, factory)
        if mine is not None:
            report.findings.extend(listing_findings(mine, rivals))
            report.findings.extend(rival_findings(mine, rivals))

        written = report.as_dict()
        written["findings"] = keep(_kind_of(run_id, factory), written["findings"])
        # What the searching is worth here, which does not need their account.
        # Google charges per call for it and a town's search volume does not move
        # daily, so a scheduled run asks for it weekly rather than every night.
        worth = _worth(run_id, settings, factory) if with_demand else None
        if worth is not None:
            written["demand"] = worth
        elif not with_demand:
            written["demand"] = _last_demand(run_id, factory)
        theirs = _their_ads(run_id, settings, factory)
        if theirs is not None:
            # Their own account, read with the permission they gave, beside what
            # the public checks found. Four locked cards open when this is here.
            written["ads"] = theirs
        pages = _their_pages(run_id, settings, factory)
        if pages is not None:
            # And the handful of pages the ads actually send people to, which is
            # where a missing conversion tag costs the most.
            written["pages"] = pages
        with factory() as session:
            run = session.get(AuditRun, run_id)
            if run is None:
                return
            run.report = written
            run.status = "done"
            run.stage = "done"
            run.pages_read = report.pages_read
            run.finished_at = datetime.now(UTC)
            session.commit()
            _print_it(run.id, settings)
            _tell_them(run, session, settings)
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
