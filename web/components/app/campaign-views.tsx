import { Button } from "@/components/ui/button";
import { AppShell, type Workspace } from "./shell";
import {
  ActionPanel,
  ActivityRow,
  AdMock,
  Choice,
  Columns,
  FieldRow,
  FilterChips,
  Footnote,
  LinkRow,
  ListRow,
  Meter,
  MiniBars,
  NoticeCard,
  PageHead,
  Panel,
  PanelText,
  Rows,
  SelectionBar,
  StatusPill,
  Step,
  Summary,
  TabsRow,
  Tile,
  Tiles,
  ValueRow,
} from "./blocks";
import { DataTable, StatusWord } from "./table";

/*
  The day-to-day Campaigns pages: the Advanced view tabs (campaigns, ad groups,
  keywords, ads, search terms, account, assets), one campaign opened, its settings,
  the add-keywords and write-an-ad editors, a new campaign, the website check,
  the Starter limit and the alert list.
*/

const alpha: Workspace = { name: "Alpha Plumbing", meta: "Mississauga, Ontario" };

const TABS = [
  { label: "Campaigns", href: "/campaigns?view=list" },
  { label: "Ad groups", href: "/campaigns?view=ad-groups" },
  { label: "Keywords", href: "/campaigns?view=keywords" },
  { label: "Ads", href: "/campaigns?view=ads" },
  { label: "Search terms", href: "/campaigns?view=search-terms" },
];
const COLS = [
  { key: "name", label: "Campaign", width: 300 },
  { key: "status", label: "Status" },
  { key: "impr", label: "Impressions", align: "right" as const },
  { key: "clicks", label: "Clicks", align: "right" as const },
  { key: "ctr", label: "CTR", align: "right" as const },
  { key: "cpc", label: "Avg CPC", align: "right" as const },
  { key: "calls", label: "Calls", align: "right" as const },
  { key: "cost", label: "Cost", align: "right" as const },
];
const on = <StatusWord>Enabled</StatusWord>;
const off = <StatusWord tone="faint">Paused</StatusWord>;

function NewButton({ label }: { label: string }) {
  return (
    <Button variant="secondary" size="sm" className="border-line h-[41px]">
      {label}
    </Button>
  );
}

/* ---------- 17:2236 ---------- */
export function CampaignList() {
  return (
    <AppShell active="campaigns" workspace={alpha}>
      <PageHead
        title="Campaigns, last 30 days."
        lead="Google's own numbers and names, for when you want them. Anything you change here is still checked against your limits."
      />
      <Tiles>
        <Tile tone="brand" label="Impressions" value="18,692" chip="Times your ad was shown" />
        <Tile label="Clicks" value="592" chip="3.17% of the time" />
        <Tile label="Average cost per click" value="$2.09" chip="Down 8 cents this month" />
        <Tile label="Conversion rate" value="9.8%" progress={22 / 226} />
      </Tiles>
      <TabsRow tabs={TABS} active="Campaigns" action={<NewButton label="New campaign" />} />
      <DataTable
        columns={COLS}
        rows={[
          {
            name: "Plumbing repairs in Mississauga",
            status: on,
            impr: "12,481",
            clicks: "402",
            ctr: "3.22%",
            cpc: "$2.14",
            calls: "41",
            cost: "$860.28",
          },
          {
            name: "Google Maps (Local)",
            status: on,
            impr: "5,207",
            clicks: "168",
            ctr: "3.23%",
            cpc: "$2.00",
            calls: "17",
            cost: "$336.16",
          },
          {
            name: "Emergency plumbing",
            status: off,
            impr: "1,004",
            clicks: "22",
            ctr: "2.19%",
            cpc: "$1.98",
            calls: "0",
            cost: "$43.56",
          },
        ]}
        total={{
          name: "Total",
          status: "3 campaigns",
          impr: "18,692",
          clicks: "592",
          ctr: "3.17%",
          cpc: "$2.09",
          calls: "58",
          cost: "$1,240.00",
        }}
      />
      <SelectionBar text="1 selected: Emergency plumbing, paused since 20 Aug">
        <Button size="sm" className="h-[42px]">
          Turn back on
        </Button>
        <Button size="sm" variant="secondary" className="border-line h-11">
          Edit settings
        </Button>
        <Button size="sm" className="bg-red-strong hover:bg-red h-[42px]">
          Remove
        </Button>
      </SelectionBar>
    </AppShell>
  );
}

/* ---------- 79:2 ---------- */
export function AdGroups() {
  return (
    <AppShell active="campaigns" workspace={alpha}>
      <PageHead
        title="Ad groups, last 30 days."
        lead="Each campaign splits into ad groups, one for each kind of job. Google Maps (Local) uses an asset group instead, so you will find it on the Ads tab."
      />
      <Tiles>
        <Tile
          tone="brand"
          label="Ad groups live"
          value="3"
          chip="2 paused with Emergency plumbing"
        />
        <Tile label="Cheapest call" value="$19.15" chip="In Burst pipes" />
        <Tile label="Keywords in live groups" value="42" chip="18, 15 and 9" />
        <Tile label="Calls from Burst pipes" value="51%" progress={0.51} />
      </Tiles>
      <TabsRow tabs={TABS} active="Ad groups" action={<NewButton label="Add an ad group" />} />
      <DataTable
        columns={[{ ...COLS[0], label: "Ad group · campaign" }, ...COLS.slice(1)]}
        rows={[
          {
            name: "Burst pipes · Plumbing repairs",
            status: on,
            impr: "6,020",
            clicks: "188",
            ctr: "3.12%",
            cpc: "$2.14",
            calls: "21",
            cost: "$402.18",
          },
          {
            name: "Near me · Plumbing repairs",
            status: on,
            impr: "4,210",
            clicks: "146",
            ctr: "3.47%",
            cpc: "$2.13",
            calls: "14",
            cost: "$311.64",
          },
          {
            name: "Drains · Plumbing repairs",
            status: on,
            impr: "2,251",
            clicks: "68",
            ctr: "3.02%",
            cpc: "$2.15",
            calls: "6",
            cost: "$146.46",
          },
          {
            name: "After-hours · Emergency plumbing",
            status: off,
            impr: "702",
            clicks: "15",
            ctr: "2.14%",
            cpc: "$2.08",
            calls: "0",
            cost: "$31.20",
          },
          {
            name: "Weekends · Emergency plumbing",
            status: off,
            impr: "302",
            clicks: "7",
            ctr: "2.32%",
            cpc: "$1.77",
            calls: "0",
            cost: "$12.36",
          },
        ]}
        total={{
          name: "5 ad groups",
          status: "3 enabled",
          impr: "13,485",
          clicks: "424",
          ctr: "3.14%",
          cpc: "$2.13",
          calls: "41",
          cost: "$903.84",
        }}
      />
      <Panel
        title="Bidding strategy"
        action={{ label: "Change in campaign settings", href: "/campaigns?view=settings" }}
        className="mt-4"
      >
        <Rows className="mt-1">
          <LinkRow
            title="Plumbing repairs · Maximize conversions"
            meta="Since 4 Aug · 41 calls at $20.98 each · Google sets each bid to win calls within its $28 a day"
            link="Report"
          />
          <LinkRow
            title="Target cost per call is now open to you"
            meta="It needs 30 calls in 30 days, reached on 2 Sep. Switching restarts Google's learning for about 14 days."
            link="Compare"
          />
          <LinkRow
            title="Emergency plumbing · Maximize clicks"
            meta="Paused since 20 Aug · kept as it was so it can restart without relearning"
            link="Report"
            tone="muted"
          />
        </Rows>
      </Panel>
    </AppShell>
  );
}

