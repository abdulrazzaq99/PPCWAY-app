# The internal console has its own dark look

**Date:** 4 November 2026
**Status:** built and measured, not yet committed or deployed
**Decided by:** the owner asked for "a new look" after five rounds; this is that look
**Departs from:** CLAUDE.md's "screens must match Version 2, blue brand", for `/admin` only

## What changed

PPCWay's internal panel (`/admin`, staff only) no longer wears the merchant
app's Version 2 palette. It is a dark operations console of its own:

- true neutral darks (`#171719` ground, panels a step darker), no navy, no slate;
- one accent, the brand's own blue for dark grounds (`#8faeff`, the "PP" of the
  white wordmark), used on data and on the one selection mark;
- Public Sans for words, IBM Plex Mono for every figure, loaded only on `/admin`;
- a labelled sidebar and a 64px top bar on one ground, divided by 1px rules.

Every token lives under `.adm` in `web/app/globals.css`, so nothing outside the
console changes. The merchant app and the public site are untouched.

## Why the console, and only the console

1. **The owner rejected the panel five times** for reading as "simple html css"
   and "nowhere near an admin panel". Four rounds polished the merchant palette;
   the fifth request was for a new look, not more polish.
2. **A different world is a safety property.** The worst failure this panel can
   have is a member of staff forgetting they are inside somebody else's
   business. A merchant's dashboard is light; the console is not, so the two
   cannot be mistaken for each other at a glance.
3. **It is a monitoring tool.** Syncs every 15 minutes, failures, quota and the
   write switch are read the way a monitoring screen is read. The tasteskill
   app study's dark "data terminal" style was dealt for exactly that use.

## What it shows that it did not

- **The one door to Google** is on every screen: a chip in the top bar saying
  whether PPCWay may write to Google Ads, linking to the switch.
- **A real merchant screen.** `/admin?view=merchant&id=` was a Figma mockup with
  another business's sample data; it now reads the merchant, its changes, who
  opened it and its quota, and can stop writes for that account alone.
- **What became of Otto's proposals**, per day, by where each one stands now.

## Backend additions, all read-only

- `GET /v1/admin/overview` carries `series`: proposals per day (per hour for
  "today") by current status, from the same rows the figures count.
- `GET /v1/admin/staff` and `GET /v1/admin/merchants/{id}/who-looked` name
  people by email as well as by account id.
- Sentences say "in the last 7 days" rather than "in the last 7d", and the
  "today" window no longer reads "in the last today".

## What stays as it was

The admin screens still drawn from Figma mockups (`reviews`, `runbook`, `audit`,
`rules`, AI quality, the change log) keep the old shell. They are not in the
console's navigation. Figma's admin frames no longer match the code; the
console was designed in the browser against the tasteskill inspector, and the
frames can be redrawn from it if the owner wants them.
