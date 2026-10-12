"""Finding somebody's organisation, and deciding what they may do in it.

Every endpoint that touches a business's data asks one question here: which
organisation is this, and may this person do this to it. The answer is not the
interface's to decide, which is the requirement's own wording.
"""

from __future__ import annotations

import secrets
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session as DbSession

from ppcway.auth.google import hash_session_token
from ppcway.auth.models import UserAccount
from ppcway.org.models import CAN, Invitation, Membership, Organization, Role

#: How long an invitation link works for. Long enough to be read on Monday.
INVITE_DAYS = 14


class NotAllowed(PermissionError):
    """This person may not do this. Carries what was refused, never why in detail:
    whether a thing exists is itself something to know."""


def home_for(session: DbSession, account: UserAccount) -> Organization:
    """The organisation this person belongs to, made on the spot if they have none.

    Somebody who signed up before organisations existed, or who has just arrived
    from the free audit, owns a business of one. They do not fill in a form to
    get it; the first thing they do in the app creates it.
    """
    place = session.scalar(
        select(Organization)
        .join(Membership, Membership.organization_id == Organization.id)
        .where(Membership.account_id == account.id)
        .order_by(Membership.created_at.asc())
    )
    if place is not None:
        return place

    place = Organization(name=account.name or account.email.split("@")[0] or "My business")
    session.add(place)
    session.flush()
    session.add(Membership(organization_id=place.id, account_id=account.id, role=Role.OWNER.value))
    session.commit()
    return place


def role_of(session: DbSession, account: UserAccount, place: Organization) -> Role | None:
    """What this person is in that organisation, or None if they are nothing."""
    held = session.scalar(
        select(Membership).where(
            Membership.organization_id == place.id, Membership.account_id == account.id
        )
    )
    if held is None:
        return None
    try:
        return Role(held.role)
    except ValueError:  # a role written by a newer version of this code
        return None


def may(session: DbSession, account: UserAccount, place: Organization, what: str) -> bool:
    """Whether they may do one named thing."""
    role = role_of(session, account, place)
    return role is not None and what in CAN[role]


def insist(session: DbSession, account: UserAccount, place: Organization, what: str) -> None:
    """The same question, raising rather than answering, for an endpoint to use."""
    if not may(session, account, place, what):
        raise NotAllowed(what)


def people_in(session: DbSession, place: Organization) -> list[tuple[UserAccount, Role]]:
    """Everybody in the organisation, with what they are."""
    rows = session.execute(
        select(UserAccount, Membership.role)
        .join(Membership, Membership.account_id == UserAccount.id)
        .where(Membership.organization_id == place.id)
        .order_by(Membership.created_at.asc())
    ).all()
    out: list[tuple[UserAccount, Role]] = []
    for person, role in rows:
        try:
            out.append((person, Role(role)))
        except ValueError:
            continue
    return out


def invite(
    session: DbSession,
    place: Organization,
    *,
    by: UserAccount,
    email: str,
    role: Role,
) -> str:
    """Ask somebody to join. Returns the secret for the link, once.

    An owner cannot be invited: there is one, and it is whoever pays. Inviting
    somebody who is already here changes nothing and says so by raising.
    """
    if role is Role.OWNER:
        raise NotAllowed("invite an owner")
    address = email.strip().lower()
    already = session.scalar(
        select(Membership)
        .join(UserAccount, UserAccount.id == Membership.account_id)
        .where(Membership.organization_id == place.id, UserAccount.email == address)
    )
    if already is not None:
        raise NotAllowed("invite somebody already here")

    token = secrets.token_urlsafe(32)
    session.add(
        Invitation(
            organization_id=place.id,
            email=address,
            role=role.value,
            invited_by=by.id,
            token_hash=hash_session_token(token),
            expires_at=datetime.now(UTC) + timedelta(days=INVITE_DAYS),
        )
    )
    session.commit()
    return token


def accept(session: DbSession, token: str, account: UserAccount) -> Organization | None:
    """Take up an invitation, or None if it is spent, expired or not theirs.

    The address has to match. An invitation is to a person, not a link to pass
    around, and the whole point of roles is undone if it is the second thing.
    """
    held = session.scalar(
        select(Invitation).where(Invitation.token_hash == hash_session_token(token))
    )
    if held is None or held.accepted_at or held.revoked_at:
        return None
    expires = held.expires_at
    if expires.tzinfo is None:
        expires = expires.replace(tzinfo=UTC)
    if expires <= datetime.now(UTC):
        return None
    if held.email.strip().lower() != account.email.strip().lower():
        return None

    place = session.get(Organization, held.organization_id)
    if place is None:
        return None
    if role_of(session, account, place) is None:
        session.add(Membership(organization_id=place.id, account_id=account.id, role=held.role))
    held.accepted_at = datetime.now(UTC)
    session.commit()
    return place


def change_role(session: DbSession, place: Organization, account: UserAccount, role: Role) -> None:
    """Move somebody between roles. The last owner cannot be demoted."""
    held = session.scalar(
        select(Membership).where(
            Membership.organization_id == place.id, Membership.account_id == account.id
        )
    )
    if held is None:
        raise NotAllowed("change somebody who is not here")
    if held.role == Role.OWNER.value and role is not Role.OWNER and _owners(session, place) <= 1:
        raise NotAllowed("leave the business with no owner")
    held.role = role.value
    session.commit()


def remove(session: DbSession, place: Organization, account: UserAccount) -> None:
    """Take somebody out. The last owner stays, or nobody could ever pay."""
    held = session.scalar(
        select(Membership).where(
            Membership.organization_id == place.id, Membership.account_id == account.id
        )
    )
    if held is None:
        return
    if held.role == Role.OWNER.value and _owners(session, place) <= 1:
        raise NotAllowed("leave the business with no owner")
    session.delete(held)
    session.commit()


def _owners(session: DbSession, place: Organization) -> int:
    return len(
        session.scalars(
            select(Membership).where(
                Membership.organization_id == place.id, Membership.role == Role.OWNER.value
            )
        ).all()
    )
