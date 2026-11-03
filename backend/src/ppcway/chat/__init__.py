"""Ask Otto: a read-only conversation about one Google Ads account.

Phase 3 of the client's brief. Nothing here can change anything, and that is
structural rather than a setting: there is no write tool, not a disabled one.

- `tools` -- the eight typed lookups the brief names. None of them learns which
  account it is reading; the scope comes from the session, so an injected
  instruction has no field in which to redirect itself.
- `untrusted` -- marking the text somebody outside PPCWay wrote, because one
  search term will eventually be an attempt at an instruction.
- `ask` -- one turn: look up, answer, check every number against what the
  tools returned, and stream what is being done while it happens.
"""
