"""Sending approved changes to Google: straight after a yes, and on a schedule.

`apply_now` makes one change safely. This is what calls it, which until 5
November nothing did: a merchant could approve a change, be told "Otto will
make the change and tell you when it is done", and nothing would ever happen to
it. Two callers now:

- **The answer itself.** Approving a change, or asking for one to be put back,
  sends it in the same request when writes are on, so the merchant reads
  "done" or Google's reason rather than a promise.
- **The scheduled pass** (`send_waiting`), for everything that could not go at
  that moment: approved while writes were stopped, held for a day's quota,
  approved unasked by the nightly pass under auto-apply, or approved while a
  connection needed renewing.

Both go through `apply_now`, so both read the switches, run the guardrails a
third time, count quota and take the change before the call. Taking it is what
stops the two callers sending one change twice.

**Nothing is built until it is needed.** The switches are read before any
permission is unlocked, so with writes off -- as they are until the client's
Terms, consent and Google access are settled -- a pass reads the log, says why
everything is waiting, and opens no connection to Google at all.

**The door is built here and nowhere else.** `GoogleDoor` holds credentials
and sends mutations, and `tests/gateway/test_one_door.py` allows only this
package to import it. So the API asks this module to send; it never holds a
door of its own.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any, Final

from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from ppcway.ads.models import AdsConnection
from ppcway.ads.oauth import AdsConnectionRefused, TokenVault, VaultUnavailable, fresh_access_token
from ppcway.config import Settings
from ppcway.gateway import switch
from ppcway.gateway.apply import CannotApply, apply_now
from ppcway.gateway.changes import Unsendable, batch_for, done_words
from ppcway.gateway.google import GoogleDoor, Keys
from ppcway.gateway.port import Door
from ppcway.opt.models import OptimizationAction, Status

log = logging.getLogger(__name__)

#: A door for one connection. The real one unlocks the stored permission and
#: asks Google for an access token; tests hand in one that records what it was
#: asked to send.
DoorFor = Callable[[AdsConnection], Door]

#: How long a change may sit taken with no answer before the pass says so. A
#: send takes seconds, so one taken this long ago was interrupted between the
#: call and the answer, and only a person looking at Google Ads can say whether
#: it landed. It is reported, never sent again.
TAKEN_TOO_LONG: Final = timedelta(minutes=10)

#: How many changes one pass sends. A night's worth for every account is far
#: below this; it exists so a backlog after writes resume goes out over a few
#: passes rather than in one request the scheduler gives up on.
MOST_A_PASS: Final = 200


class NoDoor(RuntimeError):
    """Google cannot be reached for this account, for a reason about the
    connection rather than the change. The change stays approved."""


@dataclass(frozen=True, slots=True)
class Sent:
    """What became of one attempt to send a change."""

    #: The row's status afterwards: still approved when nothing was attempted.
    status: str
    words: str
    #: True when nothing reached Google and the change is still waiting.
    held: bool = False
    #: "gate", "global" or "account" when a switch held it, for the words a
    #: screen chooses; empty otherwise.
    stopped_by: str = ""


def doors(settings: Settings) -> DoorFor:
    """Real doors, one per connection, built from that connection's permission."""

    def open_one(connection: AdsConnection) -> Door:
        if settings.google_ads_developer_token is None or not (
            settings.google_oauth_client_id and settings.google_oauth_client_secret
        ):
            raise NoDoor("Writing to Google Ads is not set up on this deployment.")
        try:
            vault = TokenVault(
                settings.google_oauth_token_key.get_secret_value()
                if settings.google_oauth_token_key
                else None
            )
            access = fresh_access_token(
                vault.unlock(connection.ciphertext),
                client_id=settings.google_oauth_client_id,
                client_secret=settings.google_oauth_client_secret.get_secret_value(),
            )
        except (AdsConnectionRefused, VaultUnavailable) as exc:
            log.warning("no door to %s: %s", connection.customer_id, exc)
            raise NoDoor(
                "The permission to reach this Google Ads account has stopped working."
                " Reconnect it in Settings and Otto will send the change."
            ) from exc
        return GoogleDoor(
            Keys(
                access_token=access,
                developer_token=settings.google_ads_developer_token.get_secret_value(),
                login_customer_id=settings.google_ads_login_customer_id,
                api_version=settings.google_ads_api_version,
            )
        )

    return open_one


