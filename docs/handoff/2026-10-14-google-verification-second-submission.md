# The second verification submission, after Google's rejection

Date: 14 October 2026.
Reviewer: the Third-Party Data Safety Team, replying to the verification request
submitted on 12 October.

Google did not question the scope itself. They asked for three things, and the
rejection is procedural rather than substantive:

1. a demo video that shows the consent screen with every scope expanded,
2. the scopes in the app matching the scopes in the Cloud Console exactly,
3. test credentials with no blockers, plus navigation instructions.

Nothing in the product has to change. What follows is what to check, what to
record, and what to send.

## 1. What this app actually asks Google for

There are two separate things, and only one of them is a scope grant.

**Sign in with Google** uses Google Identity Services in its ID-token form —
`google.accounts.id.initialize` in `web/components/auth/google-button.tsx`. It
returns a signed JWT saying who the person is. It is not an OAuth grant and it
requests no scopes, which is why nothing has to be declared for it.

**Connect Google Ads** is the OAuth grant, and it asks for exactly one scope:

```
https://www.googleapis.com/auth/adwords
```

It is built in `backend/src/ppcway/ads/oauth.py` (`ADWORDS_SCOPE`), with
`access_type=offline` and `prompt=consent` so that a refresh token comes back.
There is no second scope anywhere in the codebase, and there is no narrower
Google Ads scope to request: Google offers one scope for the Ads API, with no
read-only variant. Read-only is what this app does with it, not a permission it
can ask for.

### What the Cloud Console must say

The console has moved this. It is no longer under APIs & Services: it is its own
product, **Google Auth Platform**, and the scopes are the **Data Access** item
in its left sidebar.

    console.cloud.google.com/auth/scopes?project=ppcway-509313

Checked on 14 October, and it is already right:

| Section | What it holds | Correct? |
| --- | --- | --- |
| Non-sensitive | nothing | yes — the sign-in button grants no scopes |
| Sensitive | `.../auth/adwords` | yes — the one scope the app requests |
| Restricted | nothing | yes |

**Nothing is to be added here.** An earlier draft of this note said `openid`,
`userinfo.email` and `userinfo.profile` should be listed as well. They should
not: the sign-in button uses the ID-token flow, which asks for no scopes, so
declaring them would widen the request beyond what the app makes — the opposite
of the least privilege this rejection is about.

One scope requested, one scope declared, nothing spare. That is what "scope
matching" means in the rejection email, and this project already satisfies it.
A scope declared and not demonstrated is the usual cause of this rejection, and
we have none.

## 2. The test account

Made on 14 October, in production, with no blockers of any kind: no email
confirmation to pass, no phone number, no card, and no payment wall anywhere in
the product.

```
email:    google.reviewer@ppcway.com
password: in ~/.ppcway-review-account on the owner's machine
```

The password is deliberately not written in this file, which is in version
control. `cat ~/.ppcway-review-account` and paste it into the reply to Google.

The account signs in, lands on the dashboard, and shows the Connect Google Ads
banner. It has no Google Ads account attached on purpose: the reviewer connects
their own, which is the flow being reviewed.

## 3. The video

Unlisted on YouTube, no edits, no cuts, one take, screen and cursor visible. Six
or seven minutes is ample. It goes in **two** places when it is done: the
**Demo video** field at the foot of the Data Access page, and the reply to the
email. The reviewer reads the console; the thread is how they know to look. What matters is that every item below is legible on
screen — pause on each one rather than scrolling past it.

**Before recording:** sign out everywhere, clear the browser, and use a Google
account that has access to at least one Google Ads account so the picker has
something in it. Zoom the browser to 110–125% so the consent text is readable at
YouTube's compression.

| # | What to show | Say |
| --- | --- | --- |
| 1 | `https://app.ppcway.com` — the home page, then the privacy policy and terms links at the foot | "PPCway, a Google Ads assistant for small businesses. This is the production app at app.ppcway.com." |
| 2 | Sign in with the test credentials above, typed on camera | "Signing in with the test account provided to the review team." |
| 3 | The dashboard, with the empty cards and the Connect Google Ads banner | "No Google Ads account is connected, so there is nothing to show. This is what the scope is for." |
| 4 | Click **Connect Google Ads** | "This starts the OAuth flow." |
| 5 | Google's account chooser, then **the consent screen**. If a scope line is collapsed, click **Show all services** so the full text is visible. Hold still for five seconds. | "The consent screen requests one scope: see, edit, download and permanently delete your Google Ads accounts and data. That is `https://www.googleapis.com/auth/adwords`, the only scope this application requests." |
| 6 | Click **Continue** / **Allow** | "Granting access." |
| 7 | The account picker listing the Google Ads accounts the permission reaches; choose one | "The user chooses which single account PPCway may read." |
| 8 | The dashboard now filled: spend, leads, cost per lead | "The scope is used to read performance figures and show them in plain language." |
| 9 | **Campaigns**, then open one campaign: keywords with Quality Score, search terms, ads with their policy status | "Each of these numbers comes from the Google Ads API through that scope. This is the product's entire purpose: a small business owner who cannot read the Google Ads interface can read this." |
| 10 | **Settings** → the Google Ads card → **Disconnect** → confirm | "The user can revoke at any time, from inside the product. The stored refresh token is destroyed and we stop reading immediately." |
| 11 | Back on the dashboard: the empty state again | "With the permission withdrawn, the data is gone from the product." |

