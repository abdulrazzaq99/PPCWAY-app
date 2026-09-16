"""The conversion path: what a visitor can do in the first screen, and what gets
in the way. Chat and booking tools tell us how leads would arrive."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime

TOOLS = {
    "chat": (
        ("Tawk.to", "tawk.to"), ("Intercom", "intercom.io"), ("Drift", "drift.com"), ("Tidio", "tidio.co"),
        ("LiveChat", "livechatinc.com"), ("Crisp", "crisp.chat"), ("HubSpot chat", "hs-scripts.com"),
        ("Podium", "podium.com"), ("Birdeye", "birdeye.com"), ("Zendesk", "zdassets.com"),
    ),
    "booking": (
        ("Housecall Pro", "housecallpro.com"), ("Jobber", "getjobber.com"), ("ServiceTitan", "servicetitan.com"),
        ("Calendly", "calendly.com"), ("Acuity", "acuityscheduling.com"), ("Square Appointments", "squareup.com/appointments"),
        ("Setmore", "setmore.com"), ("Booksy", "booksy.com"), ("Mindbody", "mindbodyonline.com"),
    ),
}


@dataclass
class ConversionSignals:
    headline: str
    has_h1: bool
    ctas_above_fold: list[str]
    phone_above_fold: bool
    tel_link: bool
    overlay: str | None
    chat_tool: str | None
    booking_tool: str | None
    copyright_year: int | None
    #: Years behind the current year, 0 when current or unknown.
    years_stale: int = 0
    form_fields: int | None = None
    problems: list[str] = field(default_factory=list)


def detect_conversion(*, html: str, scripts: list[str], requests: list[str], headline: str, has_h1: bool,
                      ctas: list[str], phone_above_fold: bool, tel_links: list[str], overlay: str | None,
                      copyright_year: int | None, form_fields: int | None) -> ConversionSignals:
    everything = (html + "\n".join(scripts) + "\n".join(requests)).lower()
    found: dict[str, str | None] = {"chat": None, "booking": None}
    for kind, tools in TOOLS.items():
        for name, needle in tools:
            if needle in everything:
                found[kind] = name
                break
    stale = 0
    if copyright_year:
        stale = max(0, datetime.now(UTC).year - copyright_year)
    out = ConversionSignals(
        headline=headline, has_h1=has_h1, ctas_above_fold=ctas, phone_above_fold=phone_above_fold,
        tel_link=bool(tel_links), overlay=overlay, chat_tool=found["chat"], booking_tool=found["booking"],
        copyright_year=copyright_year, years_stale=stale, form_fields=form_fields,
    )
    if overlay:
        out.problems.append(f"A pop-up covers the page on arrival ({overlay[:60]}).")
    if not ctas and not phone_above_fold:
        out.problems.append("Nothing to do in the first screen: no call button, quote button or phone number before scrolling.")
    if not has_h1:
        out.problems.append("The page has no headline (no h1), so the first thing a visitor reads is not chosen.")
    if form_fields is not None and form_fields > 6:
        out.problems.append(f"The contact form asks {form_fields} questions. Four or fewer gets more sends.")
    if stale >= 2:
        out.problems.append(f"The footer says {copyright_year}. A stale year reads as a closed business.")
    return out
