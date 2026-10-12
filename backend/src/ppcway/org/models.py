"""Who a business is, and who may do what inside it.

The requirements name five roles, and are explicit that the limits are enforced
in the backend rather than hidden in the interface. So this is the table every
screen and every endpoint asks before it does anything.

One organisation per paying customer or agency. A person can belong to several:
an agency's staff sit in the agency and in each client they look after, and an
expert is a person with a membership of the accounts assigned to them.
"""

from __future__ import annotations

import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from ppcway.db.base import Base


class Role(str, enum.Enum):
    """The five roles, in order of what they may do.

    Spelled out rather than numbered, because a role appears in the change log
    and a reader should not have to look up what a 3 meant.
    """

    OWNER = "owner"
    ADMIN = "admin"
    MEMBER = "member"
    EXPERT = "expert"
    CLIENT_VIEWER = "client_viewer"


#: What each role may do. Read as "can this role do this thing", and nothing
#: else: a capability absent here is refused, so adding a power is deliberate.
CAN: dict[Role, frozenset[str]] = {
    Role.OWNER: frozenset(
        {
            "view",
            "propose",
            "approve",
            "connect",
            "disconnect",
            "invite",
            "billing",
            "thresholds",
        }
    ),
    Role.ADMIN: frozenset({"view", "propose", "approve", "connect", "disconnect", "invite"}),
    Role.MEMBER: frozenset({"view", "propose"}),
    # An expert signs off high-risk changes and logs hours; they do not own the
    # account and cannot connect or disconnect it.
    Role.EXPERT: frozenset({"view", "propose", "approve", "sign_off", "log_hours"}),
    # An agency's client sees their own results and nothing else.
    Role.CLIENT_VIEWER: frozenset({"view"}),
}


class Organization(Base):
    """One paying customer, or one agency."""

    __tablename__ = "organization"
    id: Mapped[uuid.UUID] = mapped_column(Uuid(), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(200))
    #: starter, growth or agency. The plan's limits live in code, not here.
    plan: Mapped[str] = mapped_column(String(20), default="starter")
    #: Where the business is, which decides currency and, later, residency.
    country: Mapped[str] = mapped_column(String(2), default="CA")
    currency: Mapped[str] = mapped_column(String(3), default="CAD")
    #: The customer id at the payment provider, when there is one.
    billing_customer: Mapped[str] = mapped_column(String(80), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Membership(Base):
    """One person's place in one organisation."""

    __tablename__ = "membership"
    __table_args__ = (UniqueConstraint("organization_id", "account_id", name="one_place_each"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid(), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organization.id"), index=True)
    account_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("account.id"), index=True)
    role: Mapped[str] = mapped_column(String(20), default=Role.OWNER.value)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Invitation(Base):
    """Somebody asked to join, who has not arrived yet.

    Held by the address they were invited at, because that is all we know about
    them until they sign in and become an account.
    """

    __tablename__ = "membership_invite"
    id: Mapped[uuid.UUID] = mapped_column(Uuid(), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organization.id"), index=True)
    email: Mapped[str] = mapped_column(String(320), index=True)
    role: Mapped[str] = mapped_column(String(20), default=Role.MEMBER.value)
    invited_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("account.id"))
    #: The secret in the link, held as a hash like any other credential.
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
