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
from collections.abc import Mapping
from typing import TYPE_CHECKING, Final, cast
from urllib.parse import urlsplit

if TYPE_CHECKING:
    from playwright._impl._api_structures import PdfMargins

log = logging.getLogger(__name__)

#: The report draws itself after fetching the run; this is the pause that lets
#: the last paint land rather than printing a half-built page.
SETTLE_MS = 1500


class NotPrinted(RuntimeError):
    """The page did not become a PDF. Carries why, for the log."""


#: Room for the page to breathe, in Chromium's own print margins.
MARGIN: Final = {"top": "14mm", "bottom": "14mm", "left": "12mm", "right": "12mm"}


def to_pdf(
    url: str,
    *,
    timeout_seconds: float = 60,
    session_cookie: tuple[str, str] | None = None,
    footer: str = "",
    margin: Mapping[str, str] | None = None,
) -> bytes:
    """One report page, as A4 with its colours kept.

    `session_cookie` is (name, value) for a page that is only drawn for
    somebody signed in: it is set on that page's own address and nowhere else,
    and the browser it lives in is thrown away when the page is printed.
    Requests from the page to anywhere but its own address are refused, so a
    signed-in page cannot be made to carry the cookie, or anything else, away.

    `footer` is Chromium's footer template, where `pageNumber` and
    `totalPages` are filled in on every sheet.
    """
    from playwright.sync_api import Error as BrowserTrouble
    from playwright.sync_api import Route, sync_playwright

    home = urlsplit(url)
    origin = f"{home.scheme}://{home.netloc}"

    def own_only(route: Route) -> None:
        asked = urlsplit(route.request.url)
        if f"{asked.scheme}://{asked.netloc}" == origin or asked.scheme == "data":
            route.continue_()
        else:
            route.abort()

    try:
        with sync_playwright() as play:
            browser = play.chromium.launch(args=["--disable-dev-shm-usage"])
            try:
                context = browser.new_context(viewport={"width": 1120, "height": 1500})
                if session_cookie is not None:
                    name, value = session_cookie
                    context.add_cookies(
                        [
                            {
                                "name": name,
                                "value": value,
                                "url": origin,
                                "httpOnly": True,
                                "secure": home.scheme == "https",
                                "sameSite": "Lax",
                            }
                        ]
                    )
                    context.route("**/*", own_only)
                page = context.new_page()
                page.goto(url, wait_until="networkidle", timeout=int(timeout_seconds * 1000))
                page.wait_for_timeout(SETTLE_MS)
                return page.pdf(
                    format="A4",
                    print_background=True,
                    display_header_footer=bool(footer),
                    header_template="<span></span>",
                    footer_template=footer or "<span></span>",
                    margin=cast("PdfMargins", dict(margin or MARGIN)),
                )
            finally:
                browser.close()
    except BrowserTrouble as exc:
        raise NotPrinted(f"the report would not print: {exc}") from None
