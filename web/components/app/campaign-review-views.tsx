import { Button } from "@/components/ui/button";
import { AppShell, type Workspace } from "./shell";
import {
  ActionPanel,
  ActivityRow,
  AdMock,
  Columns,
  DropZone,
  Footnote,
  Gallery,
  LinkRow,
  ListRow,
  Meter,
  MiniBars,
  NoticeCard,
  PageHead,
  Panel,
  PanelText,
  Rows,
  StatusPill,
  Summary,
  Tile,
  Tiles,
  ValueRow,
} from "./blocks";
import { DetailPage, type DetailSpec } from "./detail-page";

/*
  The campaign review: what the owner reads before launch (the preview, the
  searches, the ads and their checks, why this shape, Performance Max images), and
  the Summit Heating takeover (the plan, the five campaigns, the leaks, the first
  month, the keyword tidy-up, the ad test, the five-week result).
*/

const alpha: Workspace = { name: "Alpha Plumbing", meta: "Mississauga, Ontario" };
const birch: Workspace = { name: "Birch & Wick Candles", meta: "Hamilton, Ontario" };
const summit: Workspace = { name: "Summit Heating & Cooling", meta: "Brampton, Ontario" };

/* ---------- 17:2048 ---------- */
export function Built() {
  return (
    <AppShell active="campaigns" workspace={alpha} badges={{}}>
      <PageHead
        title="Here's the campaign we built for you."
        lead="Read it in plain English and change anything you like. Nothing goes live, and nothing costs money, until you approve it."
      />
      <Tiles>
        <Tile tone="brand" label="Daily budget" value="$40" chip="About $1,200 a month" />
        <Tile label="Search themes" value="4" chip="Taken from your own website" />
        <Tile label="Ads written" value="3" chip="Google shows the best one" />
        <Tile label="Ready to launch" value="2 of 3" progress={150 / 226} />
      </Tiles>
      <Columns
        aside={
          <>
            <NoticeCard
              tag="One thing left"
              title="Add a payment method on Google"
              body="Google takes card details on their own site, and only they can. It takes about three minutes. Your account is linked and call counting is working, so this is the last step."
              primary={{ label: "Add on Google" }}
              secondary={{ label: "Later" }}
            />
            <Panel title="Searches we'll never pay for">
              <Rows className="mt-1">
                <ListRow
                  title="hiring, careers, wages"
                  meta="People looking for work, not a plumber"
                  chip="Never"
                  dot
                />
                <ListRow
                  title="free, how to fix, tutorial"
                  meta="People fixing it themselves"
                  chip="Never"
                  dot
                />
              </Rows>
            </Panel>
          </>
        }
      >
        <Panel title="In one sentence" action={{ label: "Edit any part", tone: "brand" }}>
          <Summary>
            We&rsquo;ll show your ad to people within 25 km of Mississauga who search for things
            like emergency plumber, water heater repair and drain cleaning. You&rsquo;ll spend up to
            $40 a day, and every click goes to alphaplumbing.ca where people can call you.
          </Summary>
        </Panel>
        <Panel title="What people will search to find you" action={{ label: "Edit keywords" }}>
          <Rows>
            <ActivityRow
              icon="bars"
              iconTone="brand"
              title="Emergency plumbing"
              meta="emergency plumber mississauga, 24 hour plumber, plumber open now"
              action="Edit"
            />
            <ActivityRow
              icon="plus"
              iconTone="brand"
              title="Water heaters"
              meta="water heater repair, water heater installation, tankless water heater"
              action="Edit"
            />
            <ActivityRow
              icon="line"
              iconTone="brand"
              title="Drains and leaks"
              meta="drain cleaning, clogged drain, leak repair"
            />
          </Rows>
        </Panel>
        <Panel title="Your ad, as people will see it" action={{ label: "Edit wording" }}>
          <AdMock
            kicker="Sponsored"
            source={<>Alpha Plumbing&nbsp;&nbsp;&nbsp;&nbsp;alphaplumbing.ca</>}
            headline="Emergency Plumber Mississauga | Same-Day Repairs"
            headlineTone="link"
            body="Licensed plumbers available today. Water heaters, drains and leaks fixed right the first time. Call now for a free quote."
          />
          <Footnote>
            Three versions of this ad rotate. Google shows whichever brings the most calls.
          </Footnote>
        </Panel>
      </Columns>
    </AppShell>
  );
}

/* ---------- 42:4772 ---------- */
export function SearchesWhy() {
  return (
    <AppShell active="campaigns" workspace={alpha} badges={{}}>
      <PageHead
        title="Every search we will pay for, and why."
        lead="Google offered 261 search terms for a plumber in Mississauga. We kept 47. Here is what survived, what we threw out, and the reason for each."
      />
      <Tiles>
        <Tile tone="brand" label="Terms kept" value="47" chip="Out of 261 Google offered" />
        <Tile label="Search themes" value="4" chip="One ad group each" />
        <Tile label="Typical cost a click" value="$9.40" chip="Google's own estimate" />
        <Tile label="Words we block" value="312" progress={196 / 226} />
      </Tiles>
      <Columns
        aside={
          <>
            <NoticeCard
              tone="brand"
              tag="312 blocked"
              title="Words that stop your ad showing"
              body="Three lists. One we keep for every business, one for plumbers, and one built from your own site where you say what you do not do."
              primary={{ label: "See the list" }}
              secondary={{ label: "Add one" }}
            />
            <Panel title="Never pay for">
              <Rows className="mt-1">
                <ListRow
                  title="hiring, careers"
                  meta="People looking for work, not a plumber"
                  chip="Master"
                  dot
                />
                <ListRow
                  title="plumbing school, how to fix"
                  meta="People doing it themselves"
                  chip="Plumbers"
                  dot
                />
              </Rows>
            </Panel>
          </>
        }
      >
        <Panel title="How we chose" action={{ label: "Change the rules", tone: "brand" }}>
          <Summary>
            We kept terms people really search for near you, dropped anything so dear that three
            clicks would eat your whole day, and refused competitor names because bidding on them
            invites a trademark complaint.
          </Summary>
        </Panel>
        <Panel title="The four themes, and what is in them" action={{ label: "Edit keywords" }}>
          <Rows>
            <ActivityRow
              icon="bars"
              iconTone="brand"
              title="Emergency plumbing · 18 terms"
              meta="emergency plumber mississauga · 880 searches a month · about $11.20 a click"
              action="Edit"
            />
            <ActivityRow
              icon="plus"
              iconTone="brand"
              title="Water heaters · 12 terms"
              meta="water heater repair · 590 searches a month · about $8.60 a click"
              action="Edit"
            />
            <ActivityRow
              icon="line"
              iconTone="brand"
              title="Drains and leaks · 11 terms"
              meta="drain cleaning mississauga · 320 searches a month · about $7.90 a click"
            />
            <ActivityRow
              icon="line"
              iconTone="brand"
              title="Frozen and burst pipes · 6 terms"
              meta="burst pipe repair · 140 searches a month · about $12.80 a click"
            />
          </Rows>
        </Panel>
        <Panel title="What we threw out" action={{ label: "See all 214" }}>
          <AdMock
            kicker="Too rare to bother with"
            source="141 terms · fewer than 10 searches a month in your area"
            headline="Too dear for a $40 day"
            body={
              <>
                52 terms. One click would have cost more than a third of your daily budget.
                &ldquo;emergency plumbing services toronto&rdquo; came back at $31 a click, and
                Toronto is outside your radius anyway.
              </>
            }
          />
          <Footnote>
            We also left out 21 competitor names. Bidding on a rival&rsquo;s brand invites a
            trademark complaint and rarely pays.
          </Footnote>
        </Panel>
        <Panel title="Competitors' names" action={{ label: "Why" }} tone="plain">
          <PanelText>
            We left out 21 competitor names. Bidding on another company&rsquo;s name can break
            Google&rsquo;s trademark rules, and it usually costs more for fewer calls.
          </PanelText>
          <Rows className="mt-1">
            <ListRow
              title="Drain King Plumbing"
              meta="About 90 searches a month nearby"
              chip="Left out"
            />
            <ListRow
              title="Peel Pipe Pros"
              meta="About 40 searches a month nearby"
              chip="Left out"
            />
          </Rows>
          <Button variant="secondary" size="sm" className="border-line mt-4 h-11">
            Allow one anyway
          </Button>
        </Panel>
      </Columns>
    </AppShell>
  );
}