Two things the reviewer is specifically checking, so do not skip them: the
consent screen **fully expanded**, and the connection being **revocable**.

## 4. The reply to send

Reply directly to the rejection email, in the same thread, with the video link
and the credentials filled in.

> Hello,
>
> Thank you for the review. A new demonstration video is below, recorded against
> the production app, showing the consent screen with the scope fully expanded.
>
> **Video:** `[unlisted YouTube link]`
>
> **Scope requested:** `https://www.googleapis.com/auth/adwords` — this is the
> only scope our application requests. It matches the Data access configuration
> in our Cloud project exactly. Google publishes no read-only variant of the
> Google Ads API scope, so no narrower permission is available for the feature.
>
> **Why it is needed:** PPCway is a Google Ads assistant for small businesses.
> With the owner's permission it reads their Google Ads account — campaigns,
> spend, conversions, search terms, Quality Score and ad policy status — and
> explains the results in plain language, so an owner who cannot read the Google
> Ads interface can still see what their advertising costs and what it returns.
> The account the user chooses is the only one read. Users can disconnect from
> inside the product at any time, which revokes the grant and destroys the
> stored token.
>
> **Test credentials** (no email confirmation, no phone verification, no card,
> no paywall):
>
> - URL: `https://app.ppcway.com/login`
> - Email: `google.reviewer@ppcway.com`
> - Password: `[paste from ~/.ppcway-review-account]`
>
> **Step-by-step navigation:**
>
> 1. Open `https://app.ppcway.com/login` and sign in with the credentials above.
> 2. You arrive at the dashboard. It is empty because no Google Ads account is
>    connected.
> 3. Click **Connect Google Ads** in the banner at the top.
> 4. Sign in with a Google account that has access to a Google Ads account and
>    grant the permission on the consent screen.
> 5. Choose which Google Ads account PPCway may read.
> 6. The dashboard now shows that account's spend, leads and cost per lead.
>    **Campaigns** shows each campaign; opening one shows its keywords, search
>    terms and ads.
> 7. To revoke: **Settings** → Google Ads → **Disconnect**. The permission ends
>    and the stored token is destroyed.
>
> The app's publishing status remains In Production, and the scope is not newly
> deployed: it has been part of the production app throughout, used only by the
> users who have explicitly connected an account.
>
> Please let me know if anything further is needed.

## 5. One thing the console flagged while we were in there

The Project Checkup on the Google Auth Platform overview says:

> **Use secure flows.** Your app is not configured to use secure OAuth flows and
> may be vulnerable to impersonation. The following production Web OAuth clients
> are allowing loopback IP redirects: PPCWay web.

It is true and it is ours. The production client carries the live redirect

    https://app.ppcway.com/ads/callback

and, beside it, the localhost ones this project uses in development:

    http://localhost:3001/ads/callback
    http://localhost:3001/api/oauth/google/callback

A loopback redirect on a production client is a known impersonation path:
anything running on the developer's machine can receive an authorisation code
meant for the app. It is not what Google rejected us for, and it does not block
the reply — but it is the sort of thing a reviewer looking at a security warning
may ask about, and it should not be true of a production client anyway.

**The fix, and the order matters.** Make a second OAuth client for development
first, then clean the production one:

1. Google Auth Platform → **Clients** → **Create client** → Web application,
   named `PPCWay web (local)`. Give it the two localhost redirect URIs above.
2. Put its client id and secret in `web/.env` for local development. It sits in
   the same project, so it shares this consent screen and its branding.
3. Only then: open **PPCWay web** and remove the two `http://localhost:3001`
   redirect URIs, leaving `https://app.ppcway.com/ads/callback` alone.

**Do not touch the production redirect URI.** Changing or removing
`https://app.ppcway.com/ads/callback` breaks Connect Google Ads for every
merchant with `redirect_uri_mismatch`, which this project has already lost an
afternoon to once.

## 6. Before sending, check these four

- [ ] The Data access list in the Console is exactly the four scopes above.
- [ ] The video shows the consent screen expanded and readable.
- [ ] The test account signs in — try it yourself in a private window first.
- [ ] The password gate on the site stays **off** until verification clears. It
      was removed on 14 October for exactly this reason; switching it back on
      would block the reviewer at the door and fail the submission a second time.

## What this does not change

The 100-user lifetime cap stands until verification clears, and every Google
account that connects spends one of those permanently — including the
reviewer's. Four are used so far. Sign-ups with an email and a password do not
count against it; only the Google Ads connection does.
