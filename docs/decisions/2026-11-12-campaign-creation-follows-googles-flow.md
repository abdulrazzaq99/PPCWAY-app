# Campaign creation follows Google Ads' own flow

12 November 2026. Asked for by the client, through the owner: "implement the same
flow for the campaign creation as it is in the google ads campaign, like every
single thing that is in that flow, using every available API in the google ads",
and then "exactly replicated at all costs, use every API needed".

## What changed

- **Step 1 is Google's "New campaign" page**: objective, the account's conversion
  goals (pre-selected, removable, addable), campaign type, the ways to reach the
  goal, the name. It makes a draft (`CampaignDraft.plan` with `"v": 2`).
- **Then Google's steps for the type**, with the progress menu on the left and
  autosave. Search: Bidding, Campaign settings, AI Max, Keyword and asset
  generation, Keywords and ads, Budget, Review. Performance Max: Bidding,
  Campaign settings, Asset group, Budget, Review.
- **The model is `builder/spec.py`**, setting for setting; **the request is
  `builder/ops.py`**, in the creation order Google's guides give, still one
  all-or-nothing `GoogleAdsService.Mutate` checked first with `validateOnly`.
- **The review step asks Google to check the whole campaign** (validate only,
  nothing created) and lists every error Google returns, each filed against the
  step it belongs to. The gateway now keeps all of Google's errors, not the first.
- **Images go into the account's asset library when they are added**, as Google's
  screens do, through the gateway (`gateway/assets.py`); the launch links them.
  Forty images inside the launch request would have made it many megabytes.
- **New-customer bidding is set after the campaign exists**, through `GoalService`
  and `CampaignGoalConfigService`, which Google keeps out of the mutate request.
- **Reads for the screens** (`ads/setup.py`): conversion goals, audience segments,
  brands, Google's budget recommendation and Keyword Planner's forecast, shared
  budgets and negative lists, Merchant Center links, image URLs.

## Google's defaults, not PPCWay's

Where Google pre-selects something, so does PPCWay: AI Max on for a new Search
campaign, search partners and the Display Network ticked, "Presence or interest"
for locations, account goals, broad match for keywords. Each is visible and can be
changed. This reverses the first builder's tighter defaults (Google Search only,
phrase match, presence only), because the client asked for Google's flow.

## Left out on purpose, because Google refuses them now

A language on a Search campaign (refused since late September 2026; the first
builder also stops sending it), the campaign-level broad match setting (since 3
August 2026), Enhanced CPC, call-only ads, new Smart campaigns through the API
(since 23 September 2026), new Dynamic Search Ads. Video and Smart are shown on
the type step and explained: the API cannot create them.

## Every type Google lets an app create

Search, Performance Max, Demand Gen, Display, Shopping and App are built, each on
Google's own steps for it (Demand Gen, Display, Shopping and App ask for the budget
on "Bidding and budget", as Google does). Video and Smart are shown on step 1 and
explained, because the API cannot create them.

Not offered yet, each for a stated reason on the screen: AI Max URL inclusions
(page feeds), location assets (they need a linked Google Business Profile),
Demand Gen 9:16 images and product feeds, Display Viewable CPM, Shopping product
group splits, App custom store listings, and lead form custom questions.

## Conversions, as Google's Conversions screens set them up

Asked for the same evening ("add the conversion same as it is in the Google ads
account"). `/conversions` is Google's Conversions summary (the Google tag, every
conversion action with its status and last 30 days, imports, account-default
goals); `/conversions/new` is Google's three steps: choose data sources (website,
app, phone calls, offline), create conversion actions with Google's settings
(value, count, windows, attribution, primary or secondary), then the summary with
the Google tag and each action's event snippet to install. Created through
`ConversionActionService` behind the gateway's switches (`ads/conversions.py`).

The API cannot create everything Google's screen can: Google Analytics and
Firebase conversions are imported by switching on the hidden action Google lists;
codeless URL-rule conversions, lead form, store and Smart campaign conversions are
read only; uploads of offline conversions come after the action exists. PPCWay
reads the merchant's page for the Google tag, since it cannot see the tag fire as
Google does; a tag added through Tag Manager does not show in the page and the
screen says so.

Research: `docs/reference/campaign-creation/`.
