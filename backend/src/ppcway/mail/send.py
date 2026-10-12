"""Putting a message in the post.

One function the rest of the app calls, and two ways of carrying it out: an HTTP
provider, or plain SMTP for a business that already has a mailbox. Neither is
chosen here; the deployment says which, and with nothing configured `send`
refuses rather than pretending.

That refusal matters. An invitation that silently goes nowhere is worse than one
that fails loudly: the person who sent it waits, and the person who should have
received it never knew.
"""

from __future__ import annotations

import logging
import smtplib
from dataclasses import dataclass
from email.message import EmailMessage

import httpx

log = logging.getLogger(__name__)

RESEND_ENDPOINT = "https://api.resend.com/emails"


class NotSent(RuntimeError):
    """The message did not go. Carries why, in words a log reader can act on."""


@dataclass(frozen=True)
class Letter:
    """One message. Plain text always; HTML when it is worth the trouble."""

    to: str
    subject: str
    text: str
    html: str = ""

    def as_email(self, sender: str) -> EmailMessage:
        message = EmailMessage()
        message["From"] = sender
        message["To"] = self.to
        message["Subject"] = self.subject
        message.set_content(self.text)
        if self.html:
            message.add_alternative(self.html, subtype="html")
        return message


@dataclass(frozen=True)
class Post:
    """How this deployment sends. Built once from settings, passed where needed."""

    sender: str
    provider: str = ""
    api_key: str = ""
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""

    @property
    def ready(self) -> bool:
        if self.provider == "resend":
            return bool(self.api_key and self.sender)
        if self.provider == "smtp":
            return bool(self.smtp_host and self.sender)
        return False


def send(post: Post, letter: Letter, *, client: httpx.Client | None = None) -> None:
    """Send one message, or raise saying why it did not go."""
    if not post.ready:
        raise NotSent("email is not set up: no provider is configured, so nothing was sent")
    if post.provider == "resend":
        _by_resend(post, letter, client=client)
    elif post.provider == "smtp":
        _by_smtp(post, letter)
    else:
        raise NotSent(f"unknown email provider {post.provider!r}")
    log.info("sent %r to %s", letter.subject, _blurred(letter.to))


def _by_resend(post: Post, letter: Letter, *, client: httpx.Client | None = None) -> None:
    own = client is None
    c = client or httpx.Client(timeout=httpx.Timeout(20))
    try:
        body: dict[str, object] = {
            "from": post.sender,
            "to": [letter.to],
            "subject": letter.subject,
            "text": letter.text,
        }
        if letter.html:
            body["html"] = letter.html
        reply = c.post(
            RESEND_ENDPOINT,
            headers={"Authorization": f"Bearer {post.api_key}"},
            json=body,
        )
        if reply.status_code >= 300:
            # The key is in the header, never in the URL, so this cannot leak it.
            raise NotSent(f"the email provider refused it: {reply.status_code} {reply.text[:200]}")
    except httpx.HTTPError as exc:
        raise NotSent(f"the email provider could not be reached: {exc}") from None
    finally:
        if own:
            c.close()


def _by_smtp(post: Post, letter: Letter) -> None:
    try:
        with smtplib.SMTP(post.smtp_host, post.smtp_port, timeout=20) as server:
            server.starttls()
            if post.smtp_user:
                server.login(post.smtp_user, post.smtp_password)
            server.send_message(letter.as_email(post.sender))
    except (smtplib.SMTPException, OSError) as exc:
        raise NotSent(f"the mail server refused it: {exc}") from None


def _blurred(address: str) -> str:
    """An address in a log, recognisable to its owner and nobody else."""
    name, _, domain = address.partition("@")
    return f"{name[:2]}…@{domain}" if domain else "…"
