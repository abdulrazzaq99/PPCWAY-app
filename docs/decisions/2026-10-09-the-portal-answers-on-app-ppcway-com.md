# The portal answers on app.ppcway.com, behind a load balancer

**9 October 2026.** Decided with the owner.

## What was asked

Point `ppcway.com`, which sits on Cloudflare, at the portal.

## What was found first

`ppcway.com` is not parked. It serves the client's WordPress marketing site,
"PPCWAY — Supercharge Your Paid Acquisition", through Cloudflare's proxy. Moving
the apex would have taken that site off the air. There are no MX records, so no
email was at risk, but the website was.

## What was decided

The portal answers on **`app.ppcway.com`**. The apex and `www` keep serving the
marketing site, untouched. This is the ordinary split between a company's site
and its product, it satisfies Google's brand verification just as well, and
nothing had to go down to get it.

## How it is routed, and why not the simple way

Cloud Run maps custom domains in ten regions. `northamerica-northeast2` is not
one of them, and both services live there by the decision of 1 October, taken so
that Canadian merchants' data stays in Canada. Rather than reopen that, the
domain is served by a **global external Application Load Balancer** in front of
the Toronto service, which is Google's own recommendation for this case.

What exists now, all in project `ppcway-509313`:

- `ppcway-app-ip` — a reserved global address, **136.68.192.38**
- `ppcway-web-neg` — a serverless network endpoint group pointing at `ppcway-web`
  in `northamerica-northeast2`
- `ppcway-web-backend` — the backend service
- `ppcway-app-urlmap` → the backend; `ppcway-app-redirect` sends plain HTTP to HTTPS
- `ppcway-app-cert` — a Google-managed certificate for `app.ppcway.com`
- forwarding rules on :80 and :443

In Cloudflare, one record was added and nothing else was changed:

```
app   A   136.68.192.38   DNS only
```

The record is deliberately **not proxied**. Google has to see it pointing at its
own load balancer to validate the domain and issue the certificate. Once the
certificate is active the record can be proxied if Cloudflare's CDN is wanted,
with SSL mode set to Full (strict).

## What it costs

A global forwarding rule is billed whether or not anybody visits: roughly
$18–25 a month, plus traffic. The owner accepted that in preference to a
Cloudflare Worker rewriting the Host header, which is free but adds a hop we
would own and have to debug.

## What this unblocks

Brand verification for the Cloud project, which Google requires before Basic
access to the Ads API, and publishing the OAuth consent screen, without which
Google expires every merchant's connection after seven days. Both need a domain
we can prove we own, with a privacy policy and terms served from it.
