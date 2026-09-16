"""One site, loaded in a real browser the way a phone and a laptop would load it.

The static crawl reads HTML. This loads the home page in headless Chromium, at
phone size and at laptop size, and records what the page did: every request it
made (which is how we know a tag fired), what failed, console errors, the
``dataLayer``, the phone links, whether it overflows sideways, whether a pop-up
covers the page on arrival, and what sits above the fold. It takes a screenshot
of each. It never clicks, types or submits.

Safety: the URL is judged by the crawler's SSRF rules before the browser starts,
and every request the page makes is checked again by host, so a page cannot use
the browser to reach an address the crawler would have refused.
"""

from __future__ import annotations

import ipaddress
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import urlsplit

from ppcway.crawler.ssrf import BlockedAddress, assert_safe_address

PHONE = {"width": 390, "height": 844}
LAPTOP = {"width": 1440, "height": 900}
PHONE_UA = (
    "Mozilla/5.0 (Linux; Android 13; Pixel 7) AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0 Mobile Safari/537.36 PPCWay/0.1 (+https://ppcway.example/crawler)"
)
LAPTOP_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0 Safari/537.36 PPCWay/0.1 (+https://ppcway.example/crawler)"
)

PROBE = r"""() => {
  const vh = window.innerHeight, vw = window.innerWidth;
  const inFold = el => { const r = el.getBoundingClientRect(); return r.bottom > 0 && r.top < vh && r.width > 0 && r.height > 0; };
  const text = el => (el.innerText || el.textContent || '').trim().replace(/\s+/g, ' ');
  const tel = [...document.querySelectorAll('a[href^="tel:"]')].map(a => a.getAttribute('href'));
  const phoneRe = /(\+?1[\s.-]?)?\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4}/;
  const leaves = [...document.querySelectorAll('body *')].filter(el => el.children.length === 0 && inFold(el));
  const foldText = leaves.map(el => text(el)).join(' ');
  const ctaRe = /\b(call|quote|book|estimate|schedule|contact|get started|request|appointment|free)\b/i;
  const ctas = [...document.querySelectorAll('a, button')].filter(el => inFold(el) && ctaRe.test(text(el)) && text(el).length < 60).map(el => text(el));
  const h1 = document.querySelector('h1');
  // A pop-up on arrival: a fixed or sticky element covering a large share of the screen.
  let overlay = null;
  for (const el of document.querySelectorAll('body *')) {
    const cs = getComputedStyle(el);
    if ((cs.position === 'fixed' || cs.position === 'sticky') && cs.visibility !== 'hidden' && cs.display !== 'none' && parseFloat(cs.opacity || '1') > 0.2) {
      const r = el.getBoundingClientRect();
      const share = (Math.min(r.right, vw) - Math.max(r.left, 0)) * (Math.min(r.bottom, vh) - Math.max(r.top, 0)) / (vw * vh);
      if (share > 0.35) { overlay = text(el).slice(0, 120) || el.tagName.toLowerCase(); break; }
    }
  }
  const html = document.documentElement.outerHTML;
  const yearMatch = html.match(/(?:©|&copy;|copyright)\s*(?:\d{4}\s*[-–]\s*)?(20\d{2})/i);
  return {
    tel,
    phoneAboveFold: [...document.querySelectorAll('a[href^="tel:"]')].some(inFold) || phoneRe.test(foldText),
    ctasAboveFold: [...new Set(ctas)].slice(0, 5),
    headline: h1 ? text(h1).slice(0, 160) : '',
    hasH1: !!h1,
    overlay,
    overflowX: document.documentElement.scrollWidth > document.documentElement.clientWidth + 1,
    viewportMeta: !!document.querySelector('meta[name="viewport"]'),
    lang: document.documentElement.getAttribute('lang') || '',
    title: document.title,
    metaDescription: (document.querySelector('meta[name="description"]') || {}).content || '',
    mapsEmbed: !!document.querySelector('iframe[src*="google.com/maps"], iframe[src*="maps.google"]'),
    copyrightYear: yearMatch ? parseInt(yearMatch[1], 10) : null,
    scripts: [...document.scripts].map(s => s.src || s.textContent.slice(0, 4000)),
    dataLayer: (() => { try { return JSON.parse(JSON.stringify(window.dataLayer || [])); } catch (e) { return []; } })(),
  };
}"""


