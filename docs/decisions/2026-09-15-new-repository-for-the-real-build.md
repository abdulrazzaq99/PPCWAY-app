# 2026-09-15: the real product is built in a new repository

**Decision.** The production build starts in this repository, from the Figma
Version 2 designs, rather than by extending the proof-of-concept code in
`../PPCWay`. The PoC stays deployed and untouched as a reference and demo.

**Why.** The PoC was scoped to prove nine claims and the Google Ads handshake.
Its console follows the older twelve-frame design; the real product follows
Version 2 with the blue brand, six-step onboarding including the website audit,
agency white-label, admin, emails and reports. Starting clean avoids carrying PoC
shortcuts (simulator-only paths, mock world, Vercel-only topology without
Temporal) into production.

**What is carried over.** The gateway's OAuth and GAQL code and its tests are
worth porting. The API contract of the PoC is kept for comparison in
`docs/reference/poc-merchant-api.openapi.json`.

**Owner.** Abdul Razzaq, decided in conversation on 15 September 2026.
