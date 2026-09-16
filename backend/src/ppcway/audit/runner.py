"""Run the eight checks on one site and write the report in plain words.

Stages: judge the URL, crawl, render the home page, measure speed, then derive
each finding. A stage that fails leaves a note and the findings that depend on
it say "unknown" with the reason, so a partial audit still reports.
"""

from __future__ import annotations

import logging
import re
from datetime import UTC, datetime
from urllib.parse import urlsplit

from ppcway.audit import conversion, forms, health, local, policy, tags, trust
from ppcway.audit.health import HealthSignals
from ppcway.audit.pagespeed import SpeedSignals, fetch_pagespeed
from ppcway.audit.render import Rendering, render
from ppcway.audit.types import MORE_KEYS, AuditReport, Finding
from ppcway.config import Settings
from ppcway.crawler.fetch import CrawlResult, build_client, crawl
from ppcway.crawler.ssrf import BlockedAddress, assert_safe_url

log = logging.getLogger(__name__)


def normalise_site(site: str) -> str:
    s = site.strip()
    if not s.startswith(("http://", "https://")):
        s = "https://" + s
    parts = urlsplit(s)
    return f"{parts.scheme}://{parts.netloc}{parts.path or '/'}"


def _seconds(ms: int | None) -> str:
    return f"{ms / 1000:.1f} seconds" if ms is not None else "unknown"


def run_audit(site: str, settings: Settings) -> AuditReport:
    url = normalise_site(site)
    report = AuditReport(site=url, started_at=datetime.now(UTC))

    try:
        assert_safe_url(url)
    except BlockedAddress as exc:
        report.notes.append(f"refused: {exc}")
        report.findings = [
            Finding(k, t, "unknown", "We could not reach this address safely.", group="more" if k in MORE_KEYS else "checks")
            for k, t in _TITLES.items()
        ]
        report.finished_at = datetime.now(UTC)
        return report

    crawled: CrawlResult | None = None
    try:
        with build_client(timeout_seconds=15) as client:
            crawled = crawl(
                url,
                max_pages=settings.audit_crawl_max_pages,
                timeout_seconds=settings.audit_crawl_timeout_seconds,
                rps_per_host=1.0,
                client=client,
            )
        report.pages_read = len(crawled.pages)
        report.business_name = crawled.business_name
        report.phone = crawled.phone
    except Exception as exc:  # noqa: BLE001 - a stage failure is a note, not a crash
        log.warning("crawl failed for %s: %s", url, exc)
        report.notes.append(f"crawl failed: {type(exc).__name__}")

    rendered: Rendering | None = None
    try:
        rendered = render(url, timeout_seconds=settings.audit_render_timeout_seconds)
    except Exception as exc:  # noqa: BLE001
        log.warning("render failed for %s: %s", url, exc)
        report.notes.append(f"render failed: {type(exc).__name__}")

    # The contact page is where the form lives; load it too when the crawl found one.
    contact: Rendering | None = None
    contact_url = _contact_link(crawled) if crawled else None
    if contact_url and contact_url != url:
        try:
            contact = render(contact_url, timeout_seconds=settings.audit_render_timeout_seconds)
        except Exception as exc:  # noqa: BLE001
            report.notes.append(f"contact page render failed: {type(exc).__name__}")

    if rendered:
        report.screenshots = {k: v for k, v in (("phone", rendered.screenshot_phone), ("laptop", rendered.screenshot_laptop)) if v}
        report.headline = rendered.headline

    site_health: HealthSignals | None = None
    try:
        internal = [l for p in (crawled.pages if crawled else ()) for l in p.extract.links]
        site_health = health.check_health(url, internal)
    except Exception as exc:  # noqa: BLE001
        log.warning("health check failed for %s: %s", url, exc)
        report.notes.append(f"health check failed: {type(exc).__name__}")

    speed: SpeedSignals | None = None
    if settings.pagespeed_api_key:
        try:
            speed = fetch_pagespeed(url, api_key=settings.pagespeed_api_key.get_secret_value())
        except Exception as exc:  # noqa: BLE001
            log.warning("pagespeed failed for %s: %s", url, exc)
            report.notes.append(f"pagespeed failed: {type(exc).__name__}")
    else:
        report.notes.append("pagespeed skipped: no PAGESPEED_API_KEY")

    report.findings = build_findings(crawled, rendered, speed, contact, site_health)
    report.finished_at = datetime.now(UTC)
    return report


