"""The brief's constraint on the model service, enforced rather than stated.

*The model service and chat code have no import path to the Google Ads token
vault and cannot fetch URLs.* Blueprint §18.2: an architectural rule that is
not enforced mechanically decays, and this one protects the thing worth
protecting -- a model that can be talked into reading a URL, in a package that
can reach a merchant's refresh token, is the shape of the worst day this
platform could have.

This is static analysis of `import` statements, which is a narrower guarantee
than "no code path reaches Google", and the difference is worth stating: a
dynamic `importlib.import_module("ppcway.ads.oauth")` is an ordinary function
call to `ast` and invisible here. Nothing does that, and it would be a
conspicuous way to write it, but a reviewer reading this test as proof should
know where the proof stops.

**The `anthropic` SDK is the one permitted import that speaks HTTP, and this
test does not forbid it.** Pretending otherwise would be the dishonest version
of this check: the model service obviously makes a network call, or it could
not call a model. What makes that acceptable, and what "cannot fetch URLs"
actually rests on, is three things the SDK import does not weaken -- it reaches
exactly one host, Vertex AI in the configured region; `service.ask` declares no
tools at all, so there is no `web_fetch` or `code_execution` for a prompt to
talk its way into; and Vertex does not offer web fetch or code execution to
Claude in the first place. A reviewer should check those three rather than
read this test as proving more than it does.
"""

from __future__ import annotations

import ast
import pathlib

PACKAGE = pathlib.Path(__file__).resolve().parents[2] / "src" / "ppcway" / "model"

#: What may not be reached from the model service, and why each one.
FORBIDDEN = {
    # The one door to Google. Holds and decrypts refresh tokens.
    "ppcway.ads.oauth": "the Google Ads credential vault",
    "ppcway.ads.accounts": "the Google Ads client",
    "ppcway.ads.sync": "the Google Ads reader",
    "ppcway.ads.reports": "the Google Ads reader",
    "google.ads": "the Google Ads SDK",
    # Anything that fetches a URL. The crawler is the deliberate one; httpx and
    # requests are the general case, and the Vertex client brings its own.
    "ppcway.crawler": "the website crawler",
    "httpx": "an HTTP client that could fetch a URL",
    "requests": "an HTTP client that could fetch a URL",
    "urllib.request": "an HTTP client that could fetch a URL",
    "aiohttp": "an HTTP client that could fetch a URL",
}


def _imports(path: pathlib.Path) -> set[str]:
    """Every module name this file's import statements reach.

    `from X import a` records `X` and `X.a` both: `from ppcway.ads import oauth`
    is an ordinary way to import a submodule, and recording only the module
    would let it past a prefix check without a word.
    """
    found: set[str] = set()
    for node in ast.walk(ast.parse(path.read_text())):
        if isinstance(node, ast.Import):
            found.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            found.add(node.module)
            found.update(f"{node.module}.{alias.name}" for alias in node.names)
    return found


def test_the_model_service_cannot_reach_google_ads_or_fetch_a_url() -> None:
    files = sorted(PACKAGE.glob("*.py"))
    assert files, f"no modules found under {PACKAGE}; this test would pass vacuously"

    broken: list[str] = []
    for path in files:
        for name in _imports(path):
            for banned, what in FORBIDDEN.items():
                if name == banned or name.startswith(f"{banned}."):
                    broken.append(f"{path.name} imports {name} -- {what}")
    assert not broken, (
        "the model service must not be able to reach Google Ads credentials or fetch a"
        " URL (client brief, model service): " + "; ".join(broken)
    )


def test_the_guard_would_notice() -> None:
    """A test that can only pass is not a test. This proves the check bites."""
    pretend = ast.parse("from ppcway.ads import oauth\nimport httpx\n")
    found: set[str] = set()
    for node in ast.walk(pretend):
        if isinstance(node, ast.Import):
            found.update(a.name for a in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            found.add(node.module)
            found.update(f"{node.module}.{a.name}" for a in node.names)
    assert "ppcway.ads.oauth" in found
    assert "httpx" in found
    assert any(name in FORBIDDEN for name in found)
