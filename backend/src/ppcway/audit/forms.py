"""Contact form: found, and is there a thank-you page a send can be counted on.

We never submit a form on a merchant's site. What can be seen from outside is
whether a form exists, which product built it, and whether a thank-you page is
linked or sits at one of the usual addresses. When the thank-you step cannot be
seen, the finding asks the merchant one question rather than guessing.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from selectolax.parser import HTMLParser

PROVIDERS = (
    ("Gravity Forms", ("gform_", "gravityforms")),
    ("WPForms", ("wpforms",)),
    ("Contact Form 7", ("wpcf7",)),
    ("HubSpot", ("hsforms", "hs-form")),
    ("Jotform", ("jotform",)),
    ("Typeform", ("typeform.com",)),
    ("Wix", ("wix-form", "wixforms", "static.parastorage.com")),
    ("Squarespace", ("sqs-block-form", "squarespace")),
    ("Webflow", ("w-form", "webflow")),
    ("Elementor", ("elementor-form",)),
    ("Formspree", ("formspree.io",)),
    ("Netlify Forms", ("data-netlify",)),
)

THANK_YOU_PATH = re.compile(r"/(thank[-_]?you|thanks|merci|confirmation|success|submitted)\b", re.IGNORECASE)
SEARCH_HINT = re.compile(r"search|newsletter|subscribe", re.IGNORECASE)
CONTACT_FIELD = re.compile(r"phone|tel|email|name|message", re.IGNORECASE)


@dataclass(frozen=True)
class FormSignals:
    forms_found: int
    #: A form with the shape of a contact form (name, phone, email or message).
    contact_form: bool
    provider: str | None
    #: Where the contact form was seen.
    on_page: str
    thank_you_url: str | None
    #: The form posts somewhere we can see (an action) rather than being script-only.
    has_action: bool
    #: Visible questions on the contact form (inputs, textareas and selects).
    fields: int | None = None


def _field_count(form) -> int:  # type: ignore[no-untyped-def]
    n = 0
    for f in form.css("input, textarea, select"):
        t = (f.attributes.get("type") or "text").lower()
        if t in ("hidden", "submit", "button", "reset", "image"):
            continue
        n += 1
    return n


def _looks_like_contact(form) -> bool:  # type: ignore[no-untyped-def]
    attrs = " ".join(f"{k}={v}" for k, v in (form.attributes or {}).items())
    if SEARCH_HINT.search(attrs):
        return False
    fields = form.css("input, textarea, select")
    named = [
        (f.attributes.get("name") or "") + " " + (f.attributes.get("type") or "") + " " + (f.attributes.get("placeholder") or "")
        for f in fields
    ]
    if any(SEARCH_HINT.search(n) for n in named):
        return False
    real = [n for n in named if "hidden" not in n and "submit" not in n]
    return len(real) >= 2 and any(CONTACT_FIELD.search(n) for n in real)


def detect_forms(pages: list[tuple[str, str]], links: list[str]) -> FormSignals:
    """`pages` is (url, html). `links` are every link the crawl saw."""
    forms_found = 0
    contact_page = ""
    provider: str | None = None
    has_action = False
    fields: int | None = None
    for url, html in pages:
        tree = HTMLParser(html)
        lowered = html.lower()
        if provider is None:
            for name, needles in PROVIDERS:
                if any(n in lowered for n in needles):
                    provider = name
                    break
        for form in tree.css("form"):
            forms_found += 1
            if not contact_page and _looks_like_contact(form):
                contact_page = url
                has_action = bool((form.attributes or {}).get("action"))
                fields = _field_count(form)
    thank_you = next((l for l in links if THANK_YOU_PATH.search(l)), None)
    # Some builders render forms only in the browser: a provider script with no <form>.
    contact = bool(contact_page) or (provider is not None and forms_found == 0)
    return FormSignals(
        forms_found=forms_found,
        contact_form=contact,
        provider=provider,
        on_page=contact_page,
        thank_you_url=thank_you,
        has_action=has_action,
        fields=fields,
    )
