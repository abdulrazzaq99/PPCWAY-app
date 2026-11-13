# The merchant's website reports to PPCWay

13 November 2026. Asked for by the client, through the owner: integrate with the
merchant's own website "to get the conversions and statistics directly", with
"some kind of a plugin". The owner said "please build it" to the proposal: a
script that works on any site, the leads it finds, jobs sent back to Google Ads,
and a WordPress plugin.

Blueprint §13.5 calls conversion tracking the single point of failure. This is
the answer to it that does not depend on a tag the merchant pasted correctly.

## What changed

- **A script for any website** (`web/public/t.js`, served at `/t.js`, one tag
  with the business's public key). It reports page views (with where the visit
  came from, including Google's click ids) and leads: forms sent, phone numbers
  and email addresses tapped. Contact Form 7, WPForms, Elementor and Gravity
  Forms are counted on their own "sent" signal, so a refused form is not a lead.
- **A public endpoint** behind it (`/api/collect` on the web app, then
  `POST /v1/site/collect`). It trusts nothing: unknown keys and robots are
  dropped silently, a business takes at most 60 leads an hour, one sender 10,
  one visit 5, and password, card and hidden fields are never kept.
- **The Website screen** (`/website`): visits, where they came from, the pages
  people arrive on, and the leads, each of which the merchant can mark as a job
  (with its value), not a job, or spam.
- **Jobs go back to Google Ads** as offline click conversions
  (`ConversionUploadService.UploadClickConversions`) against the click that
  brought the visitor. Off until somebody who may approve switches it on, which
  creates the "Jobs from PPCWay leads" conversion action (Converted lead, 90-day
  window, primary). Sent through the gateway behind the same switches as every
  write (`gateway.create.upload_alone`); what Google is not ready for waits for
  the hourly pass, `POST /v1/internal/site`.
- **Google's conversions can be fired by the script** for a form or a call, if
  the merchant chooses one of their website conversion actions. Off by default,
  because a site that already has Google's tag would count twice.
- **A WordPress plugin** (`integrations/wordpress/ppcway`, zipped to
  `web/public/downloads/ppcway-wordpress.zip` by `build.sh`): a settings page
  for the key, the script in every page's head, the merchant's own signed-in
  visits left out, and an option to wait for cookie consent.

## Decisions made with it

- **Lead details are kept** (what the form said, name, email, phone), because a
  lead list without them is not one the merchant can act on. Kept 13 months,
  then deleted by the hourly pass. Only that business can read them.
- **Global Privacy Control is honoured**: the lead is counted, what was typed is
  not kept. Sites that need consent first set `data-consent="wait"`.
- **The plugin holds no Google access.** One door to Google stays one door.
- **Enhanced conversions for leads** (hashed email and phone, no click needed)
  are not built: they need the merchant to accept Google's customer data terms
  first. Jobs without a Google ad click say so instead of failing.

## Still to do

- The Cloud Scheduler job for `/v1/internal/site` (hourly) has to be created
  with the deploy.
- A Shopify app, if the client's merchants include shops.
- Server-side form hooks in the WordPress plugin, for visitors whose browser
  blocks the script.
- Figma frames for the Website screen.