/* ---------- 74:407 ---------- */
export function Keywords() {
  return (
    <AppShell active="campaigns" workspace={alpha}>
      <PageHead
        title="Keywords, last 30 days."
        lead="Every keyword across your campaigns, with Google's own figures. Pause one, change its bid or add new ones here. Every change still runs through your limits."
      />
      <Tiles>
        <Tile tone="brand" label="Keywords live" value="41" chip="Across 3 ad groups" />
        <Tile label="Keywords with calls" value="19" chip="Nearly half of them" />
        <Tile label="Paused" value="6" chip="By you or by us" />
        <Tile label="Average quality score" value="7 of 10" progress={0.7} />
      </Tiles>
      <TabsRow tabs={TABS} active="Keywords" action={<NewButton label="Add keywords" />} />
      <DataTable
        columns={[{ ...COLS[0], label: "Keyword · ad group" }, ...COLS.slice(1)]}
        rows={[
          {
            name: "burst pipe repair · Burst pipes",
            status: on,
            impr: "4,812",
            clicks: "164",
            ctr: "3.41%",
            cpc: "$2.21",
            calls: "18",
            cost: "$362.44",
          },
          {
            name: "“emergency plumber” · Near me",
            status: on,
            impr: "3,960",
            clicks: "131",
            ctr: "3.31%",
            cpc: "$2.34",
            calls: "13",
            cost: "$306.54",
          },
          {
            name: "[blocked toilet] · Drains",
            status: off,
            impr: "1,388",
            clicks: "39",
            ctr: "2.81%",
            cpc: "$1.96",
            calls: "2",
            cost: "$76.44",
          },
        ]}
        total={{
          name: "Total",
          status: "41 keywords",
          impr: "18,692",
          clicks: "592",
          ctr: "3.17%",
          cpc: "$2.09",
          calls: "58",
          cost: "$1,240.00",
        }}
      />
      <SelectionBar text="1 selected: [blocked toilet] in Drains, paused">
        <Button size="sm" className="h-[42px]">
          Enable
        </Button>
        <Button size="sm" variant="secondary" className="border-line h-11">
          Change bid
        </Button>
        <Button size="sm" className="bg-red-strong hover:bg-red h-[42px]">
          Remove
        </Button>
      </SelectionBar>
    </AppShell>
  );
}

/* ---------- 79:322 ---------- */
export function Ads() {
  return (
    <AppShell active="campaigns" workspace={alpha}>
      <PageHead
        title="Ads, last 30 days."
        lead="Every ad Google is showing, how strong Google rates it, and what it brought in. Pause, turn back on or remove any ad here; each change lands in your activity feed."
      />
      <Tiles>
        <Tile tone="brand" label="Ads live" value="4" chip="3 search ads, 1 Maps asset group" />
        <Tile label="Approved by Google" value="4 of 4" chip="Checked 2 hours ago" />
        <Tile
          label="Headlines to replace"
          value="2"
          chip="Google rates them low"
          chipTone="amber"
        />
        <Tile label="Ad strength, Burst pipes ad" value="Excellent" progress={1} />
      </Tiles>
      <TabsRow tabs={TABS} active="Ads" action={<NewButton label="New ad" />} />
      <DataTable
        columns={[
          { key: "name", label: "Ad · first headline", width: 300 },
          { key: "status", label: "Status" },
          { key: "strength", label: "Ad strength" },
          { key: "impr", label: "Impressions", align: "right" },
          { key: "clicks", label: "Clicks", align: "right" },
          { key: "ctr", label: "CTR", align: "right" },
          { key: "calls", label: "Calls", align: "right" },
          { key: "cost", label: "Cost", align: "right" },
        ]}
        rows={[
          {
            name: "Emergency Plumber Mississauga",
            status: on,
            strength: "Excellent",
            impr: "6,020",
            clicks: "188",
            ctr: "3.12%",
            calls: "21",
            cost: "$402.18",
          },
          {
            name: "Plumber Near You in 60 Minutes",
            status: on,
            strength: "Good",
            impr: "4,210",
            clicks: "146",
            ctr: "3.47%",
            calls: "14",
            cost: "$311.64",
          },
          {
            name: "Blocked Drain? Same-Day Service",
            status: on,
            strength: "Good",
            impr: "2,251",
            clicks: "68",
            ctr: "3.02%",
            calls: "6",
            cost: "$146.46",
          },
          {
            name: "Google Maps asset group",
            status: on,
            strength: "Average",
            impr: "5,207",
            clicks: "168",
            ctr: "3.23%",
            calls: "17",
            cost: "$336.16",
          },
        ]}
        total={{
          name: "4 live ads",
          status: "4 enabled",
          strength: "",
          impr: "17,688",
          clicks: "570",
          ctr: "3.22%",
          calls: "58",
          cost: "$1,196.44",
        }}
      />
      <Panel
        title="Headlines in the Burst pipes ad"
        action={{ label: "Pause this ad · Remove" }}
        className="mt-4"
      >
        <PanelText>
          Google mixes up to 15 headlines and learns which pairs bring calls. We replace the ones it
          rarely shows, and ask you first.
        </PanelText>
        <Rows className="mt-1">
          <ListRow
            title="Emergency Plumber Mississauga"
            meta="Shown most often"
            chip="Best"
            chipTone="pale"
          />
          <ListRow
            title="Licensed & Insured Since 2009"
            meta="Shown often"
            chip="Good"
            chipTone="pale"
          />
          <ListRow
            title="Burst Pipe? We're There in 60 Min"
            meta="Shown often"
            chip="Good"
            chipTone="pale"
          />
          <ListRow
            title="Upfront Prices, No Call-out Fee"
            meta="Rarely shown · we suggest a replacement on 14 Sep"
            chip="Low"
            chipTone="amber"
          />
          <ListRow
            title="Family Owned in Mississauga"
            meta="Rarely shown · we suggest a replacement on 14 Sep"
            chip="Low"
            chipTone="amber"
          />
        </Rows>
        <Footnote>
          Emergency plumbing&rsquo;s two ads are paused with their campaign and not counted above
          ($43.56 before the pause).
        </Footnote>
      </Panel>
    </AppShell>
  );
}