/* ---------- 42:4941 ---------- */
export function AdsRules() {
  return (
    <AppShell active="campaigns" workspace={alpha} badges={{}}>
      <PageHead
        title="The ads, and the rules they had to pass."
        lead="Google counts every character and refuses a long list of things you may not say. Every line below came off your own pages, then went through the checks."
      />
      <Tiles>
        <Tile tone="brand" label="Headlines written" value="12" chip="Google wants 3, allows 15" />
        <Tile label="Descriptions" value="4" chip="The most Google allows" />
        <Tile label="Rewritten after checks" value="3" chip="Two too long, one unprovable" />
        <Tile label="Longest headline" value="29 of 30" progress={218 / 226} />
      </Tiles>
      <Columns
        aside={
          <>
            <NoticeCard
              tone="red"
              tag="Never"
              title="What we will not put in an ad"
              body="Prices we cannot verify, guarantees you never offered, a rival's name, or work your licence does not cover. Google refuses these too, but we would rather catch it here than have your ad rejected."
              primary={{ label: "See the rules" }}
              primaryTone="red"
              secondary={{ label: "Edit" }}
            />
            <Panel title="Links and buttons under the ad">
              <Rows className="mt-1">
                <ListRow
                  title="4 sitelinks"
                  meta="Each opens its own page"
                  chip="Ready"
                  chipTone="pale"
                  dot
                />
                <ListRow
                  title="Call button"
                  meta="(905) 555-0142, tracked"
                  chip="Ready"
                  chipTone="pale"
                  dot
                />
              </Rows>
            </Panel>
          </>
        }
      >
        <Panel title="How Google shows these" action={{ label: "Edit wording", tone: "brand" }}>
          <Summary>
            You do not get one fixed ad. Google mixes your headlines and descriptions into different
            combinations and keeps showing whichever brings the most calls, so every single line has
            to make sense on its own.
          </Summary>
        </Panel>
        <Panel
          title="Your headlines, and the room Google gives you"
          action={{ label: "Edit headlines" }}
        >
          <Rows>
            <ActivityRow
              icon="bars"
              iconTone="brand"
              title="Emergency Plumber Mississauga"
              meta="29 of 30 characters · taken from your home page"
              action="Edit"
            />
            <ActivityRow
              icon="plus"
              iconTone="brand"
              title="Same-Day Water Heater Repair"
              meta="28 of 30 characters · taken from your services page"
              action="Edit"
            />
            <ActivityRow
              icon="line"
              iconTone="brand"
              title="Licensed & Insured Since 2009"
              meta="29 of 30 characters · taken from your about page"
            />
            <ActivityRow
              icon="line"
              iconTone="brand"
              title="Call Now For A Free Quote"
              meta="25 of 30 characters · written to ask for the call"
            />
          </Rows>
        </Panel>
        <Panel title="Rewritten before you saw them" action={{ label: "See all checks" }}>
          <AdMock
            kicker="Refused by our own check"
            source={<>&ldquo;Best Plumber In All Of Ontario&rdquo; · 30 characters</>}
            headline="Nobody can prove they are the best"
            headlineTone="red"
            body={
              <>
                Google refuses claims like this, and a rejected ad stops your whole ad group. We
                swapped it for &ldquo;Licensed & Insured Since 2009&rdquo;, which is true and
                checkable. Two more were cut for running past 30 characters.
              </>
            }
          />
          <Footnote>
            Every line is checked for length, unprovable claims, other companies&rsquo; names,
            SHOUTING and repeated punctuation.
          </Footnote>
        </Panel>
        <Panel title="Callouts, up to 25 characters" action={{ label: "Edit" }} tone="plain">
          <Rows className="mt-1">
            <ListRow
              title="Licensed since 2009"
              meta="19 of 25 · from your about page"
              chip="Passes"
              chipTone="pale"
            />
            <ListRow
              title="Upfront prices"
              meta="14 of 25 · from your pricing page"
              chip="Passes"
              chipTone="pale"
            />
            <ListRow
              title="Same-day visits"
              meta="15 of 25 · from your home page"
              chip="Passes"
              chipTone="pale"
            />
            <ListRow
              title="Open 24 hours"
              meta="13 of 25 · from your contact page"
              chip="Passes"
              chipTone="pale"
            />
          </Rows>
        </Panel>
      </Columns>
    </AppShell>
  );
}

