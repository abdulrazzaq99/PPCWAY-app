"""The audit report as a page you can keep, print or hand to somebody.

A report that lives only at a URL is one a small business owner cannot take to
their accountant, give to their web developer, or put in a folder. So this
prints it.

It prints the same page the browser already draws, using the same headless
Chromium the audit already runs for its screenshots. One layout, printed, not a
second layout built to look like the first and free to drift away from it. The
page is asked for with `?paper=1`, which is how it knows to leave off the
navigation, the floating bar and the sign-up panel: none of them mean anything
on paper.
"""

from __future__ import annotations

import logging

log = logging.getLogger(__name__)

#: The report draws itself after fetching the run; this is the pause that lets
#: the last paint land rather than printing a half-built page.
SETTLE_MS = 1500


class NotPrinted(RuntimeError):
    """The page did not become a PDF. Carries why, for the log."""


def to_pdf(url: str, *, timeout_seconds: float = 60) -> bytes:
    """One report page, as A4 with its colours kept."""
    from playwright.sync_api import Error as BrowserTrouble
    from playwright.sync_api import sync_playwright

    try:
        with sync_playwright() as play:
            browser = play.chromium.launch(args=["--disable-dev-shm-usage"])
            try:
                page = browser.new_page(viewport={"width": 1120, "height": 1500})
                page.goto(url, wait_until="networkidle", timeout=int(timeout_seconds * 1000))
                page.wait_for_timeout(SETTLE_MS)
                # Room for the page to breathe, in Chromium's own print margins.
                return page.pdf(
                    format="A4",
                    print_background=True,
                    margin={
                        "top": "14mm",
                        "bottom": "14mm",
                        "left": "12mm",
                        "right": "12mm",
                    },
                )
            finally:
                browser.close()
    except BrowserTrouble as exc:
        raise NotPrinted(f"the report would not print: {exc}") from None
