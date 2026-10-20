# Weeks one and two, shipped — and the three commands that finish it

**20 October 2026.** What is in the repository against what the four-week
delivery plan promised, what still has to be run against production, and what
was deliberately left for week three.

## Week one, against the plan

| Promised | State |
| --- | --- |
| Campaigns, ad groups, keywords, ads and daily facts in our own database, with the resource name and the version we last saw | **done** (`ads/mirror.py`, `ads/sync.py`) |
| Structure every fifteen minutes, today hourly, nightly pass over the previous three days, manual refresh | **done**, three Cloud Scheduler jobs live and verified |
| External change detection: noticed, recorded as "made in Google Ads", never silently overwritten | **done**, and a deletion now counts as a change too |
| The connect flow in full, both paths, the first sync streaming in, a first look, and disconnecting with the permission deleted | **done** |
| Gate starts: seven days of clean sync on five internal accounts | **counted, not passed** — see below |

### The gate, honestly

`python -m ppcway.cli gate` counts it per account out of the sync runs we keep,
and prints the truth rather than a claim:

```
2 of the 5 accounts the gate asks for have 7 clean days.
It is running on 2 connected accounts. The gate is not passed.
```

It exits non-zero until the gate passes, so it can be wired into a check. The
same answer is at `GET /v1/internal/gate` behind the sync key. **What it needs
is three more Google Ads accounts to read, not more code.**

## Week two, against the plan

| Promised | State |
| --- | --- |
| Home against the mirror: results strip with the change against the previous period, "needs you", the activity list, the Visibility Score over time | **done** |
| Campaigns and campaign detail finished: per-row sparkline, Learning chip counting its days, all five tabs | **done** |
| Reports: thirty, ninety, year on year, the significance test, the definitions panel, sharing by an expiring link | **done** |
| The audit as a living tool: scheduled re-runs, score history with markers, "what changed since last time", per-page checks on every page the ads send people to | **done** |
| The post: the weekly summary every Monday, the alerts, "send the fix list to my web person" with a link that needs no login | **done in code**, needs the three commands below to run on the clock |

## What has to be run against production

Nothing here changes behaviour until the API is redeployed: the new endpoints,
the six new tables and columns, and the scheduler's three new doors all arrive
with it. Migrations run on container start, and all of them are additive, so a
rolling deploy is safe.

### 1. Deploy the API

```
cd backend
gcloud run deploy ppcway-api --source . \
  --region northamerica-northeast2 --project ppcway-509313
```

### 2. Deploy the web app

```
cd web
gcloud run deploy ppcway-web --source . \
  --region northamerica-northeast2 --project ppcway-509313
```

### 3. The three new scheduler jobs

The same key header the three sync jobs already use. Read it once from Secret
Manager into a shell variable rather than putting it on a command line:

```
KEY=$(gcloud secrets versions access latest --secret=ppcway-sync-key \
  --project=ppcway-509313)
API=https://ppcway-api-734687676224.northamerica-northeast2.run.app

# The Monday summary, 8am Toronto. Safe to fire twice: one row a week per account.
gcloud scheduler jobs create http ppcway-post-weekly \
  --location=northamerica-northeast2 --project=ppcway-509313 \
  --schedule="0 8 * * 1" --time-zone="America/Toronto" \
  --uri="$API/v1/internal/post" --http-method=POST \
  --update-headers="x-sync-key=$KEY" \
  --attempt-deadline=600s

# The alerts, every hour at half past. One letter per thing per day per business.
gcloud scheduler jobs create http ppcway-alerts \
  --location=northamerica-northeast2 --project=ppcway-509313 \
  --schedule="30 * * * *" --time-zone="America/Toronto" \
  --uri="$API/v1/internal/alerts" --http-method=POST \
  --update-headers="x-sync-key=$KEY" \
  --attempt-deadline=600s

# The nightly audit re-runs, 2am Toronto. Starts up to twenty and returns.
gcloud scheduler jobs create http ppcway-audit-nightly \
  --location=northamerica-northeast2 --project=ppcway-509313 \
  --schedule="0 2 * * *" --time-zone="America/Toronto" \
  --uri="$API/v1/internal/audit" --http-method=POST \
  --update-headers="x-sync-key=$KEY" \
  --attempt-deadline=900s
```

Check the secret's real name first with `gcloud secrets list --project=ppcway-509313`;
the sync jobs were created with the same value, so whatever they use is the one.

### 4. Prove each one, once

```
# What the Monday email will actually say, sent to nobody:
cd backend && python -m ppcway.cli post --dry

# Where the gate stands:
python -m ppcway.cli gate

# And each job, forced once rather than waited for:
gcloud scheduler jobs run ppcway-post-weekly --location=northamerica-northeast2
gcloud scheduler jobs run ppcway-alerts      --location=northamerica-northeast2
gcloud scheduler jobs run ppcway-audit-nightly --location=northamerica-northeast2
```

`post --dry` reads the production database only if it is pointed at it; run
locally it reads the local one and will say there is nothing to send.

## What week two deliberately did not do

**Per-keyword performance and search terms are still read live.** Mirroring them
means a keyword-day table and a search-term table, and the week-three
recommendation engine is what needs them — wasteful search terms and weak
keywords are two of its five proposal types. Building them now and again for
Otto would be building them twice. Campaign detail merges Google's reporting
over our own structure in the meantime, and says which half it could not read
when Google refuses. Recorded in
`docs/decisions/2026-10-20-every-screen-reads-the-mirror-first.md`.

**The monthly PDF.** The reports screen is the report, it shares by a link that
needs no login, and a PDF of it is a rendering job rather than a reporting one.
It was not in week two's list.

**Impression share is not in the mirror**, so "lost to budget" and "lost to
rank" on a campaign still come from the live read. It belongs with the
keyword-day work in week three.

## Two client decisions were due this Friday

Auto-apply defaults, and data residency. Neither blocks anything built so far —
PPCway still writes nothing to anybody's account, and every letter it sends says
so — but both block the approval flow in week four.