/* ---------- 79:162 ---------- */
export function SearchTerms() {
  return (
    <AppShell active="campaigns" workspace={alpha}>
      <PageHead
        title="Search terms, last 30 days."
        lead="The exact words people typed before they clicked your ad, with Google's own figures. The plain version, with keep and block buttons, is on Searches."
      />
      <Tiles>
        <Tile tone="brand" label="Search terms" value="214" chip="From your two Search campaigns" />
        <Tile label="Brought a call" value="23" chip="11% of all terms" />
        <Tile label="Blocked this month" value="3" chip="Saved about $38 a month" />
        <Tile label="Cost on terms with calls" value="81%" progress={0.81} />
      </Tiles>
      <TabsRow tabs={TABS} active="Search terms" action={<NewButton label="Download report" />} />
      <DataTable
        columns={[
          { ...COLS[0], label: "Search term" },
          { key: "status", label: "Action" },
          ...COLS.slice(2),
        ]}
        rows={[
          {
            name: "burst pipe repair mississauga",
            status: <StatusWord tone="faint">Keyword</StatusWord>,
            impr: "1,204",
            clicks: "61",
            ctr: "5.07%",
            cpc: "$2.20",
            calls: "9",
            cost: "$134.20",
          },
          {
            name: "emergency plumber near me",
            status: <StatusWord>Added 7 Sep</StatusWord>,
            impr: "842",
            clicks: "38",
            ctr: "4.51%",
            cpc: "$2.31",
            calls: "4",
            cost: "$87.78",
          },
          {
            name: "24 hour plumber brampton",
            status: <StatusWord tone="amber">Watching</StatusWord>,
            impr: "356",
            clicks: "12",
            ctr: "3.37%",
            cpc: "$2.05",
            calls: "1",
            cost: "$24.60",
          },
          {
            name: "plumber salary ontario",
            status: <StatusWord tone="red">Blocked 8 Sep</StatusWord>,
            impr: "310",
            clicks: "9",
            ctr: "2.90%",
            cpc: "$1.60",
            calls: "0",
            cost: "$14.40",
          },
          {
            name: "diy drain unblock",
            status: <StatusWord tone="red">Blocked 8 Sep</StatusWord>,
            impr: "280",
            clicks: "8",
            ctr: "2.86%",
            cpc: "$1.55",
            calls: "0",
            cost: "$12.40",
          },
          {
            name: "plumbing courses mississauga",
            status: <StatusWord tone="red">Blocked 8 Sep</StatusWord>,
            impr: "190",
            clicks: "6",
            ctr: "3.16%",
            cpc: "$1.87",
            calls: "0",
            cost: "$11.20",
          },
        ]}
        total={{
          name: "214 search terms",
          status: "4 changes",
          impr: "13,485",
          clicks: "424",
          ctr: "3.14%",
          cpc: "$2.13",
          calls: "41",
          cost: "$903.84",
        }}
      />
    </AppShell>
  );
}

