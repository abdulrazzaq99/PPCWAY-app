"""Putting a message in the post, and refusing to pretend.

An invitation that silently goes nowhere is worse than one that fails loudly:
the sender waits, and the person who should have received it never knew.
"""

from __future__ import annotations

import base64
import json

import httpx
import pytest

from ppcway.mail.letters import audit_ready, invitation, verify_email
from ppcway.mail.send import Attachment, Letter, NotSent, Post, send

LIVE = Post(sender="PPCway <hello@ppcway.com>", provider="resend", api_key="key")


def provider(status: int = 200) -> tuple[httpx.Client, list[dict[str, object]]]:
    sent: list[dict[str, object]] = []

    def handle(request: httpx.Request) -> httpx.Response:
        sent.append(
            {
                "headers": dict(request.headers),
                "body": json.loads(request.content),
                "url": str(request.url),
            }
        )
        return httpx.Response(status, json={"id": "abc"} if status < 300 else {"message": "no"})

    return httpx.Client(transport=httpx.MockTransport(handle)), sent


def test_nothing_configured_refuses_rather_than_dropping_it() -> None:
    with pytest.raises(NotSent) as refused:
        send(Post(sender="PPCway <hello@ppcway.com>"), Letter(to="d@x.ca", subject="Hi", text="Hi"))
    assert "not set up" in str(refused.value)


def test_a_message_goes_with_its_text_and_html() -> None:
    c, sent = provider()
    with c:
        send(
            LIVE,
            Letter(to="dana@alphaplumbing.ca", subject="Hello", text="Plain", html="<p>Rich</p>"),
            client=c,
        )
    body = sent[0]["body"]
    assert body["to"] == ["dana@alphaplumbing.ca"]
    assert body["text"] == "Plain"
    assert body["html"] == "<p>Rich</p>"


def test_the_key_travels_in_a_header_never_in_the_address() -> None:
    """A refusal quotes the URL. A key in the URL ends up in a log."""
    c, sent = provider()
    with c:
        send(LIVE, Letter(to="d@x.ca", subject="Hi", text="Hi"), client=c)
    assert "key" not in sent[0]["url"]
    assert sent[0]["headers"]["authorization"] == "Bearer key"


def test_a_refusal_says_so(caplog: pytest.LogCaptureFixture) -> None:
    c, _ = provider(status=422)
    with c, pytest.raises(NotSent) as refused:
        send(LIVE, Letter(to="d@x.ca", subject="Hi", text="Hi"), client=c)
    assert "refused" in str(refused.value)


def test_every_letter_carries_its_link_in_the_plain_text_too() -> None:
    """Some people read mail as text, and some clients strip the button."""
    letters = [
        verify_email(to="d@x.ca", name="Dana Reid", link="https://app.ppcway.com/verify?t=1"),
        invitation(
            to="s@x.ca",
            business="Alpha Plumbing",
            inviter="Dana",
            role="member",
            link="https://app.ppcway.com/invite?token=2",
        ),
        audit_ready(
            to="d@x.ca", business="Alpha Plumbing", score=61, link="https://app.ppcway.com/audit/3"
        ),
    ]
    for letter in letters:
        link = [w for w in letter.text.split() if w.startswith("https://")]
        assert link, f"{letter.subject} has no link in its text"
        assert link[0] in letter.html


def test_an_invitation_says_what_the_role_can_do() -> None:
    letter = invitation(
        to="maya@ppcway.com",
        business="Alpha Plumbing",
        inviter="Dana",
        role="expert",
        link="https://app.ppcway.com/invite?token=9",
    )
    assert "sign off" in letter.text
    assert "Alpha Plumbing" in letter.subject


def test_an_attachment_travels_base64_to_the_provider() -> None:
    """The provider takes bytes as text, so they have to be encoded on the way."""
    c, sent = provider()
    with c:
        send(
            LIVE,
            Letter(
                to="dana@alphaplumbing.ca",
                subject="Your audit",
                text="It is attached.",
                attachments=(Attachment(filename="audit.pdf", content=b"%PDF-1.4 hello"),),
            ),
            client=c,
        )
    files = sent[0]["body"]["attachments"]  # type: ignore[index]
    assert files == [
        {
            "filename": "audit.pdf",
            "content": base64.b64encode(b"%PDF-1.4 hello").decode("ascii"),
            "content_type": "application/pdf",
        }
    ]


def test_a_letter_with_an_attachment_is_still_readable_as_a_message() -> None:
    """Text, HTML and the file: three parts, and the words come first."""
    message = Letter(
        to="dana@alphaplumbing.ca",
        subject="Your audit",
        text="It is attached.",
        html="<p>It is attached.</p>",
        attachments=(Attachment(filename="audit.pdf", content=b"%PDF-1.4 hello"),),
    ).as_email("PPCway <hello@ppcway.com>")

    assert message.get_content_type() == "multipart/mixed"
    carried = list(message.iter_attachments())
    assert [part.get_filename() for part in carried] == ["audit.pdf"]
    assert carried[0].get_content_type() == "application/pdf"
    assert message.get_body(("plain",)) is not None
    assert message.get_body(("html",)) is not None