/* ---------- 42:5110 ---------- */
export function WhyShape() {
  return (
    <AppShell active="campaigns" workspace={alpha} badges={{}}>
      <PageHead
        title="Why this shape, and not another."
        lead="None of these came from a guess or from a model. Each one is a written rule with your numbers put into it, and you can read the rule."
      />
      <Tiles>
        <Tile tone="brand" label="Campaign types" value="2" chip="Search and Local" />
        <Tile label="Bidding" value="Max clicks" chip="You have no results yet" />
        <Tile label="Most for one click" value="$14" chip="So one click cannot eat the day" />
        <Tile label="How far we go" value="25 km" progress={170 / 226} />
      </Tiles>
      <Columns
        aside={
          <>
            <NoticeCard
              tag="Never automatic"
              title="What never happens without you"
              body="Raising your daily budget, going past your cost cap, switching on a new campaign type, or bidding on another company's name. These wait for your yes whatever autonomy level you pick."
              primary={{ label: "Autonomy settings", href: "/settings" }}
              secondary={{ label: "Later" }}
            />
            <Panel title="Your limits">
              <Rows className="mt-1">
                <ListRow
                  title="$48 a day, $35 a call"
                  meta="We stop before this, never after"
                  chip="Hard"
                  dot
                />
                <ListRow
                  title="$14 most for one click"
                  meta="Set from your budget. You can change it."
                  chip="Yours"
                  dot
                />
              </Rows>
            </Panel>
          </>
        }
      >
        <Panel title="The rule we applied" action={{ label: "See all rules", tone: "brand" }}>
          <Summary>
            A local service chasing calls on $750 to $3,000 a month gets two campaigns: Search for
            people typing what they need, and Local for people on Google Maps. Performance Max stays
            off because we could not explain it to you.
          </Summary>
        </Panel>
        <Panel title="Every choice, and what decided it" action={{ label: "Change any of these" }}>
          <Rows>
            <ActivityRow
              icon="bars"
              iconTone="brand"
              title="Search and Local, no Performance Max"
              meta="Your $1,200 a month sits in the $750 to $3,000 band for local services."
              action="Change"
            />
            <ActivityRow
              icon="plus"
              iconTone="brand"
              title="Maximize clicks, capped at $14"
              meta="A cost target needs 30 results in 30 days. You have none yet."
              action="Change"
            />
            <ActivityRow
              icon="line"
              iconTone="brand"
              title="Phrase and exact match, almost no broad"
              meta="Broad match learns quickly but wastes money doing it. Not on $40 a day."
            />
            <ActivityRow
              icon="line"
              iconTone="brand"
              title="One ad group for each theme"
              meta="Keeps the wording close to what was typed, which lifts the score Google gives you."
            />
          </Rows>
        </Panel>
        <Panel
          title="When these change by themselves"
          action={{ label: "Autonomy settings", href: "/settings" }}
        >
          <AdMock
            kicker="At 15 results"
            source="We move you to Maximize Conversions"
            headline="At 30, we set a target cost per call"
            body="Both of those wait for your yes, because you are on Approve-first. After each change we leave the bidding alone for two weeks while Google relearns. Fighting its learning makes both of us worse."
          />
          <Footnote>
            Every automatic change is written down before it happens, and every one can be undone.
          </Footnote>
        </Panel>
      </Columns>
    </AppShell>
  );
}

/* ---------- 81:2827 ---------- */
export function PmaxLogo() {
  return (
    <AppShell active="campaigns" workspace={birch} initials="EB" badges={{}}>
      <PageHead
        title="Performance Max needs a square logo. The rest is ready."
        lead="These ads also run on YouTube, Gmail, Maps and across the web, so Google needs pictures as well as words. We use your uploads first, then photos from your site, then licensed stock. We never make images up."
      />
      <Tiles>
        <Tile tone="brand" label="Images found" value="6" chip="4 wide, 2 square" />
        <Tile
          label="Square logo"
          value="Missing"
          valueTone="red"
          chip="Google needs one"
          chipTone="red"
        />
        <Tile label="Words" value="Ready" chip="15 headlines, 5 descriptions" />
        <Tile label="Ad strength so far" value="Good" progress={0.7} />
      </Tiles>
      <Columns
        aside={
          <>
            <ActionPanel
              title="One thing left"
              body="Upload a square logo and this campaign is ready to launch. We check the size before anything goes to Google."
              primary="Upload logo"
              secondary="Later"
            />
            <Panel title="What Google requires" tone="plain">
              <Rows className="mt-1">
                <ListRow
                  title="Headlines"
                  meta="15 written · Google needs 3, allows 15"
                  chip="Ready"
                  chipTone="pale"
                />
                <ListRow
                  title="Long headlines"
                  meta="5 written · needs 1, up to 90 characters"
                  chip="Ready"
                  chipTone="pale"
                />
                <ListRow
                  title="Descriptions"
                  meta="5 written · needs 2, one of them 60 characters or less"
                  chip="Ready"
                  chipTone="pale"
                />
                <ListRow
                  title="Wide images, 1.91:1"
                  meta="4 from your site · needs 1, at least 600 × 314"
                  chip="Ready"
                  chipTone="pale"
                />
                <ListRow
                  title="Square images, 1:1"
                  meta="2 from your site · needs 1, at least 300 × 300"
                  chip="Ready"
                  chipTone="pale"
                />
                <ListRow
                  title="Square logo, 1:1"
                  meta="None yet · needs 1, at least 128 × 128"
                  chip="Missing"
                  chipTone="red"
                />
                <ListRow
                  title="Videos"
                  meta="None · Google makes a short one from your images"
                  chip="Optional"
                />
              </Rows>
            </Panel>
            <Panel title="Your products" tone="plain">
              <PanelText>
                No Merchant Center feed found, so these ads will not show product listings.
                Connecting a feed is a separate step you can do later.
              </PanelText>
            </Panel>
          </>
        }
      >
        <Panel title="Images from your site" action={{ label: "Upload more" }} tone="plain">
          <Gallery
            items={[
              { tint: "#e9dcc9", caption: "1200 × 628 · shop page" },
              { tint: "#d8e2d9", caption: "1200 × 628 · home page" },
              { tint: "#e7d5cf", caption: "1600 × 838 · gift sets" },
              { tint: "#dfe3ea", caption: "1200 × 628 · about us" },
            ]}
          />
          <Gallery
            square
            items={[
              { tint: "#e9dcc9", caption: "1080 × 1080" },
              { tint: "#d8e2d9", caption: "1200 × 1200" },
              { tint: "", empty: true },
              { tint: "", empty: true },
            ]}
          />
          <Footnote>
            Google can use up to 20 images. More variety usually means more places your ads can
            show.
          </Footnote>
        </Panel>
        <Panel title="Logo" tone="plain">
          <div className="mt-4 flex flex-wrap items-center gap-4">
            <div className="bg-ad-bg border-line flex h-[60px] w-[200px] items-center justify-center rounded-[10px] border text-[18px] font-bold text-[#5a4632]">
              Birch & Wick
            </div>
            <div>
              <p className="text-ink text-[15px] leading-[18px] font-medium">
                The logo on your site is 400 × 120
              </p>
              <p className="text-faint mt-1 text-[13px] leading-4">
                Google needs a square one, so this cannot be used
              </p>
            </div>
          </div>
          <DropZone
            title="Drop a square logo here, or choose a file"
            meta="At least 128 × 128 pixels. PNG or JPG."
            button="Choose file"
          />
        </Panel>
      </Columns>
    </AppShell>
  );
}

