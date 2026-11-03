"""The switches the panel can actually throw, and what each one costs.

Everything here changes the platform's behaviour, so every function takes the
caller's level and checks it. The check is here rather than only in the
endpoint because this module is the thing with the authority: an endpoint is
one caller, and the second caller -- a CLI, a task, a test somebody writes in a
hurry -- would otherwise arrive unchecked.

**Reading is not the same as throwing.** `standing` and `quota_today` are open
to any level that may read the platform. Stopping writes and setting a flag
need `principal`, because those two are the ones that change what happens to a
merchant's money.

**Nothing here can start writes that the deployment itself has not enabled.**
`ads_writes_enabled` is a setting, not a switch: the panel can stop writes and
can release a stop, and if the setting is off then writes remain off either
way. A panel button that appeared to enable live writing to Google Ads would be
the most dangerous control in the product, so it does not exist.
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from typing import Final

from sqlalchemy import select
from sqlalchemy.orm import Session

from ppcway.auth.models import UserAccount
from ppcway.gateway import quota, switch
from ppcway.staff.guard import require
from ppcway.staff.models import Level

log = logging.getLogger(__name__)

#: The whole platform, rather than one account. The kill switch uses an empty
#: customer id for this, and spelling it out here stops `""` appearing at call
#: sites where a reader cannot tell whether it was meant.
EVERYTHING: Final = ""

#: A reason has to be at least this long to be a reason. "x" is not an
#: explanation, and this row is read by whoever picks up the incident.
LEAST_REASON: Final = 12


@dataclass(frozen=True, slots=True)
class Stop:
    """One stop in force, as the panel shows it."""

    customer_id: str
    because: str
    ours: bool
    pulled_at: datetime
    pulled_by: uuid.UUID | None

    @property
    def scope(self) -> str:
        return "the whole platform" if not self.customer_id else self.customer_id

    @property
    def words(self) -> str:
        who = "PPCWay" if self.ours else "the merchant"
        return f"Writes are stopped on {self.scope}, set by {who}: {self.because}"


@dataclass(frozen=True, slots=True)
class Standing:
    """Whether anything can be written right now, and why not.

    Carries both the deployment setting and the switches, because "writes are
    off" has two completely different causes and the fix differs: one is a
    deploy, the other is a button.
    """

    writes_enabled_in_this_deployment: bool
    auto_apply_enabled_in_this_deployment: bool
    stops: tuple[Stop, ...] = field(default_factory=tuple)

    @property
    def platform_stopped(self) -> Stop | None:
        for one in self.stops:
            if not one.customer_id:
                return one
        return None

    @property
    def anything_can_be_written(self) -> bool:
        return self.writes_enabled_in_this_deployment and self.platform_stopped is None

    @property
    def words(self) -> str:
        """One sentence a person can read at the top of the screen."""
        if not self.writes_enabled_in_this_deployment:
            return (
                "PPCWay is not writing to any Google Ads account. That is this"
                " deployment's setting, not a switch -- it takes a deploy to change."
            )
        stopped = self.platform_stopped
        if stopped is not None:
            return stopped.words
        if self.stops:
            return (
                f"Writes are on, with {len(self.stops)} account"
                f"{'s' if len(self.stops) > 1 else ''} stopped individually."
            )
        return "Writes are on and nothing is stopped."


def _as_stop(row: switch.KillSwitch) -> Stop:
    return Stop(
        customer_id=row.customer_id or "",
        because=row.because or "",
        ours=bool(row.ours),
        pulled_at=row.pulled_at,
        pulled_by=row.pulled_by,
    )


def standing(
    session: Session,
    account: UserAccount | None,
    *,
    writes_enabled: bool,
    auto_apply_enabled: bool,
) -> Standing:
    """What is stopped and what is merely switched off. Any reader may ask."""
    require(session, account, "read_platform")
    live = session.scalars(
        select(switch.KillSwitch)
        .where(switch.KillSwitch.released_at.is_(None))
        .order_by(switch.KillSwitch.pulled_at.desc())
    )
    return Standing(
        writes_enabled_in_this_deployment=writes_enabled,
        auto_apply_enabled_in_this_deployment=auto_apply_enabled,
        stops=tuple(_as_stop(row) for row in live),
    )


def stop_writes(
    session: Session,
    account: UserAccount | None,
    *,
    customer_id: str = EVERYTHING,
    because: str,
) -> Stop:
    """Stop writes, for one account or all of them. Principal only.

    Marked `ours=True`, which is what stops a merchant turning it back on: the
    one case this exists for is "we have found a problem and are stopping while
    we look", and that must not be a case the merchant can overrule.
    """
    level = require(session, account, "stop_writes")
    reason = (because or "").strip()
    if len(reason) < LEAST_REASON:
        raise ValueError(
            f"say why in at least {LEAST_REASON} characters. Whoever picks this up"
            f" reads this line, and {reason!r} does not tell them anything."
        )
    row = switch.stop(
        session,
        customer_id=customer_id,
        because=reason,
        pulled_by=account.id if account is not None else None,
        ours=True,
    )
    log.warning(
        "writes stopped on %s by %s access: %s",
        customer_id or "the whole platform",
        level.value,
        reason,
    )
    return _as_stop(row)


def release_writes(
    session: Session,
    account: UserAccount | None,
    *,
    customer_id: str = EVERYTHING,
) -> Stop | None:
    """Let writes resume. Principal only. None where nothing was stopped."""
    level = require(session, account, "stop_writes")
    row = switch.release(
        session,
        customer_id=customer_id,
        released_by=account.id if account is not None else None,
        staff=True,
    )
    if row is None:
        return None
    log.warning(
        "writes released on %s by %s access",
        customer_id or "the whole platform",
        level.value,
    )
    return _as_stop(row)


@dataclass(frozen=True, slots=True)
class Room:
    """How much Google Ads quota is left today, for one account."""

    customer_id: str
    used: int
    allowance: int
    day: date

    @property
    def left(self) -> int:
        return max(0, self.allowance - self.used)

    @property
    def share_used(self) -> float:
        return (self.used / self.allowance) if self.allowance else 0.0

    @property
    def tight(self) -> bool:
        return self.share_used >= quota.SHOUT_AT

    @property
    def words(self) -> str:
        return f"{self.used:,} of {self.allowance:,} operations used today, {self.left:,} left."


def quota_today(
    session: Session,
    account: UserAccount | None,
    *,
    customer_id: str,
    today: date | None = None,
) -> Room:
    """What is left of one account's daily operations."""
    require(session, account, "read_platform")
    day = today or datetime.now(UTC).date()
    found = quota.room_today(session, customer_id, today=day)
    return Room(
        customer_id=customer_id,
        used=found.used,
        allowance=found.allowance,
        day=day,
    )


