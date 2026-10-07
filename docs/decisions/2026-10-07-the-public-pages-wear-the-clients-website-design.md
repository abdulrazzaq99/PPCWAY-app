# The public pages wear the client's website design; the app keeps Version 2

Date: 7 October 2026. Decided by the owner, after the client sent the handoff
package `ppcway-website-handoff` (a 66-page static marketing site, its tokens, and
a free-audit tool page) and asked for the audit to be built "along these lines".

What the client's package settles:

- Brand blue `#2F5BEA`, warm ground `#F6F4F0`, night panels `#120E24`, Outfit for
  headings over DM Sans for everything else, 22px card radii.
- The audit tool reads as: score out of 100 in a ring, a verdict in three words,
  one list of checks badged pass, warn, fail or information, four checks locked
  behind the merchant's own Google Ads account, and a table saying where each
  number came from.

So:

1. Everything a stranger sees — the landing page and the whole audit flow — wears
   that design. The signed-in app keeps the Figma Version 2 tokens.
2. The palette lives as a `.site` class in `globals.css` that redefines the same
   variable names. Components did not have to change to follow it, and the two
   designs can sit in one app until the app moves across as well.
3. The report follows the client's shape with our own data. Their page fills it
   with sample numbers from a hash of the business name; ours fills it from a real
   crawl, a real speed test and the real listing, which is the whole difference
   between a demonstration and an audit.
4. Our sticky bar stays, though their page has no equivalent: it is the one thing
   that follows a reader down a long report and asks.
5. The landing page takes the palette and the typefaces but keeps our layout. The
   client's package already contains a finished marketing site, so redrawing ours
   section by section would be work thrown away if theirs is adopted.

Still open, for the owner and the client to settle:

- Whether their 66-page marketing site replaces ours entirely, with our app living
  at `app.ppcway.com` as their handoff assumes.
- Their "Otto" owl and its wording: it is their AI persona, and nothing in our app
  uses that name yet.
- The four locked checks are named in their words (wasted spend, Quality Score,
  lost impression share, disapprovals). We can only deliver them once the client's
  Google Ads API access reaches production level.

What this costs if wrong: the palette is one class and the report is one component,
so going back to Version 2 for the public pages is a small change, not a rebuild.
