from ppcway.audit.pagespeed import parse_pagespeed
from ppcway.audit.render import Rendering
from ppcway.audit.runner import build_findings, normalise_site
from ppcway.audit.types import CHECK_KEYS, MORE_KEYS


def test_sites_are_normalised_to_a_scheme_and_a_path() -> None:
    assert normalise_site("alphaplumbing.ca") == "https://alphaplumbing.ca/"
    assert normalise_site("http://x.ca/contact?a=1") == "http://x.ca/contact"


def test_with_nothing_every_check_is_answered() -> None:
    findings = build_findings(None, None, None)
    assert [f.key for f in findings if f.group == "checks"] == list(CHECK_KEYS)
    assert [f.key for f in findings if f.group == "more"] == list(MORE_KEYS)
    assert all(f.summary for f in findings)


def test_a_bare_site_reports_in_plain_words() -> None:
    rendered = Rendering(url="https://x.ca/", final_url="https://x.ca/", title="X", html="<html><body>Call us</body></html>",
                         requests=["https://x.ca/"], tel_links=[], viewport_meta=False)
    speed = parse_pagespeed({"lighthouseResult": {"categories": {"performance": {"score": 0.4}}, "audits": {"largest-contentful-paint": {"numericValue": 4600}}}})
    by_key = {f.key: f for f in build_findings(None, rendered, speed)}
    assert by_key["counting"].status == "needs_you"
    assert by_key["speed"].status == "needs_you" and "4.6 seconds" in by_key["speed"].summary
    assert by_key["mobile"].status == "needs_you" and any("viewport" in d for d in by_key["mobile"].detail)
    assert by_key["tags"].status == "ours"
