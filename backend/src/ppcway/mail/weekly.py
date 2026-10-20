"""The Monday post: last week in their account, in words, by email.

The requirements ask for a weekly plain-language summary, and the delivery plan
promises it for the end of week two. This is it, and it is deliberately dull: a
small business owner reading on a phone between jobs should learn in the first
line whether last week was better or worse than the one before, and in the
second whether anything needs them.

Three rules it keeps.

  A sentence before a number. "You got twelve leads last week" and then the
  comparison, never a bare table of figures.

  Nothing is dressed up. A week with no leads says so in the subject line. A
  week where the ads did not run at all says that instead of printing zeros.

  It says what PPCway did, which for now is nothing. An email from an
  optimisation product that does not say whether it touched the account leaves
  the reader to assume, and the assumption will be wrong in both directions.

Every figure comes from our own mirror — the same reader the dashboard uses, so
the email and the screen can never disagree.
"""

from __future__ import annotations

import logging
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from uuid import UUID

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from ppcway.ads.models import AdsConnection
from ppcway.ads.numbers import MONTH, Held, account_numbers, plain_money
from ppcway.auth.models import UserAccount
from ppcway.config import Settings
from ppcway.mail.letters import FOOT, _wrap
from ppcway.mail.models import WeeklyPost
from ppcway.mail.send import Letter, NotSent, Post, send

log = logging.getLogger(__name__)

#: What PPCway did to the account, which for now is nothing. An email from an
#: optimisation product that does not say leaves the reader to assume, and the
#: assumption will be wrong in both directions.
UNTOUCHED = (
    "PPCway has not changed anything in your account. It only reads it for now; "
    "when that changes, you will be asked first."
)

#: The window the post speaks in. A week, because a week is how a small
#: business already thinks about its trade.
WEEK = 7


def _count(value: float) -> str:
    return f"{round(value):,}"


def _monday(day: date) -> date:
    """The Monday of the week this day falls in."""
    return day - timedelta(days=day.weekday())


def _leads_line(held: Held) -> str:
    """Last week's leads, and whether that is better than the week before."""
    if not held.leads:
        if held.cost:
            return (
                f"Nothing came in last week, and you spent {plain_money(held.cost, held.currency)}. "
                "If your phone did ring, the tracking may not be counting it — "
                "the website audit checks that."
            )
        return "Your ads did not run last week, so nothing came in and nothing was spent."

    split = []
    if held.calls:
        split.append(f"{_count(held.calls)} phone {'call' if round(held.calls) == 1 else 'calls'}")
    if held.forms:
        split.append(f"{_count(held.forms)} {'form' if round(held.forms) == 1 else 'forms'}")
    said = f"You got {_count(held.leads)} leads last week"
    if split:
        said += f" — {' and '.join(split)}"
    said += "."

    if not held.leads_before:
        return f"{said} There is nothing to compare it with yet."
    difference = round(held.leads) - round(held.leads_before)
    if difference == 0:
        return f"{said} That is the same as the week before."
    word = "more" if difference > 0 else "fewer"
    return f"{said} That is {abs(difference):,} {word} than the week before."


def _cost_line(held: Held) -> str:
    """What a lead cost, and whether it is getting cheaper."""
    if not held.leads:
        return ""
    said = f"Each one cost {plain_money(held.cost_per_lead, held.currency)}."
    before = held.cost_per_lead_before
    if not before:
        return said
    difference = round(held.cost_per_lead - before, 2)
    if abs(difference) < 0.01:
        return f"{said} That is the same as the week before."
    word = "dearer" if difference > 0 else "cheaper"
    return (
        f"{said} That is {plain_money(abs(difference), held.currency)} {word} than the week before."
    )


def _spend_line(held: Held) -> str:
    """What it cost, against what the daily budgets allow in a week."""
    if not held.cost:
        return ""
    said = f"You spent {plain_money(held.cost, held.currency)}."
    if held.monthly_budget:
        a_week = round(held.monthly_budget / MONTH * WEEK, 2)
        said += f" Your daily budgets allow about {plain_money(a_week, held.currency)} a week."
    return said


def _subject(held: Held) -> str:
    if held.leads:
        return (
            f"Last week: {_count(held.leads)} leads at "
            f"{plain_money(held.cost_per_lead, held.currency)} each"
        )
    if held.cost:
        return f"Last week: {plain_money(held.cost, held.currency)} spent and nothing came in"
    return "Last week: your ads did not run"


