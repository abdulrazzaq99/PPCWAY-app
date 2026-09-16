"""The crawler: the one component that fetches untrusted third-party content.

Blueprint §12.6 and spec §6.1. `docker-compose.yml`'s `worker-crawler` is
deliberately the least-privileged container on the platform - no Google Ads
credentials, no LLM key, no database - because this is the package that follows
a URL a merchant typed into a form. `ssrf` is the boundary that decides which
URLs it may follow at all.
"""