def send(
    session: Session,
    action: OptimizationAction,
    *,
    connection: AdsConnection,
    gate_open: bool,
    door_for: DoorFor,
    now: datetime | None = None,
) -> Sent:
    """Send one approved change, or say why it is still waiting."""
    at = now or datetime.now(UTC)

    # The switches first, so nothing is unlocked while writes are stopped.
    # `apply_now` reads them again; this is the cheap early answer.
    standing = switch.may_write(session, customer_id=action.customer_id, gate_open=gate_open)
    if not standing.may_write:
        return Sent(
            status=action.status,
            words=standing.because,
            held=True,
            stopped_by=standing.stopped_by,
        )

    try:
        batch = batch_for(action)
    except Unsendable as exc:
        # A row this gateway cannot turn into a request will never become one.
        # Refused, with the reason kept, rather than left approved for every
        # pass to trip over.
        log.error("cannot send %s: %s", action.id, exc)
        action.status = Status.REJECTED.value
        action.outcome = {"at": at.isoformat(), "words": str(exc), "unsendable": True}
        session.commit()
        return Sent(status=Status.REJECTED.value, words=str(exc))

    try:
        door = door_for(connection)
    except NoDoor as exc:
        return Sent(status=action.status, words=str(exc), held=True)

    try:
        made = apply_now(
            session,
            action,
            batch,
            door=door,
            connection=connection,
            organization_id=action.organization_id,
            gate_open=gate_open,
            now=at,
        )
    except CannotApply as exc:
        # Nothing was attempted. Rolled back, and the status read again rather
        # than assumed: "already being sent" means another sender has it.
        session.rollback()
        return Sent(status=action.status, words=str(exc), held=True)

    if made.quota_alert:
        log.warning("account %s has used most of today's Google Ads allowance", action.customer_id)
    if made.status is Status.APPLIED:
        return Sent(status=made.status.value, words=done_words(action))
    return Sent(status=made.status.value, words=made.words)


def words_for(sent: Sent, *, undoing: bool = False) -> str:
    """What to tell the person who just said yes, now that it has been tried.

    Never a promise the code cannot keep. With writes off the merchant is told
    plainly that nothing in their account has changed, and that the change is
    checked again before it is made -- because it is, and an approval that has
    waited weeks for writes to open may be refused on stale figures then.
    """
    if not sent.held:
        if sent.status == Status.APPLIED.value:
            return f"Done. {sent.words}" + ("" if undoing else " You can undo it for 30 days.")
        return sent.words
    first = "Putting that back." if undoing else "Approved."
    if sent.stopped_by == "gate":
        return (
            f"{first} PPCWay is not making changes in Google Ads yet, so nothing in your"
            " account has changed. When it starts, Otto checks this again and makes it"
            " if it still holds."
        )
    if sent.stopped_by in {"global", "account"}:
        return (
            f"{first} Changes to Google Ads are stopped right now: {sent.words}"
            " Otto checks this again and makes it when they resume."
        )
    return f"{first} {sent.words}"


@dataclass
class Round:
    """What one scheduled pass did, for the scheduler and for whoever reads it."""

    ran_at: datetime
    waiting: int = 0
    applied: int = 0
    failed: int = 0
    rejected: int = 0
    held: int = 0
    #: Each reason something was held, once, so a report of two hundred held
    #: changes reads as one sentence rather than two hundred.
    held_because: list[str] = field(default_factory=list)
    #: Taken and never answered. Looked at by a person, never sent again.
    stuck: int = 0

    def as_dict(self) -> dict[str, Any]:
        return {
            "ran_at": self.ran_at.isoformat(),
            "waiting": self.waiting,
            "applied": self.applied,
            "failed": self.failed,
            "rejected": self.rejected,
            "held": self.held,
            "held_because": list(self.held_because),
            "stuck": self.stuck,
        }

    def _held(self, why: str) -> None:
        self.held += 1
        if why and why not in self.held_because:
            self.held_because.append(why)


