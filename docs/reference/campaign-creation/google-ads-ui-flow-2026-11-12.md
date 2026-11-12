# How a campaign is created in the Google Ads web interface (state as of 12 November 2026)

Research input for the PPCWay rebuild. It describes what the advertiser sees and chooses in ads.google.com when they click "New campaign". It does not map settings to the Google Ads API; that is a separate piece of work.

## How to read this file

- Every factual claim carries an inline source link. Links written as a bare number, for example [7450050](https://support.google.com/google-ads/answer/7450050), are Google Ads Help articles at `support.google.com/google-ads/answer/<number>`.
- Google Ads Help articles carry no publish date. All of them were read on 12 November 2026 and show a "©2026 Google" footer, so they are treated as current unless the text itself is visibly stale. Where a page is stale, this file says so.
- Third-party sources (PPC Land, Search Engine Journal, Search Engine Land and others) are used only to date a change or fill a gap, and each one is dated.
- **(unconfirmed)** means no source confirmed the claim. Option names in quotation marks are as the source gives them; where the help page and the live UI may word a label differently, that is flagged.
- A warning about Google's own Search guide: the help article "Create a Search campaign" ([9510373](https://support.google.com/google-ads/answer/9510373)) still describes old text ads ("Write 1-3 headlines", two 90-character descriptions) and Dynamic Search Ads as a creation option. Both are out of date (see sections 2.7 and 2.3.13). This file therefore builds the Search flow from the individual feature articles, not from that guide.

---

## 1. Entry steps shared by every campaign type

### 1.1 Where creation starts

| Item | What the advertiser sees | Source |
|---|---|---|
| Entry point | Campaigns, then the plus button, then "New campaign". Newer guides say "Create", then "Campaign". | [6324971](https://support.google.com/google-ads/answer/6324971), [13717903](https://support.google.com/google-ads/answer/13717903) |
| Step 1 | Choose an objective (or no guidance), confirm or edit conversion goals, choose a campaign type and subtype, then "Continue". | [6324971](https://support.google.com/google-ads/answer/6324971) |
| Drafts | Work saves automatically as a draft. Drafts show at the top of the Campaigns list and can be resumed. Limit: 25 campaign drafts. | [9510373](https://support.google.com/google-ads/answer/9510373), [6372658](https://support.google.com/google-ads/answer/6372658) |
| Progress panel | A navigation menu on the left shows progress and flags problems with targeting, bidding, budget and other settings that must be fixed before publishing. | [6324971](https://support.google.com/google-ads/answer/6324971), [9510373](https://support.google.com/google-ads/answer/9510373) |
| New accounts | A brand-new advertiser goes through a different, shorter flow: add business information (business name, website, optional Google Business Profile or YouTube channel link), then campaign goal and budget with a recommended campaign type, then payment details. Google says it is "updating new-user onboarding". | [6324971](https://support.google.com/google-ads/answer/6324971), [9510373](https://support.google.com/google-ads/answer/9510373) |

### 1.2 Objectives and the campaign types each one offers

Google's objectives article gives this table ([7450050](https://support.google.com/google-ads/answer/7450050)):

| Objective (exact label) | Campaign types offered | Notes | Source |
|---|---|---|---|
| Sales | Performance Max, Search, Display, Demand Gen, Shopping, Video | Purchases or other conversions. | [7450050](https://support.google.com/google-ads/answer/7450050) |
| Leads | Performance Max, Search, Display, Demand Gen, Shopping, Video | Contact details, sign-ups. | [7450050](https://support.google.com/google-ads/answer/7450050) |
| Website traffic | Search, Display, Demand Gen, Shopping, Video | The objectives article excludes Performance Max, but the current Performance Max step-1 guide lists "Website traffic" among Performance Max objectives. Treat Performance Max under Website traffic as possible in the live UI. | [7450050](https://support.google.com/google-ads/answer/7450050), [13717903](https://support.google.com/google-ads/answer/13717903) |
| YouTube reach, views, and engagements | Display, Demand Gen, Video | Replaces "Awareness and consideration" for new campaigns. Google says the objective itself is unchanged. | [7450050](https://support.google.com/google-ads/answer/7450050), [2375497](https://support.google.com/google-ads/answer/2375497) |
| App promotion | App campaigns | | [7450050](https://support.google.com/google-ads/answer/7450050) |
| Local store visits and promotions | Performance Max (store goals); also offered when creating Shopping | Missing from the objectives table but present in the Performance Max and Shopping guides. | [10724896](https://support.google.com/google-ads/answer/10724896), [3455481](https://support.google.com/google-ads/answer/3455481) |
| Create a campaign without a goal's guidance | All types are shown | You set goals later. A Search campaign still needs at least one conversion goal. | [13717903](https://support.google.com/google-ads/answer/13717903), [9510373](https://support.google.com/google-ads/answer/9510373) |

Other points:

- Performance Max, Demand Gen and Video campaigns cannot change their objective after creation ([7450050](https://support.google.com/google-ads/answer/7450050)).
- The Display guide still shows "Brand awareness and reach" as an objective label for Display ([10759203](https://support.google.com/google-ads/answer/10759203)). That is probably an older label for the same objective **(unconfirmed)**.
- The Campaigns menu also lists AI Max for Search, AI Max for Shopping, Hotel, Call, Things to do and Events ticketing. The setup guide names only Search, Display, Video, Shopping, Demand Gen, App, Smart and Performance Max as types picked at this step ([6324971](https://support.google.com/google-ads/answer/6324971)). AI Max is a setting inside Search and Shopping, not a campaign type ([15909989](https://support.google.com/google-ads/answer/15909989), [17091277](https://support.google.com/google-ads/answer/17091277)).

### 1.3 Conversion goals at this step

| Setting | Options | Default | Limits and rules | Source |
|---|---|---|---|---|
| Goal list for the new campaign | Keep, remove ("Remove goal" from the three-dot menu) or "Add goal" | All account-default goals are pre-selected | Shown only for Sales, Leads, Website traffic, Local store visits and Custom objectives. | [10995481](https://support.google.com/google-ads/answer/10995481), [6324971](https://support.google.com/google-ads/answer/6324971) |
| Custom goal | Add one custom goal built from the conversions summary | None | Only one custom goal per campaign: "You can't add multiple custom goals for a single campaign." Google calls custom goals an advanced option. | [10995481](https://support.google.com/google-ads/answer/10995481), [10995103](https://support.google.com/google-ads/answer/10995103) |
| No goals yet | Pick "ways to reach your goals", then "Create a Conversion Action", then "Installation options" for the tag | Offered when the account has no account-default goals | If conversion tracking is not set up, the advertiser is prompted to set it up when selecting a goal. | [10995481](https://support.google.com/google-ads/answer/10995481) |
| Goal values | Different values per goal (for example a call valued at the average order value) | | Google AI favours the goals with the highest return. Shown in the Performance Max guide. | [13717903](https://support.google.com/google-ads/answer/13717903) |
| Later, in campaign settings | "Account-default" or "Campaign-specific"; "Use account goals" switches back | | A conversion action drives bidding only if it is Primary and its goal is selected. Changing goals can cause a "Learning" status of up to 7 days. | [10995103](https://support.google.com/google-ads/answer/10995103), [10995481](https://support.google.com/google-ads/answer/10995481) |

### 1.4 Ways to reach your goal, website and campaign name

| Item | What is known | Source |
|---|---|---|
| "Select the ways you'd like to reach your goal" | Google confirms the step and gives "website visits" and "phone calls" as examples. | [10995481](https://support.google.com/google-ads/answer/10995481) |
| Full option list | Website visits, Phone calls, Store visits, App downloads, Lead form submissions. **(unconfirmed)**: only a third-party guide lists all five; Google's pages give two examples. | [rb.com.au](https://rb.com.au/blog/types-of-google-ads/) (undated third party), [10995481](https://support.google.com/google-ads/answer/10995481) |
| Fields under each way | A website URL for website visits and a phone number for calls are the usual inputs **(unconfirmed)**. Google's Search guide only says "you can enter additional information about your business". | [9510373](https://support.google.com/google-ads/answer/9510373) |
| Business website URL | Asked at step 1 in the Display flow ("business website URL and a campaign name"). | [10759203](https://support.google.com/google-ads/answer/10759203) |
| Campaign name | Entered at step 1 ("Click Continue, then name the campaign"). Customers never see it. | [9510373](https://support.google.com/google-ads/answer/9510373), [1704395](https://support.google.com/google-ads/answer/1704395) |

### 1.5 EU political ads declaration (every campaign)

| Setting | Options (exact wording) | Default | Rules | Source |
|---|---|---|---|---|
| EU political ads | "No, this campaign doesn't have EU political ads" or "Yes, this campaign has EU political ads" | None; a declaration is required | A campaign declared "Yes" cannot serve ads in the EU. An account-level declaration is also possible: "No, I don't plan to use this account to run EU political ads" or "Yes, I plan to use this account to run EU political ads". | [SA360 16501722](https://support.google.com/sa360/answer/16501722), [Google Ads API EU PAR](https://developers.google.com/google-ads/api/docs/api-policy/eu-par) |
| Timing | Launched September 2025. The API enforces a declaration on every campaign create or update from 3 September 2025 (API v21). | | Third-party reporting says from April 2026 undeclared campaigns block all campaign management in an account **(unconfirmed by Google)**. | [SA360 16501722](https://support.google.com/sa360/answer/16501722), [PPC Land, 2026](https://ppc.land/google-ads-api-tightens-eu-political-ads-rules-with-april-1-deadline/) |

The Search Ads 360 page is Google's own documentation of the Google Ads declaration wording. The exact step where the question appears inside the Google Ads web flow is **(unconfirmed)**; third-party guides place it in campaign settings and say it is mandatory before continuing ([nilsrooijmans.com](https://nilsrooijmans.com/daily/new-eu-political-ads-campaign-setting), undated).

### 1.6 Guided versus expert

| Mode | What it means | Source |
|---|---|---|
| Goal-guided creation | Picking an objective narrows the campaign types and pre-fills goals. | [6324971](https://support.google.com/google-ads/answer/6324971) |
| "Create a campaign without a goal's guidance" | Shows every type, no objective-based recommendations. | [7450050](https://support.google.com/google-ads/answer/7450050) |
| Smart Mode versus Expert Mode | Smart campaigns can only be created in Smart Mode ("You can only create Smart Campaigns in Smart Mode"). Other types need Expert Mode. | [7652860](https://support.google.com/google-ads/answer/7652860), [9520605](https://support.google.com/google-ads/answer/9520605) |
| Switching | Settings icon, then "Switch to Expert Mode". Third-party guides say new accounts start in Smart Mode and that the switch is one-way **(unconfirmed by Google)**. | [9520605](https://support.google.com/google-ads/answer/9520605), [megadigital.ai](https://megadigital.ai/en/blog/google-ads-expert-mode/) (2026) |

---

## 2. Search campaign, end to end

### 2.0 Step order

The live UI steps are documented only in pieces. The order below is assembled from the sources cited in each row.

| # | Step | Source |
|---|---|---|
| 1 | Objective, conversion goals, type "Search", ways to reach your goal, campaign name | [9510373](https://support.google.com/google-ads/answer/9510373), [10995481](https://support.google.com/google-ads/answer/10995481) |
| 2 | Bidding | [9510373](https://support.google.com/google-ads/answer/9510373) |
| 3 | Campaign settings (networks, locations, languages, audiences, more settings) | [9510373](https://support.google.com/google-ads/answer/9510373) |
| 4 | "AI Max" page ("When you reach the 'AI Max' page, toggle to opt-in") | [15913066](https://support.google.com/google-ads/answer/15913066) |
| 5 | "Keyword and asset generation" (conversational AI, if eligible) | [14145186](https://support.google.com/google-ads/answer/14145186) |
| 6 | "Keywords and ads" (ad groups, keywords, responsive search ads, assets) | [14145186](https://support.google.com/google-ads/answer/14145186) |
| 7 | Budget | [2375454](https://support.google.com/google-ads/answer/2375454) |
| 8 | Review, then "Publish campaign" | [9510373](https://support.google.com/google-ads/answer/9510373) |

The exact left-menu labels for steps 2, 3, 7 and 8 in late 2026 are **(unconfirmed)**.

### 2.1 Bidding

The Search bidding step asks what to focus on, then offers optional targets ([9510373](https://support.google.com/google-ads/answer/9510373)).

| Setting | Options | Default | Limits and help | Source |
|---|---|---|---|---|
| What do you want to focus on? | "Conversions", "Conversion value", "Clicks", "Impression share" | **(unconfirmed)** | Conversions needs conversion tracking. Conversion value needs conversions with values. | [9510373](https://support.google.com/google-ads/answer/9510373) |
| Conversions: optional target | Checkbox "Set a target cost per action" | Off | Gives Target CPA. Without it the strategy is Maximize conversions. | [15862641](https://support.google.com/google-ads/answer/15862641), [2472725](https://support.google.com/google-ads/answer/2472725) |
| Conversion value: optional target | Checkbox "Set a target return on ad spend" | Pre-ticked with a suggested value when Google has a recommended Target ROAS (documented for Performance Max) | Gives Target ROAS. Without it the strategy is Maximize conversion value. | [15862641](https://support.google.com/google-ads/answer/15862641) |
| Label change | "Maximize conversions with a Target CPA" now reads "Target CPA"; "Maximize conversion value with a Target ROAS" now reads "Target ROAS". Behaviour unchanged. | From June 2026 | | [13717096](https://support.google.com/google-ads/answer/13717096) |
| Clicks | Maximize clicks, with an optional campaign-wide maximum CPC bid limit | | You cannot set keyword-level bids under Maximize clicks. | [2472725](https://support.google.com/google-ads/answer/2472725) |
| Impression share | Target impression share: where ads appear ("Top", "Absolute top", "Anywhere"), percent to target, "Max CPC bid limit" | | Impression share counts only Google Search, not search partners. A low bid limit can stop the target being reached. | [9121108](https://support.google.com/google-ads/answer/9121108) |
| Select a bid strategy directly | For experienced advertisers. Search strategies: Target CPA, Target ROAS, Maximize conversions, Maximize conversion value, Maximize clicks, Target impression share, Manual CPC | | Enhanced CPC "is no longer available for Search and Display campaigns" from the week of 31 March 2025. Target CPC exists only in Demand Gen. | [9510373](https://support.google.com/google-ads/answer/9510373), [2979071](https://support.google.com/google-ads/answer/2979071) |
| Show more settings | "Conversions" (which conversions to bid for), "Ad schedule", "Ad rotation" | | | [9510373](https://support.google.com/google-ads/answer/9510373) |
| Smart Bidding Exploration (Target ROAS only) | "Allow Smart Bidding to explore new traffic", with a Target ROAS tolerance of 5 to 30% | Off | Not effective when limited by budget. Google suggests running it at least 6 weeks. | [16294612](https://support.google.com/google-ads/answer/16294612) |
| Journey-aware bidding | Lets Target CPA learn from non-biddable conversions | Beta (2026) | No setting name given. | [blog.google, GML 2026](https://blog.google/products/ads-commerce/bidding-budgeting-google-marketing-live-2026/) |

Bidding behaviour notes for the rebuild:

- AI Max search term matching "will not work with manual CPC bidding" ([15913066](https://support.google.com/google-ads/answer/15913066)).
- From 17 August 2026, budget-limited campaigns on Target CPA or Target ROAS aim at their targets more strictly, and a "Bid Target Adjustment Tool" (from 6 July 2026) lets the advertiser keep, adjust, customise or drop the target ([PPC Land, 2026](https://ppc.land/google-ads-gets-promotion-mode-and-a-major-bidding-overhaul-this-august/)).
- "Promotion mode" (beta) schedules temporary ROAS tolerance and extra daily budget for date ranges, for Search and Performance Max ([PPC Land, 2026](https://ppc.land/google-ads-gets-promotion-mode-and-a-major-bidding-overhaul-this-august/)). Where it appears in the UI is **(unconfirmed)**.

### 2.2 Customer acquisition (inside bidding)

| Setting | Options (help-page names) | Default | Requirements | Source |
|---|---|---|---|---|
| Customer acquisition | "Bid higher for new customers" (New Customer Value), "Bid higher for high-value new customers" (High Value New Customer), "Bid only for new customers" (New Customer Only) | Bids equally for new and existing customers (stated for Shopping) | New Customer Value and High Value need value-based bidding (Target ROAS or Maximize conversion value) and a Purchase goal. New Customer Only also works with Maximize conversions or Target CPA. All three work in Search, Performance Max and Shopping; High Value does not work in Demand Gen. | [12080169](https://support.google.com/google-ads/answer/12080169), [14007601](https://support.google.com/google-ads/answer/14007601), [3455481](https://support.google.com/google-ads/answer/3455481) |
| Customer retention | "Bid higher for lapsed customers", "Bid higher for high-value lapsed customers" | | | [14007601](https://support.google.com/google-ads/answer/14007601) |
| How new customers are defined | Customer lists, website tag, and Google autodetection (on automatically when Purchase conversions are tracked; looks back up to 540 days) | | Lists need at least 100 active members in one network. The Performance Max bidding step instead says the "Bid for new customers only" checkbox needs a segment of at least 1,000 active members. The two pages conflict. | [14007601](https://support.google.com/google-ads/answer/14007601), [15862641](https://support.google.com/google-ads/answer/15862641) |

### 2.3 Campaign settings

#### 2.3.1 Networks

| Setting | Options | Default | Notes | Source |
|---|---|---|---|---|
| Google search partners | Checkbox "Include Google search partners" | On ("search partners are included by default") | Partner sites can be excluded individually. | [1722047](https://support.google.com/google-ads/answer/1722047) |
| Display Network | Checkbox to extend a Search campaign to the Display Network | **(unconfirmed)** | From February 2027 the current spend split for Search campaigns with the Display Network on is removed; to keep it, set the Display Network to Low priority with 50% allocation. | [9510373](https://support.google.com/google-ads/answer/9510373), [blog.google, 14 Oct 2026](https://blog.google/products/ads-commerce/channel-prioritization-budget-allocation/) |
| Channel prioritization (new, October 2026) | Mark Google Search, Search partners and Display Network each as "High" or "Low" priority; optional cap on the share of daily budget Low-priority channels get | Optional | Account and campaign level, works with shared budgets. Rolling out "over the coming months". Whether it is in the creation flow is **(unconfirmed)**. | [blog.google, 14 Oct 2026](https://blog.google/products/ads-commerce/channel-prioritization-budget-allocation/), [1704395](https://support.google.com/google-ads/answer/1704395) |

#### 2.3.2 Locations

| Setting | Options | Default | Limits | Source |
|---|---|---|---|---|
| Locations | Countries, regions, cities, postcodes; Include or Exclude; "Radius" around an address; "Add locations in bulk" | **(unconfirmed)**; the labels "All countries and territories" and "Enter another location" are not on the targeting article, but "Enter another location" and "Advanced search" appear in the Performance Max settings guide | Radius at least 1 km. Bulk: up to 1,000 per paste. 10,500 location targets per campaign (10,000 places plus 500 radius), counting exclusions. An alert shows if predicted clicks are zero. | [1722043](https://support.google.com/google-ads/answer/1722043), [15864837](https://support.google.com/google-ads/answer/15864837), [6372658](https://support.google.com/google-ads/answer/6372658), [9510373](https://support.google.com/google-ads/answer/9510373) |
| Location groups | Places of interest, business locations, tiered demographics | | Setup not documented on that page. | [1722043](https://support.google.com/google-ads/answer/1722043) |
| Location options, Target | "Presence or Interest" (people in, regularly in, or interested in the locations) or "Presence" (people in or regularly in) | "Presence or Interest" (recommended) | Interest-only targeting can no longer be set for Search, Display or Shopping. | [1722038](https://support.google.com/google-ads/answer/1722038) |
| Location options, Exclude | "Presence" | "Presence" | "Presence or Interest" can no longer be used as an exclusion for Search, Display, Performance Max or Shopping. | [1722038](https://support.google.com/google-ads/answer/1722038) |
| Household income | Moved from location targeting to demographic targeting | | | [1722038](https://support.google.com/google-ads/answer/1722038) |

#### 2.3.3 Languages

| Setting | Options | Default | Notes | Source |
|---|---|---|---|---|
| Languages (Search) | **Removed.** "Starting in September 2026 ... The campaign-level language targeting setting will be removed. Search ads will automatically match based on the language of your ads." | n/a | Applies to Search and AI Max for Search. Google says no advertiser action is needed and existing language criteria stay but no longer affect Search targeting. | [1722078](https://support.google.com/google-ads/answer/1722078), [SEJ, 13 Aug 2026](https://www.searchenginejournal.com/google-is-removing-language-targeting-from-search-campaigns/585592/) |
| Languages (Performance Max) | Still set, but no longer applies to Google Search inventory; still applies to YouTube, Display, Discover and Gmail. Shopping ads are not affected by language settings. | | | [1722078](https://support.google.com/google-ads/answer/1722078) |

Whether the Languages field is fully hidden in the Search creation flow, or shown and ignored, is **(unconfirmed)**.

#### 2.3.4 Audience segments

| Setting | Options | Default | Notes | Source |
|---|---|---|---|---|
| Audiences | Demographics, interests, online activity, remarketing; "Browse" option | None | | [9510373](https://support.google.com/google-ads/answer/9510373) |
| Targeting setting | "Targeting" (restricts reach) or "Observation" (does not restrict reach; used for reporting, bid adjustments, and as signals for Smart Bidding) | Observation is recommended for all Search campaigns. Whether it is the default is **(unconfirmed)**. | An observation method cannot be added when the ad group is first created; it is added afterwards. | [7365594](https://support.google.com/google-ads/answer/7365594) |
| Browse categories | Category names such as "What they are actively researching or planning" appear in Google's example. The full category list is **(unconfirmed)**. | | | [7365594](https://support.google.com/google-ads/answer/7365594) |

#### 2.3.5 Broad match campaign setting (retired)

| Item | Detail | Source |
|---|---|---|
| Status | New campaign-level broad match settings were blocked from 3 August 2026 in the UI, Editor and API. Existing ones were converted into AI Max for Search from 1 September 2026, with search term matching on. | [PPC Land, 6 Aug 2026](https://ppc.land/google-ads-broad-match-campaigns-face-ai-max-auto-upgrade-on-september-1/), [relevantaudience.com, 2026](https://www.relevantaudience.com/google-ads-en/google-blocks-new-broad-match-settings-ai-max-migration/), [business.google.com, Apr 2026](https://business.google.com/us/accelerate/announcements/dsa-upgrade-to-ai-max-2026/) |
| Effect on keyword priority | After the upgrade, broad keywords are no longer treated as exact match in prioritisation. Google suggests adding exact-match copies to keep old behaviour. | [15910187](https://support.google.com/google-ads/answer/15910187) |
| Rebuild implication | A rebuild should not offer a "broad match setting" toggle. Broad, phrase and exact remain as keyword match types (section 2.6). | [15910187](https://support.google.com/google-ads/answer/15910187) |

#### 2.3.6 AI Max for Search

AI Max is a layer inside a Search campaign, not a separate type ([15909989](https://support.google.com/google-ads/answer/15909989)). Announced May 2025 ([blog.google](https://blog.google/products/ads-commerce/google-ai-max-for-search-campaigns/)), out of beta in April 2026 ([business.google.com](https://business.google.com/us/accelerate/announcements/dsa-upgrade-to-ai-max-2026/)).

| Setting | Level | Options | Default | Limits and dependencies | Source |
|---|---|---|---|---|---|
| AI Max toggle | Campaign | On or off | On; "the AI Max option is pre-selected during creation" for new Search campaigns | Turning off disables every AI Max feature; turning back on restores earlier choices. Alerts if the campaign is limited by budget. | [15909989](https://support.google.com/google-ads/answer/15909989), [15910187](https://support.google.com/google-ads/answer/15910187) |
| Search term matching | Campaign switch, then per ad group | On or off | On with AI Max | Uses broad match plus asset- and landing-page-based matching. Must be on at campaign level for ad groups to use it. Does not work with Manual CPC. Negative keywords are still respected. | [15910187](https://support.google.com/google-ads/answer/15910187), [15913066](https://support.google.com/google-ads/answer/15913066) |
| Text customization (formerly "automatically created assets") | Campaign (in the "Asset optimization" panel) | On or off | On with AI Max | Generates headlines and descriptions from the site, landing pages, existing ads and keywords. Turning it off marks generated assets "Removed" and also turns off Final URL expansion. | [15909989](https://support.google.com/google-ads/answer/15909989) |
| Text guidelines (beta) | Campaign ("Add text guidelines" under Asset optimization) | Term exclusions; messaging restrictions | Off | Up to 25 term exclusions and up to 40 messaging restrictions per campaign. Needs text customization on. Non-compliant generated assets stop serving. | [16489313](https://support.google.com/google-ads/answer/16489313) |
| Final URL expansion | Campaign | On or off | On with AI Max for new campaigns; off by default for campaigns migrated from automatically created assets | Requires text customization. When a more relevant page is chosen, pinned RSA assets are not used. "pinning of RSA assets will not be respected" when text customization and Final URL expansion are both on. | [15910187](https://support.google.com/google-ads/answer/15910187), [15913066](https://support.google.com/google-ads/answer/15913066), [PPC Land, 6 Aug 2026](https://ppc.land/google-ads-broad-match-campaigns-face-ai-max-auto-upgrade-on-september-1/) |
| URL exclusions | Campaign | "URLs" tab and "Rules" tab | None | Needs AI Max, text customization and Final URL expansion. "URL Contains" rules match whole words. | [15909989](https://support.google.com/google-ads/answer/15909989) |
| URL inclusions | Ad group | List of URLs | None | Needs search term matching and asset optimization. Pinned assets are not used when inclusions are active. | [15909989](https://support.google.com/google-ads/answer/15909989) |
| Locations of interest | Ad group | Geographic intent targeting | None | Described as exclusive to AI Max. | [15910187](https://support.google.com/google-ads/answer/15910187) |
| Brand inclusions | Campaign or ad group | Brand lists | None | Ad group setting overrides campaign for that ad group. | [15909989](https://support.google.com/google-ads/answer/15909989) |
| Brand exclusions | Campaign | Brand lists | None | | [15909989](https://support.google.com/google-ads/answer/15909989) |
| Tracking | | | | Tracking templates can cause 404s on expanded landing pages; Google recommends the bare `{lpurl}` tag when no parameters are needed. | [15910187](https://support.google.com/google-ads/answer/15910187) |

Stale text warning: the AI Max FAQ still says "AI Max is not yet available in the API and Editor" ([15913066](https://support.google.com/google-ads/answer/15913066)), while Google's API documentation describes `Campaign.ai_max_setting.enable_ai_max` ([API guide](https://developers.google.com/google-ads/api/docs/campaigns/ai-max-for-search-campaigns/getting-started)). Treat the FAQ line as out of date.

#### 2.3.7 Brand lists (inclusions and exclusions)

| Setting | Options | Default | Limits | Source |
|---|---|---|---|---|
| Where lists live | Tools, Shared library, Brand lists; "Create a brand list"; search the Google brand library or request a brand | | 10,000 lists per account, 10 lists per campaign, 5,000 brands per list. No extra cost. | [14450499](https://support.google.com/google-ads/answer/14450499), [6372658](https://support.google.com/google-ads/answer/6372658), [13721847](https://support.google.com/google-ads/answer/13721847) |
| Brand inclusions | Search only: serve only on queries about the chosen brands | None | | [13721847](https://support.google.com/google-ads/answer/13721847) |
| Brand exclusions | Search and Performance Max (Search and Shopping inventory) | None | Exclusions win over inclusions. | [13721847](https://support.google.com/google-ads/answer/13721847) |
| Requirement in new Search campaigns | Brand controls now sit only in the AI Max panel; creating or editing inclusions or exclusions needs AI Max on. Existing lists on old campaigns keep working. | | Reported as a UK beta in July 2025 and later broader; Performance Max is not affected. | [browsermedia.agency, 23 Jul 2025](https://browsermedia.agency/blog/google-locks-brand-controls-behind-ai-max/), [15909989](https://support.google.com/google-ads/answer/15909989) |

#### 2.3.8 Start and end dates

| Setting | Options | Default | Notes | Source |
|---|---|---|---|---|
| Start date | Date | Today | With a campaign total budget, the budget type cannot change once the start date is set. | [15137812](https://support.google.com/google-ads/answer/15137812) |
| End date | None or a date | None **(unconfirmed for Search; Demand Gen documents dates as optional on daily budgets)** | Required for a campaign total budget. | [13695389](https://support.google.com/google-ads/answer/13695389), [9510373](https://support.google.com/google-ads/answer/9510373) |

#### 2.3.9 Ad schedule

| Setting | Options | Default | Limits | Source |
|---|---|---|---|---|
| Ad schedule | Days and time ranges, optional bid adjustments | "All day" | Up to 6 schedules per day per campaign. Uses the account time zone. Overnight runs need one entry per day. | [2404244](https://support.google.com/google-ads/answer/2404244), [6372656](https://support.google.com/google-ads/answer/6372656) |
| Pacing change | From 1 June 2026, campaigns with day-of-week schedules pace toward up to 30.4 times the daily budget per month, not daily budget times scheduled days. Hour-based schedules are unaffected. | | Still never more than 2x daily budget in a day. | [16913225](https://support.google.com/google-ads/answer/16913225) |
| Granularity | 15-minute steps **(unconfirmed)** | | | |

#### 2.3.10 Devices

| Setting | Options | Default | Limits | Source |
|---|---|---|---|---|
| Devices (Search) | Computers, mobile phones, tablets; set as bid adjustments | All devices **(default unconfirmed)** | Range -100% to +900%; -100% stops serving on that device, and a campaign-level -100% overrides ad group adjustments. Under Target impression share, existing bid adjustments are not used, except -100% device adjustments. | [2732132](https://support.google.com/google-ads/answer/2732132), [9121108](https://support.google.com/google-ads/answer/9121108) |

#### 2.3.11 Campaign URL options

| Setting | Options | Default | Limits | Source |
|---|---|---|---|---|
| Tracking template | Text field (ValueTrack allowed) | Empty | Cross-domain redirects not allowed in final URLs. | [6080568](https://support.google.com/google-ads/answer/6080568) |
| Final URL suffix | Parameters appended to the landing page URL | Empty | | [6080568](https://support.google.com/google-ads/answer/6080568) |
| Custom parameters | Name and value pairs | None | Up to 8 per level (campaign, ad group, ad, keyword, sitelink; not account). Name up to 16 alphanumeric characters; value up to 250 characters. | [6325879](https://support.google.com/google-ads/answer/6325879) |

#### 2.3.12 IP exclusions

| Setting | Options | Default | Limits | Source |
|---|---|---|---|---|
| IP exclusions (campaign, under "Additional settings") | Specific addresses, or an asterisk replacing the last block | None | Up to 500 per campaign. Not available at campaign level for Video, Hotel, App, Performance Max or Smart Display. An account-level list covers App, Performance Max, Demand Gen, Search, Shopping, Display, Discover and YouTube, and merges with campaign lists. | [2456098](https://support.google.com/google-ads/answer/2456098) |

#### 2.3.13 Dynamic Search Ads and page feeds

| Item | Status in late 2026 | Source |
|---|---|---|
| New DSA campaigns or dynamic ad groups | From September 2026 advertisers "won't be able to create new campaigns with DSA via Google Ads, Google Ads Editor and the Google Ads API". Whether the "Dynamic" ad group choice is fully gone from the creation screen is **(unconfirmed)**; Google's Search guide still shows it but is stale. | [business.google.com, Apr 2026](https://business.google.com/us/accelerate/announcements/dsa-upgrade-to-ai-max-2026/), [9510373](https://support.google.com/google-ads/answer/9510373) |
| Existing DSA | Automatic upgrade to AI Max moved to February 2027. Dynamic ad groups become standard ad groups; DSAs become responsive search ads; "page title contains" and "page content contains" rules become read-only. | [7166527](https://support.google.com/google-ads/answer/7166527), [15909989](https://support.google.com/google-ads/answer/15909989), [PPC Land, 6 Aug 2026](https://ppc.land/google-ads-broad-match-campaigns-face-ai-max-auto-upgrade-on-september-1/) |
| Page feeds | Spreadsheet with "Page URL" and "Custom label" columns, up to 20 labels per URL, uploaded under Tools, Business data. Targeting source options for DSA: "Use URLs from my page feed only" or "Use URLs from both Google's index of my website and my page feed". Crawl takes 2 to 14 days. | [7166527](https://support.google.com/google-ads/answer/7166527) |
| Page feed limits | The page feed article says 100 page feeds per account; the account limits article says 180 per customer. The two conflict. | [7166527](https://support.google.com/google-ads/answer/7166527), [6372658](https://support.google.com/google-ads/answer/6372658) |

#### 2.3.14 Other "more settings"

| Setting | Options | Default | Source |
|---|---|---|---|
| Ad rotation | "Optimize" or "Do not optimize" | Smart Bidding forces "Optimize". The default for non-Smart strategies is **(unconfirmed)**. | [112876](https://support.google.com/google-ads/answer/112876) |
| Conversions (campaign goals) | Account-default or campaign-specific | Account-default | [10995103](https://support.google.com/google-ads/answer/10995103) |
| Attribution model | Listed under "Additional settings" | **(unconfirmed)** | [1704395](https://support.google.com/google-ads/answer/1704395) |
| Assets in settings | Sitelink, callout and call assets are shown by default; "Ad asset" adds the rest | | [9510373](https://support.google.com/google-ads/answer/9510373) |

### 2.4 Keyword and asset generation

| Item | Detail | Source |
|---|---|---|
| Where | The "Keyword and asset generation" step and the "Keywords and ads" step of a new Search campaign, if the account is eligible. | [14145186](https://support.google.com/google-ads/answer/14145186) |
| Inputs | Landing page URL. Google AI writes a business summary from the page, which the advertiser reviews and edits. Chat requests refine the output. A separate "product or service description" field is not documented **(unconfirmed)**. | [14145186](https://support.google.com/google-ads/answer/14145186) |
| Output | Suggested ad groups (name and URL editable), then after "Generate", per ad group: keywords, headlines, descriptions, sitelinks and images (from the page or generated by Google AI). | [14145186](https://support.google.com/google-ads/answer/14145186) |
| Eligibility | Global, for Search campaigns and RSAs in English, French, Spanish or German. Not for sensitive verticals (political, gambling, sexual content and others). Not available when adding ad groups to an existing campaign. | [14145186](https://support.google.com/google-ads/answer/14145186) |
| How to skip | Not documented **(unconfirmed)**. | |

### 2.5 Ad groups and keywords

| Setting | Options | Default | Limits | Source |
|---|---|---|---|---|
| Ad group name | Text | | 20,000 ad groups per campaign. | [6372658](https://support.google.com/google-ads/answer/6372658) |
| Keywords | One per line | | 20,000 ad group targeting items per ad group (keywords included). | [9510373](https://support.google.com/google-ads/answer/9510373), [6372658](https://support.google.com/google-ads/answer/6372658) |
| Match type | Broad (no symbol), phrase ("quotes"), exact ([brackets]) | Broad | Google: "It's critical to use Smart Bidding with broad match." Identical exact keywords beat Performance Max; phrase and broad share priority with identical Performance Max search themes. | [7478529](https://support.google.com/google-ads/answer/7478529) |
| Keyword ideas | Suggestions in the editor and Keyword Planner | | | [9510373](https://support.google.com/google-ads/answer/9510373) |
| Negative keywords | Broad, phrase or exact negatives; entered with a minus sign in the keyword box | Broad | Negatives do not match close variants. 10,000 per campaign; 20 lists; 5,000 per list. Account-level negatives apply to Search and Shopping inventory. | [2453972](https://support.google.com/google-ads/answer/2453972), [9510373](https://support.google.com/google-ads/answer/9510373), [6372658](https://support.google.com/google-ads/answer/6372658) |

### 2.6 Responsive search ads

| Field | Min | Max | Character limit | Notes | Source |
|---|---|---|---|---|---|
| Final URL | 1 | 1 | | A unique final URL per RSA is recommended. | [7684791](https://support.google.com/google-ads/answer/7684791) |
| Display path | 0 | 2 | 15 each | | [7684791](https://support.google.com/google-ads/answer/7684791) |
| Headlines | 3 | 15 | 30 each | Up to 3 show in the headline position. | [7684791](https://support.google.com/google-ads/answer/7684791) |
| Descriptions | 2 | 4 | 90 each | | [7684791](https://support.google.com/google-ads/answer/7684791) |
| Double-width languages | | | Each character counts as 2 | Korean, Japanese, Chinese. | [7684791](https://support.google.com/google-ads/answer/7684791) |
| Enabled RSAs per ad group | | 3 | | | [6372658](https://support.google.com/google-ads/answer/6372658) |
| Ad customizers | | 40 attributes | 90 per value | | [6372658](https://support.google.com/google-ads/answer/6372658) |

| Rule | Detail | Source |
|---|---|---|
| Pinning | Pin to Headline position 1, 2 or 3, or Description position 1 or 2. Pins to H1, H2 and D1 always show; H3 and D2 are not guaranteed. Pinning "isn't recommended for most advertisers and can affect ad strength". | [7684791](https://support.google.com/google-ads/answer/7684791) |
| Pinning under AI Max | Not respected when text customization and Final URL expansion are both on, or when URL inclusions are set. | [15913066](https://support.google.com/google-ads/answer/15913066) |
| Ad Strength labels | "Incomplete", "Poor", "Average", "Good", "Excellent" | [9921843](https://support.google.com/google-ads/answer/9921843) |
| What Ad Strength checks | Keywords in headlines (whole keyword inside one headline), number of assets, uniqueness, sitelinks at any level, pinning, and missing final URL, ad group or keywords (gives "Incomplete"). | [9921843](https://support.google.com/google-ads/answer/9921843) |
| Recommendations | Fill 15 headlines and 4 descriptions, at least 6 sitelinks, at least 2 RSAs rated Good or Excellent per ad group, 4 or more unique images. | [9921843](https://support.google.com/google-ads/answer/9921843) |
| Auction effect | Ad Strength "isn't used to calculate Ad Rank, Quality Score, or auction wins". | [9921843](https://support.google.com/google-ads/answer/9921843) |
| Generated text | Headlines and descriptions come from the conversational step (2.4) and from AI Max text customization (2.3.6). An in-editor "headline ideas" panel is **(unconfirmed)**. | [14145186](https://support.google.com/google-ads/answer/14145186), [15909989](https://support.google.com/google-ads/answer/15909989) |
| Enhanced flexibility | Unused headlines and descriptions may serve as link-style assets in space formerly reserved for sitelinks. | [7684791](https://support.google.com/google-ads/answer/7684791) |

### 2.7 Assets

General rule: assets can be added at account, campaign and ad group level for most types, and a more specific level overrides a higher one for callouts and promotions ([6079510](https://support.google.com/google-ads/answer/6079510), [7367521](https://support.google.com/google-ads/answer/7367521)). Some assets are added automatically at account level and can be switched off ([7331111](https://support.google.com/google-ads/answer/7331111)).

| Asset | Fields and limits | Levels | Source |
|---|---|---|---|
| Sitelinks | Link text up to 25 characters (12 in double-width languages). Two optional description lines, up to 35 characters each, set together. Final URL. Start and end dates, "Asset scheduling". Show up to 6 on desktop, 8 on mobile; at least 2 needed to show. Google recommends at least 6 with descriptions, and at least 4 at account level. | Account, campaign, ad group, asset group | [2375416](https://support.google.com/google-ads/answer/2375416), [SitelinkAsset API reference](https://developers.google.com/google-ads/api/reference/rpc/v20/SitelinkAsset) (35-character figure) |
| Callouts | Text up to 25 characters (12 double-width). Up to 10 can show. Scheduling under Advanced options. A more specific level blocks higher-level callouts. | Account, campaign, ad group | [6079510](https://support.google.com/google-ads/answer/6079510) |
| Structured snippets | Header from a fixed list: Amenities, Brands, Courses, Degree programs, Destinations, Featured hotels, Insurance coverage, Models, Neighborhoods, Service catalog, Shows, Styles, Types. 3 to 10 values, each up to 25 characters. Up to 2 headers show on computers, 1 on mobile. | Account, campaign, ad group | [6280012](https://support.google.com/google-ads/answer/6280012), [StructuredSnippetAsset API reference](https://developers.google.com/google-ads/api/reference/rpc/v22/StructuredSnippetAsset) (counts and length) |
| Images | Square 1:1 required (min 300x300, recommended 1200x1200); landscape 1.91:1 optional (min 600x314, recommended 1200x628). PNG or JPG, max 5,120 KB, keep content in the central 80%. Up to 20 images across the campaign. Eligibility: account open 60 days or more, good policy history, active campaigns and text ads, Search spend in the last 30 days; not for sensitive verticals. Dynamic image assets can pull images from landing pages. | Account, campaign, ad group | [9566341](https://support.google.com/google-ads/answer/9566341) |
| Business name and logo | One business name and one logo at account level, and one of each per campaign. Must match the domain or the verified legal name (Advertiser verification), or use Brand verification for a trademark. Needs Search spend in the last 28 days. Business name up to 25 characters (Performance Max spec). Square 1:1 logo required, landscape 4:1 optional (specs in 3.5). Dynamic logos for Search and Performance Max; dynamic names for Search in English, French, Japanese and German. | Account, campaign | [12497613](https://support.google.com/google-ads/answer/12497613), [17091269](https://support.google.com/google-ads/answer/17091269) |
| Calls | Phone number (E.164 format, verified as belonging to the business). No vanity, premium or fax numbers. Call reporting uses Google forwarding numbers and creates a "Call from ads" conversion. Day and hour scheduling. | Account, campaign, ad group | [2453991](https://support.google.com/google-ads/answer/2453991) |
| Lead forms | Required fields: business name, call to action type and description, headline, description, privacy policy URL; optional post-submit headline, description and call to action; optional background image exactly 1200x628. Up to 5 custom qualifying questions. Delivery: CSV download (last 30 days), email, API (60 days), webhook, Zapier. Needs good policy history, eligible vertical, conversion-based bidding and a lead form conversion goal. Character limits (headline 30, description 200) come only from third parties **(unconfirmed)**. | Campaign **(level unconfirmed)** | [9423234](https://support.google.com/google-ads/answer/9423234), [LeadFormAsset API reference](https://developers.google.com/google-ads/api/reference/rpc/v22/LeadFormAsset) |
| Prices | Type: Brands, Events, Location, Neighborhoods, Product categories, Product tiers, Services, Service categories, Service tiers. Currency from a fixed list. 3 to 8 items, each with header up to 25, description up to 25, and a final URL. Price qualifier and unit options are not listed on the help page **(unconfirmed)**. | Account, campaign, ad group | [7065415](https://support.google.com/google-ads/answer/7065415), [PriceAsset API reference](https://developers.google.com/google-ads/api/reference/rpc/v22/PriceAsset) |
| Promotions | Occasion (optional), language, currency, monetary or percent discount, item, final URL, promotion details (promo code or spend threshold), promotion dates, "Days and hours" schedule. Item limit of 20 characters is third-party only **(unconfirmed)**. | Account, campaign, ad group (most specific wins) | [7367521](https://support.google.com/google-ads/answer/7367521), [PromotionAsset API reference](https://developers.google.com/google-ads/api/reference/rpc/v22/PromotionAsset), [adspolicy 7374309](https://support.google.com/adspolicy/answer/7374309) |
| Apps | Platform, app, link text, final URL **(field list and limits unconfirmed; Google's app asset page returned 404)** | **(unconfirmed)** | [7331111](https://support.google.com/google-ads/answer/7331111) |
| Locations | Link a Google Business Profile in Location manager (Tools, Shared library), optionally filtered by name or label; or affiliate locations for chain stores and auto dealers; or up to 10 Google Maps locations. Only one location asset type per account. | Account, campaign, ad group (campaign overrides account) | [2404182](https://support.google.com/google-ads/answer/2404182) |
| Limits on totals | 50,000 campaign-level and 250,000 ad group-level assets per account; 10,000 ad group-level assets per campaign. | | [6372658](https://support.google.com/google-ads/answer/6372658) |

### 2.8 Budget

| Setting | Options | Default | Limits and help | Source |
|---|---|---|---|---|
| Budget type | "Daily budget" (average per day) or "Campaign total budget" (fixed amount over the dates) | Daily | Total budget needs start and end dates. For Search, Standard Shopping and Performance Max: recommended minimum 3 days, maximum 90 days. Budget type cannot change after the start date is set. Total budgets launched in open beta on 15 January 2026. | [9510373](https://support.google.com/google-ads/answer/9510373), [15137812](https://support.google.com/google-ads/answer/15137812), [blog.google](https://blog.google/products/ads-commerce/campaign-total-budgets/) |
| Daily spend rules | | | Up to 2x the daily budget on a given day; never charged more than 30.4x daily budget in a month. | [2375454](https://support.google.com/google-ads/answer/2375454) |
| Recommended budgets | Google suggests options and allows a custom amount. Later, "View recommended budget" uses about the last 15 days. | | What estimates appear next to each option (clicks, conversions, cost per week) is **(unconfirmed)** for Search. Demand Gen documents three levels (Low, Medium, High) with forecasts. | [9510373](https://support.google.com/google-ads/answer/9510373), [2375454](https://support.google.com/google-ads/answer/2375454), [13695777](https://support.google.com/google-ads/answer/13695777) |
| Shared budget | Pick an existing shared budget instead of an individual one | | Managed in the Shared library. Not usable with campaign groups or experiments. 11,000 shared budgets per account. | [2375454](https://support.google.com/google-ads/answer/2375454), [6372658](https://support.google.com/google-ads/answer/6372658) |
| Budget and AI Max | | | AI Max "won't be effective" when the campaign is limited by budget. | [15910187](https://support.google.com/google-ads/answer/15910187) |
| Demand-led pacing | Shifts daily spend toward high-demand days within monthly and daily caps | "Rolling out in the coming months" (2026) | No setting name given. | [blog.google, GML 2026](https://blog.google/products/ads-commerce/bidding-budgeting-google-marketing-live-2026/) |

### 2.9 Review and publish, and what happens next

| Item | Detail | Source |
|---|---|---|
| Review page | Summary of the campaign with issues to fix (billing, missing keywords or ads, invalid final URL); "Fix it" links, then publish. | [9510373](https://support.google.com/google-ads/answer/9510373) |
| Errors and warnings | The navigation menu flags settings to resolve before publishing; a location alert appears if predicted clicks are zero. | [9510373](https://support.google.com/google-ads/answer/9510373) |
| EU political ads | Must be declared (section 1.5). | [SA360 16501722](https://support.google.com/sa360/answer/16501722) |
| Optimization score during creation | Not documented. The score is shown for active campaigns only (Search, Display, Video Action, App, Performance Max, Demand Gen, Shopping) **(unconfirmed that any score appears during creation)**. | [9061546](https://support.google.com/google-ads/answer/9061546) |
| Ad review | "Most ads are reviewed within one business day." Statuses: "Under review", "Eligible", "Disapproved". Editing an ad restarts review. Check after 2 business days; contact support after a week. | [1722120](https://support.google.com/google-ads/answer/1722120) |
| "Eligible (limited)" | Can come from policy restrictions or from a learning period after significant changes. Distinct from "Limited by budget" and "Limited by bid strategy". | [2616012](https://support.google.com/google-ads/answer/2616012) (via search summary) |
| Learning | Bid strategy status "Learning" after creation or changes; hover shows the reason. Goal changes: up to 7 days. Performance Max: usually 1 to 2 weeks, up to 6. | [6263057](https://support.google.com/google-ads/answer/6263057), [10995103](https://support.google.com/google-ads/answer/10995103), [10724896](https://support.google.com/google-ads/answer/10724896) |
| Delivery start | Ads usually take a few days to appear; bidding may take longer to optimise. | [9510373](https://support.google.com/google-ads/answer/9510373) |

---

## 3. Performance Max, end to end

### 3.1 Steps

Google's guide has six steps ([13717903](https://support.google.com/google-ads/answer/13717903), [15862641](https://support.google.com/google-ads/answer/15862641)):

1. Create your campaign and choose a goal
2. Set your bidding preferences
3. Set your campaign settings
4. Set up your asset group and assets
5. Set your budget
6. Review and publish your campaign

Only one asset group can be set up before publishing; more are added later ([10724492](https://support.google.com/google-ads/answer/10724492)). Up to 100 Performance Max campaigns per account ([6372658](https://support.google.com/google-ads/answer/6372658)) and up to 100 asset groups per campaign ([API docs](https://developers.google.com/google-ads/api/performance-max/asset-groups)).

### 3.2 Step 1: goal, conversion goals and product feed

| Setting | Options | Default | Notes | Source |
|---|---|---|---|---|
| Objective | "Sales", "Leads", "Website traffic", "Local store visits and promotions", "Create a campaign without a goal's guidance" | | | [13717903](https://support.google.com/google-ads/answer/13717903) |
| Conversion goals | Remove defaults, add goals, set different values per goal | Account goals filled in | | [13717903](https://support.google.com/google-ads/answer/13717903) |
| Merchant Center feed | Attach the linked Merchant Center account's products for Shopping ads | Optional | With a feed, the asset minimums apply differently. Page feeds cannot be used with a Merchant Center account attached. | [13717903](https://support.google.com/google-ads/answer/13717903), [17091269](https://support.google.com/google-ads/answer/17091269), [15864837](https://support.google.com/google-ads/answer/15864837) |
| Campaign name | Text | | | [13717903](https://support.google.com/google-ads/answer/13717903) |
| Other paths | Separate guides exist for online sales or leads, website traffic, store goals, travel goals, no guidance, and feed-based retail campaigns, plus pay-per-lead goals. | | | [Options article search result](https://support.google.com/google-ads/answer/15865233), [17325051](https://support.google.com/google-ads/answer/17325051) |

### 3.3 Step 2: bidding

| Setting | Options | Default | Limits | Source |
|---|---|---|---|---|
| Focus | "Conversions" or "Conversion value" | | Google recommends Maximize conversion value if values are tracked. | [15862641](https://support.google.com/google-ads/answer/15862641) |
| Target | "Set a target cost per action"; "Set a target return on ad spend" | Target ROAS box pre-ticked with a suggested value when a recommendation exists | | [15862641](https://support.google.com/google-ads/answer/15862641) |
| Customer acquisition | "Bid for new customers only" checkbox; modes described in 2.2 | Off | Needs a segment with at least 1,000 active members in one network (this page). | [15862641](https://support.google.com/google-ads/answer/15862641), [12080169](https://support.google.com/google-ads/answer/12080169) |

### 3.4 Step 3: campaign settings (in Google's order)

| # | Setting | Options and rules | Source |
|---|---|---|---|
| 1 | Locations | Include or Exclude, "Enter another location", "Nearby", "Advanced search" for bulk or radius. | [15864837](https://support.google.com/google-ads/answer/15864837) |
| 2 | Languages | Multi-select. No longer applies to Search inventory (section 2.3.3). | [15864837](https://support.google.com/google-ads/answer/15864837), [1722078](https://support.google.com/google-ads/answer/1722078) |
| 3 | More settings | Ad scheduling, start and end dates, URL settings. | [15864837](https://support.google.com/google-ads/answer/15864837) |
| 4 | Text customization (formerly "Automatically created assets") | Google AI may generate assets from landing pages. Not available for Shopping ads. | [15864837](https://support.google.com/google-ads/answer/15864837) |
| 5 | Final URL expansion | Replaces the final URL with a more relevant page when text customization and Final URL settings are on. On by default. Not supported with store goals only. Controls: URL exclusions, URL parameter rules, account-level negatives. | [15864837](https://support.google.com/google-ads/answer/15864837), [10724492](https://support.google.com/google-ads/answer/10724492), [14670793](https://support.google.com/google-ads/answer/14670793) |
| 6 | Brand guidelines (once per campaign) | Business name (required), logos 1 to 5, brand colour(s) and font (optional). Google pre-fills from the final URL. Since April (year not stated) business names and logos are managed here. Text guidelines can also be set here or under Asset optimization. | [15864837](https://support.google.com/google-ads/answer/15864837), [14934472](https://support.google.com/google-ads/answer/14934472), [16489313](https://support.google.com/google-ads/answer/16489313) |
| 7 | Ad scheduling | Days and hours. | [15864837](https://support.google.com/google-ads/answer/15864837) |
| 8 | Brand exclusions | Apply a brand list (Search and Shopping inventory). | [15864837](https://support.google.com/google-ads/answer/15864837), [13721847](https://support.google.com/google-ads/answer/13721847) |
| 9 | Demographic exclusions | Age, gender, household income (income in beta). Age controls are fully available; gender controls launched as a beta (August 2025). | [15864837](https://support.google.com/google-ads/answer/15864837), [16451273](https://support.google.com/google-ads/answer/16451273) |
| 10 | Data exclusions | Exclude Customer Match, website visitor or Google Analytics lists from Search, Display, Shopping, Video and Discover inventory. | [15864837](https://support.google.com/google-ads/answer/15864837) |
| 11 | Campaign URL options | Only account- or campaign-level tracking templates; lower-level templates are removed. | [15864837](https://support.google.com/google-ads/answer/15864837) |
| 12 | Page feeds | Needs automatically created assets (text customization) on; not with Merchant Center. Asset groups pick URLs by custom label. | [15864837](https://support.google.com/google-ads/answer/15864837), [10724492](https://support.google.com/google-ads/answer/10724492) |
| 13 | Devices | Target or exclude computers, mobile phones, tablets, TV screens. | [15864837](https://support.google.com/google-ads/answer/15864837) |
| 14 | Negative keywords | Campaign-level negatives (2025) and shared negative keyword lists apply to Search and Shopping inventory. | [16451273](https://support.google.com/google-ads/answer/16451273) |
| 15 | Channel prioritization | Google surfaces are grouped as "Google channels"; Performance Max still has no per-channel opt-out. October 2026 rollout. | [blog.google, 14 Oct 2026](https://blog.google/products/ads-commerce/channel-prioritization-budget-allocation/) |

### 3.5 Step 4: asset group

Google publishes two different sets of numbers. The newer specification article ([17091269](https://support.google.com/google-ads/answer/17091269)) agrees with the Ad Strength article ("All 15 headline and 5 description slots", [14143250](https://support.google.com/google-ads/answer/14143250)), so it is used as current. The older step-4 guides ([15864535](https://support.google.com/google-ads/answer/15864535), [15864742](https://support.google.com/google-ads/answer/15864742)) say images up to 15, videos up to 5, one short description of 60 characters plus up to 4 long descriptions of 90.

| Asset | Required | Min | Recommended | Max | Size or length | Source |
|---|---|---|---|---|---|---|
| Final URL | Yes | 1 | 1 | | Mobile final URL optional | [17091269](https://support.google.com/google-ads/answer/17091269), [15864535](https://support.google.com/google-ads/answer/15864535) |
| Display path | No | 1 | 2 | 2 | 15 characters each | [17091269](https://support.google.com/google-ads/answer/17091269) |
| Headlines | Yes | 3 | 11 or more | 15 | 30 characters; at least one of 15 or fewer | [17091269](https://support.google.com/google-ads/answer/17091269) |
| Long headlines | Yes | 1 | 2 or more | 5 | 90 characters | [17091269](https://support.google.com/google-ads/answer/17091269) |
| Descriptions | Yes | 2 | 4 or more | 5 | 90 characters (older guide: one of 60 or fewer) | [17091269](https://support.google.com/google-ads/answer/17091269), [15864535](https://support.google.com/google-ads/answer/15864535) |
| Business name | Yes | | | | 25 characters; must match domain or verified legal name | [17091269](https://support.google.com/google-ads/answer/17091269) |
| Call to action | Yes | | 1 | | Automated or chosen from a list | [17091269](https://support.google.com/google-ads/answer/17091269) |
| Landscape image 1.91:1 | Yes | 4 | 4 or more | 20 (shared image cap) | Min 600x314, recommended 1200x628, 5,120 KB | [17091269](https://support.google.com/google-ads/answer/17091269) |
| Square image 1:1 | Yes | 4 | 4 or more | 20 | Min 300x300, recommended 1200x1200, 5,120 KB | [17091269](https://support.google.com/google-ads/answer/17091269) |
| Portrait image 4:5 | No | 2 | 2 or more | 20 | Min 480x600, recommended 960x1200 | [17091269](https://support.google.com/google-ads/answer/17091269) |
| Square logo 1:1 | Yes | 1 | 1 | 5 (all logos) | Min 128x128, recommended 1200x1200 | [17091269](https://support.google.com/google-ads/answer/17091269) |
| Landscape logo 4:1 | No | 1 | 1 | 5 (all logos) | Min 512x128, recommended 1200x300 | [17091269](https://support.google.com/google-ads/answer/17091269) |
| Videos (16:9, 1:1, 9:16) | No | | 1 of each orientation | 15 (the table lists 15 against each orientation; whether 15 is per orientation or in total is **(unconfirmed)**) | 10 seconds or more | [17091269](https://support.google.com/google-ads/answer/17091269) |
| Auto-generated video | | | | | If no video is uploaded, Google may generate one. Upload all three orientations to avoid it and to reach "Excellent". | [17091269](https://support.google.com/google-ads/answer/17091269), [14143250](https://support.google.com/google-ads/answer/14143250) |
| Other assets | | | | | Sitelinks, promotions, prices, locations and similar. | [15864535](https://support.google.com/google-ads/answer/15864535) |
| Asset group URL options | | | | | Tracking template, final URL suffix, custom parameters. | [10724492](https://support.google.com/google-ads/answer/10724492) |
| Listing groups (with a feed) | | | | 1,000 per asset group | | [6372658](https://support.google.com/google-ads/answer/6372658) |

Image file formats: JPG or PNG, max 5 MB ([17091269](https://support.google.com/google-ads/answer/17091269)). Double-width characters count as 2 ([17091269](https://support.google.com/google-ads/answer/17091269)). A generative AI asset builder exists for asset groups ([14150602](https://support.google.com/google-ads/answer/14150602), title only; contents not read).

### 3.6 Audience signals and search themes

| Setting | Options | Default | Limits | Source |
|---|---|---|---|---|
| Audience signal | Named audience built from: "Your customers' interactions with your business" (website visitors, app users, customer lists, video viewers, Firebase); "Your custom audience segments" (keywords, similar URLs, app names); "Demographics"; "Additional audience segments" (detailed demographics, life events, affinity, in-market) | Optional | Lists need more than 1,000 active users (the creation guide says over 100 active users in 30 days). Lists refresh every 540 days; 24 to 72 hours to populate; up to 2 weeks to learn. Performance Max may serve outside the signals. | [14753570](https://support.google.com/google-ads/answer/14753570), [10724896](https://support.google.com/google-ads/answer/10724896), [15864742](https://support.google.com/google-ads/answer/15864742) |
| Search themes | Free-text themes, entered under "Signals" | Optional | Up to 50 per asset group (raised from 25 in 2025). Same priority as phrase and broad keywords in Search campaigns. Exclusions and negatives still apply. Character limit **(unconfirmed)**. | [14767319](https://support.google.com/google-ads/answer/14767319), [16451273](https://support.google.com/google-ads/answer/16451273) |

### 3.7 Store goals

| Item | Detail | Source |
|---|---|---|
| Objective | "Local store visits and promotions". | [10724896](https://support.google.com/google-ads/answer/10724896) |
| Locations | Link a Google Business Profile for location assets; affiliate locations available for chains. | [10724896](https://support.google.com/google-ads/answer/10724896), [2404182](https://support.google.com/google-ads/answer/2404182) |
| Final URL expansion | Not supported if only store goals (store visits, contacts, direction clicks) are added. | [15864837](https://support.google.com/google-ads/answer/15864837) |
| Local promotions | Required: promotion type, amount, item, logo, image, business name, description. Optional: code (QR, barcode or alphanumeric), dates, terms. Serves only with an offline conversion goal; not with an omnichannel goal plus Merchant Center feed. Saves report as "Business Profile - Save Coupon". | [15864742](https://support.google.com/google-ads/answer/15864742) |
| Location asset sets | 5 per asset group. | [6372658](https://support.google.com/google-ads/answer/6372658) |

### 3.8 Steps 5 and 6: budget, review, Ad Strength

| Item | Detail | Source |
|---|---|---|
| Budget | Average daily budget, or optional campaign total budget (3 to 90 days). Google advises at least 3 times the CPA. | [15864652](https://support.google.com/google-ads/answer/15864652), [15137812](https://support.google.com/google-ads/answer/15137812) |
| Review | Summary page, then "Publish campaign". In CSS countries, any Comparison Shopping Service can be used. | [15864745](https://support.google.com/google-ads/answer/15864745) |
| Ad review | New or edited ads are reviewed within 1 to 2 days. No impressions after 3 business days means troubleshooting. | [10724896](https://support.google.com/google-ads/answer/10724896) |
| Ad Strength | Same five labels. "Poor" serves on only some inventory; "Average" and above can serve everywhere. "Excellent" needs every asset type, at least 6 sitelinks, own videos in three orientations, 15 headlines and 5 descriptions. Generated text counts. | [14143250](https://support.google.com/google-ads/answer/14143250) |
| Reporting (2025) | Search terms report, full asset stats, final URL expansion asset report, channel performance report (beta from GML 2025). | [16451273](https://support.google.com/google-ads/answer/16451273) |

---

## 4. Demand Gen, Display, Video, Shopping, App and Smart

### 4.1 Demand Gen

Six steps ([13695389](https://support.google.com/google-ads/answer/13695389)):

| Step | Settings | Source |
|---|---|---|
| 1. New campaign | Campaign name; optional "Run a product feed campaign" toggle; conversion goals. | [13695389](https://support.google.com/google-ads/answer/13695389) |
| 2. Goal | "Sales", "Leads", "Website Traffic", "YouTube reach, views, and engagements", or no guidance. | [13695389](https://support.google.com/google-ads/answer/13695389) |
| 3. Campaign targeting | Devices: all eligible, or computers, mobile phones, tablets, TV screens; advanced OS, device model and network targeting for mobile and tablet. "Enable campaign level location and language targeting" (cannot go back to ad group level after publishing). | [13695389](https://support.google.com/google-ads/answer/13695389) |
| 4. Bidding and budget | "Maximize conversion value", "Target Return on ad spend (TROAS) bidding", "Maximize Conversions", "Target Cost Per Action (CPA)", "Maximize Clicks"; Target CPC appears only when the goal is Clicks, settable at campaign or ad group level. Daily (dates optional) or total budget (dates required; 7 days to 1 year). Google suggests a daily budget of at least 10x the target CPA. Budget panel offers Low, Medium, High with forecasts. | [13695389](https://support.google.com/google-ads/answer/13695389), [16262529](https://support.google.com/google-ads/answer/16262529), [15137812](https://support.google.com/google-ads/answer/15137812), [13695777](https://support.google.com/google-ads/answer/13695777) |
| 5. Ad group | Channels: "All Google channels" (optionally add the Display Network) or "Let me choose": YouTube (in-stream, in-feed, Shorts), Discover, Gmail, Maps, Display Network. Google recommends All Google channels. Maps serves only with a non-affiliate location asset. Audiences: custom segments, data segments, lookalike segments, interests, detailed demographics; exclusions; demographics. "Optimized targeting" on by default and recommended. | [13695389](https://support.google.com/google-ads/answer/13695389), [15973205](https://support.google.com/google-ads/answer/15973205) |
| 6. Ads | "Ad name"; types "Video ad", "Image ad", "Carousel ad", "Classic display" (under "More options"). Image and Video are pre-selected. Up to 5 logos. Optional Video Builder. | [13695389](https://support.google.com/google-ads/answer/13695389) |

Demand Gen asset specs:

| Format | Specs | Source |
|---|---|---|
| Single image ad | Headlines up to 5, 40 characters; descriptions up to 5, 90 characters; business name 25; 1 square logo (min 144x144, 150 KB); up to 20 images (1:1, 1.91:1, 4:5, 9:16), 5 MB | [17140672](https://support.google.com/google-ads/answer/17140672), [13704860](https://support.google.com/google-ads/answer/13704860) |
| Carousel ad | 2 to 10 cards with consistent ratio; ad headline and description 40 each; card headline 40 (not on Discover); separate URL per card; not with a product feed | [17140672](https://support.google.com/google-ads/answer/17140672) |
| Video ad | 1 to 5 videos per ad, at least 5 seconds (under 10 seconds will not serve in YouTube in-stream); descriptions 90; business name 25 | [13704860](https://support.google.com/google-ads/answer/13704860), [17141078](https://support.google.com/google-ads/answer/17141078) (search summary) |
| Image sizes | 1:1 min 300x300; 1.91:1 min 600x314; 4:5 min 480x600; 9:16 min 600x1067 | [13704860](https://support.google.com/google-ads/answer/13704860) |

Other: brand suitability is set at account level ("Content Suitability"), not per campaign ([13695777](https://support.google.com/google-ads/answer/13695777)). Frequency controls for Demand Gen are **(unconfirmed)**. Demand Gen expands to Google Maps (announced GML 2026) ([PPC Land, 20 May 2026](https://ppc.land/google-marketing-live-2026-every-announcement-that-actually-matters)).

### 4.2 Display (being folded into Demand Gen)

| Item | Detail | Source |
|---|---|---|
| Status | From June 2026, a migration tool moves Display campaigns into Demand Gen. Later, "New campaigns can only be created within Demand Gen", and remaining campaigns migrate automatically into 2027. The creation cutoff date is not given by Google (one third party says January 2027, **unconfirmed**). | [13695777](https://support.google.com/google-ads/answer/13695777), [SEJ, 26 May 2026](https://www.searchenginejournal.com/google-is-retiring-standalone-display-campaigns-in-favor-of-demand-gen/) |
| Steps today | Objective and "Standard display campaign" subtype; business website URL and name; locations and languages; additional settings (ad rotation, schedule, devices, URL options, content exclusions, dynamic ads, dates, conversions); budget and bidding (Target CPA, Maximize conversions, Maximize clicks, Viewable CPM, Manual CPC); targeting (optimized targeting, audience segments, keywords); ads; review. | [10759203](https://support.google.com/google-ads/answer/10759203) |
| Smart Display | Migrated automatically into standard Display. | [10759203](https://support.google.com/google-ads/answer/10759203) |
| Optimized targeting | Default; to turn off, add signals first, then untick "Use optimized targeting". | [10759203](https://support.google.com/google-ads/answer/10759203) (search summary) |
| Responsive display ad | Landscape 1.91:1 (1200x628, min 600x314) and square (1200x1200, min 300x300) images, 5,120 KB; logos 4:1 (1200x300, min 512x128) and square (min 128x128); short headlines 1 to 5 at 30 characters; one long headline at 90; descriptions 1 to 5 (character limit not stated); business name; final URL; optional CTA and YouTube videos. | [7005917](https://support.google.com/google-ads/answer/7005917) |
| Uploaded image ads | JPG, PNG or non-animated GIF up to 150 KB; sizes such as 300x250, 336x280, 728x90, 970x90, 160x600, 300x600, 320x50. | [13704860](https://support.google.com/google-ads/answer/13704860) |

### 4.3 Video (YouTube)

| Item | Detail | Source |
|---|---|---|
| Objectives | "Sales", "Leads", "Website traffic", "YouTube reach, views, and engagements". The subscriptions and engagements goal uses the Demand Gen flow. | [2375497](https://support.google.com/google-ads/answer/2375497) |
| Subtypes | Video views ("Pay only for views"); Video reach with "Efficient reach", "Non-skippable", "Target frequency"; "Ad sequence"; Audio reach; reservation buying ("Premier reach", "Masthead", "Standard reach"). | [2375497](https://support.google.com/google-ads/answer/2375497), [10197127](https://support.google.com/google-ads/answer/10197127) |
| Bidding | Target CPV, CPM, vCPM, Target CPA, Target ROAS, Maximize conversions, Maximize conversion value, Manual CPC, ECPC, Maximize clicks (as listed). | [2375497](https://support.google.com/google-ads/answer/2375497) |
| Budget | Daily or campaign total (dates required; total 7 days to 1 year). | [2375497](https://support.google.com/google-ads/answer/2375497), [15137812](https://support.google.com/google-ads/answer/15137812) |
| Networks | YouTube (search results, videos, channel pages, home page, Playables), video partners on the Display Network, Google TV (US only). | [2375497](https://support.google.com/google-ads/answer/2375497) |
| Content suitability | Account-level inventory types "Expanded", "Standard", "Limited" (Standard suggested for most brands); content type and label exclusions (for example live streams, embedded videos). | [7515513](https://support.google.com/google-ads/answer/7515513), [12764663](https://support.google.com/google-ads/answer/12764663) (both via search summary) |
| Frequency | Frequency caps set at campaign level only; all formats in the campaign count. Target frequency: weekly 2 to 7 or monthly 4 to 12, not a cap. Video campaign groups: weekly target 2 to 7, recommended 3. | [6034106](https://support.google.com/google-ads/answer/6034106), [17114478](https://support.google.com/google-ads/answer/17114478) (via search summaries) |
| Devices and schedule | Computers, mobile, tablets, TV screens; ad schedule under additional settings. | [2375497](https://support.google.com/google-ads/answer/2375497) |
| Ad group targeting | Demographics (age, gender, parental status, household income), audience segments, keywords, topics, placements. | [2375497](https://support.google.com/google-ads/answer/2375497) |
| Formats | Skippable in-stream (skip after 5 seconds); non-skippable in-stream (up to 30 seconds; 15 in reach); bumper (6 seconds); Shorts (at least 5 seconds); in-feed (long headline and description); out-stream. Companion banners on computers only. | [2375497](https://support.google.com/google-ads/answer/2375497) |
| Metric rename | "Views" is now "TrueView views". | [2375497](https://support.google.com/google-ads/answer/2375497) |

### 4.4 Shopping

| Step | Detail | Source |
|---|---|---|
| Objective | Sales, Leads, Website traffic, Local store visits and promotions, or no guidance. | [3455481](https://support.google.com/google-ads/answer/3455481) |
| Merchant Center | Pick the linked account; it cannot be changed after creation. Optional data sources by feed label; vehicle feeds if approved. | [3455481](https://support.google.com/google-ads/answer/3455481) |
| Budget and bidding | Daily or total budget; automated bidding (Maximize clicks and Target ROAS confirmed by Google; Maximize conversion value reported in 2026 by a third party); customer acquisition option; campaign priority (only when products overlap). Priority labels: SA360 shows Medium or High, API uses 0 to 2 **(Google Ads UI labels unconfirmed)**. | [3455481](https://support.google.com/google-ads/answer/3455481), [6309038](https://support.google.com/google-ads/answer/6309038), [6309035](https://support.google.com/google-ads/answer/6309035), [techwyse, 2026](https://www.techwyse.com/news/platform-updates/google-maximize-conversion-value-standard-shopping), [SA360 4601672](https://support.google.com/ds/answer/4601672) |
| Settings | Locations; start and end dates; URL options; networks (Google Search and search partners by default); channel prioritization with High or Low tiers and optional Low-priority budget percentage. | [3455481](https://support.google.com/google-ads/answer/3455481) |
| Local inventory | Local inventory ads "will soon run by default"; review inventory filters before August 2026 to keep budgets separate. | [3455481](https://support.google.com/google-ads/answer/3455481) |
| Ad group | Name (and bid if Manual CPC); product ads are built from feed data; product groups optional. | [3455481](https://support.google.com/google-ads/answer/3455481) |
| AI Max for Shopping (beta, announced 30 April 2026) | Text customization (rewrites product titles, English feeds only), Final URL expansion (needs text customization and Target ROAS), up to 25 term exclusions and 40 messaging restrictions, brand exclusions, URL exclusions. One-click toggle. | [17091277](https://support.google.com/google-ads/answer/17091277), [blog.google](https://blog.google/products/ads-commerce/ai-max-for-shopping/) |

### 4.5 App

| Item | Detail | Source |
|---|---|---|
| Subtypes | "App campaigns for installs (ACi)", "App campaigns for engagement (ACe)", "App campaigns for pre-registration (ACPre)". | [6247380](https://support.google.com/google-ads/answer/6247380) |
| Inputs | Select the app, text, starting bid and budget, languages and locations. Store listing assets are pulled automatically. | [6247380](https://support.google.com/google-ads/answer/6247380) |
| Bidding | "What do you want to focus on?": Install volume, in-app actions, in-app action value; optional target cost per install, target CPA, target ROAS (needs Firebase). | [12073727](https://support.google.com/google-ads/answer/12073727) (via search summary) |
| Where ads show | Google Search and search partners, Google Play, YouTube, Display Network (Gmail, apps, sites), Discover. | [6247380](https://support.google.com/google-ads/answer/6247380) |
| Assets | Up to 5 headlines (30) and 5 descriptions (90); YouTube-hosted videos in any orientation; images 1:1 (min 200x200), 1.91:1 (min 600x314), 4:5 (min 320x400), 5 MB; HTML5 ZIP up to 5 MB, 512 files, 20 per ad group; custom store listing pages for Android installs. Image and video counts **(unconfirmed)**. | [9948381](https://support.google.com/google-ads/answer/9948381) |
| Learning | Changes before 100 conversions can disrupt learning. | [6247380](https://support.google.com/google-ads/answer/6247380) |
| Ad groups per campaign | 100. | [6372658](https://support.google.com/google-ads/answer/6372658) |

### 4.6 Smart campaigns

| Item | Detail | Source |
|---|---|---|
| UI | Created only in Smart Mode. Keyword themes (aim for 7 to 10), an ad (3 to 15 headlines at 30 characters, 2 to 4 descriptions at 90), budget. Ads show on Search, Maps, YouTube, partner sites and Display. Google generates sitelinks and alternate ads. | [7652860](https://support.google.com/google-ads/answer/7652860), [9263830](https://support.google.com/google-ads/answer/9263830) |
| API | No new Smart campaigns via the API from 23 September 2026 (moved from 5 August). Existing ones keep serving and can be edited. Google points to Performance Max, Search or Demand Gen instead. | [Google Ads developer blog, 23 Jun 2026, updated 13 Aug 2026](https://developers.google.com/ads/blog/posts/2026/06/changes-to-support-for-smart-campaigns) |
| New advertisers in the UI | Whether a brand-new advertiser can still create a Smart campaign in the web UI is **(unconfirmed)**. | |

---

## 5. Other things a faithful rebuild must not miss

### 5.1 Prerequisites and prompts

| Item | Detail | Source |
|---|---|---|
| Conversion tracking | Prompted when choosing a goal if not set up; a conversion action can be created inside the flow. Performance Max can run without tracking but spend may be limited; allow 24 to 48 hours after setup. | [10995481](https://support.google.com/google-ads/answer/10995481), [10724896](https://support.google.com/google-ads/answer/10724896) |
| Billing | Review flags billing problems before publishing. | [9510373](https://support.google.com/google-ads/answer/9510373) |
| Advertiser verification | Needed for business name and logo assets, and for some lead form uses (with spend thresholds of more than $1,000 per account or $15,000 across accounts for Display or direct-to-form Search). | [12497613](https://support.google.com/google-ads/answer/12497613), [9423234](https://support.google.com/google-ads/answer/9423234) |
| Brand library | Brands not in the library can be requested. | [13721847](https://support.google.com/google-ads/answer/13721847) |

### 5.2 Auto-applied recommendations

Auto-apply is managed from the Recommendations page; the day's queue can be reviewed and items dismissed. Types include "Improve your Responsive Search Ads", "Add broad match keywords", "Expand your reach with Google search partners", "Use Display expansion", bidding changes ("Set a target CPA", "Adjust your ROAS targets" and others) and "Upgrade your conversion tracking". "Add responsive search ads" was removed from auto-apply on 26 January 2026. Budget raising is not included. The default state is not stated ([10279006](https://support.google.com/google-ads/answer/10279006)).

### 5.3 Policy review

See 2.9. Also: lead form, image and business name assets have their own eligibility checks (2.7), and phone numbers are verified ([2453991](https://support.google.com/google-ads/answer/2453991)). Demand Gen ads marked "Eligible (limited)" for "Implied Interactivity" must be fixed before they serve ([13695777](https://support.google.com/google-ads/answer/13695777)).

### 5.4 Optimization score

Scores run 0 to 100% and show at campaign, account and manager level for active campaigns ([9061546](https://support.google.com/google-ads/answer/9061546)). No source shows a score during creation **(unconfirmed)**.

### 5.5 2025 and 2026 changes that affect the creation flow

| When | Change | Source |
|---|---|---|
| 31 Mar 2025 | Enhanced CPC no longer available for Search and Display. | [2979071](https://support.google.com/google-ads/answer/2979071) |
| May 2025 | AI Max for Search announced (beta). | [blog.google](https://blog.google/products/ads-commerce/google-ai-max-for-search-campaigns/) |
| 21 May 2025 | "Power Pack": AI Max for Search, Performance Max and Demand Gen promoted together. | [16290177](https://support.google.com/google-ads/answer/16290177) (via search summary), [WordStream](https://www.wordstream.com/blog/2025-google-ads-updates) |
| 2025 | Performance Max: search themes 25 to 50; campaign-level negatives and shared lists; device targeting; age controls; gender beta; full asset reporting (summary post 7 Aug 2025). | [16451273](https://support.google.com/google-ads/answer/16451273) |
| Jul 2025 | Brand inclusions and exclusions in new Search campaigns moved under AI Max. | [browsermedia.agency, 23 Jul 2025](https://browsermedia.agency/blog/google-locks-brand-controls-behind-ai-max/) |
| Sep 2025 | EU political ads declaration required. | [SA360 16501722](https://support.google.com/sa360/answer/16501722) |
| 2025 | Smart Bidding Exploration for Search (Target ROAS tolerance 5 to 30%). | [16294612](https://support.google.com/google-ads/answer/16294612) |
| 15 Jan 2026 | Campaign total budgets for Search, Performance Max and Shopping (open beta). | [blog.google](https://blog.google/products/ads-commerce/campaign-total-budgets/) |
| 26 Jan 2026 | "Add responsive search ads" removed from auto-apply. | [10279006](https://support.google.com/google-ads/answer/10279006) |
| Apr 2026 | AI Max out of beta; upgrade tools for DSA, automatically created assets and broad match. Performance Max business name and logos moved into brand guidelines "as of April". | [business.google.com](https://business.google.com/us/accelerate/announcements/dsa-upgrade-to-ai-max-2026/), [14934472](https://support.google.com/google-ads/answer/14934472) |
| 30 Apr 2026 | AI Max for Shopping (beta). | [17091277](https://support.google.com/google-ads/answer/17091277), [blog.google](https://blog.google/products/ads-commerce/ai-max-for-shopping/) |
| 20 May 2026 | Google Marketing Live 2026: AI Brief (natural-language guidance for AI Max, later Performance Max), Ask Advisor, Asset Studio updates, Demand Gen on Maps, creator partnerships in campaign setup. Availability dates mostly not given. | [PPC Land, 20 May 2026](https://ppc.land/google-marketing-live-2026-every-announcement-that-actually-matters) |
| 1 Jun 2026 | Ad schedule pacing change. | [16913225](https://support.google.com/google-ads/answer/16913225) |
| Jun 2026 | Bid strategy labels renamed to "Target CPA" and "Target ROAS". Display-to-Demand Gen migration tool. | [13717096](https://support.google.com/google-ads/answer/13717096), [13695777](https://support.google.com/google-ads/answer/13695777) |
| 3 Aug 2026 | No new campaign-level broad match or legacy automatically created assets. | [relevantaudience.com, 2026](https://www.relevantaudience.com/google-ads-en/google-blocks-new-broad-match-settings-ai-max-migration/) |
| 17 Aug 2026 | Target CPA and Target ROAS hold targets more strictly when budget-limited. | [PPC Land, 2026](https://ppc.land/google-ads-gets-promotion-mode-and-a-major-bidding-overhaul-this-august/) |
| 1 Sep 2026 | Automatic upgrade of broad match setting and automatically created assets campaigns to AI Max. No new DSA campaigns. | [PPC Land, 6 Aug 2026](https://ppc.land/google-ads-broad-match-campaigns-face-ai-max-auto-upgrade-on-september-1/), [business.google.com](https://business.google.com/us/accelerate/announcements/dsa-upgrade-to-ai-max-2026/) |
| Late Sep 2026 | Campaign-level language targeting removed for Search and for Performance Max Search inventory. | [1722078](https://support.google.com/google-ads/answer/1722078) |
| 23 Sep 2026 | No new Smart campaigns via the API. | [developer blog](https://developers.google.com/ads/blog/posts/2026/06/changes-to-support-for-smart-campaigns) |
| 14 Oct 2026 | Channel prioritization and budget allocation for Search, Shopping, Performance Max, Demand Gen (rolling out). | [blog.google](https://blog.google/products/ads-commerce/channel-prioritization-budget-allocation/) |
| Feb 2027 (planned) | DSA automatic upgrade to AI Max; Search plus Display Network spend split removed. | [7166527](https://support.google.com/google-ads/answer/7166527), [blog.google](https://blog.google/products/ads-commerce/channel-prioritization-budget-allocation/) |

---

## 6. The five things most easily missed

1. **AI Max is on by default for every new Search campaign** ([15909989](https://support.google.com/google-ads/answer/15909989)). It turns on search term matching, text customization and Final URL expansion together, which means pins are ignored ([15913066](https://support.google.com/google-ads/answer/15913066)), brand lists live only inside it ([browsermedia.agency, 2025](https://browsermedia.agency/blog/google-locks-brand-controls-behind-ai-max/)), and the old broad match setting no longer exists ([relevantaudience.com, 2026](https://www.relevantaudience.com/google-ads-en/google-blocks-new-broad-match-settings-ai-max-migration/)).
2. **Several settings and types are gone in late 2026 and should not be rebuilt:** campaign-level language for Search ([1722078](https://support.google.com/google-ads/answer/1722078)), new Dynamic Search Ads ([business.google.com](https://business.google.com/us/accelerate/announcements/dsa-upgrade-to-ai-max-2026/)), Enhanced CPC ([2979071](https://support.google.com/google-ads/answer/2979071)), Smart campaigns via the API ([developer blog](https://developers.google.com/ads/blog/posts/2026/06/changes-to-support-for-smart-campaigns)), and soon standalone Display ([13695777](https://support.google.com/google-ads/answer/13695777)). Google's own "Create a Search campaign" guide still shows some of these ([9510373](https://support.google.com/google-ads/answer/9510373)).
3. **Conversion goals are inherited, not chosen from scratch.** Account-default goals are pre-selected, a Search campaign needs at least one goal even without guidance, and only one custom goal is allowed per campaign ([10995481](https://support.google.com/google-ads/answer/10995481), [9510373](https://support.google.com/google-ads/answer/9510373)).
4. **The EU political ads declaration is mandatory on every campaign**, with exact "No, this campaign doesn't have EU political ads" wording, and a "Yes" stops the campaign serving in the EU ([SA360 16501722](https://support.google.com/sa360/answer/16501722)).
5. **Budget rules shape what the advertiser is told:** spend can reach 2x the daily budget on a day but never more than 30.4x in a month ([2375454](https://support.google.com/google-ads/answer/2375454)); a total budget needs dates (3 to 90 days for Search), and the budget type cannot be changed once the start date is set ([15137812](https://support.google.com/google-ads/answer/15137812)); search partners are on by default ([1722047](https://support.google.com/google-ads/answer/1722047)).
