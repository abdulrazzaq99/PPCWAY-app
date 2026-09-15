# The merchant console, redesigned: Slate and Emerald

**Status:** design, awaiting review. **Source of truth for the look:** the Figma
file `PPCWay`, twelve frames, read on 2026-09-09. **Scope rule:** every screen
the backend can stand behind is built; nothing the backend cannot feed is
invented. Where the design shows a panel the PoC has no data for, the panel is
left out of the live world rather than filled with a plausible number.

## 1. What changes and what does not

The console keeps its data flows, its API client, its merchant context, its
two worlds (demonstration and live), and its 126 tests, which are extended
rather than replaced. What changes is the shell, the palette, and how each
screen is composed.

| Today | After |
|:--|:--|
| Top tabs: Connect, Set up, Preview, Approvals, Activity, Controls | Left sidebar: Home, Activity, Approvals, Campaigns, Settings; an Advanced view toggle; Help and support |
| Header badge for the world, business picker, Add a business | The same three, moved into the sidebar's business block and the top bar |
| Each page opens with a panel | Each page opens with a written headline: a sentence before a number, a number before a chart |
| Connect and Set up as tabs | A five-step onboarding rail, steps 2 to 5, reached from sign-up and from "Add a business" |
| Controls page for the simulator | A "Simulator" section at the foot of Settings, shown only in the simulated world |

## 2. Design foundations, from the style tile

Colour, named as the tile names them. These replace the current values of the
existing tokens; no new token names are introduced where an existing one fits.

| Tile | Hex | Existing token it becomes |
|:--|:--|:--|
| Canvas | `#F4F6F8` | `--background` |
| Shell | `#EAEEF2` | `--surface-sunken` (the tinted shell a panel sits inside) |
| Panel | `#FFFFFF` | `--card`, `--surface` |
| Ink | `#16202A` | `--foreground` |
| Muted | `#5C6B7A` | `--muted-foreground` |
| Line | `#DDE3EA` | `--border` |
| Emerald | `#12855D` | `--brand` (hover one step darker) |
| Amber | `#B7791F` | `--warn` |
| Red | `#B93838` | `--danger` |