/* ---------- 87:6751 ---------- */
export function Account() {
  return (
    <AppShell active="campaigns" workspace={alpha}>
      <PageHead
        title="Your account, last 30 days."
        lead="Google's figures for the whole account, compared with the 30 days before. Switch between 30, 60 and 90 days, or pick a figure to chart."
      />
      <Tiles>
        <Tile tone="brand" label="Impressions" value="18,692" chip="Up 9% on the 30 before" />
        <Tile label="Clicks" value="592" chip="3.17% of impressions" />
        <Tile label="Conversions" value="58" chip="Calls over 30 seconds" />
        <Tile label="Search impression share" value="64%" progress={0.64} />
      </Tiles>
      <TabsRow
        tabs={[{ label: "Overview", href: "/campaigns?view=account" }, ...TABS]}
        active="Overview"
        action={
          <div className="flex gap-[6px]">
            {["30 days", "60 days", "90 days"].map((r, i) => (
              <button
                key={r}
                type="button"
                className={
                  i === 0
                    ? "bg-rail h-[33px] rounded-full px-[14px] text-[14px] font-semibold text-white"
                    : "bg-panel border-line text-ink h-[35px] rounded-full border px-[15px] text-[14px] font-semibold"
                }
              >
                {r}
              </button>
            ))}
          </div>
        }
      />
      <DataTable
        columns={[
          ...COLS.slice(0, 5),
          { key: "share", label: "Impr. share", align: "right" },
          { key: "calls", label: "Conversions", align: "right" },
          COLS[7],
        ]}
        rows={[
          {
            name: "Plumbing repairs in Mississauga",
            status: on,
            impr: "12,481",
            clicks: "402",
            ctr: "3.22%",
            share: "71%",
            calls: "41",
            cost: "$860.28",
          },
          {
            name: "Google Maps (Local)",
            status: on,
            impr: "5,207",
            clicks: "168",
            ctr: "3.23%",
            share: "52%",
            calls: "17",
            cost: "$336.16",
          },
          {
            name: "Emergency plumbing",
            status: off,
            impr: "1,004",
            clicks: "22",
            ctr: "2.19%",
            share: "–",
            calls: "0",
            cost: "$43.56",
          },
        ]}
        total={{
          name: "Account total",
          status: "3 campaigns",
          impr: "18,692",
          clicks: "592",
          ctr: "3.17%",
          share: "64%",
          calls: "58",
          cost: "$1,240.00",
        }}
      />
      <Panel title="Clicks each day" action={{ label: "Download" }} className="mt-4">
        <FilterChips
          options={["Clicks", "Cost", "Conversions", "CTR", "Impression share"]}
          active="Clicks"
        />
        <MiniBars
          height={110}
          bars={[
            56, 72, 88, 76, 68, 100, 92, 64, 80, 84, 96, 76, 72, 88, 104, 84, 68, 76, 92, 80, 72,
            88, 100, 84, 76, 96, 80, 72, 88, 80,
          ].map((h, i, a) => ({ h: h / 104, tone: i === a.length - 1 ? "brand" : "soft" }))}
          labels={["11 Aug", undefined, "9 Sep"]}
        />
      </Panel>
    </AppShell>
  );
}

/* ---------- 89:13533 ---------- */
export function Assets() {
  return (
    <AppShell active="campaigns" workspace={alpha}>
      <PageHead
        title="Sitelinks, callouts and your call button."
        lead="The extra lines Google can show under your ad. Add, edit, pause or turn any of them back on; Google still decides which ones to show each time."
      />
      <Tiles>
        <Tile tone="brand" label="Assets live" value="10" chip="1 paused, by you" />
        <Tile label="Calls from the call button" value="31" chip="Of your 41 calls" />
        <Tile label="Sitelinks" value="3 of 4" chip="Google shows up to 4" />
        <Tile label="Callouts" value="4 of 10" progress={0.4} />
      </Tiles>
      <TabsRow
        tabs={[
          { label: "Overview", href: "/campaigns?view=account" },
          ...TABS.slice(0, 3),
          { label: "Ads and assets", href: "/campaigns?view=assets" },
          TABS[4],
        ]}
        active="Ads and assets"
        action={<NewButton label="Add an asset" />}
      />
      <DataTable
        columns={[
          { key: "name", label: "Asset", width: 300 },
          { key: "type", label: "Type" },
          { key: "status", label: "Status" },
          { key: "shown", label: "Shown", align: "right" },
          { key: "clicks", label: "Clicks", align: "right" },
          { key: "ctr", label: "CTR", align: "right" },
          { key: "calls", label: "Calls", align: "right" },
          { key: "by", label: "Added by" },
        ]}
        rows={[
          {
            name: "Emergency Repairs",
            type: "Sitelink",
            status: on,
            shown: "2,310",
            clicks: "96",
            ctr: "4.16%",
            calls: "9",
            by: "PPCWay",
          },
          {
            name: "Water Heater Service",
            type: "Sitelink",
            status: on,
            shown: "1,480",
            clicks: "51",
            ctr: "3.45%",
            calls: "4",
            by: "PPCWay",
          },
          {
            name: "Drain Cleaning",
            type: "Sitelink",
            status: on,
            shown: "1,120",
            clicks: "38",
            ctr: "3.39%",
            calls: "2",
            by: "PPCWay",
          },
          {
            name: "About Our Plumbers",
            type: "Sitelink",
            status: off,
            shown: "0",
            clicks: "0",
            ctr: "–",
            calls: "0",
            by: "You",
          },
          {
            name: "Licensed since 2009",
            type: "Callout",
            status: on,
            shown: "5,820",
            clicks: "–",
            ctr: "–",
            calls: "–",
            by: "PPCWay",
          },
          {
            name: "(905) 555-0142",
            type: "Call",
            status: on,
            shown: "6,020",
            clicks: "–",
            ctr: "–",
            calls: "31",
            by: "PPCWay",
          },
        ]}
        total={{
          name: "10 live assets",
          type: "",
          status: "1 paused",
          shown: "",
          clicks: "",
          ctr: "",
          calls: "",
          by: "",
        }}
      />
      <SelectionBar text="1 selected: About Our Plumbers, paused by you on 21 Aug">
        <Button size="sm" className="h-[42px]">
          Turn back on
        </Button>
        <Button size="sm" variant="secondary" className="border-line h-11">
          Edit
        </Button>
        <Button size="sm" className="bg-red-strong hover:bg-red h-[42px]">
          Remove
        </Button>
      </SelectionBar>
    </AppShell>
  );
}

