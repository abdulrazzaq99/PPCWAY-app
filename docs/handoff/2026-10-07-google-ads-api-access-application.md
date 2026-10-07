# Applying for Google Ads API access

**For the owner of the developer token to send. Prepared 7 October 2026.**

Reading a merchant's own Google Ads account is the half of the audit the public
checks cannot do: wasted spend on search terms, Quality Score, budget lost to
impression share, and disapproved ads. The code for all four is written, tested
and deployed. One thing stands between it and real numbers.

## What Google told us

Connecting works. The permission is stored, and Google lists the accounts it
reaches. Reading one is refused, in Google's own words:

```
CLOUD_PROJECT_NOT_APPROVED_FOR_PRODUCTION
The Google Cloud project is only approved for use with test accounts.
To access non-test accounts, apply for Explorer/Basic access.
```

A test-tier developer token may list accounts and read *test* accounts only.
Byte9 (258-058-6343) is a live account, so it is refused. No arrangement of
permissions, managers or scopes changes this; it is an application.

## Who applies, and where

The owner of the developer token, from the **Google Ads manager account that
holds it**: **Tools → API Center**, or <https://ads.google.com/aw/apicenter>.
The API Center is only visible on a manager (MCC) account.

If the client would rather not expose their own token, the alternative is a
developer token under a PPCWay-owned manager account. Same application, and it
keeps the two businesses' Google access apart.

## What the application needs

| Field | What to put |
|---|---|
| Google Cloud project id | `ppcway-509313` |
| Google Cloud project number | `734687676224` |
| Company website | the PPCWay site |
| Contact email | the address that should receive Google's questions |
| API access level | **Basic** (Explorer if a faster approval is wanted first) |
| Tool type | internal tool used on behalf of our own clients |

### The description to paste

> PPCWay is an onboarding and optimisation service for small businesses that
> advertise on Google. A business owner connects their own Google Ads account
> with OAuth, read only, and we produce an audit of it alongside checks of their
> website and Google Business Profile.
>
> We use the API to read, not to write: campaign and budget structure, search
> term reports, keyword Quality Score, impression share lost to budget and to
> rank, and ad policy status. Each account is read on the owner's request and
> only after they have granted access; permissions are encrypted at rest and the
> owner can disconnect at any time. Reports are shown to that owner alone and
> are not resold or aggregated.
>
> No campaign is created or changed without the owner's explicit approval of the
> specific change, recorded before it is applied.

### The two levels

- **Explorer** — reaches live accounts at 2,880 operations a day and excludes
  planning tools. Enough for all four checks above. Usually the faster approval.
- **Basic** — 15,000 operations a day and includes Keyword Planner, which the
  report's "what this is worth a month" estimate needs. Expect brand verification.

Start with Basic; take Explorer if Google offers it as an interim.

## Two things that also need doing

1. **Publish the OAuth consent screen.** While it is in Testing, Google expires
   every refresh token after seven days, so a merchant who connects on Monday is
   disconnected the next Monday. Publishing requires verification: a privacy
   policy and terms page on a verified domain, which is the `ppcway.com` work.
   Until then, each tester must be listed under **Audience → Test users**.

2. **The scope is sensitive.** `https://www.googleapis.com/auth/adwords` is
   reviewed by Google when the app is published. The description above is the
   same one that review will ask for, so keeping the two consistent saves a round.

## What works today, without any of this

Test accounts. The proof of concept's test manager and its accounts can be read
now, which exercises the whole path: connect, choose an account, run the five
queries, draw the four cards. Every figure comes back zero, because a test
account never serves an ad. It proves the plumbing, not the numbers.
