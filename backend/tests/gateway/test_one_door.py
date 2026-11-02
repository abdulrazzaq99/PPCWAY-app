"""One door to Google, enforced by reading imports rather than by agreement.

CLAUDE.md: "only one service holds Google Ads credentials and may mutate."
Blueprint §18.2: an architectural rule that is not enforced mechanically
decays. This is the enforcement.

What it can prove is narrower than "no code path mutates Google", and the gap
is worth naming: this is static analysis of import statements, so a dynamic
`importlib.import_module("ppcway.gateway.google")` is an ordinary function call
to `ast` and invisible here. Nothing does that. A reviewer reading this as
proof should know where the proof stops.
"""

from __future__ import annotations

import ast
import pathlib

SRC = pathlib.Path(__file__).resolve().parents[2] / "src" / "ppcway"

#: Only the gateway may reach the module that sends mutations.
THE_DOOR = "ppcway.gateway.google"

#: And these are the packages allowed to import the gateway at all. Everything
#: else proposes, records and reports; it does not act.
MAY_USE_THE_GATEWAY = {"gateway", "api"}


def _imports(path: pathlib.Path) -> set[str]:
    """Every module name this file's imports reach, as far as `ast` can tell.

    `from X import a` records `X` and `X.a` both, because `from ppcway.gateway
    import google` is an ordinary way to import a submodule and recording only
    the module would let it past a prefix check without a word.
    """
    found: set[str] = set()
    for node in ast.walk(ast.parse(path.read_text())):
        if isinstance(node, ast.Import):
            found.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            found.add(node.module)
            found.update(f"{node.module}.{alias.name}" for alias in node.names)
    return found


def _every_module() -> list[pathlib.Path]:
    return sorted(p for p in SRC.rglob("*.py") if "__pycache__" not in p.parts)


def test_only_the_gateway_reaches_the_module_that_mutates() -> None:
    files = _every_module()
    assert files, f"no modules found under {SRC}; this test would pass vacuously"

    outside: list[str] = []
    for path in files:
        where = path.relative_to(SRC).parts
        if where and where[0] == "gateway":
            continue
        for name in _imports(path):
            if name == THE_DOOR or name.startswith(f"{THE_DOOR}."):
                outside.append(str(path.relative_to(SRC)))
    assert not outside, (
        "only ppcway.gateway may import the module that sends mutations to Google"
        f" (CLAUDE.md, one door): {', '.join(sorted(set(outside)))}"
    )


def test_the_gateway_itself_is_reached_from_few_places() -> None:
    """A door everything holds is not a door."""
    reached_from: set[str] = set()
    for path in _every_module():
        where = path.relative_to(SRC).parts
        top = where[0] if len(where) > 1 else ""
        if top in MAY_USE_THE_GATEWAY:
            continue
        for name in _imports(path):
            if name == "ppcway.gateway" or name.startswith("ppcway.gateway."):
                reached_from.add(str(path.relative_to(SRC)))
    assert not reached_from, (
        "the gateway is reached from somewhere that should not act:"
        f" {', '.join(sorted(reached_from))}. Packages allowed:"
        f" {', '.join(sorted(MAY_USE_THE_GATEWAY))}"
    )


def test_the_check_would_notice() -> None:
    """A test that can only pass is not a test."""
    pretend = ast.parse("from ppcway.gateway import google\n")
    found: set[str] = set()
    for node in ast.walk(pretend):
        if isinstance(node, ast.ImportFrom) and node.module:
            found.add(node.module)
            found.update(f"{node.module}.{a.name}" for a in node.names)
    assert THE_DOOR in found