/* ---------- 66:101 ---------- */
export function CampaignDetail() {
  return (
    <AppShell active="campaigns" workspace={alpha}>
      <PageHead
        title="Plumbing repairs is bringing most of your calls."
        lead="Search campaign in Mississauga, running since 4 August. Everything you can change is on this page, and anything we change shows up in Activity first."
      />
      <Tiles>
        <Tile
          tone="brand"
          label="Calls in the last 30 days"
          value="41"
          chip="71% of all your calls"
        />
        <Tile
          label="Spent in the last 30 days"
          value="$860"
          chip="Of $1,240 across all three campaigns"
        />
        <Tile label="Cost per call" value="$20.98" chip="Below your $21.40 average" />
        <Tile label="Share of your budget" value="70%" progress={0.7} />
      </Tiles>
      <Columns
        aside={
          <>
            <NoticeCard
              tone="panel"
              tag="Campaign controls"
              title="Pause, change or remove"
              body="Pausing stops spending within a few minutes and keeps everything Google has learned. Removing takes the campaign out of Google Ads for good, and cannot be undone."
              primary={{ label: "Pause campaign" }}
              primaryTone="ink"
              secondary={{ label: "Remove" }}
            />
            <Panel title="Health">
              <Rows className="mt-1">
                <ListRow
                  title="Ads"
                  meta="3 of 3 approved by Google"
                  chip="Serving"
                  chipTone="pale"
                  dot
                />
                <ListRow
                  title="Call tracking"
                  meta="Last call counted 2 hours ago"
                  chip="Working"
                  chipTone="pale"
                  dot
                />
              </Rows>
            </Panel>
          </>
        }
      >
        <Panel
          title="Settings you control"
          action={{ label: "Edit settings", href: "/campaigns?view=settings" }}
        >
          <Summary>
            $28 of your $40 a day, never more than $14 for one click, shown in Mississauga, Brampton
            and Oakville, all day, every day.
          </Summary>
        </Panel>
        <Panel title="Ad groups in this campaign" action={{ label: "Add an ad group" }}>
          <Rows>
            <ActivityRow
              icon="bars"
              iconTone="brand"
              title="Burst pipes and leaks"
              meta="18 keywords · 21 calls · $19 a call"
              action="Pause"
            />
            <ActivityRow
              icon="plus"
              iconTone="brand"
              title="Emergency plumber near me"
              meta="15 keywords · 14 calls · $22 a call"
              action="Pause"
            />
            <ActivityRow
              icon="line"
              iconTone="brand"
              title="Drains and blocked toilets"
              meta="9 keywords · 6 calls · $24 a call · top bid lowered 8 Sep"
            />
          </Rows>
        </Panel>
        <Panel title="Your ad right now" action={{ label: "Edit wording" }}>
          <AdMock
            kicker="Sponsored"
            source={<>Alpha Plumbing&nbsp;&nbsp;&nbsp;&nbsp;alphaplumbing.ca</>}
            headline="Emergency Plumber Mississauga | Licensed & Insured Since 2009"
            headlineTone="link"
            body="Burst pipe or flooding? A licensed plumber can be with you within the hour, day or night. Call now for a free quote."
          />
          <Footnote>
            Google picks from your 12 headlines. This is the combination it showed most this week.
          </Footnote>
        </Panel>
      </Columns>
    </AppShell>
  );
}

/* ---------- 80:657 ---------- */
export function CampaignSettings() {
  return (
    <AppShell active="campaigns" workspace={alpha}>
      <PageHead
        title="Settings for Plumbing repairs."
        lead="Change the budget, how Google bids, and where and when your ad shows. Every change goes to Google when you press Save, and shows in your activity feed with a way to undo it."
      />
      <Columns
        aside={
          <>
            <Panel title="Campaign status" tone="plain">
              <div className="mt-[14px] flex items-center gap-[10px]">
                <StatusPill tone="pale" dot>
                  Live
                </StatusPill>
                <span className="text-muted text-[14px] leading-[17px]">
                  Serving since 4 August
                </span>
              </div>
              <Rows className="mt-2">
                <ListRow
                  title="Pause"
                  meta="Stops spending within minutes. Everything is kept for when you turn it back on."
                  right={
                    <Button variant="secondary" size="sm" className="border-line h-11">
                      Pause
                    </Button>
                  }
                />
                <ListRow
                  title="Remove"
                  meta="Google cannot undo this. The history stays in your reports."
                  right={
                    <button type="button" className="text-red-strong text-[14px] font-semibold">
                      Remove
                    </button>
                  }
                />
              </Rows>
            </Panel>
            <Panel title="Bidding report" tone="plain">
              <Rows className="mt-1">
                <ValueRow title="Calls, last 30 days" meta="Maximize conversions" value="41" />
                <ValueRow
                  title="Cost per call"
                  meta="Target cost per call would aim near this"
                  value="$20.98"
                />
                <ValueRow title="Top bid cap" meta="Set in Autonomy and limits" value="$14" />
                <ListRow
                  title="Google's learning"
                  meta="Finished 18 August"
                  chip="Settled"
                  chipTone="pale"
                  dot
                />
              </Rows>
            </Panel>
            <ActionPanel
              title="Nothing changed yet"
              body="Saving sends your changes to Google straight away. Each one shows in Activity with an undo that puts the setting back."
              primary="Save changes"
              secondary="Cancel"
              disabled
            />
          </>
        }
      >
        <Panel title="Daily budget" tone="plain">
          <FieldRow label="This campaign" value="$28" suffix="a day, about $850 a month" />
          <PanelText>
            Your two campaigns share $40 a day. Google Maps (Local) gets the other $12. Your hard
            limit in Autonomy is $48 a day, so no setting here can go past it.
          </PanelText>
        </Panel>
        <Panel title="How Google bids" action={{ label: "Bidding report" }} tone="plain">
          <Choice
            name="bid"
            selected
            title="Maximize conversions"
            meta="Google sets each bid to get the most calls within your budget. In use since 4 August."
            chip="In use"
          />
          <Choice
            name="bid"
            title="Target cost per call"
            meta="Google aims for an average cost per call you choose. Open to you since 2 September, when this campaign passed 30 calls in 30 days."
            chip="Now open"
            chipTone="amber"
          />
          <Choice
            name="bid"
            title="Maximize clicks"
            meta="The most visits for the money. Best for a brand new campaign with no calls yet."
          />
          <Choice
            name="bid"
            disabled
            title="Target return on ad spend"
            meta="For online stores that record the value of each sale. It does not work with calls."
            chip="Not for calls"
            chipTone="grey"
          />
          <Footnote>
            Switching restarts Google&rsquo;s learning for about 14 days. We hold other bid changes
            while it learns, so the numbers settle.
          </Footnote>
        </Panel>
        <Panel title="Where your ad shows" action={{ label: "Add a place" }} tone="plain">
          <Rows className="mt-1">
            <LinkRow
              title="Mississauga"
              meta="City, all of it · 41 calls in 30 days"
              link="Remove"
              tone="muted"
            />
            <LinkRow title="Brampton" meta="City · 9 of those calls" link="Remove" tone="muted" />
            <LinkRow title="Oakville" meta="City · 5 of those calls" link="Remove" tone="muted" />
            <LinkRow
              title="People in these places, or often there"
              meta="Not people elsewhere who only search for them. Google calls this presence."
              link="Change"
            />
          </Rows>
        </Panel>
        <Panel title="Language and hours" tone="plain">
          <FieldRow label="Language of the people you reach" value="English" select />
          <Footnote>
            Your ads are written in English. French needs its own ads, which we do not write yet.
          </Footnote>
          <Choice
            name="hours"
            selected
            title="All day, every day"
            meta="Burst pipes do not wait for office hours. 6 of your calls last month came after 10 pm."
          />
          <Choice
            name="hours"
            title="Only the hours you choose"
            meta="For example Monday to Saturday, 7 am to 9 pm. Your ad stops outside those hours."
          />
        </Panel>
      </Columns>
    </AppShell>
  );
}

