"""Site health: the plumbing an agency checks before it sends paid traffic.

HTTPS and the certificate's expiry, the redirects from http and www, broken
internal links, and what the browser saw fail. The link check is bounded and
polite: a dozen links, one request a second, through the same pinned client the
crawler uses.
"""

from __future__ import annotations

import socket
import ssl
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime
from urllib.parse import urlsplit

import httpx

from ppcway.crawler.fetch import SAFE_TARGET_EXTENSION, build_client
from ppcway.crawler.ssrf import BlockedAddress, assert_safe_url

MAX_LINKS = 12


@dataclass
class HealthSignals:
    https: bool
    #: Days until the certificate expires, None when it could not be read.
    cert_days_left: int | None
    cert_issuer: str
    #: http://host redirects to https.
    http_redirects: bool | None
    #: The www or bare variant redirects to the canonical host, rather than serving a copy.
    www_redirects: bool | None
    #: (url, status) for internal links that did not answer 2xx or 3xx.
    broken_links: list[tuple[str, int]] = field(default_factory=list)
    links_checked: int = 0
    notes: list[str] = field(default_factory=list)


def _certificate(host: str, port: int = 443, timeout: float = 8) -> tuple[int | None, str]:
    ctx = ssl.create_default_context()
    with socket.create_connection((host, port), timeout=timeout) as raw, ctx.wrap_socket(raw, server_hostname=host) as tls:
        cert = tls.getpeercert()
    not_after = cert.get("notAfter")
    issuer = ""
    for rdn in cert.get("issuer", ()):
        for key, value in rdn:
            if key == "organizationName":
                issuer = str(value)
    if not not_after:
        return None, issuer
    expires = datetime.strptime(str(not_after), "%b %d %H:%M:%S %Y %Z").replace(tzinfo=UTC)
    return (expires - datetime.now(UTC)).days, issuer


def _head(client: httpx.Client, url: str) -> httpx.Response | None:
    try:
        target = assert_safe_url(url)
    except BlockedAddress:
        return None
    request = client.build_request("GET", url, headers={"Range": "bytes=0-0"})
    request.extensions[SAFE_TARGET_EXTENSION] = target
    try:
        return client.send(request, stream=True)
    except httpx.HTTPError:
        return None


def check_health(url: str, internal_links: list[str], *, timeout_seconds: float = 10) -> HealthSignals:
    parts = urlsplit(url)
    host = parts.hostname or ""
    out = HealthSignals(https=parts.scheme == "https", cert_days_left=None, cert_issuer="", http_redirects=None, www_redirects=None)

    if out.https:
        try:
            out.cert_days_left, out.cert_issuer = _certificate(host)
        except (OSError, ssl.SSLError, ValueError) as exc:
            out.notes.append(f"certificate could not be read: {type(exc).__name__}")

    with build_client(timeout_seconds=timeout_seconds) as client:
        # http:// should send people to https://
        if out.https:
            r = _head(client, f"http://{host}/")
            out.http_redirects = bool(r is not None and 300 <= r.status_code < 400 and str(r.headers.get("location", "")).startswith("https://"))
            if r is not None:
                r.close()
        # the other host spelling should redirect to this one
        other = host[4:] if host.startswith("www.") else "www." + host
        r = _head(client, f"{parts.scheme}://{other}/")
        if r is None:
            out.www_redirects = None
            out.notes.append(f"{other} did not answer")
        else:
            out.www_redirects = 300 <= r.status_code < 400
            r.close()

        seen: set[str] = set()
        for link in internal_links:
            if len(seen) >= MAX_LINKS:
                break
            if link in seen or urlsplit(link).hostname != host:
                continue
            seen.add(link)
            r = _head(client, link)
            if r is None:
                out.broken_links.append((link, 0))
            elif r.status_code >= 400:
                out.broken_links.append((link, r.status_code))
            if r is not None:
                r.close()
            time.sleep(1.0)
        out.links_checked = len(seen)
    return out