@dataclass
class Rendering:
    url: str
    final_url: str
    title: str
    html: str
    meta_description: str = ""
    lang: str = ""
    requests: list[str] = field(default_factory=list)
    #: (url, status) for responses that failed, 400 and up.
    failed: list[tuple[str, int]] = field(default_factory=list)
    #: Requests the browser could not complete at all (DNS, refused, aborted by us).
    errored: list[str] = field(default_factory=list)
    console_errors: list[str] = field(default_factory=list)
    mixed_content: list[str] = field(default_factory=list)
    scripts: list[str] = field(default_factory=list)
    data_layer: list[Any] = field(default_factory=list)
    tel_links: list[str] = field(default_factory=list)
    phone_above_fold: bool = False
    ctas_above_fold: list[str] = field(default_factory=list)
    headline: str = ""
    has_h1: bool = False
    #: Text of a pop-up covering the page on arrival, or None.
    overlay: str | None = None
    overflow_x: bool = False
    viewport_meta: bool = False
    maps_embed: bool = False
    copyright_year: int | None = None
    screenshot_phone: bytes | None = None
    screenshot_laptop: bytes | None = None
    blocked: list[str] = field(default_factory=list)


def _host_is_safe(url: str) -> bool:
    parts = urlsplit(url)
    if parts.scheme not in ("http", "https"):
        return False
    host = parts.hostname or ""
    try:
        ipaddress.ip_address(host)
    except ValueError:
        return bool(host) and host != "localhost" and not host.endswith(".local")
    try:
        assert_safe_address(host, url=url)
    except BlockedAddress:
        return False
    return True


def render(url: str, *, timeout_seconds: float = 45, laptop: bool = True) -> Rendering:
    from playwright.sync_api import sync_playwright

    result = Rendering(url=url, final_url=url, title="", html="")
    with sync_playwright() as p:
        browser = p.chromium.launch(args=["--disable-dev-shm-usage"])
        try:
            _load(browser, result, PHONE, PHONE_UA, mobile=True, timeout=timeout_seconds, probe=True)
            if laptop:
                shot = _load(browser, Rendering(url=url, final_url=url, title="", html=""), LAPTOP, LAPTOP_UA, mobile=False, timeout=timeout_seconds, probe=False)
                result.screenshot_laptop = shot.screenshot_phone
        finally:
            browser.close()
    return result


def _load(browser, result: Rendering, viewport: dict[str, int], ua: str, *, mobile: bool, timeout: float, probe: bool) -> Rendering:  # type: ignore[no-untyped-def]
    context = browser.new_context(
        viewport=viewport, user_agent=ua, is_mobile=mobile, has_touch=mobile,
        device_scale_factor=2 if mobile else 1, locale="en-CA",
    )
    page = context.new_page()
    page_is_https = urlsplit(result.url).scheme == "https"

    def gate(route, request):  # type: ignore[no-untyped-def]
        if _host_is_safe(request.url):
            route.continue_()
        else:
            result.blocked.append(urlsplit(request.url).hostname or request.url)
            route.abort()

    page.route("**/*", gate)
    page.on("request", lambda r: result.requests.append(r.url))
    page.on("response", lambda r: result.failed.append((r.url, r.status)) if r.status >= 400 else None)
    page.on("requestfailed", lambda r: result.errored.append(r.url))
    page.on("console", lambda m: result.console_errors.append(m.text[:300]) if m.type == "error" else None)
    page.on("pageerror", lambda e: result.console_errors.append(str(e)[:300]))
    try:
        page.goto(result.url, wait_until="networkidle", timeout=timeout * 1000)
    except Exception:  # noqa: BLE001 - networkidle can time out on chatty pages; take what loaded
        page.wait_for_timeout(500)
    page.wait_for_timeout(1500)
    result.final_url = page.url
    result.title = page.title()
    result.html = page.content()
    if page_is_https:
        result.mixed_content = [r for r in result.requests if r.startswith("http://")]
    try:
        result.screenshot_phone = page.screenshot(type="jpeg", quality=70, full_page=False)
    except Exception:  # noqa: BLE001
        result.screenshot_phone = None
    if probe:
        data = page.evaluate(PROBE)
        result.tel_links = list(data.get("tel") or [])
        result.phone_above_fold = bool(data.get("phoneAboveFold"))
        result.ctas_above_fold = list(data.get("ctasAboveFold") or [])
        result.headline = str(data.get("headline") or "")
        result.has_h1 = bool(data.get("hasH1"))
        result.overlay = data.get("overlay") or None
        result.overflow_x = bool(data.get("overflowX"))
        result.viewport_meta = bool(data.get("viewportMeta"))
        result.lang = str(data.get("lang") or "")
        result.meta_description = str(data.get("metaDescription") or "")
        result.maps_embed = bool(data.get("mapsEmbed"))
        result.copyright_year = data.get("copyrightYear")
        result.scripts = list(data.get("scripts") or [])
        result.data_layer = list(data.get("dataLayer") or [])
    context.close()
    return result
