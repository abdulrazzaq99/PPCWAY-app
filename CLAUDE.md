# PPCWay, the real product

This repository is the production build of PPCWay, the Google Ads onboarding and
auto-optimisation platform for small businesses. It follows the proof of concept
in `../PPCWay`, which stays as a reference and is not modified from here.

Start by reading `docs/handoff/2026-09-15-poc-handoff.md`. It carries the full
context of the proof of concept: what was proven, what was deployed, the Google
Ads test accounts, the Figma Version 2 designs, and every decision the owner has
already made. Do not re-open those decisions unless the owner asks.

## Sources of truth

- Requirements: the Developer Requirements Document (DRD) v1.0, held by the client.
- Architecture: `docs/reference/PPCWay_Technical_Architecture_Blueprint_v1.0.pdf`
  (§4 flows, §5.5 guardrails, §8.3 autonomy levels, §8.4 action log, §10.1 dashboard).
- Design: the Figma file `PPCWay`, key `fI61nZuEBSsMVsRHGcDrcH`, Version 2 "Slate and
  Emerald", now recoloured to blue. 168 screens. Read it through the Claude Talk to
  Figma plugin (the owner gives the channel id) or the Figma MCP.
- Proof of concept code and its tests: `../PPCWay`. Its API contract is copied at
  `docs/reference/poc-merchant-api.openapi.json`.

## How the owner works

- Commit as `Abdul Razzaq <abdulrazzaq99@users.noreply.github.com>`, committer the
  same, no co-author trailer of any kind. Push and merge only when asked.
- Prefer fast, direct execution over ceremony. Batch work, avoid long check-ins.
- Never echo secrets. Credentials live in a gitignored `.env`; copy names, never values.
- No mock mode when a real thing is asked for. No published artifacts unless asked;
  a local HTML file is preferred for explainers.
- Plain words in every screen: a sentence before a number, a number before a chart.
- Never run a test suite against a database that holds demo or real sign-in data.

## Working conventions for this repo

- Design first in Figma, then implement. Screens must match Version 2, blue brand.
- One door to Google: only one service holds Google Ads credentials and may mutate.
- Every automated change passes the guardrail order in Blueprint §5.5 and is written
  to an append-only action log before it is applied.
- Decisions that change scope or architecture are recorded in `docs/decisions/` as
  dated files.