/* ---------- 87:6199 ---------- */
export function AddKeywords() {
  const match = (sel: number) => (
    <span className="flex gap-[6px]">
      {["Exact", "Phrase", "Broad"].map((m, i) => (
        <StatusPill key={m} tone={i === sel ? "pale" : "grey"}>
          {m}
        </StatusPill>
      ))}
    </span>
  );
  return (
    <AppShell active="campaigns" workspace={alpha}>
      <PageHead
        title="Add keywords to Plumbing repairs."
        lead="Type the searches you want to show up for. Each one is checked against Google's rules and your blocked list before anything is added."
      />
      <Columns
        aside={
          <>
            <Panel title="What Google expects" tone="plain">
              <p className="text-ink mt-[10px] text-[15px] leading-[18px] font-medium">
                About 40 to 70 more clicks a month at $2.00 to $2.40 each, from Google&rsquo;s own
                planner.
              </p>
            </Panel>
            <Panel title="Checks" tone="plain">
              <Rows className="mt-1">
                <ListRow
                  title="Google's rules"
                  meta="No trademarks or banned words"
                  chip="Passed"
                  chipTone="pale"
                />
                <ListRow
                  title="Your blocked list"
                  meta="1 keyword removed"
                  chip="1 removed"
                  chipTone="amber"
                />
                <ListRow
                  title="Already in your account"
                  meta="No duplicates"
                  chip="None"
                  chipTone="pale"
                />
              </Rows>
            </Panel>
            <ActionPanel
              title="Ready to add"
              body="3 keywords go to Burst pipes and leaks. It shows in Activity with an undo."
              primary="Add 3 keywords"
              secondary="Cancel"
            />
          </>
        }
      >
        <Panel title="Which ad group" tone="plain">
          <Choice
            name="group"
            selected
            title="Burst pipes and leaks"
            meta="18 keywords · 21 calls in 30 days"
          />
          <Choice
            name="group"
            title="Drains and blocked toilets"
            meta="9 keywords · 6 calls in 30 days"
          />
          <Choice
            name="group"
            title="A new ad group"
            meta="Give it a name. We write an ad for it, and nothing goes live until you approve."
          />
        </Panel>
        <Panel title="Keywords" action={{ label: "Paste a list" }} tone="plain">
          <Rows className="mt-1">
            <ListRow
              title="frozen pipe repair"
              meta="Google expects 20 to 40 searches a month nearby"
              right={match(1)}
            />
            <ListRow
              title="burst pipe emergency"
              meta="Google expects 50 to 90 searches a month nearby"
              right={match(0)}
            />
            <ListRow
              title="pipe leak repair mississauga"
              meta="Google expects 10 to 30 searches a month"
              right={match(1)}
            />
            <ListRow
              title="free plumbing advice"
              meta="On your blocked list, so it will not be added"
              chip="Blocked"
              chipTone="red"
            />
          </Rows>
          <FieldRow label="Add another" placeholder="Type a search and press Enter" />
        </Panel>
        <Panel title="Bids" tone="plain">
          <Choice
            name="bids"
            selected
            title="Let Google set the bids"
            meta="This campaign uses Maximize conversions, so Google bids for each search. Your $14 cap still applies."
          />
          <Choice
            name="bids"
            disabled
            title="Set a top bid for these"
            meta="Only with manual bidding. Change the bidding strategy in campaign settings first."
          />
        </Panel>
      </Columns>
    </AppShell>
  );
}

