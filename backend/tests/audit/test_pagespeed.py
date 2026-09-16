from ppcway.audit.pagespeed import parse_pagespeed


def _payload(lcp: float, field: bool = False) -> dict:  # type: ignore[type-arg]
    p = {
        "lighthouseResult": {
            "lighthouseVersion": "13.4.1",
            "categories": {"performance": {"score": 0.91}},
            "audits": {
                "largest-contentful-paint": {"numericValue": lcp},
                "cumulative-layout-shift": {"numericValue": 0.01},
                "total-blocking-time": {"numericValue": 120},
                "speed-index": {"numericValue": 1800},
                "total-byte-weight": {"numericValue": 1_450_000},
                "render-blocking-resources": {"numericValue": 300},
                "viewport": {"score": 1},
                "tap-targets": {"score": 0.6},
                "font-size": {"score": None},
            },
        }
    }
    if field:
        p["loadingExperience"] = {"metrics": {"LARGEST_CONTENTFUL_PAINT_MS": {"percentile": 3100}}}
    return p


def test_lab_numbers_are_read_and_rounded() -> None:
    s = parse_pagespeed(_payload(2412.6))
    assert s.performance_score == 91 and s.lcp_ms == 2413 and s.total_bytes == 1_450_000
    assert s.viewport_ok is True and s.tap_targets_ok is False and s.font_size_ok is None
    assert not s.field_available and s.lcp_verdict == "good"


def test_real_user_data_wins_over_the_lab_when_present() -> None:
    s = parse_pagespeed(_payload(900, field=True))
    assert s.field_available and s.field_lcp_ms == 3100 and s.lcp_verdict == "slow"


def test_an_empty_reply_is_all_unknown() -> None:
    s = parse_pagespeed({})
    assert s.performance_score is None and s.lcp_ms is None and s.lcp_verdict == "unknown"
