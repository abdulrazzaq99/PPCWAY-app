from datetime import UTC, datetime

from ppcway.audit.conversion import detect_conversion


def _run(**kw):  # type: ignore[no-untyped-def]
    base = dict(html="", scripts=[], requests=[], headline="Emergency plumber in Oakville", has_h1=True, ctas=["Call now"],
                phone_above_fold=True, tel_links=["tel:1"], overlay=None, copyright_year=datetime.now(UTC).year, form_fields=4)
    base.update(kw)
    return detect_conversion(**base)


def test_a_good_first_screen_has_no_problems() -> None:
    assert _run().problems == []


def test_pop_ups_missing_buttons_long_forms_and_stale_years_are_named() -> None:
    c = _run(overlay="Subscribe to our newsletter", ctas=[], phone_above_fold=False, has_h1=False, form_fields=9, copyright_year=datetime.now(UTC).year - 3)
    joined = " ".join(c.problems)
    assert "pop-up" in joined and "first screen" in joined and "headline" in joined and "9 questions" in joined and "footer says" in joined
    assert c.years_stale == 3


def test_chat_and_booking_tools_are_recognised() -> None:
    c = _run(scripts=["https://embed.tawk.to/abc/default"], requests=["https://book.housecallpro.com/x"])
    assert c.chat_tool == "Tawk.to" and c.booking_tool == "Housecall Pro"