/* ---------- 87:6490 ---------- */
export function WriteAd() {
  return (
    <AppShell active="campaigns" workspace={alpha}>
      <PageHead
        title="Write a new ad for Drains and blocked toilets."
        lead="Google mixes your headlines and descriptions, so each one must make sense on its own. Every line goes through the same checks as the ads we write."
      />
      <Columns
        aside={
          <>
            <Panel title="Preview" action={{ label: "Mobile" }} tone="plain">
              <div className="bg-ad-bg border-line mt-[14px] rounded-[12px] border px-4 py-4">
                <p className="text-muted text-[12px] leading-[15px]">
                  Sponsored · alphaplumbing.ca/drains/same-day
                </p>
                <p className="mt-[6px] text-[17px] leading-[21px] font-semibold text-[#1a4fb8]">
                  Blocked Drain? Same-Day Fix | Drain Cleaning in Mississauga
                </p>
                <p className="text-muted mt-[6px] text-[13px] leading-4">
                  Blocked toilet or slow drain? A licensed plumber can be there today, price agreed
                  first.
                </p>
              </div>
            </Panel>
            <Panel title="Ad strength" tone="plain">
              <Meter name="Good" value="4 headlines" fill={0.6} />
              <PanelText>
                Add 3 more headlines for Excellent. Google likes variety: a price, a promise, a
                place.
              </PanelText>
            </Panel>
            <ActionPanel
              title="Send to Google"
              body="Fix the 'best' headline first. Google reviews every new ad, usually within a day."
              primary="Send for review"
              secondary="Save draft"
              disabled
            />
          </>
        }
      >
        <Panel title="Headlines, 3 to 15" action={{ label: "Suggest more" }} tone="plain">
          <Rows className="mt-1">
            <ListRow
              title="Blocked Drain? Same-Day Fix"
              meta="27 of 30 characters"
              chip="Passes"
              chipTone="pale"
            />
            <ListRow
              title="Drain Cleaning in Mississauga"
              meta="29 of 30 characters"
              chip="Passes"
              chipTone="pale"
            />
            <ListRow
              title="Licensed Plumbers, 24 Hours"
              meta="27 of 30 characters"
              chip="Passes"
              chipTone="pale"
            />
            <ListRow
              title="The Best Drain Service in Town"
              meta="30 of 30 characters · 'best' needs proof Google can see"
              chip="Needs proof"
              chipTone="amber"
            />
          </Rows>
          <FieldRow label="Add a headline" placeholder="Up to 30 characters" />
        </Panel>
        <Panel title="Descriptions, 2 to 4" tone="plain">
          <Rows className="mt-1">
            <ListRow
              title={
                <span className="font-normal">
                  Blocked toilet or slow drain? A licensed plumber can be there today, price agreed
                  first.
                </span>
              }
              meta="88 of 90 characters"
              chip="Passes"
              chipTone="pale"
            />
            <ListRow
              title={
                <span className="font-normal">
                  Camera checks, drain clearing and repairs across Mississauga, Brampton and
                  Oakville.
                </span>
              }
              meta="84 of 90 characters"
              chip="Passes"
              chipTone="pale"
            />
          </Rows>
        </Panel>
        <Panel title="Where the ad sends people" tone="plain">
          <FieldRow label="Page" value="alphaplumbing.ca" />
          <FieldRow label="Shown as" value="alphaplumbing.ca/drains/same-day" />
        </Panel>
      </Columns>
    </AppShell>
  );
}

/* ---------- 87:10926 ---------- */
export function NewCampaign() {
  return (
    <AppShell active="campaigns" workspace={alpha}>
      <PageHead
        title="Start a new campaign."
        lead="Pick what it should be about. We write it the same way as your first one: from your site and from real searches, checked by rules. Nothing goes live until you approve."
      />
      <Columns
        aside={
          <>
            <Panel title="How it gets written" tone="plain">
              <ol className="mt-[10px]">
                <Step n={1} title="Read your water heater pages" meta="8 pages, about 20 seconds" />
                <Step
                  n={2}
                  title="Ask Google what people type"
                  meta="Real searches only. The writer cannot invent any."
                />
                <Step
                  n={3}
                  title="Write and check the ads"
                  meta="The writer drafts; rules check length, claims and trademarks."
                />
                <Step
                  n={4}
                  title="You review it"
                  meta="Nothing goes to Google until you approve."
                />
              </ol>
            </Panel>
            <ActionPanel
              title="Ready when you are"
              body="About a minute. The 4 water heater calls from Plumbing repairs move here, so your two campaigns never bid against each other."
              primary="Start writing"
              secondary="Cancel"
            />
          </>
        }
      >
        <Panel title="What should it be about?" tone="plain">
          <Choice
            name="about"
            selected
            title="Water heaters"
            meta="8 pages on your site · about 590 searches a month nearby · 4 calls already come from it in Plumbing repairs"
            chip="Suggested"
          />
          <Choice
            name="about"
            title="Sump pumps"
            meta="2 pages on your site · about 90 searches a month · small but cheap"
          />
          <Choice
            name="about"
            title="Something else"
            meta="Type a service. We check that people search for it near you first."
          />
        </Panel>
        <Panel title="Budget" tone="plain">
          <Choice
            name="budget"
            selected
            title="Use the room under your limit: $8 a day"
            meta="Takes you to $48 a day in total, the most you allowed."
          />
          <Choice
            name="budget"
            title="Move $8 a day from Plumbing repairs"
            meta="Keeps you at $40 a day. Plumbing repairs would have $20."
          />
          <Footnote>
            $8 a day is tight for a new campaign. Google learns faster from about $10.
          </Footnote>
        </Panel>
      </Columns>
    </AppShell>
  );
}

/* ---------- 87:5746 ---------- */
export function Website() {
  return (
    <AppShell active="campaigns" workspace={alpha}>
      <PageHead
        title="Your website, through Google's eyes."
        lead="Google rewards pages that load fast and match the ad. We cannot change your site, but here is what to ask your web person, most useful first."
      />
      <Tiles>
        <Tile tone="brand" label="Speed on phones" value="3.8 s" chip="Google wants under 2.5 s" />
        <Tile label="Works on phones" value="Yes" chip="Text and buttons fit" />
        <Tile label="Secure address" value="Yes" chip="https on every page" />
        <Tile label="Quality score, average" value="7 of 10" progress={0.7} />
      </Tiles>
      <Columns
        aside={
          <>
            <NoticeCard
              tone="amber"
              compact
              title="Send it to your web person"
              body="We write it up in plain terms with the numbers above, so they know exactly what to change."
              secondary={{ label: "Email the list" }}
            />
            <Panel title="How we check" tone="plain">
              <PanelText>
                Google&rsquo;s own speed test on a mid-range phone, run every week. Quality score
                comes straight from Google Ads.
              </PanelText>
            </Panel>
          </>
        }
      >
        <Panel title="What to fix, most useful first" tone="plain">
          <Rows className="mt-1">
            <ListRow
              title="Make the home page load faster on phones"
              meta="The big photo at the top is 2.4 MB. Shrinking it would save about 1.5 seconds."
              chip="High"
              chipTone="amber"
            />
            <ListRow
              title="Put the phone number at the top"
              meta="People on phones look for it first. Yours sits at the bottom of the page."
              chip="High"
              chipTone="amber"
            />
            <ListRow
              title="Give drains a page of its own"
              meta="Drain ads land on your home page. A matching page usually lifts quality score."
              chip="Medium"
            />
            <ListRow
              title="Show your licence number"
              meta="It builds trust and backs up 'licensed' in your ads."
              chip="Low"
            />
          </Rows>
        </Panel>
        <Panel title="Pages your ads send people to" tone="plain">
          <Rows className="mt-1">
            <ListRow
              title="alphaplumbing.ca"
              meta="Home page · 3.8 s on phones · used by 2 ad groups"
              chip="Slow"
              chipTone="amber"
            />
            <ListRow
              title="alphaplumbing.ca/water-heaters"
              meta="1.9 s on phones · used by 1 ad group"
              chip="Good"
              chipTone="pale"
            />
          </Rows>
        </Panel>
      </Columns>
    </AppShell>
  );
}

