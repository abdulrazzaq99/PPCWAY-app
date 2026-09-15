# PPCWay: handoff from the proof of concept to the real build

Written 15 September 2026, at the end of the proof-of-concept phase. This is the
continuation point. Everything below was established in the PoC sessions and is
treated as settled unless the owner reopens it.

## 1. Where things are

| Thing | Location |
|---|---|
| PoC repository | `/Users/abdulrazzaq/Documents/PPCWay`, GitHub `buzzgrewal/PPCWay`, branch `main` at commit `a4f8341` |
| PoC hosted console | https://ppcway-web.vercel.app (Vercel team `byte27`, account byte9co-9281) |
| PoC hosted API and gateway | https://ppcway-api.vercel.app, https://ppcway-gateway.vercel.app |
| PoC demo site for the crawler | https://ppcway-fixture-site.vercel.app |
| PoC database and cache | Neon Postgres `neon-cinereous-park`, Upstash Redis `upstash-kv-cinnabar-paddle`, both currently empty |
| Blueprint PDF | `docs/reference/PPCWay_Technical_Architecture_Blueprint_v1.0.pdf` |
| Figma file | `PPCWay`, key `fI61nZuEBSsMVsRHGcDrcH`, one page, Version 2 |
| Credentials | `../PPCWay/.env`, gitignored. Names only are listed in §5 |
| PoC screen explainer | `docs/reference/screens-explained.html`, plain-language walk-through of the twelve PoC frames against the Blueprint |

## 2. What the proof of concept proved

Nine client claims were verified on the compose stack (`make verify` 9 of 9,
`make demo` exit 0), and the hosted stack ran the same code. In particular:

- **The Google Ads handshake is real.** Sign-up, Google OAuth consent, a real
  `listAccessibleCustomers` call, a real `customer_client` GAQL query, and a link
  to a test client account under a test manager account. The refresh token is
  stored encrypted with Fernet. Only the gateway service holds Google credentials.
- **A real campaign read works.** `GET /api/merchants/{id}/google/campaigns` refreshes
  the access token and runs a campaign GAQL query. It returned the campaign
  "Emergency plumbing" (id 24233414588, ENABLED, SEARCH, CA$10 a day) created by
  hand in the test client. Metrics stay at zero because test accounts never serve.
- **The console redesign shipped.** Sidebar shell, sentence-first pages (Home,
  Activity, Approvals, Campaigns, Settings), a five-step onboarding rail, an
  Advanced view with a live "From Google Ads" table, an "Add a business" door,
  old routes redirecting. All checks green (`npm run check`).
- **Guardrails, approvals, undo and the action log** exist in the PoC backend in
  simplified form, with a Google Ads simulator for the demonstration world.
- **25 extra trades** were added to the category list, so sign-up no longer fails
  with TRADE_NOT_LISTED for common trades.

What the PoC does **not** do: login and billing for PPCWay itself, team members,
alerts and email, search-term reports, ad-group and keyword tables, one-click tag
installation, editing keywords or wording from the console, writing guardrail
limits from the console, Temporal workers on Vercel (Docker only), an existing-
account audit.

## 3. Google Ads facts

- Developer token: the client's, **Test tier**. It only works against test
  accounts. Production needs Basic or Standard access applied for by the client.
- Google Cloud project `733299437383` holds the OAuth client. The Google Ads API had
  to be enabled there by hand.
- Test manager account **426-910-6223** is owned by abdulrazzaq.devv@gmail.com.
- Test client **295-726-1692** "Alpha Plumbing", CAD, America/Toronto, holds the
  "Emergency plumbing" Search campaign. Two other test clients also exist under the
  manager (4269106223 is the manager itself, 1303580474 is a second client).
- `GOOGLE_ADS_LOGIN_CUSTOMER_ID` must be the manager id (4269106223) for reads on
  client accounts to succeed.
- Google will not accept card details programmatically; billing is always a hand-
  off to Google's UI (Blueprint §13.1).
- Conversion tracking is the single point of failure (Blueprint §13.5) and must be a
  blocking gate before launch.

## 4. The Figma Version 2 designs

- Designed 8 to 11 September 2026, 163 screens; five audit screens added
  15 September, so 168. An "Index" frame at the top left of the page lists sections:
  Sign-in, Onboarding, Campaign review, Website audit and intake form, Dashboard,
  Campaigns and Advanced view, Existing campaigns, Settings, Agency, Internal admin,
  Emails, Report PDF, Mobile, Version 1 (old).
