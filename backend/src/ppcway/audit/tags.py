"""Google's tags and call tracking: present, and did they fire.

Pure functions over what the headless browser observed: the URLs it requested,
the scripts on the page and the ``dataLayer``. Presence of a script is not the
same as a tag firing, which is why the runner records network requests and this
module reads those first.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

GTM_ID = re.compile(r"\bGTM-[A-Z0-9]{4,10}\b")
GA4_ID = re.compile(r"\bG-[A-Z0-9]{6,12}\b")
ADS_ID = re.compile(r"\bAW-\d{6,12}\b")

CALL_TRACKING = {
    "CallRail": ("cdn.callrail.com", "callrail.com/companies"),
    "WhatConverts": ("whatconverts.com", "wc.tracking"),
    "CallTrackingMetrics": ("tctm.co", "calltrackingmetrics.com"),
    "Ringba": ("ringba.com",),
    "Invoca": ("invoca.net",),
    "CallTrackingMetrics (Marchex)": ("marchex.io",),
}


@dataclass(frozen=True)
class TagSignals:
    gtm_ids: tuple[str, ...]
    ga4_ids: tuple[str, ...]
    ads_ids: tuple[str, ...]
    #: A GA4 hit (`/g/collect`) was sent on load.
    ga4_fired: bool
    #: A Google Ads conversion or remarketing hit was sent on load.
    ads_fired: bool
    #: Tag Manager container script was downloaded.
    gtm_loaded: bool
    call_tracking: str | None
    #: Consent Mode default for ad_storage, if the page set one: "granted"/"denied".
    consent_ad_storage: str | None
    other_analytics: tuple[str, ...] = field(default_factory=tuple)


def _ids(pattern: re.Pattern[str], *texts: str) -> tuple[str, ...]:
    found: list[str] = []
    for t in texts:
        for m in pattern.findall(t):
            if m not in found:
                found.append(m)
    return tuple(found)


def _consent_default(data_layer: list[Any]) -> str | None:
    """`gtag('consent','default',{ad_storage:'denied',...})` lands in the dataLayer as
    an arguments-like object: {0:'consent',1:'default',2:{...}}."""
    for entry in data_layer:
        if not isinstance(entry, dict):
            continue
        values = [entry.get(str(i), entry.get(i)) for i in range(3)]
        if values[0] == "consent" and values[1] == "default" and isinstance(values[2], dict):
            v = values[2].get("ad_storage")
            return str(v) if v is not None else None
    return None


def classify_tags(
    *, requests: list[str], scripts: list[str], data_layer: list[Any], html: str
) -> TagSignals:
    joined_requests = "\n".join(requests)
    joined_scripts = "\n".join(scripts)
    everything = joined_requests + "\n" + joined_scripts + "\n" + html

    ga4_fired = any("google-analytics.com/g/collect" in r or "analytics.google.com/g/collect" in r for r in requests)
    ads_fired = any(
        "googleads.g.doubleclick.net/pagead/" in r
        or "google.com/pagead/1p-conversion" in r
        or "googleadservices.com/pagead/conversion" in r
        for r in requests
    )
    gtm_loaded = any("googletagmanager.com/gtm.js" in r for r in requests)

    call_tracking = None
    for name, needles in CALL_TRACKING.items():
        if any(n in everything for n in needles):
            call_tracking = name
            break

    other: list[str] = []
    for name, needle in (
        ("Meta Pixel", "connect.facebook.net"),
        ("Hotjar", "hotjar.com"),
        ("Microsoft Clarity", "clarity.ms"),
        ("HubSpot", "hs-scripts.com"),
    ):
        if needle in everything:
            other.append(name)

    return TagSignals(
        gtm_ids=_ids(GTM_ID, joined_requests, joined_scripts, html),
        ga4_ids=_ids(GA4_ID, joined_requests, joined_scripts, html),
        ads_ids=_ids(ADS_ID, joined_requests, joined_scripts, html),
        ga4_fired=ga4_fired,
        ads_fired=ads_fired,
        gtm_loaded=gtm_loaded,
        call_tracking=call_tracking,
        consent_ad_storage=_consent_default(data_layer),
        other_analytics=tuple(other),
    )
