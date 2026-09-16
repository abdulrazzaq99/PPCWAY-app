from ppcway.audit.tags import classify_tags


def test_a_site_with_nothing_has_nothing() -> None:
    t = classify_tags(requests=["https://example.ca/", "https://example.ca/style.css"], scripts=[], data_layer=[], html="<html></html>")
    assert t.gtm_ids == () and t.ga4_ids == () and t.ads_ids == ()
    assert not t.ga4_fired and not t.ads_fired and t.call_tracking is None


def test_tag_manager_analytics_and_ads_are_found_and_firing_is_observed() -> None:
    t = classify_tags(
        requests=[
            "https://www.googletagmanager.com/gtm.js?id=GTM-ABC1234",
            "https://www.googletagmanager.com/gtag/js?id=G-1A2B3C4D5E",
            "https://www.google-analytics.com/g/collect?v=2&tid=G-1A2B3C4D5E",
            "https://googleads.g.doubleclick.net/pagead/viewthroughconversion/123456789/?random=1",
        ],
        scripts=["gtag('config', 'AW-123456789');"],
        data_layer=[],
        html="",
    )
    assert t.gtm_ids == ("GTM-ABC1234",)
    assert t.ga4_ids == ("G-1A2B3C4D5E",)
    assert t.ads_ids == ("AW-123456789",)
    assert t.gtm_loaded and t.ga4_fired and t.ads_fired


def test_a_present_tag_that_never_fired_is_not_counted_as_firing() -> None:
    t = classify_tags(requests=[], scripts=["gtag('config', 'AW-987654321');"], data_layer=[], html="")
    assert t.ads_ids == ("AW-987654321",)
    assert not t.ads_fired


def test_call_tracking_providers_are_named() -> None:
    t = classify_tags(requests=["https://cdn.callrail.com/companies/123/abc/12/swap.js"], scripts=[], data_layer=[], html="")
    assert t.call_tracking == "CallRail"


def test_consent_mode_default_is_read_from_the_data_layer() -> None:
    dl = [{"0": "consent", "1": "default", "2": {"ad_storage": "denied", "analytics_storage": "denied"}}]
    t = classify_tags(requests=[], scripts=[], data_layer=dl, html="")
    assert t.consent_ad_storage == "denied"