/* ---------- 87:5974 ---------- */
export function Starter() {
  return (
    <AppShell
      active="campaigns"
      workspace={{ name: "Kettle Creek Landscaping", meta: "Guelph, Ontario" }}
      initials="TK"
    >
      <PageHead
        title="Starter covers one campaign."
        lead="Kettle Creek already runs Lawn care. A second campaign, for snow removal, needs Growth. Nothing changes until you choose."
      />
      <Tiles>
        <Tile tone="brand" label="Your plan" value="Starter" chip="$49 a month" />
        <Tile label="Campaigns" value="1 of 1" chip="At the limit" chipTone="amber" />
        <Tile label="Growth" value="$99" chip="Up to four campaigns" />
        <Tile label="Ad spend this month" value="$910" progress={137 / 226} />
      </Tiles>
      <Columns
        aside={
          <ActionPanel
            title="Confirm the upgrade"
            body="Growth starts today. About $35 now, then $99 on 1 October. You can go back to Starter at the end of any month."
            primary="Upgrade"
            secondary="Cancel"
          />
        }
      >
        <Panel title="What would you like to do?" tone="plain">
          <Choice
            name="plan"
            selected
            title="Upgrade to Growth · $99 a month"
            meta="Up to four campaigns, call tracking and the Monday email. Today we charge the difference for the rest of September, about $35."
            chip="Suggested"
          />
          <Choice
            name="plan"
            title="Swap your campaign"
            meta="Pause Lawn care for the winter and run Snow removal instead. Stay on Starter."
          />
          <Choice
            name="plan"
            title="Not now"
            meta="Keep things as they are. Snow removal stays saved as a draft."
          />
        </Panel>
        <Panel title="What Growth adds" tone="plain">
          <Rows className="mt-1">
            <ListRow
              title="Up to four campaigns"
              meta="Lawn care and Snow removal can run side by side"
              chip="Included"
              chipTone="pale"
            />
            <ListRow
              title="Call tracking"
              meta="Count the calls your ads bring, not just clicks"
              chip="Included"
              chipTone="pale"
            />
            <ListRow
              title="Up to $5,000 of ad spend a month"
              meta="Starter stops at $1,500"
              chip="Included"
              chipTone="pale"
            />
          </Rows>
        </Panel>
      </Columns>
    </AppShell>
  );
}

/* ---------- 89:13120 ---------- */
export function AlertList() {
  const link = (l: string) => (
    <a href="/activity" className="text-brand shrink-0 text-[14px] leading-[17px] font-semibold">
      {l}
    </a>
  );
  return (
    <AppShell active="campaigns" workspace={alpha}>
      <PageHead
        title="Five alerts this week. Two need you."
        lead="Everything PPCWay noticed, newest first. Things that need you stay at the top until they are done; everything else is here so nothing happens behind your back."
      />
      <Tiles>
        <Tile tone="brand" label="Need you" value="2" chip="Calls and headlines" />
        <Tile label="Sorted by us" value="1" chip="The refused keyword" />
        <Tile label="For your information" value="2" chip="Nothing to do" />
        <Tile label="Answered this month" value="9 of 10" progress={0.9} />
      </Tiles>
      <Columns
        aside={
          <>
            <Panel title="Show" tone="plain">
              <FilterChips
                options={["All", "Needs you", "Sorted", "For your information"]}
                active="All"
              />
            </Panel>
            <Panel
              title="How we tell you"
              action={{ label: "Change", href: "/settings?view=notifications" }}
              tone="plain"
            >
              <PanelText>
                Things that need you come by email straight away. The rest go in your Monday email.
              </PanelText>
            </Panel>
          </>
        }
      >
        <Panel title="This week" action={{ label: "Mark all as read" }} tone="plain">
          <Rows className="mt-1">
            <ListRow
              title="Calls are down 40% this week"
              meta="A new competitor is outbidding you on 'emergency plumber near me'"
              right={
                <span className="flex items-center gap-3">
                  <StatusPill tone="amber">Needs you</StatusPill>
                  {link("See what we suggest")}
                </span>
              }
            />
            <ListRow
              title="2 weak headlines, new ones ready"
              meta="Google has rated them low after 5,000 views. The replacements need your OK"
              right={
                <span className="flex items-center gap-3">
                  <StatusPill tone="amber">Needs you</StatusPill>
                  {link("Review")}
                </span>
              }
            />
            <ListRow
              title="Google refused a keyword you added"
              meta="'roto rooter near me' is another company's trademark. We removed it; nothing else changed"
              right={
                <span className="flex items-center gap-3">
                  <StatusPill tone="pale">Sorted</StatusPill>
                  {link("Details")}
                </span>
              }
            />
            <ListRow
              title="Not all of Water heaters' budget was spent"
              meta="$4 of $9 a day used: fewer people searched this week. Nothing to fix, and we will not raise it"
              right={
                <span className="flex items-center gap-3">
                  <StatusPill>For your information</StatusPill>
                  {link("Details")}
                </span>
              }
            />
            <ListRow
              title="An idea expired without an answer"
              meta="Block 'plumbing supplies near me' was not answered in 7 days, so nothing changed"
              right={
                <span className="flex items-center gap-3">
                  <StatusPill>Expired</StatusPill>
                  {link("Suggest again")}
                </span>
              }
            />
          </Rows>
        </Panel>
      </Columns>
    </AppShell>
  );
}
