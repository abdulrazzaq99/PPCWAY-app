# The backend starts by porting the proof of concept's Python, service by service

Date: 15 September 2026. Decided by the owner's instruction to start the backend
with the credentials in `web/.env`, and by these facts:

- The Neon database the owner provisioned already carries the proof of concept's
  schema (33 tables, 12 migrations) and its data, including real Google Ads links.
- The proof of concept's crawler, SSRF defences, validator and gateway are tested
  (the crawler alone has 469 tests) and the handoff names the gateway as worth porting.
- The Blueprint's service shape (api, ads-gateway, worker-crawler, worker-generation)
  is Python.

So:

1. `backend/` is a Python 3.12 project. Next.js on Vercel stays the web and thin API
   layer and reaches the backend through `BACKEND_URL`.
2. Packages are ported one at a time, with their tests, as the product needs them.
   First the crawler (done) and the audit (new). Next the gateway's OAuth and GAQL.
3. This repository's own migrations use the Alembic version table
   `alembic_version_app`, beside the proof of concept's `alembic_version`, and only
   add tables. The proof of concept's data is left in place until the owner says
   otherwise.
4. Temporal is not carried over yet. The audit runs as a background task in the API
   process; a job table and worker replace that before launch.
5. The audit's headless browser needs a container host (Fly.io, Railway or Cloud Run).
   Vercel functions cannot run it.

What this costs if wrong: if the owner later prefers a single TypeScript stack, the
audit and crawler have to be rewritten. The port keeps three months of tested code
in service until then.