/* ---------- 92:16712 ---------- */
export function PmaxMonth() {
  return (
    <AppShell active="campaigns" workspace={birch} initials="EB" badges={{}}>
      <PageHead
        title="Performance Max, four weeks in."
        lead="Google has now shown every picture and line enough to rate them. Two images are rarely picked, so we suggest replacing them. Google's ratings are relative: 'Low' means less useful than the rest, not broken."
      />
      <Tiles>
        <Tile tone="brand" label="Sales from these ads" value="31" chip="$2,270 in orders" />
        <Tile label="Return on ad spend" value="4.2x" chip="$540 spent for $2,270" />
        <Tile label="Assets rated low" value="3" chip="2 images, 1 headline" />
        <Tile label="Asset group strength" value="Good" progress={0.7} />
      </Tiles>
      <Columns
        aside={
          <>
            <ActionPanel
              title="Replace the 2 weak images?"
              body="Pick from 5 new photos on your shop page, or upload your own. We check the sizes first, and the old images are paused, not deleted."
              primary="Choose images"
              secondary="Later"
            />
            <Panel title="Where the ads showed" tone="plain">
              <Meter name="Search results" value="48%" fill={0.48} />
              <Meter name="YouTube" value="22%" fill={0.22} />
              <Meter name="Websites and apps" value="18%" fill={0.18} />
              <Meter name="Gmail and Discover" value="12%" fill={0.12} />
              <Footnote>
                Google decides where to show them. Search brings most sales; YouTube mostly brings
                first visits.
              </Footnote>
            </Panel>
          </>
        }
      >
        <Panel title="Images, as Google rates them" action={{ label: "Upload more" }} tone="plain">
          <Gallery
            items={[
              { tint: "#e7d5cf", chip: "Best", caption: "gift sets" },
              { tint: "#e9dcc9", chip: "Good", caption: "shop page" },
              { tint: "#d8e2d9", chip: "Low", chipTone: "amber", caption: "home page" },
              { tint: "#dfe3ea", chip: "Good", caption: "about us" },
            ]}
          />
          <Gallery
            square
            items={[
              { tint: "#e9dcc9", chip: "Good" },
              { tint: "#d8e2d9", chip: "Low", chipTone: "amber" },
              { tint: "#f1e6d8", chip: "New", caption: "added 2 Sep" },
            ]}
          />
          <Footnote>
            An image needs 5,000 views before Google rates it. Both low ones have more than 20,000.
          </Footnote>
        </Panel>
        <Panel title="Words, as Google rates them" action={{ label: "Write more" }} tone="plain">
          <Rows className="mt-1">
            <ListRow title="Hand-Poured Soy Candles" meta="Headline" chip="Best" chipTone="pale" />
            <ListRow title="Free Shipping Over $60" meta="Headline" chip="Good" chipTone="pale" />
            <ListRow
              title="Made in Hamilton, Ontario"
              meta="Headline"
              chip="Good"
              chipTone="pale"
            />
            <ListRow title="Shop Our Gift Sets" meta="Headline" chip="Low" chipTone="amber" />
            <ListRow
              title="Small-batch soy candles, poured by hand in Hamilton. Gift boxes ready to send."
              meta="Description"
              chip="Good"
              chipTone="pale"
            />
          </Rows>
        </Panel>
      </Columns>
    </AppShell>
  );
}

/* ---------- 87:10317 ---------- */
export function SummitPlan() {
  return (
    <AppShell active="campaigns" workspace={summit} initials="RK" badges={{}}>
      <PageHead
        title="The plan, built around what you already run."
        lead="We read 90 days of your account before writing anything. Two of your campaigns carry on with PPCWay, one stops, one stays yours, and one new campaign fills the gap."
      />
      <Tiles>
        <Tile tone="brand" label="Managed by PPCWay" value="3" chip="2 of yours and 1 new" />
        <Tile label="Pausing" value="1" chip="Display, saves $410 a month" />
        <Tile label="Stays yours" value="1" chip="We never touch it" />
        <Tile label="Searches read, 90 days" value="1,480" progress={1} />
      </Tiles>
      <Columns
        aside={
          <>
            <ActionPanel
              title="Approve the plan"
              body="Nothing changes in Google Ads until you approve. Each change is written down with an undo, and the new ads go to Google for review."
              primary="Approve plan"
              secondary="Change something"
            />
            <Panel title="What the AI did, and did not do" tone="plain">
              <Rows className="mt-1">
                <ListRow
                  title="Wrote the new ads"
                  meta="From your site and your best headlines"
                  chip="AI"
                  chipTone="pale"
                />
                <ListRow
                  title="Grouped the searches"
                  meta="Only ones Google or your history gave us"
                  chip="AI"
                  chipTone="pale"
                />
                <ListRow
                  title="Chose bids, budgets and pauses"
                  meta="Rules decide these, from your numbers"
                  chip="Rules"
                />
              </Rows>
            </Panel>
          </>
        }
      >
        <Panel title="Your campaigns, after launch" action={{ label: "Change" }} tone="plain">
          <Rows className="mt-1">
            <ListRow
              title="Furnace Repair – Search"
              meta="Managed · target cost per call $29, set from its own 38 calls"
              chip="PPCWay"
              chipTone="pale"
            />
            <ListRow
              title="AC Install Brampton"
              meta="Managed · Maximize conversions, 9 calls is too few for a target"
              chip="PPCWay"
              chipTone="pale"
            />
            <ListRow
              title="Google Maps (Local)"
              meta="New · $12 a day, paid for by pausing display"
              chip="New"
              chipTone="pale"
            />
            <ListRow
              title="Display – Remarketing"
              meta="Paused at launch · you can restart it in Google Ads"
              chip="Pausing"
              chipTone="amber"
            />
            <ListRow
              title="Spring Promo 2026"
              meta="Yours, manual only · stays paused and untouched"
              chip="Yours"
            />
          </Rows>
        </Panel>
        <Panel title="What we learned from your history" tone="plain">
          <Rows className="mt-1">
            <ListRow
              title="22 searches that bring calls"
              meta="Added as exact keywords in Furnace Repair"
              chip="Adding"
              chipTone="pale"
            />
            <ListRow
              title="9 searches that wasted $296"
              meta="12 or more clicks each, no calls in 90 days · blocked on day one"
              chip="Blocking"
              chipTone="amber"
            />
            <ListRow
              title="12 searches both campaigns chased"
              meta="'hvac repair brampton' and 11 more · kept in Furnace Repair only"
              chip="Overlap fixed"
            />
          </Rows>
        </Panel>
      </Columns>
    </AppShell>
  );
}

