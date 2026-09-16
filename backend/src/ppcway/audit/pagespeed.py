"""Speed on a phone, from Google's own measurement.

One call to the PageSpeed Insights API per page, mobile strategy: Lighthouse runs
on a simulated mid-range phone on 4G. Real-user numbers (CrUX) come back only for
sites with traffic, which most small businesses do not have, so the report says
"simulated" unless ``field_available`` is true.

Quota is 25,000 calls a day and 400 per 100 seconds per key, no paid tier. An
audit uses one or two.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import httpx

ENDPOINT = "https://www.googleapis.com/pagespeedonline/v5/runPagespeed"

#: Google's own thresholds: LCP under 2.5 s is good, over 4 s is poor.
LCP_GOOD_MS = 2500
LCP_POOR_MS = 4000


@dataclass(frozen=True)
class SpeedSignals:
    strategy: str
    performance_score: int | None
    lcp_ms: int | None
    cls: float | None
    tbt_ms: int | None
    speed_index_ms: int | None
    total_bytes: int | None
    render_blocking_ms: int | None
    field_available: bool
    field_lcp_ms: int | None
    #: Lighthouse mobile usability audits: True passed, False failed, None not run.
    viewport_ok: bool | None
    tap_targets_ok: bool | None
    font_size_ok: bool | None
    lighthouse_version: str
    #: The other three Lighthouse categories, 0 to 100, from the same call.
    seo_score: int | None = None
    accessibility_score: int | None = None
    best_practices_score: int | None = None
    #: Health audits: True passed, False failed, None not run.
    document_title_ok: bool | None = None
    meta_description_ok: bool | None = None
    image_alt_ok: bool | None = None
    contrast_ok: bool | None = None
    console_errors_ok: bool | None = None
    https_ok: bool | None = None
    #: The largest image on the page, bytes, when Lighthouse flagged one.
    largest_image_bytes: int | None = None

    @property
    def lcp_verdict(self) -> str:
        lcp = self.field_lcp_ms if self.field_available and self.field_lcp_ms else self.lcp_ms
        if lcp is None:
            return "unknown"
        if lcp <= LCP_GOOD_MS:
            return "good"
        if lcp <= LCP_POOR_MS:
            return "slow"
        return "poor"


def _num(audits: dict[str, Any], key: str) -> float | None:
    a = audits.get(key) or {}
    v = a.get("numericValue")
    return float(v) if isinstance(v, (int, float)) else None


def _passed(audits: dict[str, Any], key: str) -> bool | None:
    a = audits.get(key)
    if not a or a.get("score") is None:
        return None
    return float(a["score"]) >= 0.9


def parse_pagespeed(payload: dict[str, Any], strategy: str = "mobile") -> SpeedSignals:
    """Turn the API's reply into the handful of numbers the report uses."""
    lh = payload.get("lighthouseResult") or {}
    audits = lh.get("audits") or {}
    score = (lh.get("categories") or {}).get("performance", {}).get("score")
    field = payload.get("loadingExperience") or {}
    metrics = field.get("metrics") or {}
    field_lcp = metrics.get("LARGEST_CONTENTFUL_PAINT_MS", {}).get("percentile")
    lcp = _num(audits, "largest-contentful-paint")
    tbt = _num(audits, "total-blocking-time")
    si = _num(audits, "speed-index")
    weight = _num(audits, "total-byte-weight")
    blocking = _num(audits, "render-blocking-resources")
    cls = _num(audits, "cumulative-layout-shift")
    def category(name: str) -> int | None:
        sc = (lh.get("categories") or {}).get(name, {}).get("score")
        return round(sc * 100) if isinstance(sc, (int, float)) else None

    largest_image = None
    items = ((audits.get("uses-optimized-images") or {}).get("details") or {}).get("items") or []
    sizes = [i.get("totalBytes") for i in items if isinstance(i.get("totalBytes"), (int, float))]
    if sizes:
        largest_image = int(max(sizes))

    return SpeedSignals(
        strategy=strategy,
        seo_score=category("seo"),
        accessibility_score=category("accessibility"),
        best_practices_score=category("best-practices"),
        document_title_ok=_passed(audits, "document-title"),
        meta_description_ok=_passed(audits, "meta-description"),
        image_alt_ok=_passed(audits, "image-alt"),
        contrast_ok=_passed(audits, "color-contrast"),
        console_errors_ok=_passed(audits, "errors-in-console"),
        https_ok=_passed(audits, "is-on-https"),
        largest_image_bytes=largest_image,
        performance_score=round(score * 100) if isinstance(score, (int, float)) else None,
        lcp_ms=round(lcp) if lcp is not None else None,
        cls=round(cls, 3) if cls is not None else None,
        tbt_ms=round(tbt) if tbt is not None else None,
        speed_index_ms=round(si) if si is not None else None,
        total_bytes=round(weight) if weight is not None else None,
        render_blocking_ms=round(blocking) if blocking is not None else None,
        field_available=bool(metrics),
        field_lcp_ms=int(field_lcp) if isinstance(field_lcp, (int, float)) else None,
        viewport_ok=_passed(audits, "viewport"),
        tap_targets_ok=_passed(audits, "tap-targets"),
        font_size_ok=_passed(audits, "font-size"),
        lighthouse_version=str(lh.get("lighthouseVersion", "")),
    )


def fetch_pagespeed(
    url: str,
    *,
    api_key: str,
    strategy: str = "mobile",
    client: httpx.Client | None = None,
    timeout_seconds: float = 120,
    attempts: int = 2,
) -> SpeedSignals:
    """Heavy, script-laden sites can take Lighthouse over a minute; one retry covers a
    read timeout without doubling the wait for the common case."""
    params = {
        "url": url,
        "strategy": strategy,
        "key": api_key,
        # One call, four categories: vitals, mobile usability, accessibility, best practices.
        "category": ["performance", "seo", "accessibility", "best-practices"],
    }
    own = client is None
    c = client or httpx.Client(timeout=httpx.Timeout(timeout_seconds))
    try:
        last: Exception | None = None
        for _ in range(max(1, attempts)):
            try:
                response = c.get(ENDPOINT, params=params)
                response.raise_for_status()
                return parse_pagespeed(response.json(), strategy)
            except httpx.TimeoutException as exc:
                last = exc
        assert last is not None
        raise last
    finally:
        if own:
            c.close()