def weekly_letter(
    held: Held,
    *,
    to: str,
    name: str = "",
    business: str = "",
    link: str = "",
    now: datetime | None = None,
) -> Letter:
    """One week, as a letter. Plain text and the same words in HTML."""
    at = now or datetime.now(UTC)
    hello = f"Hello {name.split(' ')[0]}," if name else "Hello,"
    opening = f"Here is last week in {business}." if business else "Here is last week."

    story = [line for line in (_leads_line(held), _cost_line(held), _spend_line(held)) if line]

    # Changes somebody made in Google Ads during the week this post covers. The
    # "needs you" list carries the same fact as a count; here it is the changes
    # themselves, which is more use and not worth saying twice.
    since = at - timedelta(days=WEEK)
    hands = [
        change
        for change in held.activity
        if change.when and change.when.replace(tzinfo=change.when.tzinfo or UTC) >= since
    ]
    needs = [need for need in held.needs if need.kind != "changed_in_google"]

    text = [hello, "", opening, ""]
    text += story
    if needs:
        text += ["", f"{'One thing' if len(needs) == 1 else f'{len(needs)} things'} needs you:"]
        text += [f" - {need.label}: {need.what}" for need in needs]
    if hands:
        word = "change" if len(hands) == 1 else "changes"
        was = "was" if len(hands) == 1 else "were"
        text += ["", f"{len(hands)} {word} {was} made in Google Ads itself last week:"]
        text += [f" - {change.summary} ({change.label})" for change in hands]
    text += ["", UNTOUCHED]
    if link:
        text += ["", f"The detail is here: {link}"]
    text += ["", FOOT]

    body = "".join(f"<p>{line}</p>" for line in [hello, opening, *story])
    if needs:
        body += (
            f"<p><strong>{'One thing' if len(needs) == 1 else f'{len(needs)} things'} "
            "needs you</strong></p><ul>"
            + "".join(f"<li><strong>{n.label}</strong> — {n.what}</li>" for n in needs)
            + "</ul>"
        )
    if hands:
        word = "change" if len(hands) == 1 else "changes"
        body += (
            f"<p><strong>{len(hands)} {word} made in Google Ads itself</strong></p><ul>"
            + "".join(f"<li>{c.summary} <em>({c.label})</em></li>" for c in hands)
            + "</ul>"
        )
    body += f"<p>{UNTOUCHED}</p>"

    subject = _subject(held)
    return Letter(
        to=to,
        subject=subject,
        text="\n".join(text),
        html=_wrap(subject, body, ("See the detail", link) if link else None),
    )


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


def _already_sent(session: Session, account_id: UUID, week: date) -> WeeklyPost | None:
    return session.scalars(
        select(WeeklyPost).where(WeeklyPost.account_id == account_id, WeeklyPost.week_start == week)
    ).first()


@dataclass
class Candidate:
    """One account the post might go to, and the letter it would get.

    Who gets a post is decided here once, so the dry run a person reads before
    a hundred people read it cannot drift from what actually goes out.
    """

    connection: AdsConnection
    person: UserAccount | None = None
    letter: Letter | None = None
    existing: WeeklyPost | None = None
    #: Empty when it should be sent; otherwise why it should not, in plain words.
    skip: str = ""


def candidates(
    session: Session,
    settings: Settings,
    *,
    now: datetime | None = None,
) -> Iterator[Candidate]:
    """Every connected account, with this week's letter or the reason for none."""
    at = now or datetime.now(UTC)
    week = _monday(at.date())
    connections = session.scalars(
        select(AdsConnection).where(
            AdsConnection.revoked_at.is_(None), AdsConnection.customer_id != ""
        )
    ).all()

    for connection in connections:
        existing = _already_sent(session, connection.account_id, week)
        if existing and existing.status == "sent":
            continue
        person = session.get(UserAccount, connection.account_id)
        if person is None or not person.email:
            yield Candidate(connection, skip="there is nobody to write to")
            continue
        if person.email_verified_at is None:
            # An unconfirmed address is somebody else's until it is proved.
            yield Candidate(connection, person, skip="that address is not confirmed yet")
            continue
        held = account_numbers(
            session,
            connection.customer_id,
            days=WEEK,
            currency=connection.currency,
            today=at.date(),
        )
        if not held.read:
            # Nothing mirrored yet. No row is written, so next week tries again.
            yield Candidate(connection, person, skip="we have not read that account yet")
            continue
        yield Candidate(
            connection,
            person,
            letter=weekly_letter(
                held,
                to=person.email,
                name=person.name,
                business=connection.customer_name,
                link=f"{settings.app_base_url.rstrip('/')}/home",
                now=at,
            ),
            existing=existing,
        )


def post_weekly(
    session: Session,
    settings: Settings,
    *,
    now: datetime | None = None,
    post: Post | None = None,
    client: httpx.Client | None = None,
) -> dict[str, int]:
    """Send one summary to every connected account that has not had this week's.

    A refusal is written on the row rather than raised: the scheduler walks every
    account in one call, and one address that bounces must not stop the rest.
    """
    at = now or datetime.now(UTC)
    week = _monday(at.date())
    letters = post or _post_from(settings)
    counts = {"sent": 0, "failed": 0, "skipped": 0}

    for who in list(candidates(session, settings, now=at)):
        if who.letter is None or who.person is None:
            log.info(
                "no weekly post for %s: %s",
                who.connection.customer_id,
                who.skip or "nothing to say",
            )
            counts["skipped"] += 1
            continue
        row = who.existing or WeeklyPost(
            account_id=who.connection.account_id,
            customer_id=who.connection.customer_id,
            week_start=week,
        )
        row.to_address = who.person.email
        row.subject = who.letter.subject
        row.sent_at = at
        try:
            send(letters, who.letter, client=client)
            row.status, row.trouble = "sent", ""
            counts["sent"] += 1
        except NotSent as exc:
            log.warning("the weekly post did not go to %s: %s", who.connection.customer_id, exc)
            row.status, row.trouble = "failed", str(exc)
            counts["failed"] += 1
        session.add(row)
        session.commit()

    return counts