@dataclass(frozen=True, slots=True)
class Flag:
    """One deployment setting, and whether the panel can change it.

    `changeable=False` is most of them, and saying so is the point: a screen
    that shows a toggle for something only a deploy can change teaches people
    the panel is lying to them.
    """

    name: str
    on: bool
    what_it_does: str
    changeable: bool = False
    why_not: str = ""


def flags(
    session: Session,
    account: UserAccount | None,
    *,
    writes_enabled: bool,
    auto_apply_enabled: bool,
    open_to: str,
    model_provider: str,
    armor_template: str,
) -> tuple[Flag, ...]:
    """Every setting that governs behaviour, with what each one means.

    Read-only, and honest about it. These come from the environment, so the
    panel reports them and the deploy changes them. The two that matter most --
    whether PPCWay may write to Google Ads at all, and whether it may do so
    without asking -- are deliberately not switches: a button that could turn
    on live writing to a merchant's account would be the most dangerous control
    in the product.
    """
    require(session, account, "read_platform")
    a_deploy = "This comes from the deployment's settings; it takes a deploy to change."
    return (
        Flag(
            name="Writing to Google Ads",
            on=writes_enabled,
            what_it_does=(
                "Whether PPCWay may change anything in a merchant's Google Ads account."
                " Off means every approved change is recorded and nothing is sent."
            ),
            changeable=False,
            why_not=a_deploy,
        ),
        Flag(
            name="Applying without asking",
            on=auto_apply_enabled,
            what_it_does=(
                "Whether a merchant who has opted in may have low-risk changes applied"
                " without answering each one. Off by default for every new account."
            ),
            changeable=False,
            why_not=a_deploy,
        ),
        Flag(
            name="Open to everybody",
            on=open_to.strip().lower() in ("all", "everybody", "*"),
            what_it_does=("Whether anybody can make an account, or only people who were invited."),
            changeable=False,
            why_not=a_deploy,
        ),
        Flag(
            name="Otto can talk",
            on=bool(model_provider),
            what_it_does=f"Which service answers a merchant's questions: {model_provider or 'none'}.",
            changeable=False,
            why_not=a_deploy,
        ),
        Flag(
            name="Chat is screened",
            on=bool(armor_template),
            what_it_does=(
                "Whether Model Armor checks what a merchant types before it is sent."
                " With no template, chat refuses rather than sending anything unscreened."
            ),
            changeable=False,
            why_not=a_deploy,
        ),
    )


def may_stop_writes(session: Session, account: UserAccount | None) -> bool:
    """Whether to show the stop button at all, rather than show it and refuse.

    A disabled button somebody can see and not press is a better screen than a
    button that fails, and a far better one than a button that is missing with
    no explanation.
    """
    from ppcway.staff.guard import level_of
    from ppcway.staff.models import may

    held = level_of(session, account)
    return held is not None and may(held, "stop_writes")


def levels_for_screen() -> tuple[tuple[str, str], ...]:
    """The three levels and what each is for, for a screen that grants them."""
    return (
        (
            Level.SUPPORT.value,
            "Reads a merchant's figures to answer a question. Changes nothing.",
        ),
        (
            Level.ENGINEER.value,
            (
                "Reads the platform's health and can re-run a job. Cannot touch a"
                " merchant's Google Ads account."
            ),
        ),
        (
            Level.PRINCIPAL.value,
            "The kill switch, the settings, and granting access to other people.",
        ),
    )


def quota_everywhere(
    session: Session,
    account: UserAccount | None,
    *,
    today: date | None = None,
) -> list[Room]:
    """Every connected account's quota today, tightest first.

    Tightest first because the screen's job is to show who is about to run out,
    and an alphabetical list makes somebody read all of it to find out.
    """
    require(session, account, "read_platform")
    from ppcway.ads.models import AdsConnection

    day = today or datetime.now(UTC).date()
    seen: set[str] = set()
    out: list[Room] = []
    for row in session.scalars(select(AdsConnection).where(AdsConnection.customer_id != "")):
        customer_id = row.customer_id or ""
        if not customer_id or customer_id in seen:
            continue
        seen.add(customer_id)
        found = quota.room_today(session, customer_id, today=day)
        out.append(
            Room(customer_id=customer_id, used=found.used, allowance=found.allowance, day=day)
        )
    out.sort(key=lambda one: one.share_used, reverse=True)
    return out
