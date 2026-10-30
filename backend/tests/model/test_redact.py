"""What the prompt log keeps, and what it must not.

The claim this module supports is narrow and these tests hold it to that: an
address, a telephone number, a card-shaped number or a long opaque token does
not survive into the log. A business name might, and no test here pretends
otherwise.
"""

from __future__ import annotations

import pytest

from ppcway.model.redact import MOST, redacted


@pytest.mark.parametrize(
    ("said", "gone", "instead"),
    [
        ("write to dana@alphaplumbing.ca today", "dana@alphaplumbing.ca", "[email]"),
        ("ring +353 1 234 5678 now", "+353 1 234 5678", "[phone]"),
        ("ring (01) 234 5678 now", "234 5678", "[phone]"),
        ("card 4111 1111 1111 1111 on file", "4111 1111 1111 1111", "[card]"),
        ("key AbCdEf123456GhIjKlMnOpQrStUv now", "AbCdEf123456GhIjKlMnOpQrStUv", "[token]"),
    ],
)
def test_a_person_does_not_survive_into_the_log(said: str, gone: str, instead: str) -> None:
    clean = redacted(said)
    assert gone not in clean
    assert instead in clean


@pytest.mark.parametrize(
    "kept",
    [
        "Budget rose from 40.00 to 48.00, a 20% rise",
        "Measured 2026-10-30, window 30/10/2026 to 06/11/2026",
        "1,240 clicks and 18 calls last month",
        "Quality Score 7 on three of nine keywords",
    ],
)
def test_the_figures_a_reason_is_about_are_kept(kept: str) -> None:
    """A log with the dates and numbers stripped out answers nothing."""
    assert redacted(kept) == kept


def test_a_google_token_leaves_its_prefix_behind_on_purpose() -> None:
    """`ya29.[token]` says a credential reached a prompt. That is worth seeing."""
    clean = redacted("refresh ya29.a0ARrdaM9xKQfLm2Zb7Yt4Np1Qs8Wv3Hc6Jd0Ge5Rf")
    assert "a0ARrdaM9xKQfLm2Zb7Yt4Np1Qs8Wv3Hc6Jd0Ge5Rf" not in clean
    assert "ya29.[token]" in clean


def test_a_long_prompt_is_cut_and_says_it_was() -> None:
    clean = redacted("a" * (MOST + 500))
    assert len(clean) < MOST + 100
    assert "500 more characters" in clean


def test_nothing_in_means_nothing_out() -> None:
    assert redacted("") == ""