- Typeface Inter. Canvas `#f1f4f7`, ink `#0f1720`, dark navy rail and sidebar.
- **Brand colour is now blue `#2F5BD3`**, changed by the owner on 15 September from
  the original emerald `#12855d` using Figma's Selection colors. Derived shades
  agreed: dark `#2549B0`, pale `#E8EDFB`, bars `#CFDAF6`, border `#B9C9F0`,
  pale label `#B7C8F5`, tint `#F0F3FB`. Amber `#b7791f`/`#8b5c17` is "waiting on
  you", red `#9e281e` is "broken or money at risk", grey is information.
- The agency white-label frames (Brightpath Media, client Northgate HVAC) show how
  an agency's own brand replaces PPCWay's.
- The five audit frames sit at canvas y 20400, x 0 to 6400: Your business basics,
  Your business the money, Website check running, Website report, Website report
  one finding. The onboarding rail on them has six steps: Account and plan, Connect
  Google Ads, Your business, Website check, Count your calls, Review and launch.
- The PoC console was built from the older twelve frames (Geist typeface, light
  rail, emerald). The real build follows Version 2, blue. Copies of the twelve PoC
  frames are in `docs/reference/figma-poc-frames/` for comparison only.
- Reading and writing the file works through the "Claude Talk to Figma" plugin
  (owner supplies the channel id each session). Clone an existing frame and edit it
  rather than building from scratch. Send text batches one call at a time; parallel
  batches time out. Page-wide reads disconnect the plugin.

## 5. Credentials and environment (names only)

In `../PPCWay/.env`: `GOOGLE_OAUTH_CLIENT_ID`, `GOOGLE_OAUTH_CLIENT_SECRET`,
`GOOGLE_OAUTH_REDIRECT_URI`, `GOOGLE_OAUTH_TOKEN_KEY` (Fernet),
`GOOGLE_ADS_DEVELOPER_TOKEN`, `GOOGLE_ADS_LOGIN_CUSTOMER_ID`, `VERCEL_DATABASE_URL`,
`VERCEL_REDIS_URL`, `FIGMA_TOKEN` (the owner was asked to revoke this one).

Vercel projects are deployed with `deploy/vercel.sh` and their env set with
`deploy/vercel-env.sh` in the PoC repo. Python projects deploy from a clean
`git archive HEAD` export because git metadata caused BLOCKED deployments.
Auto-deploy from GitHub needs the repository owner `buzzgrewal` to install the
Vercel GitHub app; it is not set up.

## 6. What the agency audit research established

Agencies run two audits: the website audit (measurement and tags, speed and Core
Web Vitals, message match, conversion path, trust signals, policy risk, business
facts) and, for existing advertisers, the account audit (conversion tracking,
search terms sorted by cost, structure, bidding and budget, ads and assets,
location and schedule, change history). The process is questionnaire and access,
tracking validation before anything else, the audits, a findings document ranked
by money at stake, then a thirty-day plan. Sources are listed in the session
transcript; the Website check and Website report screens encode this.

## 7. Decisions already made by the owner

1. Real app, not mock, on the owner's own Vercel team `byte27`. Backend moved off
   Docker onto Vercel Python functions with Neon and Upstash.
2. Direct merges to `main`, no cherry-picks. Commits authored as
   `abdulrazzaq99@users.noreply.github.com`, no co-author trailers.
3. Demonstrate the handshake with a Google Ads **test** manager account rather than
   wait for the client's production access.
4. Implement the Figma redesign for every PoC screen; speed over ceremony.
5. Fetch real campaign data from the test account for the PoC.
6. Add a website audit and intake form to onboarding, designed first in Figma.
7. Whole design system recoloured from emerald to blue `#2F5BD3`.
8. The real product is built in a new repository, this one, starting from the
   Version 2 designs, not by extending the PoC code.

## 8. Open items carried over

- `poc-backend-spine` on GitHub is stale history; delete or force-push, owner's call.
- The Figma token in the PoC `.env` should be revoked.
- Index colour legend in Figma still says "Emerald"; change to "Blue".
- Mobile variants of the five audit screens are not drawn.
- The existing-account audit screens are not drawn.
- Production Google Ads API access (Basic tier) must be requested by the client
  under their developer token before any real merchant can be served.

## 9. Suggested first steps in this repository

1. Brainstorm the Phase 1 scope against Blueprint §16.2 and the DRD, and record it
   in `docs/decisions/`.
2. Choose the stack. The Blueprint recommends Next.js, FastAPI, Postgres, Redis,
   Temporal, one ads-gateway service. Decide what stays from the PoC (the gateway
   OAuth and GAQL code is worth porting) and what is rebuilt.
3. Set up the repository skeleton, CI, and environments (Blueprint §18).
4. Start with authentication and the onboarding rail, screens 1 to 6, since the
   audit and tracking gate sit inside them.