_TITLES = {
    "firstscreen": "What people see first",
    "health": "Site health",
    "local": "Local presence",
    "counting": "Counting calls and forms",
    "speed": "Speed on a phone",
    "mobile": "Works on a phone",
    "match": "Page matches the ad",
    "form": "Contact form",
    "tags": "Google's tags",
    "trust": "Trust signals",
    "policy": "Words Google may object to",
}


CONTACT_PATH = re.compile(r"/(contact|contact-us|get-a-quote|quote|book|estimate)\b", re.IGNORECASE)


def _contact_link(crawled: CrawlResult) -> str | None:
    for page in crawled.pages:
        if CONTACT_PATH.search(urlsplit(page.url).path):
            return page.url
    for page in crawled.pages:
        for link in page.extract.links:
            if CONTACT_PATH.search(urlsplit(link).path):
                return link
    return None


def build_findings(
    crawled: CrawlResult | None,
    rendered: Rendering | None,
    speed: SpeedSignals | None,
    contact: Rendering | None = None,
    site_health: HealthSignals | None = None,
) -> list[Finding]:
    """Pure: turn the stage results into the eight findings and the three under the hood."""
    html_pages: list[tuple[str, str]] = []
    if rendered:
        html_pages.append((rendered.final_url, rendered.html))
    if contact:
        html_pages.append((contact.final_url, contact.html))
    page_text = crawled.page_text if crawled else ""
    links = [l for p in (crawled.pages if crawled else ()) for l in p.extract.links]
    tag = (
        tags.classify_tags(
            requests=rendered.requests, scripts=rendered.scripts, data_layer=rendered.data_layer, html=rendered.html
        )
        if rendered
        else None
    )
    form = forms.detect_forms(html_pages, links) if html_pages else None
    tr = trust.detect_trust(html_pages, address=crawled.address if crawled else "", page_text=page_text, links=links) if (rendered or crawled) else None
    hits = policy.scan_policy(page_text) if crawled else []

    out: list[Finding] = []

    # 1. Counting calls and forms
    if tag is None:
        out.append(Finding("counting", _TITLES["counting"], "unknown", "We could not load the page in a browser to see what it counts."))
    else:
        detail = []
        if tag.call_tracking:
            detail.append(f"{tag.call_tracking} call tracking is installed, so calls can be counted.")
        if tag.ads_ids:
            detail.append(f"A Google Ads tag is present ({', '.join(tag.ads_ids)}){' and fired on load' if tag.ads_fired else ', but nothing fired on load'}.")
        tel = bool(rendered and rendered.tel_links)
        if tel:
            detail.append("The phone number is a tap-to-call link.")
        if tag.call_tracking or (tag.ads_ids and tag.ads_fired):
            out.append(Finding("counting", _TITLES["counting"], "good", "Calls can be counted.", tuple(detail), evidence={"call_tracking": tag.call_tracking, "ads_ids": tag.ads_ids, "ads_fired": tag.ads_fired}))
        else:
            out.append(Finding(
                "counting", _TITLES["counting"], "needs_you",
                "There is no way to count a call yet.",
                tuple(detail) or ("No call tracking and no Google Ads tag was seen on the home page.",),
                fix="We set this up with you in the Count your calls step: a Google forwarding number or call tracking on the site. Nothing to do before then.",
                evidence={"call_tracking": tag.call_tracking, "ads_ids": tag.ads_ids, "tel_links": rendered.tel_links if rendered else []},
            ))

    # 2. Speed on a phone
    if speed is None:
        out.append(Finding("speed", _TITLES["speed"], "unknown", "Google's speed test did not run."))
    else:
        lcp = speed.field_lcp_ms if speed.field_available and speed.field_lcp_ms else speed.lcp_ms
        basis = "measured on real visitors" if speed.field_available else "on a simulated mid-range phone on 4G"
        detail = (f"The main content shows after {_seconds(lcp)}, {basis}. Google wants under 2.5 seconds.",)
        if speed.total_bytes:
            weight = f"{speed.total_bytes / 1_000_000:.1f} MB" if speed.total_bytes >= 1_000_000 else f"{speed.total_bytes // 1000} KB"
            detail += (f"The page weighs {weight}.",)
        verdict = speed.lcp_verdict
        status = "good" if verdict == "good" else ("needs_you" if verdict in ("slow", "poor") else "unknown")
        summary = {"good": f"Fast enough: {_seconds(lcp)} on a phone.", "slow": f"A little slow: {_seconds(lcp)} on a phone.", "poor": f"Slow: {_seconds(lcp)} on a phone.", "unknown": "No speed number came back."}[verdict]
        fix = None if status == "good" else "Ask whoever looks after the site to compress the largest image on the home page and remove scripts that load before the content. That usually gets under 2.5 seconds."
        out.append(Finding("speed", _TITLES["speed"], status, summary, detail, fix, evidence={"lcp_ms": lcp, "performance_score": speed.performance_score, "field": speed.field_available, "total_bytes": speed.total_bytes, "lighthouse": speed.lighthouse_version}))

    # 3. Works on a phone
    if rendered is None and speed is None:
        out.append(Finding("mobile", _TITLES["mobile"], "unknown", "We could not look at the page on a phone."))
    else:
        problems = []
        if rendered and rendered.overflow_x:
            problems.append("The page is wider than a phone screen, so it scrolls sideways.")
        if rendered and not rendered.viewport_meta:
            problems.append("The page does not tell phones how to scale it (no viewport tag).")
        if speed and speed.tap_targets_ok is False:
            problems.append("Some buttons and links are too small or too close together to tap.")
        if speed and speed.font_size_ok is False:
            problems.append("Some text is too small to read on a phone.")
        if rendered and not rendered.tel_links:
            problems.append("The phone number is not a tap-to-call link.")
        elif rendered and not rendered.phone_above_fold:
            problems.append("The phone number is not visible until you scroll.")
        status = "good" if not problems else "needs_you"
        out.append(Finding("mobile", _TITLES["mobile"], status, "Reads and taps well on a phone." if status == "good" else problems[0], tuple(problems), None if status == "good" else "Each of these is a small change for whoever built the site. Tap-to-call first: it is the one that turns a visit into a call.", evidence={"overflow_x": rendered.overflow_x if rendered else None, "viewport_meta": rendered.viewport_meta if rendered else None, "tel_links": rendered.tel_links if rendered else [], "phone_above_fold": rendered.phone_above_fold if rendered else None}))

    # 4. Page matches the ad
    if crawled is None or not crawled.services:
        out.append(Finding("match", _TITLES["match"], "ours", "We could not read the list of services; we will confirm them with you before writing ads.", evidence={"services": []}))
    else:
        titles = [(p.url, (p.extract.meta_title + " " + p.extract.business_name).lower()) for p in crawled.pages]
        covered, missing = [], []
        for s in crawled.services[:8]:
            hit = next((u for u, t in titles if s.lower() in t), None)
            (covered if hit else missing).append(s)
        if missing and covered:
            summary = f"{len(covered)} of {len(covered) + len(missing)} services have their own page."
        elif missing:
            summary = "Every service is on the home page; none has a page of its own."
        else:
            summary = "Each service has its own page, so each ad can land on the right one."
        detail = tuple(f"Has a page: {s}" for s in covered) + tuple(f"No page of its own: {s}" for s in missing)
        out.append(Finding("match", _TITLES["match"], "ours" if missing else "good", summary, detail, None if not missing else "Nothing to do now. We send each ad to the closest page and tell you which services would earn a page of their own.", evidence={"services": list(crawled.services), "covered": covered, "missing": missing}))

    # 5. Contact form
    if form is None:
        out.append(Finding("form", _TITLES["form"], "unknown", "We could not load the page in a browser to look for a form."))
    elif not form.contact_form:
        out.append(Finding("form", _TITLES["form"], "ours", "No contact form was found.", ("Calls will carry the campaign, and we can add a short form later if you want one.",), evidence={"forms_found": form.forms_found, "pages_looked_at": [u for u, _ in html_pages]}))
    elif form.thank_you_url:
        out.append(Finding("form", _TITLES["form"], "good", "A contact form with a thank-you page, so a send can be counted.", (f"Form built with {form.provider}." if form.provider else "Form found.", f"Thank-you page: {form.thank_you_url}"), evidence={"provider": form.provider, "thank_you_url": form.thank_you_url, "on_page": form.on_page}))
    else:
        out.append(Finding("form", _TITLES["form"], "needs_you", "The form works, but there is no thank-you page, so a send cannot be counted.", (f"Form built with {form.provider}." if form.provider else "Form found.", "We looked for a page like /thank-you and found none linked."), fix="One question for you: after someone sends the form, does the page change? If it shows a thank-you page, tell us its address. If not, whoever built the site can add one in a few minutes.", evidence={"provider": form.provider, "on_page": form.on_page}))

    # 6. Google's tags
    if tag is None:
        out.append(Finding("tags", _TITLES["tags"], "unknown", "We could not load the page in a browser to see the tags."))
    else:
        detail = []
        if tag.gtm_ids:
            detail.append(f"Tag Manager: {', '.join(tag.gtm_ids)}{' (loaded)' if tag.gtm_loaded else ''}.")
        if tag.ga4_ids:
            detail.append(f"Analytics: {', '.join(tag.ga4_ids)}{' (sent a hit)' if tag.ga4_fired else ' (present, no hit seen)'}.")
        if tag.ads_ids:
            detail.append(f"Ads: {', '.join(tag.ads_ids)}{' (fired)' if tag.ads_fired else ' (present, nothing fired)'}.")
        if tag.consent_ad_storage:
            detail.append(f"Consent Mode defaults ad storage to {tag.consent_ad_storage}.")
        if tag.other_analytics:
            detail.append("Also present: " + ", ".join(tag.other_analytics) + ".")
        present = bool(tag.gtm_ids or tag.ga4_ids or tag.ads_ids)
        if tag.gtm_ids and tag.ads_ids:
            out.append(Finding("tags", _TITLES["tags"], "good", "Tag Manager, Analytics and Ads are set up.", tuple(detail), evidence=tag.__dict__))
        elif present:
            out.append(Finding("tags", _TITLES["tags"], "ours", "Some of Google's tags are there; we add what is missing.", tuple(detail), evidence=tag.__dict__))
        else:
            out.append(Finding("tags", _TITLES["tags"], "ours", "None of Google's tags are on the site yet. We add them in the Count your calls step.", tuple(detail) or ("No Tag Manager, Analytics or Ads tag was seen.",), evidence=tag.__dict__))

    # 7. Trust signals
    if tr is None:
        out.append(Finding("trust", _TITLES["trust"], "unknown", "We could not read the site."))
    else:
        have, lack = [], []
        (have if tr.address else lack).append("address")
        (have if tr.hours else lack).append("hours")
        (have if tr.licence else lack).append("licence number")
        (have if tr.reviews else lack).append("reviews")
        (have if tr.privacy_policy else lack).append("privacy policy")
        detail = []
        if tr.address:
            detail.append(f"Address: {tr.address}")
        if tr.licence:
            detail.append(f"Licence: {tr.licence}")
        if tr.reviews:
            detail.append(f"Reviews: {tr.reviews}")
        if tr.insured:
            detail.append("Says licensed, insured or bonded.")
        detail += [f"Not found: {x}" for x in lack]
        status = "good" if not lack else "needs_you"
        summary = "Licence, reviews, address and hours are where people look for them." if status == "good" else f"Missing: {', '.join(lack)}."
        fix = None if status == "good" else "Put these in the footer of every page. Google requires a privacy policy for lead forms, and a licence number and reviews are what make a stranger call."
        out.append(Finding("trust", _TITLES["trust"], status, summary, tuple(detail), fix, evidence=tr.__dict__))

    # 8. Words Google may object to
    if crawled is None:
        out.append(Finding("policy", _TITLES["policy"], "unknown", "We could not read the site."))
    elif not hits:
        out.append(Finding("policy", _TITLES["policy"], "good", "Nothing on the site that Google would refuse in an ad.", evidence={"hits": []}))
    else:
        first = hits[0]
        out.append(Finding("policy", _TITLES["policy"], "ours", f"“{first.phrase}” found. We keep it out of your ads.", tuple(f"“{h.phrase}” ({h.family}): {h.context}" for h in hits[:6]), evidence={"hits": [h.__dict__ for h in hits]}))

    out.extend(build_more(crawled, rendered, speed, form, site_health))
    return out


