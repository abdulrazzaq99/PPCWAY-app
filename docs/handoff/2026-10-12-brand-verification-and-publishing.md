# Unblocking Basic access and publishing the consent screen

**12 October 2026.** Both were waiting on a domain. The domain is live, the two
pages Google asks for are written and public, and the logo exists. What remains
is form filling, in this order.

## Step 0 — the support address: done, with a caveat

Google emails this address during verification, and a bouncing one fails the
review. It does **not** have to be on the domain; it has to be read.

`abdulrazzaq.devv@gmail.com` is the address on the two pages and the one to put
in the branding form. Changing it in the Console after verification can trigger
a fresh review, so it is worth keeping.

`support@ppcway.com` is half built. Email Routing is active on the zone, and MX,
SPF and DKIM are live and visible from outside. What is missing is a verified
destination address, which is an **account-scoped** setting, and the Cloudflare
membership here is scoped to the `ppcway.com` zone alone. Only the owner of the
"CanadaHosting41" account can add the destination or grant an account role.
Nothing else depends on it.

## Step 1 — prove we own ppcway.com (10 minutes, once)

The branding form will not accept `ppcway.com` as an authorised domain until
Google has seen it verified by the same Google account.

1. <https://search.google.com/search-console>, add a **Domain** property for
   `ppcway.com`.
2. It gives a TXT record. In Cloudflare → DNS → Add record: type **TXT**, name
   **@**, content the value Google gives.
3. Back in Search Console, **Verify**.

## Step 2 — branding (10 minutes)

Google Cloud Console → **APIs & Services → OAuth consent screen → Branding**,
project `ppcway-509313`. Paste exactly:

| Field | Value |
|---|---|
| App name | `PPCWay` |
| User support email | `abdulrazzaq.devv@gmail.com` |
| App logo | upload `web/public/logo-120.png` |
| Application home page | `https://app.ppcway.com` |
| Application privacy policy | `https://app.ppcway.com/privacy` |
| Application terms of service | `https://app.ppcway.com/terms` |
| Authorised domain | `ppcway.com` |
| Developer contact | the address that should receive Google's questions |

**Save**, then click **Verify Branding**.

## Step 3 — apply for Basic access (2 minutes)

Once branding verification completes: <https://console.cloud.google.com/google/ads-apis/overview?project=ppcway-509313>
→ **Upgrade access level** → next level should read **Basic** with no warning
about brand verification → **Apply for access**. Google reviews this
automatically, within minutes.

That lifts us from 2,880 operations a day to 15,000, and unlocks Keyword
Planner, which is what the report's "what this is worth a month" figure needs.

## Step 4 — publish the consent screen

Google Cloud Console → **OAuth consent screen → Audience** → **Publish app**.

This is the one with a real wait. `https://www.googleapis.com/auth/adwords` is a
sensitive scope, so publishing triggers a review: Google wants the justification
below, and usually an unlisted YouTube video showing the consent screen, what a
merchant agrees to, and what we do with the data afterwards. Allow one to several
weeks, and answer their emails the same day — they close quiet applications.

### Scope justification to paste

> PPCWay requests the adwords scope so that a small business owner can connect
> their own Google Ads account and receive an audit of it. We read only:
> campaign and budget structure, search term reports, keyword Quality Score,
> impression share lost to budget and to rank, and ad policy status. The data is
> shown to that owner alone, in their own report. It is not sold, not pooled
> across advertisers, and not used to train models.
>
> Access is granted by the account owner through Google's own consent screen and
> can be revoked by them at any time, from their Google account or from ours.
> Permissions are encrypted at rest. No campaign is created or modified without
> the owner's explicit approval of the specific change, which is recorded before
> it is applied.

### Why it matters

Until the app is published, Google expires every merchant's refresh token after
**seven days**. A business that connects on Monday is silently disconnected the
next Monday. That is survivable in testing and fatal at launch.

## What is already done

- `https://app.ppcway.com` serves the portal, with a Google-managed certificate.
- `https://app.ppcway.com/privacy` — written against what the code actually does,
  including the Limited Use disclosure Google requires for this scope.
- `https://app.ppcway.com/terms`.
- `web/public/logo.png` (512px) and `logo-120.png` for the branding upload.
- Both pages are linked from the site footer, and are reachable without signing in,
  which the reviewer checks.