/* ---------- 87:10587 ---------- */
export function SummitList() {
  return (
    <AppShell active="campaigns" workspace={summit} initials="RK">
      <PageHead
        title="Five campaigns. PPCWay looks after three."
        lead="Campaigns you keep for yourself show here too, so everything is in one place. We report on them but never change them."
      />
      <Tiles>
        <Tile tone="brand" label="Calls, last 30 days" value="43" chip="Across all campaigns" />
        <Tile label="Managed by PPCWay" value="3" chip="$74 a day in total" />
        <Tile label="Yours, manual only" value="2" chip="Both paused" chipTone="grey" />
        <Tile label="Edits in Google Ads" value="2 this week" progress={1} />
      </Tiles>
      <Columns
        aside={
          <>
            <Panel title="Hand one over, or take one back" tone="plain">
              <PanelText>
                Move any campaign between PPCWay and manual only. Taking one back stops our changes
                straight away; nothing else happens to it.
              </PanelText>
              <Button variant="secondary" size="sm" className="border-line mt-4 h-11">
                Change who manages what
              </Button>
            </Panel>
            <Panel title="Changed in Google Ads" tone="plain">
              <Rows className="mt-1">
                <LinkRow
                  title="AC Install: budget $20 to $24"
                  meta="Tue 5:10 pm · raj@summithvac.ca · kept"
                  link="View"
                />
                <LinkRow
                  title="Furnace Repair: paused a keyword"
                  meta="Mon 9:02 am · kept"
                  link="View"
                />
              </Rows>
            </Panel>
          </>
        }
      >
        <Panel
          title="Managed by PPCWay"
          action={{ label: "Advanced view", href: "/campaigns?view=list" }}
          tone="plain"
        >
          <Rows className="mt-1">
            <ListRow
              title="Furnace Repair – Search"
              meta="31 calls · $27.10 each · aiming for $29"
              chip="Live"
              chipTone="pale"
              dot
            />
            <ListRow
              title="AC Install Brampton"
              meta="8 calls · $58 each · keywords tidied up this week"
              chip="Live"
              chipTone="pale"
              dot
            />
            <ListRow
              title="Google Maps (Local)"
              meta="4 calls · $19.40 each · new since 4 Sep"
              chip="Learning"
              dot
            />
          </Rows>
        </Panel>
        <Panel title="Yours, manual only" tone="plain">
          <Rows className="mt-1">
            <ListRow
              title="Spring Promo 2026"
              meta="Paused since 31 May · we report on it, nothing more"
              chip="Paused"
              dot
            />
            <ListRow
              title="Display – Remarketing"
              meta="Paused at launch with your OK · restart it in Google Ads"
              chip="Paused"
              dot
            />
          </Rows>
        </Panel>
      </Columns>
    </AppShell>
  );
}

/* ---------- 88:11449 ---------- */
export function SummitLeaks() {
  return (
    <AppShell active="campaigns" workspace={summit} initials="RK" badges={{ approvals: 3 }}>
      <PageHead
        title="Furnace Repair works, but about $335 a month leaks out."
        lead="We checked everything Northline Media set up, using 90 days of your own numbers. Nothing has changed yet; each fix waits for your OK."
      />
      <Tiles>
        <Tile tone="brand" label="Calls, 30 days before us" value="38" chip="$29.47 each" />
        <Tile
          label="Money that bought nothing"
          value="$335"
          valueTone="red"
          chip="A month, on average"
          chipTone="red"
        />
        <Tile label="Fixes found" value="6" chip="3 are quick wins" chipTone="amber" />
        <Tile label="Ad strength" value="Poor" progress={57 / 226} />
      </Tiles>
      <Columns
        aside={
          <>
            <ActionPanel
              title="Approve the quick wins"
              body="Turn off display expansion, block the 9 searches and fix the location setting. About $335 a month back, from tomorrow, without touching Google's learning."
              primary="Approve 3 fixes"
              secondary="One by one"
            />
            <Panel title="The other three" tone="plain">
              <PanelText>
                Headlines, broad match and bidding come in later weeks, so Google&rsquo;s learning
                resets once, not three times.
              </PanelText>
            </Panel>
          </>
        }
      >
        <Panel
          title="What we found, biggest first"
          action={{ label: "How we checked" }}
          tone="plain"
        >
          <Rows className="mt-1">
            <ListRow
              title="Display expansion is switched on"
              meta="18% of spend went to websites and apps, with 1 call in 90 days · about $200 a month"
              chip="Turn off"
              chipTone="amber"
            />
            <ListRow
              title="9 searches with 12 or more clicks and no calls"
              meta="'furnace parts', 'hvac jobs brampton' and 7 more · $296 in 90 days"
              chip="Block"
              chipTone="amber"
            />
            <ListRow
              title="Showing to people who are not in Brampton"
              meta="Location is set to 'interest', so searches from out west see your ad · about $36 a month"
              chip="Fix"
              chipTone="amber"
            />
            <ListRow
              title="Only 5 headlines in the ad"
              meta="Google wants 10 to 15. Ad strength is Poor, which pushes up what each click costs"
              chip="Rewrite"
            />
            <ListRow
              title="Every bid set by hand since 2024"
              meta="38 calls a month is enough for a target cost per call, starting at $29"
              chip="Later"
            />
            <ListRow
              title="Broad match on 61 of 86 keywords"
              meta="Broad is what lets the wasted searches in. Phrase keeps the good ones"
              chip="Tighten"
            />
          </Rows>
        </Panel>
        <Panel title="Working well, leave it" tone="plain">
          <Rows className="mt-1">
            <ListRow
              title="Call assets"
              meta="Set up properly, bringing most of the calls"
              chip="Keep"
              chipTone="pale"
            />
            <ListRow
              title="Budget of $38 a day"
              meta="Spend is on pace and nothing is lost to budget"
              chip="Keep"
              chipTone="pale"
            />
          </Rows>
        </Panel>
      </Columns>
    </AppShell>
  );
}