def _kb(n: int | None) -> str:
    if n is None:
        return "unknown"
    return f"{n / 1_000_000:.1f} MB" if n >= 1_000_000 else f"{n // 1000} KB"


def build_more(
    crawled: CrawlResult | None,
    rendered: Rendering | None,
    speed: SpeedSignals | None,
    form: forms.FormSignals | None,
    site_health: HealthSignals | None,
) -> list[Finding]:
    out: list[Finding] = []

    # What people see first
    if rendered is None:
        out.append(Finding("firstscreen", _TITLES["firstscreen"], "unknown", "We could not load the page in a browser.", group="more"))
    else:
        conv = conversion.detect_conversion(
            html=rendered.html, scripts=rendered.scripts, requests=rendered.requests, headline=rendered.headline,
            has_h1=rendered.has_h1, ctas=rendered.ctas_above_fold, phone_above_fold=rendered.phone_above_fold,
            tel_links=rendered.tel_links, overlay=rendered.overlay, copyright_year=rendered.copyright_year,
            form_fields=form.fields if form else None,
        )
        detail = []
        detail.append(f"Headline: \u201c{conv.headline}\u201d" if conv.headline else "No headline in the first screen.")
        detail.append("Buttons in the first screen: " + ", ".join(conv.ctas_above_fold) + "." if conv.ctas_above_fold else "No call, quote or book button in the first screen.")
        detail.append("The phone number shows before scrolling." if conv.phone_above_fold else "The phone number is below the fold.")
        if conv.chat_tool:
            detail.append(f"Live chat: {conv.chat_tool}.")
        if conv.booking_tool:
            detail.append(f"Online booking: {conv.booking_tool}.")
        if conv.form_fields:
            detail.append(f"The contact form asks {conv.form_fields} questions.")
        detail += conv.problems
        status = "good" if not conv.problems else "needs_you"
        summary = "A visitor can call or ask for a quote without scrolling." if status == "good" else conv.problems[0]
        fix = None if status == "good" else "The first screen on a phone should carry the trade, the town, and one button that calls you. Everything else can come after."
        out.append(Finding("firstscreen", _TITLES["firstscreen"], status, summary, tuple(detail), fix, evidence=conv.__dict__, group="more"))

    # Site health
    if site_health is None and speed is None and rendered is None:
        out.append(Finding("health", _TITLES["health"], "unknown", "We could not check the site's plumbing.", group="more"))
    else:
        problems, notes = [], []
        if site_health:
            if not site_health.https:
                problems.append("The site is not on https. Google marks it 'not secure' and ads to it get refused.")
            elif site_health.cert_days_left is not None:
                if site_health.cert_days_left < 14:
                    problems.append(f"The security certificate expires in {site_health.cert_days_left} days.")
                else:
                    notes.append(f"Secure connection, certificate good for {site_health.cert_days_left} days" + (f" ({site_health.cert_issuer})." if site_health.cert_issuer else "."))
            if site_health.http_redirects is False:
                problems.append("Typing the address without https does not redirect to the secure site.")
            if site_health.www_redirects is False:
                problems.append("The site answers at both the www and the bare address without redirecting, so Google sees two copies.")
            if site_health.broken_links:
                problems.append(f"{len(site_health.broken_links)} of {site_health.links_checked} links checked are broken: " + ", ".join(u for u, _ in site_health.broken_links[:3]) + ".")
            elif site_health.links_checked:
                notes.append(f"{site_health.links_checked} internal links checked, none broken.")
        if rendered:
            failed = [(u, st) for u, st in rendered.failed if st >= 400][:5]
            if failed:
                problems.append(f"{len(rendered.failed)} files failed to load on the home page (for example {urlsplit(failed[0][0]).path or failed[0][0]}, {failed[0][1]}).")
            if rendered.mixed_content:
                problems.append(f"{len(rendered.mixed_content)} files load over plain http on a secure page (mixed content).")
            if len(rendered.console_errors) >= 3:
                problems.append(f"{len(rendered.console_errors)} script errors on the home page.")
            if rendered.title and rendered.meta_description == "":
                notes.append("No meta description; Google writes its own snippet.")
        if speed:
            scores = [f"{n} {v}" for n, v in (("performance", speed.performance_score), ("mobile and search basics", speed.seo_score), ("accessibility", speed.accessibility_score), ("best practices", speed.best_practices_score)) if v is not None]
            if scores:
                notes.append("Google's scores out of 100: " + ", ".join(scores) + ".")
            if speed.largest_image_bytes and speed.largest_image_bytes > 500_000:
                problems.append(f"The largest image on the page is {_kb(speed.largest_image_bytes)}; it should be under 200 KB.")
            if speed.image_alt_ok is False:
                notes.append("Some images have no description (alt text).")
            if speed.contrast_ok is False:
                notes.append("Some text is hard to read against its background.")
        status = "good" if not problems else "needs_you"
        summary = "The site's plumbing is sound." if status == "good" else problems[0]
        fix = None if status == "good" else "Send this list to whoever looks after the site. Each item is under an hour of work, and the https ones come first."
        out.append(Finding("health", _TITLES["health"], status, summary, tuple(problems + notes), fix, evidence={"health": site_health.__dict__ if site_health else None, "failed": rendered.failed[:20] if rendered else [], "console_errors": rendered.console_errors[:10] if rendered else []}, group="more"))

    # Local presence
    if crawled is None and rendered is None:
        out.append(Finding("local", _TITLES["local"], "unknown", "We could not read the site.", group="more"))
    else:
        texts = [p.extract.page_text for p in crawled.pages] if crawled else []
        loc = local.detect_local(texts, address=crawled.address if crawled else "", maps_embed=rendered.maps_embed if rendered else False, tel_links=rendered.tel_links if rendered else [])
        problems, notes = [], []
        if not loc.main_number:
            problems.append("No phone number was found on the site.")
        else:
            where = f", a {loc.region} number" if loc.region else ""
            notes.append(f"Main number {loc.main_number}{where}.")
            if loc.toll_free:
                notes.append("It is toll-free. A local number gets more calls from local searches; Google Ads also refuses some vanity numbers.")
            if loc.premium:
                problems.append("The number is a premium-rate line, which Google Ads does not allow.")
            if loc.inconsistent:
                problems.append("Several different phone numbers appear across the pages: " + ", ".join(loc.numbers[:4]) + ".")
        if loc.address:
            notes.append(f"Address: {loc.address}.")
        else:
            problems.append("No address on the site. Google Ads and Google Business Profile both want one, even for a service-area business.")
        notes.append("A Google map is embedded." if loc.maps_embed else "No map on the site.")
        if loc.service_area:
            notes.append(f"Service area: \u201c{loc.service_area}\u201d")
        else:
            problems.append("The site does not say which towns you serve. Ads run by location, and the page should say the same places.")
        status = "good" if not problems else "needs_you"
        summary = "Number, address and service area are all where Google looks." if status == "good" else problems[0]
        fix = None if status == "good" else "One line in the footer fixes most of this: the number, the address, and \u201cserving\u201d followed by the towns you want calls from."
        out.append(Finding("local", _TITLES["local"], status, summary, tuple(problems + notes), fix, evidence=loc.__dict__, group="more"))

    return out
