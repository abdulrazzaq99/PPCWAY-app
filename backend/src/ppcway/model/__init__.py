"""Otto's model service: the only part of PPCWay that calls a language model.

Claude on Google Cloud Vertex AI, in the United States multi-region. Three
models for three kinds of work, chosen by job rather than by caller, in
`jobs`. The call itself is in `service`; what gets written down about it is in
`log`, and what is taken out before it is written is in `redact`.

Nothing here may import the Google Ads credential vault, and nothing here
fetches a URL. `tests/model/test_boundaries.py` enforces both.
"""