/* ---------- 88:11695 ---------- */
export function SummitMonth() {
  return (
    <AppShell active="campaigns" workspace={summit} initials="RK">
      <PageHead
        title="Your first month with PPCWay, one step at a time."
        lead="Changing everything at once would reset Google's learning and make the results impossible to read. So the fixes are spread out, and each one waits for your OK."
      />
      <Tiles>
        <Tile tone="brand" label="Changes planned" value="7" chip="Over five weeks" />
        <Tile label="Done so far" value="3" chip="The quick wins" chipTone="pale" />
        <Tile label="Learning resets" value="1" chip="Only the bidding switch" chipTone="amber" />
        <Tile label="Week" value="1 of 5" progress={0.2} />
      </Tiles>
      <Columns
        aside={
          <>
            <Panel title="Why in this order" tone="plain">
              <PanelText>
                Stop the leaks first: they cost money every day and do not upset Google&rsquo;s
                learning. The bidding switch goes last because it resets learning, and we only want
                to do that once.
              </PanelText>
            </Panel>
            <Panel title="Your starting point" action={{ label: "Details" }} tone="plain">
              <Rows className="mt-1">
                <ListRow title="Calls a month" meta="5 Aug to 3 Sep, before any change" chip="38" />
                <ListRow title="Cost per call" meta="The number we measure against" chip="$29.47" />
                <ListRow
                  title="Money that bought nothing"
                  meta="Display, wasted searches, location"
                  chip="$335"
                  chipTone="red"
                />
              </Rows>
            </Panel>
          </>
        }
      >
        <Panel title="Week 1 · 4 to 10 September" tone="plain">
          <Rows className="mt-1">
            <ListRow
              title="Turn off display expansion"
              meta="Stops about $200 a month going to websites and apps"
              chip="Done"
              chipTone="pale"
            />
            <ListRow
              title="Block 9 searches that never call"
              meta="12 or more clicks each, no calls in 90 days"
              chip="Done"
              chipTone="pale"
            />
            <ListRow
              title="Fix the location setting"
              meta="Only people in or near Brampton"
              chip="Done"
              chipTone="pale"
            />
          </Rows>
        </Panel>
        <Panel title="Week 2 · 11 to 17 September" tone="plain">
          <Rows className="mt-1">
            <ListRow
              title="Add 10 new headlines, keep the 3 best old ones"
              meta="Tested against the old ad, not instead of it"
              chip="Waiting for you"
              chipTone="amber"
            />
            <ListRow
              title="Change 61 broad keywords to phrase"
              meta="Keeps the searches that call, drops the rest"
              chip="Waiting for you"
              chipTone="amber"
            />
          </Rows>
        </Panel>
        <Panel title="Week 3 · 18 to 24 September" tone="plain">
          <Rows className="mt-1">
            <ListRow
              title="Switch to target cost per call at $29"
              meta="Restarts Google's learning for about 14 days, so it goes last"
              chip="Planned"
            />
          </Rows>
        </Panel>
        <Panel title="Weeks 4 and 5 · 25 September to 8 October" tone="plain">
          <Rows className="mt-1">
            <ListRow
              title="Hold and watch"
              meta="No new changes while Google learns. First before-and-after on 9 October"
              chip="Planned"
            />
          </Rows>
        </Panel>
      </Columns>
    </AppShell>
  );
}

/* ---------- 88:11952 ---------- */
export function SummitKeywords() {
  return (
    <AppShell active="campaigns" workspace={summit} initials="RK">
      <PageHead
        title="AC Install has 64 keywords. 41 never got a click."
        lead="Old keywords are not harmful on their own, but they hide what works, and some are broad enough to buy the wrong searches. Here is a tidy-up, one group at a time."
      />
      <Tiles>
        <Tile tone="brand" label="Keywords" value="64" chip="Set up by Northline Media" />
        <Tile
          label="No clicks in 90 days"
          value="41"
          chip="Pause, keep the history"
          chipTone="amber"
        />
        <Tile label="Broad match" value="18" chip="12 bought wasted searches" chipTone="red" />
        <Tile
          label="Shared with Furnace Repair"
          value="7"
          chip="Keep them in one place"
          chipTone="amber"
        />
      </Tiles>
      <Columns
        aside={
          <>
            <ActionPanel
              title="Approve the tidy-up"
              body="65 changes in one batch, and one undo puts them all back. Paused keywords keep their history."
              primary="Approve all"
              secondary="Review each"
            />
            <Panel title="Rules we used" tone="plain">
              <Rows className="mt-1">
                <ListRow title="No clicks in 90 days" meta="Paused, never removed" />
                <ListRow title="12 clicks and no calls" meta="The search gets blocked" />
                <ListRow title="2 calls or more" meta="The search becomes a keyword" />
              </Rows>
            </Panel>
          </>
        }
      >
        <Panel title="Suggested changes" action={{ label: "See every keyword" }} tone="plain">
          <Rows className="mt-1">
            <ListRow
              title="Pause 41 keywords with no clicks in 90 days"
              meta="'ac installation cost estimate calculator' and 40 more · nothing is deleted"
              chip="Pause"
            />
            <ListRow
              title="Change 12 broad keywords to phrase"
              meta="'ac install' was matching 'ac installer jobs' and 'install ac yourself'"
              chip="Tighten"
              chipTone="amber"
            />
            <ListRow
              title="Keep 7 shared keywords in one campaign only"
              meta="'hvac brampton' ran in both campaigns, so you bid against yourself"
              chip="Merge"
              chipTone="amber"
            />
            <ListRow
              title="Add 5 searches that brought calls"
              meta="'central air install brampton' and 4 more · 2 or more calls each"
              chip="Add"
              chipTone="pale"
            />
          </Rows>
        </Panel>
        <Panel title="Before and after" tone="plain">
          <Rows className="mt-1">
            <ValueRow title="Keywords live" meta="Now 64" value="After 23" />
            <ValueRow title="Broad match" meta="Now 18" value="After 6" />
            <ValueRow title="Wasted a month" meta="Now $96" value="After about $20" />
          </Rows>
        </Panel>
      </Columns>
    </AppShell>
  );
}

