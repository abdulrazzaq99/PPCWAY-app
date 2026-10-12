"""The messages themselves, in the words a small business owner would use.

Every one says who it is from, what it is about and what to do, in that order,
and none of them says "click here". A plumber reading this on a phone between
jobs should know in one line whether it needs them.
"""

from __future__ import annotations

from ppcway.mail.send import Letter

#: The signature on every message, so a reader knows who is writing.
FOOT = "PPCway · Mississauga, Ontario"


def _wrap(title: str, body: str, action: tuple[str, str] | None = None) -> str:
    """One plain layout for all of them. No images, no tracking, no columns."""
    button = ""
    if action:
        label, link = action
        button = (
            f'<p style="margin:26px 0"><a href="{link}" '
            'style="background:#2F5BEA;color:#fff;text-decoration:none;padding:12px 20px;'
            'border-radius:10px;font-weight:700;display:inline-block">'
            f"{label}</a></p>"
            f'<p style="color:#6B6680;font-size:13px;line-height:19px">'
            f"If the button does not work, this is the address: {link}</p>"
        )
    return (
        '<div style="font-family:system-ui,-apple-system,Segoe UI,sans-serif;'
        'color:#15112A;max-width:560px;margin:0 auto;padding:28px 20px">'
        f'<h1 style="font-size:21px;line-height:27px;margin:0 0 14px">{title}</h1>'
        f'<div style="font-size:15px;line-height:24px;color:#3A3550">{body}</div>'
        f"{button}"
        f'<p style="color:#8A8599;font-size:12px;margin-top:30px;border-top:1px solid #E8E5DF;'
        f'padding-top:14px">{FOOT}</p>'
        "</div>"
    )


def verify_email(*, to: str, name: str, link: str) -> Letter:
    """Confirming an address belongs to the person who typed it."""
    hello = f"Hello {name.split(' ')[0]}," if name else "Hello,"
    text = (
        f"{hello}\n\n"
        "Confirm this is your address and your PPCway account is ready:\n\n"
        f"{link}\n\n"
        "The link works for two days. If you did not make an account, ignore this "
        "and nothing happens.\n\n"
        f"{FOOT}"
    )
    html = _wrap(
        "Confirm your email address",
        f"<p>{hello}</p><p>Confirm this is your address and your PPCway account is ready. "
        "The link works for two days.</p>"
        "<p>If you did not make an account, ignore this and nothing happens.</p>",
        ("Confirm my address", link),
    )
    return Letter(to=to, subject="Confirm your email address", text=text, html=html)


def invitation(*, to: str, business: str, inviter: str, role: str, link: str) -> Letter:
    """Asking somebody to join a business."""
    what = {
        "admin": "approve changes and invite people",
        "member": "see everything and suggest changes",
        "expert": "sign off the riskier changes and log your hours",
        "client_viewer": "see how the advertising is doing",
    }.get(role, "work on the account")
    text = (
        f"{inviter} has asked you to join {business} on PPCway.\n\n"
        f"As {role.replace('_', ' ')}, you will be able to {what}.\n\n"
        f"{link}\n\n"
        "The link works once, for this address, for fourteen days. If you were not "
        "expecting it, ignore it.\n\n"
        f"{FOOT}"
    )
    html = _wrap(
        f"{inviter} invited you to {business}",
        f"<p>As <strong>{role.replace('_', ' ')}</strong>, you will be able to {what}.</p>"
        "<p>The link works once, for this address, for fourteen days. "
        "If you were not expecting it, ignore it.</p>",
        ("Join " + business, link),
    )
    return Letter(
        to=to, subject=f"{inviter} invited you to {business} on PPCway", text=text, html=html
    )


def reset_password(*, to: str, name: str, link: str) -> Letter:
    """Somebody asked to set a new password."""
    hello = f"Hello {name.split(' ')[0]}," if name else "Hello,"
    text = (
        f"{hello}\n\n"
        "Somebody asked to reset the password on your PPCway account. If it was you, "
        "set a new one here:\n\n"
        f"{link}\n\n"
        "The link works for two hours and once only. If it was not you, ignore this: "
        "your password has not changed and nobody has been let in.\n\n"
        f"{FOOT}"
    )
    html = _wrap(
        "Set a new password",
        f"<p>{hello}</p><p>Somebody asked to reset the password on your PPCway account. "
        "The link works for two hours and once only.</p>"
        "<p>If it was not you, ignore this: your password has not changed and nobody "
        "has been let in.</p>",
        ("Set a new password", link),
    )
    return Letter(to=to, subject="Set a new PPCway password", text=text, html=html)


def audit_ready(*, to: str, business: str, score: int, link: str) -> Letter:
    """The free audit, when somebody asked for it by email."""
    text = (
        f"Your PPCway audit of {business} is ready.\n\n"
        f"It scores {score} out of 100 on how you look to somebody searching Google "
        "right now, with every check explained and the ones that cost you money first.\n\n"
        f"{link}\n\n"
        f"{FOOT}"
    )
    html = _wrap(
        f"Your audit of {business} is ready",
        f"<p>It scores <strong>{score} out of 100</strong> on how you look to somebody "
        "searching Google right now, with every check explained and the ones that cost "
        "you money first.</p>",
        ("Read the audit", link),
    )
    return Letter(to=to, subject=f"Your PPCway audit of {business}", text=text, html=html)
