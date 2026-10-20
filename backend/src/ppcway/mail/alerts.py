"""The things worth interrupting somebody for, and nothing else.

Alerts are the part of a product that teaches people to ignore it. Six things
qualify, each because a small business owner would want to be told today rather
than on Monday, and each cheap enough to notice from our own mirror without
asking Google anything.

  Spend jumped. Yesterday cost more than twice the fortnight's daily average.
  Somebody raised a budget, or a bidding strategy found a new way to spend.

  The leads stopped. An account that was bringing enquiries has brought none
  for three days while still spending. Usually a broken form or a conversion
  tag removed by a website change — which is why the audit watches the landing
  pages too.

  An ad was refused. It spends nothing while it sits there, and Google does not
  phone anybody about it.

  The permission ended. Nothing works until it is granted again, and somebody
  who is not looking at the dashboard has no way to know.

  The syncs keep failing. Our own fault to fix, and saying so is better than a
  dashboard that quietly ages.

  The audit score dropped. Something that was good is not any more, which is
  how a redesign that dropped the conversion tag gets caught in a day.

One letter per thing per day per business. The hourly watcher can notice the
same refused ad twelve times and still send one letter.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, timedelta

import httpx
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ppcway.ads.mirror import CampaignDay, MirrorAd, MirrorCampaign, SyncRun
from ppcway.ads.models import AdsConnection
from ppcway.ads.numbers import plain_money
from ppcway.audit.history import what_changed
from ppcway.audit.models import AuditRequest, AuditRun
from ppcway.auth.models import UserAccount
from ppcway.config import Settings
from ppcway.mail.letters import FOOT, _wrap
from ppcway.mail.models import AlertSent
from ppcway.mail.send import Letter, NotSent, Post, send

log = logging.getLogger(__name__)

#: Yesterday against the fortnight before it. Twice the average is not a
#: rounding error; it is somebody having changed something.
JUMP = 2.0

#: And below this much money, twice the average is still pocket change.
JUMP_FLOOR = 20.0

#: How many days back the average is taken over.
AVERAGE_OVER = 14

#: The leads have stopped when there were none for this many days running.
QUIET_DAYS = 3

#: But only for an account that was bringing some. Below this many in the week
#: before the quiet stretch, there is nothing to have stopped.
WAS_BRINGING = 3

#: Three failed syncs in a row is a fault, not a blip.
FAILURES = 3


@dataclass
class Alarm:
    """One thing worth interrupting somebody for."""

    kind: str
    #: What within the kind: a campaign id, a check's key, or empty.
    about: str
    subject: str
    lines: list[str] = field(default_factory=list)
    #: What to do about it, in one sentence.
    todo: str = ""


def _spend_jump(session: Session, customer_id: str, currency: str, now: date) -> Alarm | None:
    """Yesterday against the fortnight before it."""
    yesterday = now - timedelta(days=1)
    spent = (
        session.scalar(
            select(func.sum(CampaignDay.cost_micros)).where(
                CampaignDay.customer_id == customer_id, CampaignDay.day == yesterday
            )
        )
        or 0
    ) / 1_000_000
    if spent < JUMP_FLOOR:
        return None
    before = (
        session.scalar(
            select(func.sum(CampaignDay.cost_micros)).where(
                CampaignDay.customer_id == customer_id,
                CampaignDay.day >= yesterday - timedelta(days=AVERAGE_OVER),
                CampaignDay.day < yesterday,
            )
        )
        or 0
    ) / 1_000_000
    days = (
        session.scalar(
            select(func.count(func.distinct(CampaignDay.day))).where(
                CampaignDay.customer_id == customer_id,
                CampaignDay.day >= yesterday - timedelta(days=AVERAGE_OVER),
                CampaignDay.day < yesterday,
            )
        )
        or 0
    )
    if days < 3:
        # Not enough history for "usual" to mean anything yet.
        return None
    usual = before / days
    if usual <= 0 or spent < usual * JUMP:
        return None
    return Alarm(
        kind="spend_jump",
        about=yesterday.isoformat(),
        subject=f"Your Google Ads spend jumped to {plain_money(spent, currency)} yesterday",
        lines=[
            f"Yesterday your advertising cost {plain_money(spent, currency)}.",
            f"The fortnight before it averaged {plain_money(round(usual, 2), currency)} a day.",
            (
                "That is more than twice as much, which usually means a budget was raised, "
                "a campaign was switched on, or a bidding strategy found somewhere new to spend."
            ),
        ],
        todo="Open your dashboard and check which campaign the money went to.",
    )


def _leads_stopped(session: Session, customer_id: str, currency: str, now: date) -> Alarm | None:
    """An account that was bringing enquiries and has stopped."""
    quiet_from = now - timedelta(days=QUIET_DAYS)
    quiet = list(
        session.scalars(
            select(CampaignDay).where(
                CampaignDay.customer_id == customer_id,
                CampaignDay.day >= quiet_from,
                CampaignDay.day < now,
            )
        )
    )
    if not quiet:
        return None
    leads_now = sum(row.calls + row.forms for row in quiet)
    spent_now = sum(row.cost for row in quiet)
    if leads_now > 0 or spent_now <= 0:
        return None
    was = (
        session.scalar(
            select(func.sum(CampaignDay.conversions)).where(
                CampaignDay.customer_id == customer_id,
                CampaignDay.day >= quiet_from - timedelta(days=7),
                CampaignDay.day < quiet_from,
            )
        )
        or 0
    )
    if was < WAS_BRINGING:
        return None
    return Alarm(
        kind="leads_stopped",
        about=quiet_from.isoformat(),
        subject="Your Google Ads has brought no enquiries for three days",
        lines=[
            (
                f"In the last {QUIET_DAYS} days your advertising cost "
                f"{plain_money(round(spent_now, 2), currency)} and Google counted no calls "
                "and no forms."
            ),
            f"In the week before that it counted {round(was)}.",
            (
                "The commonest cause is not a drop in trade: it is a form that has stopped "
                "working, or a conversion tag removed by a change to the website."
            ),
        ],
        todo="Send yourself the enquiry form on your site and see whether it arrives.",
    )


def _ad_refused(session: Session, customer_id: str, now: date) -> Alarm | None:
    """An ad Google will not show."""
    names = {
        row.campaign_id: row.name
        for row in session.scalars(
            select(MirrorCampaign).where(MirrorCampaign.customer_id == customer_id)
        )
    }
    refused = list(
        session.scalars(
            select(MirrorAd).where(
                MirrorAd.customer_id == customer_id,
                MirrorAd.gone_at.is_(None),
                MirrorAd.approval.not_in(("APPROVED", "APPROVED_LIMITED", "")),
            )
        )
    )
    if not refused:
        return None
    first = refused[0]
    headline = next((h for h in (first.headlines or []) if h), f"Ad {first.ad_id}")
    where = names.get(first.campaign_id, "your account")
    more = len(refused) - 1
    return Alarm(
        kind="ad_refused",
        about=first.resource_name,
        subject=f"Google will not show one of your ads in {where}",
        lines=[
            (
                f"The ad “{headline}” in {where} has been refused by Google, so it is not "
                "being shown to anybody."
            ),
            *(
                [f"{more} other {'ad is' if more == 1 else 'ads are'} refused as well."]
                if more > 0
                else []
            ),
            (
                "A refused ad costs nothing and earns nothing. It usually needs a word "
                "changed, or a claim on the landing page backed up."
            ),
        ],
        todo="Open Campaigns in PPCway, find the ad, and read Google's reason.",
    )


def _sync_failing(session: Session, customer_id: str) -> Alarm | None:
    """Our own fault, said out loud."""
    recent = list(
        session.scalars(
            select(SyncRun)
            .where(SyncRun.customer_id == customer_id, SyncRun.status.in_(("done", "failed")))
            .order_by(SyncRun.started_at.desc())
            .limit(FAILURES)
        )
    )
    if len(recent) < FAILURES or any(run.status != "failed" for run in recent):
        return None
    return Alarm(
        kind="sync_failing",
        about="",
        subject="PPCway cannot read your Google Ads account at the moment",
        lines=[
            (
                "Our last three attempts to read your account failed, so the figures on "
                "your dashboard are older than they should be."
            ),
            f"Google's reason, in its own words: {recent[0].trouble or 'no reason given'}.",
            (
                "Nothing in your account has been changed, and nothing of yours is lost. "
                "We are told about this at the same time as you are."
            ),
        ],
        todo="Nothing yet — if it is ours to fix we are already on it.",
    )


def _score_dropped(session: Session, organization_id: object, site: str) -> Alarm | None:
    """Something on the website that was good is not any more."""
    if not site:
        return None
    changed = what_changed(session, site, organization_id=organization_id)  # type: ignore[arg-type]
    if changed.first or not changed.broke:
        return None
    broke = changed.broke[0]
    plain = site.replace("https://", "").replace("http://", "").rstrip("/")
    return Alarm(
        kind="score_dropped",
        about=broke["key"],
        subject=f"Something on {plain} stopped working for your ads",
        lines=[
            f"Yesterday {plain} passed the check “{broke['title']}”. Today it does not.",
            broke["summary"],
            *(
                [f"{len(changed.broke) - 1} other check also went backwards."]
                if len(changed.broke) == 2
                else (
                    [f"{len(changed.broke) - 1} other checks also went backwards."]
                    if len(changed.broke) > 2
                    else []
                )
            ),
            (
                "A change to a website is the usual cause, and the person who made it will "
                "not know this happened."
            ),
        ],
        todo="Open the website audit in PPCway and send the fix list to whoever looks "
        "after the site.",
    )


def look(
    session: Session,
    connection: AdsConnection,
    *,
    now: datetime | None = None,
) -> list[Alarm]:
    """Everything worth saying about one account today."""
    at = now or datetime.now(UTC)
    today = at.date()
    found: list[Alarm | None] = []

    if connection.revoked_at is not None:
        # Nothing else matters while the permission is gone.
        return [
            Alarm(
                kind="permission_gone",
                about="",
                subject="Google has ended PPCway's permission to read your account",
                lines=[
                    (
                        "Your Google Ads permission has ended, so your dashboard, your "
                        "reports and your weekly email have stopped filling in."
                    ),
                    (
                        "Nothing in your advertising account was changed, and your campaigns "
                        "are running exactly as they were."
                    ),
                ],
                todo="Open PPCway and press Connect again. It takes about twenty seconds.",
            )
        ]

    found.append(_sync_failing(session, connection.customer_id))
    found.append(_spend_jump(session, connection.customer_id, connection.currency, today))
    found.append(_leads_stopped(session, connection.customer_id, connection.currency, today))
    found.append(_ad_refused(session, connection.customer_id, today))

    site = ""
    if connection.organization_id is not None:
        latest = session.scalars(
            select(AuditRun)
            .join(AuditRequest, AuditRun.request_id == AuditRequest.id)
            .where(
                AuditRequest.organization_id == connection.organization_id,
                AuditRun.status == "done",
            )
            .order_by(AuditRun.finished_at.desc())
            .limit(1)
        ).first()
        site = latest.site if latest else ""
        found.append(_score_dropped(session, connection.organization_id, site))

    return [alarm for alarm in found if alarm is not None]


def alert_letter(
    alarm: Alarm, *, to: str, name: str = "", business: str = "", link: str = ""
) -> Letter:
    """One alarm, as a letter. Short, because it is being read on a phone."""
    hello = f"Hello {name.split(' ')[0]}," if name else "Hello,"
    about = f" about {business}" if business else ""
    text = "\n".join(
        [
            hello,
            "",
            f"This is PPCway{about}.",
            "",
            *alarm.lines,
            "",
            f"What to do: {alarm.todo}" if alarm.todo else "",
            "",
            f"Your dashboard: {link}" if link else "",
            "",
            FOOT,
        ]
    )
    body = "".join(f"<p>{line}</p>" for line in alarm.lines)
    if alarm.todo:
        body += f"<p><strong>What to do:</strong> {alarm.todo}</p>"
    return Letter(
        to=to,
        subject=alarm.subject,
        text=text,
        html=_wrap(alarm.subject, body, ("Open my dashboard", link) if link else None),
    )


def _already(session: Session, account_id: object, alarm: Alarm, day: date) -> AlertSent | None:
    return session.scalars(
        select(AlertSent).where(
            AlertSent.account_id == account_id,
            AlertSent.kind == alarm.kind,
            AlertSent.about == alarm.about,
            AlertSent.day == day,
        )
    ).first()


def _post_from(settings: Settings) -> Post:
    return Post(
        sender=settings.email_from,
        provider=settings.email_provider,
        api_key=settings.resend_api_key.get_secret_value() if settings.resend_api_key else "",
        smtp_host=settings.smtp_host,
        smtp_port=settings.smtp_port,
        smtp_user=settings.smtp_user,
        smtp_password=settings.smtp_password.get_secret_value() if settings.smtp_password else "",
    )


def post_alerts(
    session: Session,
    settings: Settings,
    *,
    now: datetime | None = None,
    post: Post | None = None,
    client: httpx.Client | None = None,
) -> dict[str, int]:
    """Look at every connected account and send what is worth sending."""
    at = now or datetime.now(UTC)
    today = at.date()
    letters = post or _post_from(settings)
    counts = {"sent": 0, "failed": 0, "held": 0, "skipped": 0}

    connections = session.scalars(
        select(AdsConnection).where(AdsConnection.customer_id != "")
    ).all()
    for connection in connections:
        person = session.get(UserAccount, connection.account_id)
        if person is None or not person.email or person.email_verified_at is None:
            counts["skipped"] += 1
            continue
        for alarm in look(session, connection, now=at):
            if _already(session, connection.account_id, alarm, today) is not None:
                counts["held"] += 1
                continue
            letter = alert_letter(
                alarm,
                to=person.email,
                name=person.name,
                business=connection.customer_name,
                link=f"{settings.app_base_url.rstrip('/')}/home",
            )
            row = AlertSent(
                account_id=connection.account_id,
                customer_id=connection.customer_id,
                kind=alarm.kind,
                about=alarm.about,
                day=today,
                to_address=person.email,
                subject=letter.subject,
                sent_at=at,
            )
            try:
                send(letters, letter, client=client)
                counts["sent"] += 1
            except NotSent as exc:
                log.warning("the %s alert did not go out: %s", alarm.kind, exc)
                row.status, row.trouble = "failed", str(exc)
                counts["failed"] += 1
            session.add(row)
            session.commit()
    return counts