/* ---------- 88:12395 ---------- */
export function SummitAdTest() {
  const card = (
    name: string,
    by: string,
    chip: string,
    tone: "pale" | "grey",
    headline: string,
    body: string,
    rows: [string, string][],
    active?: boolean,
  ) => (
    <div className={`rounded-[14px] border px-5 py-5 ${active ? "border-brand" : "border-line"}`}>
      <div className="flex items-center justify-between gap-3">
        <p className="text-ink text-[15px] leading-[18px] font-semibold">
          {name} <span className="text-faint font-normal">· {by}</span>
        </p>
        <StatusPill tone={tone}>{chip}</StatusPill>
      </div>
      <div className="bg-ad-bg mt-[10px] rounded-[10px] px-4 py-[14px]">
        <p className="text-muted text-[12px] leading-[15px]">Sponsored · summithvac.ca</p>
        <p className="text-ad-link mt-1 text-[16px] leading-[20px] font-medium">{headline}</p>
        <p className="text-muted mt-1 text-[13px] leading-4">{body}</p>
      </div>
      <ul className="divide-line-soft mt-[10px] divide-y">
        {rows.map(([k, v]) => (
          <li
            key={k}
            className="flex items-center justify-between py-[9px] text-[14px] leading-[17px]"
          >
            <span className="text-muted">{k}</span>
            <span className="text-ink font-semibold">{v}</span>
          </li>
        ))}
      </ul>
    </div>
  );
  return (
    <AppShell active="campaigns" workspace={summit} initials="RK">
      <PageHead
        title="The old ad against our new one, three weeks in."
        lead="We did not replace Northline's ad. The new one runs next to it, Google splits the traffic, and the numbers decide. We call it when there is enough data, not before."
      />
      <Tiles>
        <Tile tone="brand" label="New ad" value="22 calls" chip="$23.10 each" chipTone="pale" />
        <Tile label="Old ad" value="14 calls" chip="$30.80 each" chipTone="grey" />
        <Tile label="Shown" value="55 / 45" chip="Google leans to the new one" chipTone="grey" />
        <Tile label="Chance the new one is better" value="91%" progress={0.91} />
      </Tiles>
      <Columns
        aside={
          <>
            <ActionPanel
              title="Pause the old ad?"
              body="Both ads have passed 10 calls, and the new one costs $7.70 less a call. Pausing the old ad sends all the traffic to the new one."
              primary="Pause the old ad"
              secondary="Keep testing"
            />
            <Panel title="Headlines doing the work" tone="plain">
              <Rows className="mt-1">
                <ListRow
                  title="Same-Day Furnace Repair"
                  meta="Shown most in calls"
                  chip="Best"
                  chipTone="pale"
                />
                <ListRow
                  title="Licensed Brampton Technicians"
                  meta="Kept from the old ad"
                  chip="Good"
                  chipTone="pale"
                />
              </Rows>
            </Panel>
          </>
        }
      >
        <Panel title="Side by side" action={{ label: "All headlines" }} tone="plain">
          <div className="mt-4 grid gap-4 md:grid-cols-2">
            {card(
              "Old ad",
              "Northline Media · 5 headlines",
              "Running",
              "grey",
              "Furnace Repair Brampton | Call Summit Today",
              "Furnace not working? Call Summit Heating for fast repair in Brampton.",
              [
                ["Calls", "14"],
                ["Cost per call", "$30.80"],
                ["Share of traffic", "45%"],
                ["Ad strength", "Poor"],
              ],
            )}
            {card(
              "New ad",
              "PPCWay · 13 headlines",
              "Leading",
              "pale",
              "Same-Day Furnace Repair | Licensed Brampton Technicians",
              "No heat? A licensed technician can be there today. Price agreed before we start.",
              [
                ["Calls", "22"],
                ["Cost per call", "$23.10"],
                ["Share of traffic", "55%"],
                ["Ad strength", "Excellent"],
              ],
              true,
            )}
          </div>
        </Panel>
        <Panel title="How the winner is decided" tone="plain">
          <Rows className="mt-1">
            <ListRow
              title="Each ad needs 10 calls or more"
              meta="Fewer than that and one lucky day could decide it"
              chip="Old ad: 14"
              chipTone="pale"
            />
            <ListRow
              title="Compare cost per call, not clicks"
              meta="Clicks are cheap. Calls are what you pay for"
              chip="New: $23.10"
              chipTone="pale"
            />
            <ListRow
              title="The loser is paused, never deleted"
              meta="Its history stays, and you can bring it back"
              chip="Rule"
            />
          </Rows>
        </Panel>
      </Columns>
    </AppShell>
  );
}

/* ---------- 88:12678 ---------- */
export function SummitResults() {
  return (
    <AppShell active="campaigns" workspace={summit} initials="RK">
      <PageHead
        title="Five weeks in: cost per call is down 25%."
        lead="Your two original campaigns, compared with the 30 days before PPCWay changed anything. Google Maps (Local) is new, so it is left out of the comparison."
      />
      <Tiles>
        <Tile tone="brand" label="Cost per call" value="$28.25" chip="Was $37.45 before us" />
        <Tile label="Calls, last 30 days" value="57" chip="Was 47" chipTone="pale" />
        <Tile
          label="Money that bought nothing"
          value="$41"
          chip="Was about $335 a month"
          chipTone="pale"
        />
        <Tile label="Changes made" value="7" chip="Each one with your OK" chipTone="grey" />
      </Tiles>
      <Columns
        aside={
          <>
            <Panel title="Each campaign" tone="plain">
              <Rows className="mt-1">
                <ListRow
                  title="Furnace Repair – Search"
                  meta="45 calls · $24.22 · was $29.47"
                  chip="−18%"
                  chipTone="pale"
                  dot
                />
                <ListRow
                  title="AC Install Brampton"
                  meta="12 calls · $43.33 · was $71.11"
                  chip="−39%"
                  chipTone="pale"
                  dot
                />
              </Rows>
            </Panel>
            <Panel title="How we measured" tone="plain">
              <PanelText>
                Before: 5 Aug to 3 Sep. After: the last 30 days. Same campaigns, same area. Last
                year the same weeks brought 9% more calls with no changes, so some of this is the
                season.
              </PanelText>
            </Panel>
            <ActionPanel
              title="Coming up"
              body="AC install searches drop about 70% from October. Move $6 a day from AC Install to Furnace Repair until April?"
              primary="Move $6 a day"
              secondary="Not now"
            />
          </>
        }
      >
        <Panel title="Cost per call each week" action={{ label: "Download" }} tone="plain">
          <Summary className="text-[17px] leading-[21px]">
            It fell as the leaks closed and kept falling once Google finished learning the new
            target. Heating searches also pick up in October, so How we measured compares with last
            year too.
          </Summary>
          <MiniBars
            height={110}
            bars={[98, 90, 107, 92, 88, 68, 50, 42, 34, 30].map((h, i) => ({
              h: h / 107,
              tone: i === 9 ? "brand" : i >= 5 ? "soft" : "empty",
            }))}
            labels={["Before PPCWay · $37", "4 Sep, we start", "This week · $28"]}
          />
        </Panel>
        <Panel title="What made the difference" tone="plain">
          <Rows className="mt-1">
            <ListRow
              title="Display expansion off, 9 searches blocked, location fixed"
              meta="4 and 5 Sep · about $335 a month stopped leaking"
              chip="Week 1"
            />
            <ListRow
              title="New ad tested against the old one, old one paused"
              meta="11 Sep to 2 Oct · $7.70 less a call"
              chip="Weeks 2 to 4"
            />
            <ListRow
              title="Target cost per call at $29 on Furnace Repair"
              meta="18 Sep · learning finished 2 Oct"
              chip="Week 3"
            />
          </Rows>
        </Panel>
      </Columns>
    </AppShell>
  );
}

