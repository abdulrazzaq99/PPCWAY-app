"""Every page the ads send people to, checked one at a time.

The audit checks a website. This checks the handful of pages that actually
matter to a Google Ads account: the ones the ads link to. A site can score well
overall and still have the one page people land on missing its conversion tag,
covered by a newsletter pop-up, or showing no phone number until you scroll.

Where the pages come from is the point. They are read out of the mirror —
`MirrorAd.final_urls` — so this is not a guess about which pages matter, it is
the list Google itself sends the traffic to, and each result says which
campaigns send people there.

Each page is opened in the same headless browser the main audit uses, because
presence of a tag in the HTML is not the same as a tag firing on load, and the
difference is most of the value here.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import urlsplit, urlunsplit

from sqlalchemy import select
from sqlalchemy.orm import Session

from ppcway.ads.mirror import MirrorAd, MirrorCampaign
from ppcway.audit.render import Rendering, render
from ppcway.audit.tags import classify_tags
from ppcway.config import Settings

log = logging.getLogger(__name__)

#: What a page that will not open at all costs: every click that lands there.
WOULD_NOT_OPEN = (
    "This page could not be opened. Your ads are sending people to it, so every "
    "click that lands here is wasted."
)

#: How many landing pages are worth opening. A small advertiser has one to five;
#: the cap stops a big account turning a daily audit into an hour of browsing.
MOST = 8


def tidy(url: str) -> str:
    """One page, one entry. Tracking parameters are not a different page."""
    parts = urlsplit(url.strip())
    if not parts.scheme or not parts.netloc:
        return ""
    path = parts.path.rstrip("/") or "/"
    return urlunsplit((parts.scheme.lower(), parts.netloc.lower(), path, "", ""))


def landing_pages(session: Session, customer_id: str) -> dict[str, list[str]]:
    """Every page the live ads point at, and which campaigns point there."""
    names = {
        row.campaign_id: row.name
        for row in session.scalars(
            select(MirrorCampaign).where(MirrorCampaign.customer_id == customer_id)
        )
    }
    found: dict[str, list[str]] = {}
    ads = session.scalars(
        select(MirrorAd).where(MirrorAd.customer_id == customer_id, MirrorAd.gone_at.is_(None))
    )
    for ad in ads:
        for raw in ad.final_urls or []:
            url = tidy(str(raw))
            if not url:
                continue
            campaign = names.get(ad.campaign_id, "")
            sending = found.setdefault(url, [])
            if campaign and campaign not in sending:
                sending.append(campaign)
    return found


@dataclass
class PageCheck:
    """One landing page, and what is wrong with it in plain sentences."""

    url: str
    campaigns: list[str] = field(default_factory=list)
    read: bool = False
    trouble: str = ""
    final_url: str = ""
    title: str = ""
    headline: str = ""
    phone_in_view: bool = False
    has_form: bool = False
    #: The buttons above the fold, when there is no form: a tool whose job is an
    #: upload button is not a page with nothing to do on it.
    call_to_action: list[str] = field(default_factory=list)
    #: A Google Ads conversion id is on the page.
    conversion_tag: bool = False
    #: And it actually sent something when the page loaded.
    tag_fired: bool = False
    overlay: str | None = None
    fits_a_phone: bool = True
    jobs: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return self.read and not self.jobs

    def as_dict(self) -> dict[str, Any]:
        return {
            "url": self.url,
            "campaigns": self.campaigns,
            "read": self.read,
            "trouble": self.trouble,
            "final_url": self.final_url,
            "title": self.title,
            "headline": self.headline,
            "phone_in_view": self.phone_in_view,
            "has_form": self.has_form,
            "call_to_action": self.call_to_action,
            "conversion_tag": self.conversion_tag,
            "tag_fired": self.tag_fired,
            "overlay": self.overlay,
            "fits_a_phone": self.fits_a_phone,
            "jobs": self.jobs,
            "ok": self.ok,
        }


def judge(page: Rendering, url: str, campaigns: list[str]) -> PageCheck:
    """What one rendered page is missing, as sentences a person can act on."""
    check = PageCheck(url=url, campaigns=campaigns, read=True)
    check.final_url = page.final_url or url
    check.title = page.title
    check.headline = page.headline
    check.phone_in_view = page.phone_above_fold
    check.overlay = page.overlay
    check.fits_a_phone = page.viewport_meta and not page.overflow_x

    html = page.html or ""
    # Something to do when you arrive: a form, a tappable number, or a button
    # that is plainly the next step. A tool whose whole job is an upload button
    # has no `<form>` in it and is not broken, so the call to action counts.
    check.has_form = "<form" in html.lower()
    check.call_to_action = [c for c in page.ctas_above_fold if c][:3]
    tags = classify_tags(
        requests=page.requests,
        scripts=page.scripts,
        data_layer=page.data_layer,
        html=html,
    )
    check.conversion_tag = bool(tags.ads_ids)
    check.tag_fired = tags.ads_fired

    if not check.conversion_tag:
        check.jobs.append(
            "Nothing on this page tells Google when somebody calls or sends a form, "
            "so every lead it brings is invisible in your advertising."
        )
    elif not check.tag_fired:
        check.jobs.append(
            "The Google Ads tag is on this page but sent nothing when the page opened. "
            "It is usually a consent banner holding it back, or an id that no longer exists."
        )
    if not check.has_form and not page.tel_links and not check.call_to_action:
        check.jobs.append(
            "There is no form, no tappable phone number and no clear button on this "
            "page, so somebody who arrives ready to buy has nothing to do."
        )
    elif page.tel_links and not check.phone_in_view:
        # Only when there is a number to hide. "Your phone number is not visible"
        # on a page that has no phone number is the kind of finding that teaches
        # somebody the whole report is guessing.
        check.jobs.append(
            "The phone number is not visible until you scroll. On a phone that is the "
            "difference between a call and a closed tab."
        )
    if page.overlay:
        check.jobs.append(
            f"A pop-up covers this page when it opens: “{page.overlay[:80]}”. "
            "People who clicked an ad meet it before they read anything."
        )
    if not check.fits_a_phone:
        check.jobs.append(
            "This page does not fit a phone screen without scrolling sideways, and most "
            "of the clicks you pay for are on phones."
        )
    if not page.has_h1:
        check.jobs.append(
            "This page has no main heading, so nothing on it tells a visitor in one "
            "line that they are in the right place."
        )
    return check


def check_pages(
    pages: dict[str, list[str]],
    settings: Settings,
    *,
    most: int = MOST,
    render_page: Callable[..., Rendering] | None = None,
) -> list[PageCheck]:
    """Open each landing page and judge it. A page that will not open says so."""
    draw = render_page or render
    out: list[PageCheck] = []
    for url in list(pages)[:most]:
        campaigns = pages[url]
        try:
            page = draw(url, timeout_seconds=settings.audit_render_timeout_seconds, laptop=False)
        except Exception as exc:  # noqa: BLE001 - one bad page must not stop the rest
            log.warning("could not open the landing page %s: %s", url, exc)
            out.append(
                PageCheck(
                    url=url,
                    campaigns=campaigns,
                    read=False,
                    trouble="This page could not be opened at all.",
                    jobs=[WOULD_NOT_OPEN],
                )
            )
            continue
        out.append(judge(page, url, campaigns))
    return out
