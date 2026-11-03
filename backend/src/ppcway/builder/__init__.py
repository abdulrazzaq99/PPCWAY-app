"""The campaign builder: Search only, as the client's brief says for the MVP.

Phase 4. Partly built, and the missing parts are missing because the
specification is: the brief cites `v0.1 §3.2` for the eight builder steps and
`§3.6` for the per-campaign-type learning windows, and neither was supplied.
What the brief states outright is here.

- `validate` -- the six stages, in the brief's own order, with the one that
  cannot be done by a word list doing most of the work.

Still waiting on the client: the eight steps, the learning windows, the
per-industry prohibited-claim lists and the category fallback templates. The
validator reads whatever lists it is given and passes everything when given
none, which is the only honest behaviour for a stage nobody has described yet.
"""
