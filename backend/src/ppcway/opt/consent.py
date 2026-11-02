"""What a merchant agreed to when they let Otto act without asking.

The client's brief specifies this one in full, and the shape of the record is
the specification: *account, user (owner only), timestamp, IP, consent wording
version, change types, limits.* Every field on it answers a question somebody
will ask later, and the whole row exists because "they agreed" is not an answer
to any of them.

- **the wording version**, because the words change. A consent given against
  version 1 is consent to version 1, and a dispute about what somebody agreed
  to cannot be settled by reading the page as it stands today.
- **the change types**, because consent to excluding wasteful searches is not
  consent to pausing ads. Snapshotted rather than read from the catalogue at
  the moment of acting: adding a rule to the eligible list must not silently
  widen a permission somebody gave last March.
- **the limits**, snapshotted for the same reason. Somebody who agreed while
  the cap was 20% did not agree to 50%.
- **the IP and the timestamp**, because that is what makes the record evidence
  rather than a note.
- **owner only**, enforced here. An admin cannot sign away the owner's money.

**Five things have to agree before anything is applied unasked**, and this
module is one of them. The deployment's feature flag, the account's autonomy
level, the client naming the change type as eligible, a live consent record,
and that record covering this particular type. Any one missing means a person
is asked, which is approve-first and is the default for a reason.
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Final

from sqlalchemy import (
    JSON,
    DateTime,
    ForeignKey,
    String,
    Text,
    Uuid,
    func,
    select,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, Session, mapped_column

from ppcway.db.base import Base
from ppcway.opt.guardrails import Limits
from ppcway.opt.models import Autonomy
from ppcway.org.models import Role
from ppcway.rules.catalogue import CATALOGUE

log = logging.getLogger(__name__)

#: The version of the words somebody is agreeing to. Bumped whenever the
#: consent screen's text changes in a way that changes what is being agreed,
#: and never reused. An old consent keeps naming the old version, which is
#: what makes it answerable.
WORDING: Final = "auto-apply-2026-11-02"

#: The words themselves, served with the screen rather than written into it,
#: so the record and the page cannot drift apart. The client approves this
#: text; it is here so that what was agreed is stored beside the version.
THE_WORDS: Final = (
    "You are letting PPCWay make two kinds of change to your Google Ads "
    "account without asking you first:\n\n"
    "  * excluding searches that have cost you money and never led to anybody "
    "getting in touch, and\n"
    "  * pausing ads that Google has refused and which are therefore not "
    "being shown to anybody.\n\n"
    "Nothing else. We will not change your budgets, your bids or your ad text "
    "without asking.\n\n"
    "Every change is written down, appears in your activity feed and in "
    "Monday's email, and can be put back for thirty days. You can turn this "
    "off at any moment, and turning it off stops it straight away."
)


class NotTheirs(PermissionError):
    """Only the owner may give or withdraw this."""


class AutoApplyConsent(Base):
    """One business's standing permission for Otto to act without asking.

    Never updated in place except to withdraw it, and a withdrawal does not
    delete the row: that somebody once agreed, and when, and to what, is the
    record. A new permission is a new row.
    """

    __tablename__ = "opt_auto_apply_consent"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organization.id"), index=True)
    #: The owner who gave it. Not "a user": the brief says owner only.
    account_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("account.id"))
    given_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )
    #: Where from. Part of what makes this evidence rather than a note.
    ip: Mapped[str] = mapped_column(String(45), default="")
    #: Which version of the words. See WORDING.
    wording: Mapped[str] = mapped_column(String(40), default=WORDING)
    #: The exact text they were shown, kept whole. A version number identifies
    #: the words; this is the words, because a dispute six months from now is
    #: not helped by an identifier whose text nobody kept.
    words: Mapped[str] = mapped_column(Text, default="")
    #: The change types agreed to, snapshotted. Adding a rule to the eligible
    #: list must not widen a permission given last March.
    change_types: Mapped[dict[str, Any] | None] = mapped_column(
        JSON().with_variant(JSONB(), "postgresql"), nullable=True
    )
    #: The limits in force when they agreed. Somebody who agreed while the cap
    #: was 20% did not agree to 50%.
    limits: Mapped[dict[str, Any] | None] = mapped_column(
        JSON().with_variant(JSONB(), "postgresql"), nullable=True
    )
    withdrawn_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    withdrawn_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("account.id"), nullable=True)

    @property
    def live(self) -> bool:
        return self.withdrawn_at is None

    def covers(self, kind: str) -> bool:
        """Whether this permission extends to one change type."""
        agreed = (self.change_types or {}).get("kinds") or []
        return kind in agreed


@dataclass(frozen=True, slots=True)
class Standing:
    """Whether Otto may act unasked on this business, and why not if not."""

    may: bool
    because: str = ""
    #: Which of the five said no, so a screen can say which and a log can be
    #: grepped for the one that matters.
    stopped_by: str = ""


#: The change types the client has named as eligible, read from the rules
#: rather than restated: a rule marked auto-eligible in one place and listed
#: here in another is two places to disagree.
def eligible_kinds() -> tuple[str, ...]:
    return tuple(sorted({rule.kind for rule in CATALOGUE.values() if rule.auto_eligible}))


def current(session: Session, organization_id: uuid.UUID) -> AutoApplyConsent | None:
    """The live permission for a business, or None."""
    return session.scalars(
        select(AutoApplyConsent)
        .where(
            AutoApplyConsent.organization_id == organization_id,
            AutoApplyConsent.withdrawn_at.is_(None),
        )
        .order_by(AutoApplyConsent.given_at.desc())
    ).first()


def may_apply_unasked(
    session: Session,
    *,
    organization_id: uuid.UUID,
    kind: str,
    autonomy: str,
    flag_on: bool,
) -> Standing:
    """All five answers. Any one no means a person is asked."""
    if not flag_on:
        return Standing(
            may=False,
            because=(
                "Otto is not making changes on its own yet. Everything is proposed"
                " and waits for you."
            ),
            stopped_by="flag",
        )
    if kind not in eligible_kinds():
        return Standing(
            may=False,
            because="That kind of change always needs a person.",
            stopped_by="kind",
        )
    if autonomy != Autonomy.FULL_AUTO.value:
        return Standing(
            may=False,
            because="This account applies nothing without being asked first.",
            stopped_by="autonomy",
        )
    held = current(session, organization_id)
    if held is None:
        return Standing(
            may=False,
            because="Nobody has agreed to let Otto make changes on its own.",
            stopped_by="consent",
        )
    if not held.covers(kind):
        return Standing(
            may=False,
            because=("The permission on this account does not cover that kind of change."),
            stopped_by="consent_scope",
        )
    return Standing(may=True)


def give(
    session: Session,
    *,
    organization_id: uuid.UUID,
    account_id: uuid.UUID,
    role: Role | None,
    ip: str = "",
    limits: Limits | None = None,
    now: datetime | None = None,
) -> AutoApplyConsent:
    """Record a permission. Owner only, and the record says what was agreed.

    Giving it again while one is live withdraws the old one first, so there is
    never more than one live permission and the one that is live is always the
    most recent set of words somebody actually read.
    """
    if role is not Role.OWNER:
        raise NotTheirs(
            "Only the owner of the business can let Otto make changes without asking."
            " An admin cannot agree to this on their behalf."
        )
    at = now or datetime.now(UTC)
    held = current(session, organization_id)
    if held is not None:
        held.withdrawn_at = at
        held.withdrawn_by = account_id

    limits = limits or Limits()
    record = AutoApplyConsent(
        organization_id=organization_id,
        account_id=account_id,
        given_at=at,
        ip=ip[:45],
        wording=WORDING,
        words=THE_WORDS,
        change_types={"kinds": list(eligible_kinds())},
        limits={
            "version": limits.version,
            "max_change_pct": limits.max_change_pct,
            "max_daily_change_pct": limits.max_daily_change_pct,
            "max_changes_per_day": limits.max_changes_per_day,
            "max_daily_budget": limits.max_daily_budget,
        },
    )
    session.add(record)
    session.commit()
    log.info("auto-apply agreed for %s against %s", organization_id, WORDING)
    return record


def withdraw(
    session: Session,
    *,
    organization_id: uuid.UUID,
    account_id: uuid.UUID,
    role: Role | None,
    now: datetime | None = None,
) -> AutoApplyConsent | None:
    """Turn it off. Takes effect at once, and the record stays.

    The owner or an admin may turn it off, which is deliberately wider than
    who may turn it on: making it harder to stop than to start would be the
    wrong way round.
    """
    if role not in {Role.OWNER, Role.ADMIN}:
        raise NotTheirs("Your role does not allow you to change this setting.")
    held = current(session, organization_id)
    if held is None:
        return None
    held.withdrawn_at = now or datetime.now(UTC)
    held.withdrawn_by = account_id
    session.commit()
    return held