/* ---------- Approvals, 17:1623 ---------- */
export function ApprovalsPage() {
  return <DetailPage spec={approvals} />;
}
const approvals: DetailSpec = {
  shell: { active: "approvals", workspace: alpha },
  head: {
    title: "Two changes are waiting for your OK.",
    lead: "PPCWay proposes and explains. You decide. Anything you leave alone expires in seven days and nothing changes.",
  },
  tiles: [
    { tone: "brand", label: "Waiting for you", value: "2", chip: "Oldest was proposed 2 days ago" },
    { label: "Approved this month", value: "6", chip: "All applied without trouble" },
    { label: "Skipped", value: "1", chip: "We won't ask again for 30 days" },
    { label: "You approve", value: "86%", progress: 0.86 },
  ],
  extra: <ApprovalsBody />,
  asideExtra: (
    <>
      <Panel title="How approvals work">
        <PanelText className="text-[15px] leading-[18px]">
          We propose a change and show the numbers behind it. Nothing happens until you approve.
          Skipped ideas stay away for 30 days, and anything you approve can be undone from Activity
          in one click.
        </PanelText>
      </Panel>
      <Panel title="Your setting">
        <Rows className="mt-1">
          <ListRow
            title="Ask me first"
            meta="Nothing changes without your OK"
            chip="In use"
            chipTone="pale"
            dot
          />
          <ListRow title="Just get on with it" meta="Arrives later this year" chip="Later" dot />
        </Rows>
      </Panel>
    </>
  ),
};

function ApprovalsBody() {
  return (
    <>
      <Proposal
        expiry="Expires in 5 days"
        title="Lower the daily budget from $40 to $32"
        body="Spend has run ahead of pace for six days, averaging $46 a day against a $40 budget. Lowering it keeps the month at about $1,200 without pausing anything."
      >
        <div className="bg-panel mt-3 flex flex-wrap items-center gap-x-7 gap-y-1 rounded-[12px] px-[18px] py-[14px]">
          <span className="text-faint text-[14px] font-medium">Daily budget</span>
          <span className="text-ink text-[15px] font-medium">Now $40 a day</span>
          <span className="text-brand text-[15px] font-semibold">Proposed $32 a day</span>
        </div>
      </Proposal>
      <Proposal
        expiry="Expires in 6 days"
        title="Block 3 searches that spent $64 without a call"
        body="People comparing prices clicked 31 times in 30 days and never called. Blocking these moves that money to searches that do ring your phone."
      >
        <div className="mt-3 flex flex-wrap gap-2">
          {["cheap plumber mississauga", "plumber prices", "plumbing cost estimate"].map((t) => (
            <span
              key={t}
              className="bg-panel border-amber-line text-ink inline-flex h-[31px] items-center rounded-full border px-[13px] text-[14px] font-medium"
            >
              {t}
            </span>
          ))}
        </div>
      </Proposal>
      <Panel title="Decided this month">
        <ul className="divide-line-soft mt-1 divide-y">
          {[
            ["Added “water heater installation” as a keyword", "Approved 28 August", "brand"],
            ["Raised the daily budget from $36 to $40", "Approved 21 August", "brand"],
            [
              "Paused the ad that mentions weekend rates",
              "Approved 14 August, undone by you 6 September",
              "faint",
            ],
          ].map(([n, s, t]) => (
            <li
              key={n}
              className="flex flex-wrap items-center justify-between gap-x-4 gap-y-1 py-[14px]"
            >
              <span className="text-ink text-[15px] leading-[18px] font-medium">{n}</span>
              <span
                className={`text-[14px] leading-[17px] font-medium ${t === "brand" ? "text-brand" : "text-faint"}`}
              >
                {s}
              </span>
            </li>
          ))}
        </ul>
      </Panel>
    </>
  );
}

function Proposal({
  expiry,
  title,
  body,
  children,
}: {
  expiry: string;
  title: string;
  body: string;
  children?: React.ReactNode;
}) {
  return (
    <section className="bg-amber-tint border-amber-line rounded-[16px] border px-5 py-5 lg:px-6 lg:py-[25px]">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <span className="bg-amber-pale text-amber-dark inline-flex h-[26px] items-center rounded-full px-3 text-[13px] font-semibold">
          Waiting for you
        </span>
        <span className="text-amber-dark text-[13px] leading-4 font-medium">{expiry}</span>
      </div>
      <h2 className="text-ink mt-3 text-[20px] leading-6 font-semibold">{title}</h2>
      <p className="text-muted mt-3 text-[15px] leading-[18px]">{body}</p>
      {children}
      <div className="mt-4 flex flex-wrap gap-[10px]">
        <Button size="sm" className="h-11 px-6 text-[15px]">
          Approve
        </Button>
        <button
          type="button"
          className="text-amber-dark hover:bg-amber-pale inline-flex h-[46px] items-center rounded-full border border-[#e6cea4] px-[21px] text-[15px] font-semibold"
        >
          Skip this
        </button>
      </div>
    </section>
  );
}