Type, Geist Sans throughout, Geist Mono for figures where the design tabulates
them: headline sentence 32 semibold (the tile's "You spent $1,240" line), big
figure 44 semibold, panel title 15 semibold, body 15 regular, meta 13 regular
muted.

Shape: shell radius 20, panel radius 14, controls 10, pills only for buttons
and status tags. No shadows, no gradients, no uppercase labels, no decorative
icons drawn by hand. Lists separate with hairlines, never boxes. Never three
equal cards in a row. Panels sit inside a tinted shell on the grey canvas.

Words: plain and specific, no Google Ads jargon in the default view. Buttons
say what happens: Approve, Skip this, Undo, Approve and launch. Anything
waiting on the merchant is amber and sits at the top. Red is only for money
and account problems. A refusal from a limit is neutral, because it is the
product working.

Existing primitives that survive with restyling: `Button`, `Panel`, `Pill`,
`Notice`, `Field`, `Input`, `Select`, `Table`, `Dialog`, `Skeleton`, the
domain components `status-pill`, `value-change`, `ad-preview`,
`validation-report`, `revert-dialog`, `step-rail`, `link-ledger`. New
primitives: `Shell` (the tinted wrapper around a panel), `Headline` (sentence
plus subline), `Sidebar`, `TopBar`, `Toggle`, `BarChart` (a small inline SVG
bar chart, no library), `HairlineList`.

## 3. The shell

Sidebar, 232 wide, white panel on the canvas: wordmark; the business block
(name, a second line, and the picker); navigation; at the foot, the Advanced
view toggle and Help and support. The business block's second line is the
service area when the profile has one, else the merchant's country. The
"Approvals" item carries a count of proposals waiting. "Add a business" moves
into the business picker's menu as its last entry, keeping the `?new=1`
contract already built.

Top bar, per page: a breadcrumb sentence in muted ("Alpha Plumbing, activity"),
a date-range control on the right where the page has a range (Home, Activity,
Advanced view), and the avatar initials. The world badge (`Mock data` /
`Live: host`) stays as the small pill it is, placed left of the avatar, because
the honesty it carries is not negotiable.

Mobile: the sidebar becomes a bottom bar of five icons, as the current
console already does at 390 wide. The Blueprint's §4.7 "mobile first" holds.

Advanced view: a single boolean in the merchant context, remembered per
browser. On, Home shows the campaign table (§4.5) in place of the
sentence-first layout, and the top bar breadcrumb says "advanced view".

## 4. Screens

Each screen lists: the headline sentence and how it is computed, the panels,
the data each panel reads, and the states (loading, empty, the API not
answering, and refusals). Every refusal keeps today's shape: the check that
refused, its own words, and one sentence for the merchant.

### 4.1 Home (`/`)

Headline: **"You spent {spend} and got {calls} {goal noun}."** from
`getMetrics` over the selected range; the goal noun follows the profile's
primary goal (calls, enquiries, sales). Subline: cost per result, its change
against the previous equal-length range, and one of three sentences: "Your
budget is on pace and nothing needs fixing." / "One thing is waiting for you."
/ "Nothing has run yet." Before any metrics exist the headline is "Nothing has
run yet." and the subline points at the step that is outstanding.

Left column: the cost-per-result panel (big figure, change line, a bar chart of
weekly cost per result with the current week emphasised, "Week of …" and "This
week, N so far" on the baseline; spend and results as a two-row figure list on
the right); "What PPCWay did this week" (the three most recent actions as
sentences from `narrative_text` or `rationale`, with Undo where the action
offers a revert, and "See all activity"). Right column: the first waiting
proposal as an amber card with Approve and Skip this (absent when none);
"Your campaigns" (name and status pill from `merchant.campaigns`).

Left out: "What people searched to find you". No route serves search terms.
The panel returns when one exists.

### 4.2 Campaigns (`/campaigns`, today's Preview)

Headline: **"Here's the campaign we built for you."** Subline as designed.
Left: "In one sentence" (built from the preview's plan: radius, themes, daily
budget, final URL, goal); "What people will search to find you" (themes as
pill groups); "Your ad, as people will see it" (`ad-preview`, plus the
rotation sentence with the real count); "Searches we'll never pay for"
(negatives). Right: "Before you launch" (account linked, payment method,
call tracking, each Done / Needs you from the link and tracking views) with
"Approve and launch", and the refusal, in the check's words, when the launch
is refused; "Budget" with the daily figure, the monthly sentence, the daily
ceiling from the limits, and Change budget (today's budget lever).
"Edit any part / Edit keywords / Edit wording" are shown only where a route
exists to act on them; none does today, so they are left out.

Before onboarding has run, this page shows the onboarding rail (§5) instead.

### 4.3 Approvals (`/approvals`)

Headline: **"{N} changes are waiting for your OK."**, singular and zero forms
("Nothing is waiting for you."). Subline as designed with the real expiry
window from the approval expiry setting. Left: one amber card per waiting
proposal: the rationale as its title sentence, the before/after row
(`value-change`), "Expires in N days", Approve and Skip this; then "Decided
this month" from actions with a terminal status in the current month, each with
its decision and date. Right: "How approvals work" (static copy, from the
design); "Your setting" (the autonomy level in the design's words, with
Change setting, which opens the same control Settings uses).

### 4.4 Activity (`/activity`)

Headline: **"Everything PPCWay did, in plain words."** Filters as designed:
Everything, Applied, Waiting for you, Undone, Held by your limits, mapping to
action statuses. The list groups by Today, Yesterday, Earlier this week, then
by date, each row a sentence with its meta line ("Applied 9:12 am", "Held by
your limits, 6:00 am", "Undone by you, Sunday") and Undo or Review where the
action offers it. Right: "This month" counts by status; "Your limits" with
the four figures the design shows and Change limits.

### 4.5 Advanced view (Home with the toggle on)

Headline: **"Search campaigns, last 30 days."** Tabs: Campaigns, Ad groups,
Keywords, Search terms. Only "Campaigns" is served today: a table of
`merchant.campaigns` with status and daily budget, and the merchant-level
metrics total row. Per-campaign impressions, clicks and cost appear only if
the metrics route can return them by campaign; the plan checks this and the
table shows the columns it can. The other three tabs are rendered disabled
with "not in this proof of concept". "New campaign" is left out.

### 4.6 Settings (`/settings`, today's autonomy, budget, limits, and Connect)

Headline: **"You decide what PPCWay may change."** Left: "How much can PPCWay
do on its own?" as three rows (Tell me, I'll decide / Ask me first / Just get
on with it) mapped to ALERTS_ONLY, APPROVE_FIRST, FULL_AUTO with "In use" and
"Switch to this"; the third row is enabled, because the backend supports
FULL_AUTO, and its copy says so. "Limits it must never cross": the four
figures plus the rest of the guardrail limits in a hairline list, with Change
limits, which today is read-only: the API has no route to write limits, so the
button is left out and the list says the version in force.

Right: "Your Google Ads account", the current Connect page's ledger and linked
account panel, restyled, with "Sign in to Google again". Left out: "Your
plan", "Who can see this account".

Foot, simulated world only: **Simulator**, the controls page's buttons
(advance the day, seed, billing approved, a test conversion, inject a fault)
with the world clock, each labelled as the stand-in it is, as they are today.

### 4.7 Alerts

Not built. The design's alerts screen needs notifications and email
recipients the PoC has neither of. The two facts it would show that do exist,
a billing hold and an ad turned down, already surface on Campaigns and
Activity.

## 5. Onboarding (`/onboarding/{step}`)

The rail reads "About 15 minutes, start to live" with five steps. Step 1,
"Account and plan", is not in the PoC (no login, no billing) and is omitted;
the rail shows steps 2 to 5 numbered as designed so the client sees where it
fits, with step 1 rendered ticked and labelled "not in this proof of concept".

- **Step 2, Connect Google Ads.** The sign-up form (trade, website, country,
  currency, time zone, limits) followed by "Continue with Google", then the
  three-row ledger (Linked to PPCWay, Payment method on Google, Active in
  {currency}) with Done / Needs you, and "Add payment method on Google", which
  in the simulated world is the billing stand-in and says so.
- **Step 3, Your business.** Today's Set up: website, service radius, goal as
  radio cards, monthly budget with the daily sentence. The right card shows
  "What we found on your site" from the crawl summary.
- **Step 4, Count your calls.** The tracking view: the three rows as designed,
  Done / Needs you from `tracking.verified`; "Add the tag for me" is left out,
  the row says what the merchant does instead, and the simulated world's
  "verify a test conversion" stand-in sits where it does today.
- **Step 5, Review and launch.** The Campaigns screen (§4.2) inside the rail.

"Save and finish later" returns to Home; every step is a plain route, so a
merchant can leave and return.

## 6. States, errors, refusals

Loading: skeletons in the shape of the panel. Empty: the sentence the design
would show if nothing had happened, never a blank panel. API not answering:
today's gate, restyled. Refusals: today's `Verdict` and `refusal-surfaces`
behaviour, restyled; a refusal from a limit is neutral, a money or account
problem is red, anything waiting on the merchant is amber at the top.

## 7. Testing

The existing suites keep passing throughout. Each screen gains tests for: the
headline sentence in each of its states; every filter; every button that acts
(calls the same API method the current page calls); the panels left out in
the live world being absent. The contract checks (`check:contract`,
`check:shapes`, `check:oauth`, `check:categories`, `check:contrast`) remain
green; the palette change is checked by `check:contrast` against the tile's
values. Two screenshots per screen, mock and live, are captured into
`docs/screenshots/redesign/` at the end for the client report.

## 8. Order of work

1. Tokens and primitives: palette, `Shell`, `Headline`, `Toggle`, `BarChart`,
   `HairlineList`; the contrast check updated.
2. The shell: sidebar, top bar, routes, Advanced view state, mobile bar.
   Old pages keep working under the new shell at their new routes.
3. Home, then Activity, then Approvals, then Campaigns, then Settings with
   the Simulator foot, then Onboarding, then Advanced view.
4. Remove the old tab pages and the Controls route; redirect old paths.
5. Screenshots; README section.

Each step is a commit reviewable locally before the next begins.

## 9. Not in this design

Login, plans and billing for PPCWay itself, team members and invitations,
alerts and email, search terms, ad-group and keyword tables, one-click tag
installation, editing keywords or ad wording from the console, writing
guardrail limits from the console. Each is listed on the screen that would
hold it only where the design shows it and the omission would otherwise
read as a bug.
