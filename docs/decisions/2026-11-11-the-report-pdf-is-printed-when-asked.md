# The report PDF is printed when it is asked for

**11 November 2026.** At the owner's request: "make sure reports are up to date,
downloadable in PDF, and have an exquisite design".

## What was wrong

The Reports page answered with a 500. The report component, rendered on the
server, called a money formatter from a module marked for the browser, which
Next.js refuses at runtime. The shared report link used the same component and
broke the same way. The formatter now lives in `web/lib/money.ts`, safe on both
sides.

There was no PDF. `/reports/pdf` was the Figma "V2 · Report · PDF" frames with
made-up figures.

## How the PDF is made

- **Download PDF** asks `/v1/reports/pdf`. The API prints the web app's own A4
  page, `/reports/pdf?days=`, in the headless Chromium the audit already uses,
  and returns the bytes as an attachment.
- **Signed in as the person asking.** Their session token is set as the web
  app's session cookie, on that page's own address only, in a browser that is
  thrown away after printing. Requests from the page to any other address are
  refused. The printed page reads nothing its reader could not read
  themselves.
- **Never stored.** Every download is printed fresh, so the PDF has the same
  figures as the screen at that moment. A kept copy would be out of date by the
  next sync. The response says `no-store`.
- **One layout.** The A4 page is the only design of the PDF. A person can open
  it in the browser too. Chromium adds the footer with the business, the dates
  and "Page X of Y".

## What "up to date" means here

The report is built from the mirror when it is opened, never cached, and covers
whole days up to yesterday: today is still being counted by Google, and half a
day beside thirty whole ones reads as a collapse every morning. The screen says
when the figures were last read from Google Ads; the paper gives that time
exactly, in UTC, because a printed copy is read days later.

## What the report now holds

The period in one sentence, the three figures that matter (leads, cost per
lead, spend) each against the period before with a verdict in words, the
quieter figures, leads and spend day by day, where the leads came from, and
**every change PPCWay made inside the report's dates**, from the action log, in
the inbox's own words. Changes are dated by when they were made in Google Ads,
or failing that when they were approved; a list longer than 60 says how many it
left out.