def send_waiting(
    factory: sessionmaker[Session],
    settings: Settings,
    *,
    door_for: DoorFor | None = None,
    now: datetime | None = None,
) -> Round:
    """Send every approved change that has not been taken, oldest yes first."""
    at = now or datetime.now(UTC)
    round_ = Round(ran_at=at)

    with factory() as session:
        ids = list(
            session.scalars(
                select(OptimizationAction.id)
                .where(
                    OptimizationAction.status == Status.APPROVED.value,
                    OptimizationAction.taken_at.is_(None),
                )
                .order_by(OptimizationAction.approved_at, OptimizationAction.created_at)
                .limit(MOST_A_PASS)
            )
        )
        round_.waiting = len(ids)
        round_.stuck = int(
            session.scalar(
                select(func.count(OptimizationAction.id)).where(
                    OptimizationAction.status == Status.APPROVED.value,
                    OptimizationAction.taken_at.is_not(None),
                    OptimizationAction.taken_at < at - TAKEN_TOO_LONG,
                )
            )
            or 0
        )
    if round_.stuck:
        log.error(
            "%d changes were sent to Google and never answered; check them in Google Ads",
            round_.stuck,
        )

    if not ids:
        return round_
    with factory() as session:
        gate_open = switch.gate(session, default=settings.ads_writes_enabled).is_open
    if not gate_open:
        # Nothing to read per row: the gate holds every one of them for the
        # same reason, and saying it once is the whole report.
        with factory() as session:
            why = switch.may_write(session, customer_id="", gate_open=False).because
        round_.held = len(ids)
        round_.held_because.append(why)
        return round_

    door_for = door_for or doors(settings)
    opened: dict[Any, Door] = {}

    def door_once(connection: AdsConnection) -> Door:
        # One access token per account per pass, not one per change.
        if connection.id not in opened:
            opened[connection.id] = door_for(connection)
        return opened[connection.id]

    for action_id in ids:
        # Its own session, like the nightly pass's accounts: one change that
        # goes wrong in an unexpected way must not cost the rest their turn.
        try:
            with factory() as session:
                action = session.get(OptimizationAction, action_id)
                if action is None or action.status != Status.APPROVED.value:
                    continue
                connection = connection_for(session, action)
                if connection is None:
                    round_._held("This business has no live connection to that Google Ads account.")
                    continue
                said = send(
                    session,
                    action,
                    connection=connection,
                    # Read again for each change, not once for the pass:
                    # somebody switching writes off mid-pass stops the rest.
                    gate_open=switch.gate(session, default=settings.ads_writes_enabled).is_open,
                    door_for=door_once,
                    now=at,
                )
        except Exception:
            log.exception("sending %s went wrong", action_id)
            round_._held("Something went wrong sending one change; it is still waiting.")
            continue
        if said.held:
            round_._held(said.words)
        elif said.status == Status.APPLIED.value:
            round_.applied += 1
        elif said.status == Status.FAILED.value:
            round_.failed += 1
        elif said.status == Status.REJECTED.value:
            round_.rejected += 1

    log.info("send pass: %s", round_.as_dict())
    return round_


def waiting_count(session: Session) -> int:
    """How many approved changes are waiting to be sent, for the panel to say."""
    return int(
        session.scalar(
            select(func.count(OptimizationAction.id)).where(
                OptimizationAction.status == Status.APPROVED.value,
                OptimizationAction.taken_at.is_(None),
            )
        )
        or 0
    )


def connection_for(session: Session, action: OptimizationAction) -> AdsConnection | None:
    """The live connection this business holds to the account a change is for.

    Matched on both, because one Google Ads account can be connected to more
    than one business, and a change may only go through the connection of the
    business it belongs to.
    """
    return session.scalars(
        select(AdsConnection)
        .where(
            AdsConnection.organization_id == action.organization_id,
            AdsConnection.customer_id == action.customer_id,
            AdsConnection.revoked_at.is_(None),
        )
        .order_by(AdsConnection.created_at.desc())
        .limit(1)
    ).first()
