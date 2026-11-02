"""The one door to Google: the only package that may change a live account.

CLAUDE.md's own rule, and Blueprint §4.1 principle 1. `tests/gateway/
test_one_door.py` enforces it by reading imports, per §18.2 -- an
architectural rule nothing checks decays.

- `port` -- the shape of a mutation, and the index-alignment invariant that
  makes partial failure legible.
- `google` -- the real door. The only module that sends a mutation.
- `switch` -- the write gate and the two kill switches.
- `quota` -- what the day has spent, counted in operations as Google counts it.
- `apply` -- the order the switches, the guardrails, the quota, the call and
  the log happen in, which is the whole of this package's correctness.
"""
