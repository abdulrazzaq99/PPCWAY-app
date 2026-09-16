from ppcway.audit.policy import scan_policy


def test_clean_text_has_no_hits() -> None:
    assert scan_policy("We fix burst pipes in Toronto, seven days a week.") == []


def test_superlatives_and_restricted_claims_are_found_with_context() -> None:
    hits = scan_policy("Best price guaranteed. Our treatment cures back pain.")
    phrases = {h.phrase for h in hits}
    assert {"best", "guaranteed", "cures"} <= phrases
    assert all(h.context for h in hits)


def test_a_word_inside_another_word_does_not_count() -> None:
    assert scan_policy("Our bestselling sump pump") == []
