import { Button } from "@/components/ui/button";
import { AppShell, type Workspace } from "./shell";
import {
  Columns,
  ListRow,
  MiniBars,
  PageHead,
  Panel,
  PanelText,
  ReasonInput,
  Rows,
  Step,
  TabsRow,
  Tile,
  Tiles,
  Toggle,
} from "./blocks";
import { DetailPage, type DetailSpec } from "./detail-page";
import { DataTable, StatusWord } from "./table";

/*
  PPCWay staff: merchants, jobs, quota, errors, the audit log, reviews, staff,
  platform, rules, AI quality, metrics and the runbook. Support sees a read-only
  console; super admins get the second menu group.
*/
const support: Workspace = { name: "PPCWay admin", meta: "Internal, read only" };
const superAdmin: Workspace = { name: "PPCWay admin", meta: "Super admin, full access" };
const readOnly = {
  kind: "admin" as const,
  workspace: support,
  initials: "SO",
  period: "Today",
  badges: { errors: 3 },
};
const full = {
  kind: "admin-super" as const,
  workspace: superAdmin,
  initials: "RC",
  period: "Today",
  badges: { errors: 3, reviews: 3 },
};

/* ---------- 17:2479 ---------- */
export function Merchants() {
  return (
    <AppShell {...readOnly} active="merchants" period="Last 30 days">
      <PageHead
        title="42 merchants, three need a person."
        lead="Account health, job status and Google Ads quota across every merchant. You are in read only mode."
      />
      <Tiles>
        <Tile tone="brand" label="Merchants live" value="38" chip="Four more onboarding" />
        <Tile label="Need a person" value="3" chip="Oldest is four hours old" />
        <Tile label="Google API errors today" value="38" chip="14 at Northside Dental" />
        <Tile label="Daily quota used" value="61%" progress={0.61} />
      </Tiles>
      <TabsRow
        tabs={[
          { label: "Merchants", href: "/admin" },
          { label: "Jobs", href: "/admin/jobs" },
          { label: "Errors", href: "/admin/errors" },
          { label: "Quota", href: "/admin/quota" },
        ]}
        active="Merchants"
        action={
          <Button variant="secondary" size="sm" className="border-line h-[41px]">
            Open runbook
          </Button>
        }
      />
      <DataTable
        columns={[
          { key: "name", label: "Merchant", width: 300 },
          { key: "status", label: "Status" },
          { key: "tracking", label: "Tracking" },
          { key: "spend", label: "Spend 30d", align: "right" },
          { key: "failed", label: "Jobs failed", align: "right" },
          { key: "errors", label: "API errors", align: "right" },
          { key: "quota", label: "Quota", align: "right" },
          { key: "run", label: "Last good run" },
        ]}
        rows={[
          {
            name: "Alpha Plumbing",
            status: <StatusWord>Healthy</StatusWord>,
            tracking: <StatusWord>Working</StatusWord>,
            spend: "$1,240",
            failed: "0",
            errors: "0",
            quota: "1%",
            run: "Today 6:00",
          },
          {
            name: "Northside Dental",
            status: <StatusWord tone="red">Card declined</StatusWord>,
            tracking: <StatusWord>Working</StatusWord>,
            spend: "$820",
            failed: "7",
            errors: "14",
            quota: "2%",
            run: <StatusWord tone="red">3 Sep</StatusWord>,
          },
          {
            name: "Beacon Roofing",
            status: <StatusWord>Healthy</StatusWord>,
            tracking: <StatusWord tone="faint">Not live yet</StatusWord>,
            spend: "$0",
            failed: "0",
            errors: "1",
            quota: "18%",
            run: "Building",
          },
        ]}
        total={{
          name: "42 merchants",
          status: "3 flagged",
          tracking: "1 not live",
          spend: "$46,805",
          failed: "7",
          errors: "38",
          quota: "61%",
          run: "1 stale",
        }}
      />
      <Panel
        title="Flags from today's checks"
        action={{ label: "All flags" }}
        className="mt-4"
        tone="plain"
      >
        <Rows className="mt-1">
          <ListRow
            title="Beacon Roofing · one new ad refused by Google"
            meta="First campaign still building · the ad is waiting on Google's review"
            chip="Watching"
            chipTone="amber"
          />
          <ListRow
            title="Northgate HVAC · calls down 40% this week"
            meta="Tracking checked and working · two bid cuts are waiting for the owner"
            chip="Proposed"
          />
          <ListRow
            title="Hillside Dental · card declined at Google"
            meta="Ads stop in about 2 days · two reminders sent"
            chip="Billing"
            chipTone="red"
          />
        </Rows>
      </Panel>
    </AppShell>
  );
}

/* ---------- 70:230 ---------- */
export const merchantDetail: DetailSpec = {
  shell: { ...readOnly, active: "merchants" },
  head: {
    title: "Northside Dental needs a person.",
    lead: "Merchant 1042 · Starter · linked 12 Aug. You are viewing read only. Anything you change needs a written reason and a second approver, and the merchant is told.",
  },
  tiles: [
    { tone: "brand", label: "Google link", value: "Active", chip: "Token refreshed 6 hrs ago" },
    {
      label: "Billing at Google",
      value: "Declined",
      valueTone: "red",
      chip: "Since Thu 3 Sep",
      chipTone: "red",
    },
    { label: "API errors today", value: "14", chip: "All from the billing hold", chipTone: "grey" },
    { label: "Last good optimisation", value: "7 days ago", progress: 40 / 226 },
  ],
  why: {
    title: "What is going on",
    legend: "What the merchant sees",
    summary:
      "Google declined the card on 3 September, so the ads stopped. Google refuses every change while billing is on hold, so automation paused itself. We have emailed the merchant twice.",
  },
  record: {
    title: "Admin audit log for this merchant",
    action: "Export",
    rows: [
      {
        icon: "bars",
        iconTone: "brand",
        title: "Paused all automation · by the system",
        meta: "3 Sep 11:02 · reason: billing hold detected",
        action: "View",
      },
      {
        icon: "plus",
        iconTone: "brand",
        title: "Opened support view · by Sam Okafor",
        meta: "4 Sep 09:15 · reason: merchant asked why ads stopped · merchant told",
        action: "View",
      },
      {
        icon: "line",
        iconTone: "brand",
        title: "Re-ran the billing check · by Sam Okafor",
        meta: "4 Sep 09:21 · reason: confirm the hold · result: still declined",
      },
    ],
  },
  next: {
    title: "Jobs and workflows",
    action: "Open in Temporal",
    mock: {
      kicker: "Failing, queue paused",
      source: "daily bid check · search term mining · budget pacing",
      headline: "7 failed runs today, next retry at 14:00",
      body: "Every failure is a change Google refused while billing is on hold. Retrying will not help until the card is fixed, so the queue is paused and nothing is piling up.",
    },
    footnote: "This merchant used 2% of today's operations budget, mostly retries.",
  },
  notice: {
    tag: "Override",
    title: "Change something for this merchant",
    body: "Say why before you act. Write access needs a second approver, and the merchant gets an email saying who and why.",
    children: <ReasonInput value="Card updated, merchant asked for a re-sync" />,
    primary: { label: "Ask for write access" },
    secondary: { label: "Cancel" },
  },
  list: {
    title: "Manual tools",
    rows: [
      {
        title: "Force a re-sync",
        meta: "Pull fresh numbers from Google",
        chip: "Reason",
        chipTone: "amber",
        dot: true,
      },
      {
        title: "Revert an action",
        meta: "Undo one change from the log",
        chip: "2 people",
        chipTone: "amber",
        dot: true,
      },
      {
        title: "Re-run generation",
        meta: "Rebuild the campaign from the profile",
        chip: "2 people",
        chipTone: "amber",
        dot: true,
      },
      {
        title: "Pause automation here",
        meta: "This merchant only, ads keep running",
        chip: "Reason",
        chipTone: "amber",
        dot: true,
      },
    ],
  },
};

/* ---------- 87:9604 ---------- */
export const changeLog: DetailSpec = {
  shell: { ...full, active: "merchants" },
  head: {
    title: "Alpha Plumbing's change log, as support sees it.",
    lead: "Merchant 1017 · Growth · linked 4 Aug. Every automatic change with the rule, the limits in force and the numbers it looked at. The owner sees the same rows in plain English.",
  },
  tiles: [
    { tone: "brand", label: "Changes, 30 days", value: "14", chip: "All written before sending" },
    {
      label: "Refused by Google",
      value: "1",
      valueTone: "red",
      chip: "Keyword removed outside PPCWay",
      chipTone: "red",
    },
    { label: "Held by limits", value: "1", chip: "A 30% bid raise", chipTone: "grey" },
    { label: "Limits version", value: "4", progress: 1 },
  ],
  why: {
    title: "Selected change",
    legend: "Rule 4.2, version 3",
    summary:
      "Lowered the top bid on Drains and blocked toilets from $14.00 to $11.50. Approved by Dana at 7:41 pm, applied at 6:12 am on 8 Sep, and Google confirmed it.",
  },
  record: {
    title: "Change log",
    action: "Export CSV",
    rows: [
      {
        icon: "bars",
        iconTone: "brand",
        title: "Lowered top bid · Drains · rule 4.2 v3",
        meta: "8 Sep 06:12 · limits v4 · metrics to 7 Sep · applied",
        action: "Open",
      },
      {
        icon: "plus",
        iconTone: "brand",
        title: "Held: raise bid 30% · Burst pipes · rule 4.1 v3",
        meta: "6 Sep 06:00 · limits v4 said no: 20% a day · rejected",
        action: "Open",
      },
      {
        icon: "line",
        iconTone: "brand",
        title: "Lower bid · water heater repair · rule 4.2 v3",
        meta: "10 Sep 06:02 · Google: RESOURCE_NOT_FOUND · failed",
      },
      {
        icon: "line",
        iconTone: "brand",
        title: "Budget $40 to $32 · proposal · rule 2.1 v2",
        meta: "8 Sep 06:00 · waiting for the owner · expires 15 Sep",
      },
    ],
  },
  next: {
    title: "Numbers the rule looked at",
    action: "Raw JSON",
    mock: {
      kicker: "Metrics snapshot",
      source: "Drains and blocked toilets · 14 days to 7 Sep",
      headline: "$114 spent · 3 calls · $38.00 a call against $35",
      body: "The rule lowers a bid when cost per call runs more than 5% over the owner's limit for 14 days. Before $14.00, after $11.50, inside the 20% a day limit.",
    },
    footnote: "Read only. Opening this page is logged, like every support view.",
  },
  notice: {
    tag: "Privacy request",
    title: "Dana asked for an export of her data",
    body: "She emailed support this morning. Run it for her: she gets the files and an email, and the request lands in the audit log.",
    children: <ReasonInput value="Owner asked by email, ticket 4821" />,
    primary: { label: "Run the export" },
    secondary: { label: "Cancel" },
  },
  list: {
    title: "Other records",
    rows: [
      {
        title: "Access log",
        meta: "Who opened this account",
        chip: "2 this month",
        chipTone: "amber",
        dot: true,
      },
      {
        title: "Full-auto consent",
        meta: "Not given · on Ask first",
        chip: "None",
        chipTone: "amber",
        dot: true,
      },
      {
        title: "Re-run generation",
        meta: "Rebuild the campaign from the profile",
        chip: "2 people",
        chipTone: "amber",
        dot: true,
      },
      {
        title: "Pause automation here",
        meta: "This merchant only, ads keep running",
        chip: "Reason",
        chipTone: "amber",
        dot: true,
      },
    ],
  },
  asideExtra: (
    <Panel title="Delete on request" tone="plain">
      <PanelText>
        Only when the owner asks. It needs a reason and a second approver, and the owner is emailed
        at each step.
      </PanelText>
      <Button variant="secondary" size="sm" className="border-line mt-4 h-11">
        Start a deletion
      </Button>
    </Panel>
  ),
};

/* ---------- 74:813 ---------- */
export const jobs: DetailSpec = {
  shell: { ...readOnly, active: "jobs" },
  head: {
    title: "Jobs are healthy. Quota is at 61%.",
    lead: "Every scheduled check across 42 merchants, and how much of today's operations budget they have used. Alerts go out at 60%, 80% and 92%.",
  },
  tiles: [
    { tone: "brand", label: "Jobs run today", value: "348", chip: "Across 42 merchants" },
    {
      label: "Failed",
      value: "7",
      valueTone: "red",
      chip: "All at Northside Dental",
      chipTone: "red",
    },
    { label: "Waiting for approval", value: "19", chip: "Oldest is 5 days old" },
    { label: "Google API quota used", value: "61%", progress: 0.61 },
  ],
  why: {
    title: "Quota by the end of today",
    legend: "Projection",
    summary:
      "At this pace we reach 74% of today's allowance before it resets tonight, comfortably under the 80% warning. Keyword planning is the heaviest job, limited to about one request a second per account.",
  },
  record: {
    title: "Jobs by type",
    action: "Open in Temporal",
    rows: [
      {
        icon: "bars",
        iconTone: "brand",
        title: "Daily bid check",
        meta: "42 runs · 42 done · about 38 seconds each",
        action: "View",
      },
      {
        icon: "plus",
        iconTone: "brand",
        title: "Search term mining",
        meta: "42 runs · 40 done · 2 failed at Northside Dental",
        action: "View",
      },
      {
        icon: "line",
        iconTone: "brand",
        title: "Spend checks, 4 times a day",
        meta: "126 runs so far · 121 done · 5 failed, all Northside Dental",
      },
    ],
  },
  next: {
    title: "Waiting for merchant approval",
    action: "See the queue",
    mock: {
      kicker: "Expiring soon",
      source: "4 proposals expire in the next 2 days, at 3 merchants",
      headline: "Anything not approved in 7 days quietly expires",
      body: "We remind the merchant on day 5. An expired proposal changes nothing, and the same idea is not suggested again for 30 days.",
    },
    footnote:
      "Quota counts come from our own tally of every request, checked against Google's report every hour.",
  },
  extra: (
    <>
      <Panel title="Stuck or retrying" action={{ label: "Open in Temporal" }} tone="plain">
        <Rows className="mt-1">
          <ListRow
            title="Northside Dental · budget pacing"
            meta="5 failed today · 3 retries left · next try 14:00"
            chip="Retrying"
            chipTone="amber"
          />
          <ListRow
            title="Northside Dental · search-term mining"
            meta="Stuck 7 days · waiting for billing to clear"
            chip="Stuck"
            chipTone="red"
          />
          <ListRow
            title="Beacon Roofing · campaign build"
            meta="Running 38 minutes · step 6 of 9, writing ads"
            chip="Running"
          />
        </Rows>
      </Panel>
      <Panel title="Queue and sync" action={{ label: "Open in Temporal" }} tone="plain">
        <Rows className="mt-1">
          <ListRow
            title="Jobs waiting"
            meta="12 in the queue · oldest 4 minutes"
            chip="Normal"
            chipTone="pale"
          />
          <ListRow
            title="Retries today"
            meta="18 retries · all but the 5 at Northside Dental succeeded"
            chip="Normal"
            chipTone="pale"
          />
          <ListRow
            title="Mismatches with Google"
            meta="2 found at the 6 am sync · both edits made in Google Ads · copies updated"
            chip="Resolved"
          />
        </Rows>
      </Panel>
    </>
  ),
  notice: {
    tag: "At 80%",
    title: "What happens as quota fills",
    body: "At 80% we page the on-call engineer and hold low-priority jobs such as ad reviews. Budget pacing and billing checks never wait.",
    primary: { label: "Open runbook", href: "/admin/runbook" },
    secondary: { label: "Later" },
  },
  list: {
    title: "Heaviest merchants today",
    rows: [
      {
        title: "Beacon Roofing",
        meta: "18% of the budget · building a campaign",
        chip: "Normal",
        chipTone: "pale",
        dot: true,
      },
      {
        title: "Northside Dental",
        meta: "2% · retries while billing is on hold",
        chip: "Normal",
        chipTone: "pale",
        dot: true,
      },
    ],
  },
};

/* ---------- 76:1584 ---------- */
export const errors: DetailSpec = {
  shell: { ...full, active: "errors" },
  head: {
    title: "38 Google API errors today, and 15 need a person.",
    lead: "Every failed call to the Google Ads API in the last 24 hours, by type, by service and by merchant. We raise an alert when an hour has three times its usual count.",
  },
  tiles: [
    { tone: "brand", label: "Errors today", value: "38", chip: "0.4% of calls, usually 0.3%" },
    { label: "Cleared on retry", value: "23", chip: "Google's own blips" },
    { label: "Need a person", value: "15", chip: "14 at Northside Dental", chipTone: "amber" },
    { label: "Error rate, alert at 1%", value: "0.4%", progress: 0.4 },
  ],
  why: {
    title: "Errors by hour, last 24 hours",
    legend: "One spike, at 06:00",
    summary:
      "Google had a short outage at 06:00 and 19 calls failed. Every one went through on the first retry. The steady trickle since then is Northside Dental, where Google refuses changes until the card is fixed.",
    bars: {
      height: 110,
      bars: [4, 9, 4, 9, 4, 4, 9, 4, 15, 105, 9, 9, 9, 9, 9, 9, 15, 9, 9, 9, 9, 9, 9, 4].map(
        (h, i) => ({ h: h / 105, tone: i === 9 ? "brand" : h <= 4 ? "empty" : "soft" }),
      ),
      labels: ["24 hours ago", "12 hours ago", "Now"],
    },
  },
  record: {
    title: "By type of error",
    action: "Export CSV",
    rows: [
      {
        icon: "bars",
        iconTone: "brand",
        title: "Temporary error at Google, retried",
        meta: "23 today · InternalError.TRANSIENT_ERROR · all went through",
        action: "View",
      },
      {
        icon: "plus",
        iconTone: "amber",
        title: "Change refused while billing is on hold",
        meta: "14 today · Northside Dental · CampaignBudgetService",
        action: "View",
      },
      {
        icon: "line",
        iconTone: "amber",
        title: "Ad refused under a Google policy",
        meta: "1 today · Beacon Roofing · PolicyFindingError.POLICY_FINDING",
      },
    ],
  },
  next: {
    title: "By Google Ads service",
    action: "Last 7 days",
    mock: {
      kicker: "Busiest service today",
      source: "GoogleAdsService, which reads reports",
      headline: "19 errors, all during Google's outage at 06:00",
      body: "CampaignBudgetService had 14, all at Northside Dental. AdGroupAdService had 1, at Beacon Roofing. The other 4 were spread across services and cleared on retry.",
    },
    footnote:
      "Counts come from our own log of every Google Ads API call, matched to Google's error codes.",
  },
  extra: (
    <Panel title="Refused ads, all merchants" action={{ label: "Last 14 days" }} tone="plain">
      <p className="text-ink mt-[14px] text-[15px] leading-[18px]">
        0.6% of new ads were refused this week, against a usual 0.5%. A sudden jump here is the
        first warning sign for the developer token, so it pages the on-call engineer at 2%.
      </p>
      <MiniBars
        height={90}
        bars={[60, 48, 72, 60, 48, 60, 72, 60, 60, 48, 72, 84, 72, 72].map((h, i) => ({
          h: h / 84,
          tone: i === 13 ? "brand" : "soft",
        }))}
        labels={["14 days ago", undefined, "Today"]}
      />
    </Panel>
  ),
  notice: {
    tag: "3 open",
    title: "Three alerts are open",
    body: "Northside Dental is waiting on the owner's card. Beacon Roofing's ad is waiting on Google's review. The 06:00 spike needs a person to confirm it was on Google's side, then close it.",
    primary: { label: "Close the spike" },
    secondary: { label: "Later" },
  },
  list: {
    title: "Errors by merchant",
    rows: [
      {
        title: "Northside Dental",
        meta: "14 errors · changes refused",
        chip: "Billing hold",
        chipTone: "red",
        dot: true,
      },
      {
        title: "Beacon Roofing",
        meta: "1 error · ad refused",
        chip: "In review",
        chipTone: "amber",
        dot: true,
      },
    ],
  },
};

/* ---------- 82:3896 ---------- */
export const quota: DetailSpec = {
  shell: { ...full, active: "quota" },
  head: {
    title: "61% of today's budget, heading for 74%.",
    lead: "Google's Standard access has no daily cap, so we keep our own budget of 4,000 operations a day and a runaway job shows up here first. Alerts go out at 60%, 80% and 92%; low-priority jobs wait from 80%.",
  },
  tiles: [
    { tone: "brand", label: "Used today", value: "2,440", chip: "Of 4,000 · resets at 3 am" },
    { label: "By 3 am", value: "74%", chip: "Below the 80% line" },
    { label: "Per merchant", value: "41", chip: "Operations a day, steady" },
    { label: "Budget used", value: "61%", progress: 0.61 },
  ],
  why: {
    title: "Operations by hour",
    legend: "Projected to 3 am",
    summary:
      "A normal Thursday. Most operations are reports we read four times a day, plus Monday and Thursday search-term mining at noon. Beacon Roofing's new campaign added about 720 this morning.",
    bars: {
      height: 104,
      bars: [4, 5, 8, 54, 12, 14, 50, 45, 16, 100, 13, 11, 5, 4, 4, 21, 4, 3, 3, 3, 3, 4, 3, 3].map(
        (h, i) => ({ h: h / 100, tone: i === 10 ? "brand" : i > 10 ? "empty" : "soft" }),
      ),
      labels: ["3 am", "Now, 2 pm", "3 am"],
    },
  },
  record: {
    title: "By job class",
    action: "Open in Temporal",
    rows: [
      {
        icon: "bars",
        iconTone: "brand",
        title: "Critical · never waits",
        meta: "Policy, billing and anomaly checks · 390 today",
        action: "View",
      },
      {
        icon: "plus",
        iconTone: "brand",
        title: "High · runs first",
        meta: "Reports, budget pacing, bid tuning · 1,020 today",
        action: "View",
      },
      {
        icon: "line",
        iconTone: "brand",
        title: "Medium and low · wait from 80%",
        meta: "Search-term mining, ad reviews · 310 today · new campaigns 720",
      },
    ],
  },
  next: {
    title: "By Google Ads service",
    action: "Last 7 days",
    mock: {
      kicker: "Top service today",
      source: "GoogleAdsService, reading reports",
      headline: "1,310 operations, 54% of today",
      body: "KeywordPlanIdeaService 420, mostly Beacon Roofing's new campaign. AdGroupCriterionService 330 for keywords and blocks. CampaignBudgetService 190. Everything else 190.",
    },
    footnote:
      "Counts come from our own tally of every call, checked against Google's report every hour.",
  },
  extra: (
    <Panel title="Accounts slowed by Google" action={{ label: "Last 24 hours" }} tone="plain">
      <Rows className="mt-1">
        <ListRow
          title="Beacon Roofing · keyword planning"
          meta="Held to 1 request a second · 42 waits today, no failures"
          chip="Throttled"
          chipTone="amber"
        />
        <ListRow
          title="Northside Dental · budget pacing"
          meta="Backing off between retries · 3 retries left"
          chip="Backing off"
        />
      </Rows>
    </Panel>
  ),
  notice: {
    tag: "60% alert",
    title: "The 60% alert went out at 13:10",
    body: "Nothing to do yet. At 80% we page the on-call engineer and hold low-priority jobs. Budget pacing and billing checks never wait.",
    primary: { label: "Change the budget" },
    secondary: { label: "Later" },
  },
  list: {
    title: "Heaviest merchants today",
    rows: [
      {
        title: "Beacon Roofing",
        meta: "720 today · building a campaign",
        chip: "Normal",
        chipTone: "pale",
        dot: true,
      },
      {
        title: "Northside Dental",
        meta: "80 today · billing retries",
        chip: "Watching",
        chipTone: "amber",
        dot: true,
      },
    ],
  },
};

/* ---------- 76:1811 ---------- */
export const audit: DetailSpec = {
  shell: { ...full, active: "audit", period: "Last 10 days" },
  head: {
    title: "Every admin action, with a name and a reason.",
    lead: "Kept for seven years and never edited, not even by a super admin. Support views are listed too, because the merchant is told about each one.",
  },
  tiles: [
    {
      tone: "brand",
      label: "Actions, last 10 days",
      value: "8",
      chip: "By 3 people and the system",
    },
    { label: "Support views", value: "2", chip: "Both merchants were told" },
    {
      label: "Needed a second approver",
      value: "3",
      chip: "1 more waiting now",
      chipTone: "amber",
    },
    {
      label: "Rows without a reason",
      value: "0",
      chip: "A reason is required to save",
      chipTone: "grey",
    },
  ],
  why: {
    title: "The last 10 days in brief",
    legend: "Kept for 7 years",
    summary:
      "Sam Okafor opened two support views and asked for write access once. Rhea Castillo changed one platform default and allowed one restricted business. Lena Park reverted one change. The system paused Northside Dental when its card was declined.",
  },
  record: {
    title: "All admin actions",
    action: "Export CSV",
    rows: [
      {
        icon: "bars",
        iconTone: "amber",
        title: "Asked for write access · Northside Dental · by Sam Okafor",
        meta: "10 Sep 11:42 · reason: card updated, owner wants a re-sync · waiting",
        action: "View",
      },
      {
        icon: "plus",
        iconTone: "brand",
        title: "Opened support view · Alpha Plumbing · by Sam Okafor",
        meta: "10 Sep 10:12 · reason: owner asked why a bid went down · merchant told",
        action: "View",
      },
      {
        icon: "plus",
        iconTone: "brand",
        title: "Changed a platform default · every merchant · by Rhea Castillo",
        meta: "10 Sep 09:05 · largest daily change 25% to 20% · Omar approved",
        action: "View",
      },
      {
        icon: "plus",
        iconTone: "brand",
        title: "Category exception · Lakeview Massage · by Rhea Castillo",
        meta: "9 Sep 16:20 · reason: massage only, no health claims · Omar approved",
        action: "View",
      },
      {
        icon: "plus",
        iconTone: "brand",
        title: "Reverted an action · Kettle Creek Landscaping · by Lena Park",
        meta: "8 Sep 14:03 · reason: owner disputed a keyword pause · Omar approved",
        action: "View",
      },
      {
        icon: "plus",
        iconTone: "brand",
        title: "Re-ran the billing check · Northside Dental · by Sam Okafor",
        meta: "4 Sep 09:21 · reason: confirm the hold · result: still declined",
        action: "View",
      },
      {
        icon: "plus",
        iconTone: "brand",
        title: "Opened support view · Northside Dental · by Sam Okafor",
        meta: "4 Sep 09:15 · reason: merchant asked why ads stopped · merchant told",
        action: "View",
      },
      {
        icon: "bars",
        iconTone: "grey",
        title: "Paused all automation · Northside Dental · by the system",
        meta: "3 Sep 11:02 · reason: billing hold detected",
        action: "View",
      },
    ],
  },
  next: {
    title: "Kept for disputes",
    action: "Retention policy",
    mock: {
      kicker: "Seven years, append only",
      source: "The same rule as the change log merchants see",
      headline: "Nobody can edit or delete a row, including super admins",
      body: "If a merchant disputes a change, export their rows as a PDF with Google's own change history beside it. Deleting a merchant's account strips their personal details from these rows but keeps the record.",
    },
    footnote:
      "Times are Toronto time. A row is written before the action runs, so a failed action still leaves a record.",
  },
  notice: {
    tag: "Waiting",
    title: "Sam's request needs a second approver",
    body: "Write access to Northside Dental, asked at 11:42. If nobody approves it by 12:42 it lapses and Sam has to ask again.",
    primary: { label: "Review the request", href: "/admin/reviews?view=access" },
    secondary: { label: "Later" },
  },
  list: {
    title: "By person, last 10 days",
    rows: [
      { title: "Sam Okafor", meta: "4 actions · support", chip: "Support", dot: true },
      {
        title: "Rhea Castillo",
        meta: "2 actions · platform and reviews",
        chip: "Super admin",
        chipTone: "pale",
        dot: true,
      },
      { title: "Lena Park", meta: "1 action · support", chip: "Support", dot: true },
      { title: "The system", meta: "1 action · automatic pause", chip: "Automatic", dot: true },
    ],
  },
  asideExtra: (
    <Panel title="Selected row" action={{ label: "Export" }} tone="plain">
      <p className="text-ink mt-1 text-[15px] leading-[18px] font-semibold">
        Changed a platform default
      </p>
      <Rows className="mt-1">
        <ListRow
          title="Largest daily change"
          meta="Before 25%"
          right={<span className="text-ink text-[14px] font-semibold">After 20%</span>}
        />
        <ListRow
          title="Defaults version"
          meta="Before 6"
          right={<span className="text-ink text-[14px] font-semibold">After 7</span>}
        />
        <ListRow
          title="Approvals expire"
          meta="Before 7 days"
          right={<span className="text-faint text-[14px]">Unchanged</span>}
        />
        <ListRow title="Reason typed" meta="Match the new launch policy" />
      </Rows>
    </Panel>
  ),
};

/* ---------- 76:2084 ---------- */
export const accessRequest: DetailSpec = {
  shell: { ...full, active: "reviews" },
  head: {
    title: "Sam wants write access to Northside Dental.",
    lead: "You are the second approver. Access lasts one hour and covers only the two steps Sam listed. The owner gets an email naming you both, and every step lands in the audit log.",
  },
  tiles: [
    { tone: "brand", label: "Asked by", value: "Sam Okafor", chip: "Support · two-step on" },
    { label: "Billing at Google", value: "Active", chip: "Card accepted at 11:38" },
    {
      label: "Access asked for",
      value: "1 hour",
      chip: "Starts when you approve",
      chipTone: "grey",
    },
    { label: "Request lapses in", value: "48 min", progress: 0.8 },
  ],
  why: {
    title: "What Sam wants to do",
    legend: "In Sam's words",
    summary:
      "Force a re-sync from Google, then turn automation back on. The owner updated the card this morning and Google shows billing as active, so the hold that paused everything on 3 September is over.",
  },
  record: {
    title: "What will change",
    action: "See before and after",
    rows: [
      {
        icon: "bars",
        iconTone: "brand",
        title: "Pull fresh numbers from Google",
        meta: "Force re-sync · reads only, changes nothing in the account",
        action: "Step 1",
      },
      {
        icon: "plus",
        iconTone: "brand",
        title: "Turn automation back on",
        meta: "Paused by the system on 3 Sep · before: paused · after: on",
        action: "Step 2",
      },
      {
        icon: "line",
        iconTone: "grey",
        title: "Nothing else",
        meta: "Limits, budget, keywords and ads stay as the owner set them",
      },
    ],
  },
  next: {
    title: "Proof from Google",
    action: "Open in Google Ads",
    mock: {
      kicker: "Billing check, 10 Sep 11:38",
      source: "Read from Google Ads for customer 604-218-5530",
      headline: "Card accepted, the account can serve ads again",
      body: "The declined hold from 3 September is cleared on Google's side. Our copy of the account is six days old, which is why Sam wants the re-sync before anything restarts.",
    },
    footnote: "Sam asked at 11:42. The request lapses at 12:42 if nobody approves it.",
  },
  notice: {
    tag: "Your decision",
    title: "Approve write access for one hour?",
    body: "Write a reason. It goes in the audit log and in the email to the owner. Nobody can approve their own request.",
    children: <ReasonInput value="Billing is active at Google, re-sync is safe" />,
    primary: { label: "Approve for 1 hour" },
    secondary: { label: "Decline" },
  },
  list: {
    title: "Also waiting in Reviews",
    rows: [
      {
        title: "Keyway Locksmiths",
        meta: "Category decision · 2 days",
        chip: "Decide",
        chipTone: "amber",
        dot: true,
      },
      {
        title: "Harbour Physiotherapy",
        meta: "Category decision · 5 hours",
        chip: "Decide",
        chipTone: "amber",
        dot: true,
      },
    ],
  },
};

/* ---------- 76:2256 ---------- */
export const categories: DetailSpec = {
  shell: { ...full, active: "reviews" },
  head: {
    title: "Two businesses are waiting on a category decision.",
    lead: "Onboarding stops before any ads are written when a business falls in a category Google restricts. Most stay blocked. Allow one only when Google's own rules permit it, write down why, and a second admin confirms.",
  },
  tiles: [
    { tone: "brand", label: "Waiting for a decision", value: "2", chip: "Oldest is 2 days" },
    {
      label: "Blocked since launch",
      value: "6",
      chip: "Health, finance and cannabis",
      chipTone: "grey",
    },
    { label: "Allowed since launch", value: "2", chip: "Both with extra guardrails" },
    { label: "Decided within 2 days", value: "7 of 8", progress: 7 / 8 },
  ],
  why: {
    title: "Keyway Locksmiths, waiting 2 days",
    legend: "Locksmith",
    summary:
      "Google only shows locksmith ads from businesses it has verified. Keyway sent Google's approval email from 8 September. If the name and address match their Google Ads account, they can go ahead.",
  },
  record: {
    title: "The queue",
    action: "Category rules",
    rows: [
      {
        icon: "bars",
        iconTone: "amber",
        title: "Keyway Locksmiths · Mississauga",
        meta: "Locksmith · Google verified them on 8 Sep · waiting 2 days",
        action: "Decide",
      },
      {
        icon: "plus",
        iconTone: "amber",
        title: "Harbour Physiotherapy · Oakville",
        meta: "Health care · physio only, no restricted treatments · 5 hours",
        action: "Decide",
      },
      {
        icon: "line",
        iconTone: "red",
        title: "Greenleaf Dispensary · Brampton",
        meta: "Cannabis · Google does not allow these ads · blocked, no exception",
      },
    ],
  },
  next: {
    title: "What an exception comes with",
    action: "Edit the rules",
    mock: {
      kicker: "Conditions on every exception",
      source: "Applied as soon as the second admin confirms",
      headline: "A stricter ad checker and a category block list",
      body: "For health care that means no treatment claims, no before and after wording, and blocked searches such as drug names. For locksmiths, every ad uses the verified business name. Each exception is reviewed again after 12 months.",
    },
    footnote:
      "Each decision is saved on the merchant's record with the admin's name, the reason and the evidence.",
  },
  notice: {
    tag: "Decision",
    title: "Allow Keyway Locksmiths?",
    body: "Check that the name on Google's email matches their Google Ads account, 482-119-3307. Then write your reason. A second admin confirms before onboarding carries on.",
    children: <ReasonInput value="Google verified them 8 Sep, details match" />,
    primary: { label: "Allow" },
    secondary: { label: "Keep blocked" },
  },
  list: {
    title: "Category rules we check",
    rows: [
      {
        title: "Locksmiths",
        meta: "Allowed once Google verifies them",
        chip: "Evidence",
        chipTone: "amber",
        dot: true,
      },
      {
        title: "Health care",
        meta: "Blocked, exceptions case by case",
        chip: "2 people",
        chipTone: "amber",
        dot: true,
      },
      {
        title: "Cannabis, gambling, lending",
        meta: "Blocked, no exceptions",
        chip: "Never",
        chipTone: "red",
        dot: true,
      },
    ],
  },
};

/* ---------- 87:9836 ---------- */
export const blockList: DetailSpec = {
  shell: { ...full, active: "reviews" },
  head: {
    title: "4 searches to add to the plumbing block list.",
    lead: "Our weekly check looks across merchants for searches that cost money and never bring a call. A person decides; nothing joins a shared list on its own.",
  },
  tiles: [
    { tone: "brand", label: "Suggested this week", value: "5", chip: "4 to add, 1 to leave off" },
    { label: "Merchants affected", value: "5", chip: "All plumbers" },
    { label: "Money it wasted", value: "$189", chip: "Last 30 days, no calls" },
    { label: "Approved last week", value: "4 of 5", progress: 0.8 },
  ],
  why: {
    title: "Why these",
    legend: "Weekly, human reviewed",
    summary:
      "Across plumbers, these searches cost money and never brought a call. Adding them to the shared list blocks them for every plumber, new and old, from the next check.",
  },
  record: {
    title: "Suggested for the plumbing list",
    action: "See the evidence",
    rows: [
      {
        icon: "bars",
        iconTone: "brand",
        title: "plumber salary",
        meta: "$62 across 4 plumbers · 0 calls",
        action: "Add",
      },
      {
        icon: "plus",
        iconTone: "brand",
        title: "plumbing apprenticeship",
        meta: "$48 across 3 plumbers · 0 calls",
        action: "Add",
      },
      {
        icon: "line",
        iconTone: "brand",
        title: "diy toilet repair",
        meta: "$41 across 5 plumbers · 0 calls",
      },
      {
        icon: "line",
        iconTone: "brand",
        title: "plumbing supplies near me",
        meta: "$38 across 2 plumbers · 0 calls",
      },
    ],
  },
  next: {
    title: "Needs a person",
    action: "Leave it off",
    mock: {
      kicker: "Not a clear waste",
      source: "drain snake rental · 38 clicks · 1 call",
      headline: "Renters sometimes call a plumber after trying",
      body: "One call from 38 clicks is weak, but it is not nothing. Keep it off the shared list and let each plumber's own mining decide.",
    },
    footnote:
      "Shared lists are versioned. Every addition names the reviewer and can be taken back.",
  },
  notice: {
    tag: "Review by Friday",
    title: "Add the 4 clear ones?",
    body: "They join the plumbing list as version 12 and apply at the next check. Rhea's name goes in the list history.",
    primary: { label: "Add all 4" },
    secondary: { label: "Later" },
  },
  list: {
    title: "Shared block lists",
    rows: [
      {
        title: "Plumbing",
        meta: "212 searches · version 11",
        chip: "Live",
        chipTone: "pale",
        dot: true,
      },
      {
        title: "Heating and cooling",
        meta: "164 searches · version 7",
        chip: "Live",
        chipTone: "pale",
        dot: true,
      },
    ],
  },
};

/* ---------- 76:2494 ---------- */
export function Staff() {
  const on = <StatusWord>On</StatusWord>;
  return (
    <AppShell {...full} active="staff">
      <PageHead
        title="4 people can see inside merchant accounts."
        lead="Every admin signs in with a two-step code. Support is read only, and any change needs a second approver. Removing someone here ends their sessions straight away."
      />
      <Tiles>
        <Tile tone="brand" label="People with access" value="5" chip="2 super admins, 3 staff" />
        <Tile label="Two-step sign-in" value="5 of 5" chip="Required for every admin" />
        <Tile label="Open sessions" value="3" chip="End after 30 min idle" />
        <Tile label="Next access review" value="1 Dec" progress={25 / 226} />
      </Tiles>
      <TabsRow
        tabs={[
          { label: "People", href: "/admin/staff" },
          { label: "Roles", href: "/admin/staff" },
          { label: "Sign-in log", href: "/admin/staff" },
          { label: "Invites", href: "/admin/staff" },
        ]}
        active="People"
        action={
          <Button variant="secondary" size="sm" className="border-line h-[41px]">
            Invite a person
          </Button>
        }
      />
      <DataTable
        columns={[
          { key: "name", label: "Person", width: 300 },
          { key: "role", label: "Role" },
          { key: "data", label: "Merchant data" },
          { key: "platform", label: "Platform" },
          { key: "two", label: "Two-step" },
          { key: "active", label: "Last active" },
          { key: "sessions", label: "Sessions", align: "right" },
          { key: "review", label: "Access review" },
        ]}
        rows={[
          {
            name: "Rhea Castillo",
            role: "Super admin",
            data: "Read, approve",
            platform: "Edit",
            two: on,
            active: "Now",
            sessions: "1",
            review: "1 Sep",
          },
          {
            name: "Omar Haddad",
            role: "Super admin",
            data: "Read, approve",
            platform: "Edit",
            two: on,
            active: "Yesterday",
            sessions: "0",
            review: "1 Sep",
          },
          {
            name: "Sam Okafor",
            role: "Support",
            data: "Read only",
            platform: "None",
            two: on,
            active: "12 min ago",
            sessions: "1",
            review: "1 Sep",
          },
          {
            name: "Lena Park",
            role: "Support",
            data: "Read only",
            platform: "None",
            two: on,
            active: "2 hrs ago",
            sessions: "1",
            review: "1 Sep",
          },
          {
            name: "Tom Adeyemi",
            role: "Engineer",
            data: "None",
            platform: "Jobs only",
            two: on,
            active: "Yesterday",
            sessions: "0",
            review: "1 Sep",
          },
        ]}
        total={{
          name: "5 people",
          role: "3 roles",
          data: "All logged",
          platform: "2 can edit",
          two: "5 of 5",
          active: "3 today",
          sessions: "3 open",
          review: "Next 1 Dec",
        }}
      />
      <Panel tone="plain" className="mt-4">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div className="max-w-[760px]">
            <h2 className="text-ink text-[16px] leading-[19px] font-semibold">
              When someone leaves
            </h2>
            <PanelText className="mt-[6px]">
              Remove them here first. That ends their sessions and cancels any write access they
              hold. Then rotate the Google OAuth client secret the same day; Platform shows when
              each key last changed.
            </PanelText>
          </div>
          <button
            type="button"
            className="bg-red-pale text-red h-[39px] shrink-0 rounded-full px-[18px] text-[14px] font-semibold"
          >
            Remove a person
          </button>
        </div>
      </Panel>
    </AppShell>
  );
}

/* ---------- 76:2713 ---------- */
export const platform: DetailSpec = {
  shell: { ...full, active: "platform" },
  head: {
    title: "One developer token serves all 42 merchants.",
    lead: "The keys, Google reviews and defaults the whole platform depends on. If Google suspends the token, every merchant stops at once, so changes here need a second super admin.",
  },
  tiles: [
    {
      tone: "brand",
      label: "Developer token",
      value: "Standard",
      chip: "Good standing since 20 Aug",
    },
    { label: "Google sign-in screen", value: "Verified", chip: "No 100-user cap" },
    { label: "AI spend today", value: "$18.40", chip: "Limit $150 a day", chipTone: "grey" },
    { label: "Google API quota today", value: "61%", progress: 0.61 },
  ],
  why: {
    title: "Why this page matters",
    legend: "Biggest single risk",
    summary:
      "Every merchant's changes go through one developer token. If Google suspends it for a policy breach, ads stop changing everywhere at the same moment. That is why every change passes the policy checker and the limits first.",
  },
  record: {
    title: "Keys and when they rotate",
    action: "Open Secret Manager",
    rows: [
      {
        icon: "bars",
        iconTone: "brand",
        title: "Google OAuth client secret",
        meta: "Rotated 14 Mar · next by 14 Mar 2027, or the day someone with access leaves",
        action: "Rotate",
      },
      {
        icon: "plus",
        iconTone: "brand",
        title: "Anthropic API key, production",
        meta: "In Secret Manager · separate workspace from staging · limit $150 a day",
        action: "Rotate",
      },
      {
        icon: "line",
        iconTone: "brand",
        title: "Google Ads developer token",
        meta: "Never leaves the ads gateway · rotate only if exposed, and tell Google",
      },
    ],
  },
  next: {
    title: "Defaults for new merchants",
    action: "Version history",
    mock: {
      kicker: "Version 7, since 10 Sep 09:05",
      source: "Changed by Rhea Castillo, approved by Omar Haddad",
      headline: "Largest daily change is now 20%, down from 25%",
      body: "New merchants also start with approvals that expire after 7 days, and Full-auto off until the owner agrees to it in writing. Merchants can tighten any default. Old versions are kept, because every past change points to the version that allowed it.",
    },
    footnote: "Defaults never override Google's own rules or a merchant's stricter limits.",
  },
  extra: (
    <Panel title="Early access: Full-auto" action={{ label: "Rollout rules" }} tone="plain">
      <PanelText>
        6 of 42 merchants are on Full-auto. Each needed 30 days on Ask first and working tracking.
        Turning one on needs a second super admin.
      </PanelText>
      <Rows className="mt-1">
        <ListRow
          title="Tran Auto Repair"
          meta="On since 2 Sep · 45 days on Ask first before that"
          right={<Toggle on label="Tran Auto Repair" />}
        />
        <ListRow
          title="Alpha Plumbing"
          meta="Asked to join today · 37 days on Ask first · tracking working"
          right={<Toggle on={false} label="Alpha Plumbing" />}
        />
        <ListRow
          title="Beacon Roofing"
          meta="Not eligible yet · first campaign still being built"
          chip="Not yet"
        />
      </Rows>
    </Panel>
  ),
  notice: {
    tone: "panel",
    tag: "Emergency",
    tagTone: "red",
    title: "Pause automation for every merchant",
    body: "Stops every change PPCWay makes, everywhere, until you turn it back on. Ads keep running as they are. Use it if Google warns us about the developer token.",
    children: <ReasonInput placeholder="Say what happened" tone="line" />,
    primary: { label: "Pause everything" },
    primaryTone: "red",
    secondary: { label: "Cancel" },
  },
  list: {
    title: "Google reviews",
    rows: [
      {
        title: "Developer token",
        meta: "Standard access since 20 Aug",
        chip: "Active",
        chipTone: "pale",
        dot: true,
      },
      {
        title: "OAuth sign-in screen",
        meta: "Verified 2 Sep for the adwords scope",
        chip: "Verified",
        chipTone: "pale",
        dot: true,
      },
      {
        title: "Brand verification",
        meta: "Done 28 Aug, speeds up token reviews",
        chip: "Done",
        chipTone: "pale",
        dot: true,
      },
    ],
  },
};

/* ---------- 90:15498 ---------- */
export const rules: DetailSpec = {
  shell: { ...full, active: "platform" },
  head: {
    title: "The same rules for everyone, unless we tune them.",
    lead: "Every automatic change comes from these rules. Defaults live in versioned config; a merchant gets its own threshold only when its numbers are unusual, and every override has a reason.",
  },
  tiles: [
    { tone: "brand", label: "Rules live", value: "14", chip: "Config version 22" },
    { label: "Merchant overrides", value: "3", chip: "All with a reason" },
    { label: "Google's limits", value: "v31", chip: "Character limits, asset minimums" },
    { label: "Tested before release", value: "100%", progress: 1 },
  ],
  why: {
    title: "Blocking a search",
    legend: "Default",
    summary:
      "Block a search after 12 clicks with no calls, once it has cost at least the target cost per call. For quiet accounts the click count scales down, so they are not blocked into silence.",
  },
  record: {
    title: "Rules and their defaults",
    action: "Change history",
    rows: [
      {
        icon: "bars",
        iconTone: "brand",
        title: "Block a search",
        meta: "12 clicks, no calls, cost at least the target · 3 overrides",
        action: "Edit",
      },
      {
        icon: "plus",
        iconTone: "brand",
        title: "Add a search as a keyword",
        meta: "2 calls, cost within 1.2 times the target",
        action: "Edit",
      },
      {
        icon: "line",
        iconTone: "brand",
        title: "Spend spike",
        meta: "3 times the usual for that hour, and over $10",
      },
    ],
  },
  next: {
    title: "An override",
    action: "All 3",
    mock: {
      kicker: "Keyway Locksmiths",
      source: "Set by Rhea on 2 Sep, approved by Omar",
      headline: "Block a search after 20 clicks, not 12",
      body: "Locksmith searches are rare and expensive, so 12 clicks would block searches that go on to call. Reviewed again on 2 Dec.",
    },
    footnote: "A rule change ships only after the test suite passes against the new thresholds.",
  },
  notice: {
    tag: "Second super admin",
    title: "Raise the spike rule to 3.5 times?",
    body: "Omar proposed it: evening surges in heating searches trip the rule every night in October. Tests pass with 3.5.",
    primary: { label: "Approve" },
    secondary: { label: "Later" },
  },
  list: {
    title: "Config from outside",
    rows: [
      {
        title: "Google's limits · v31",
        meta: "Updated 2 Sep · video maximum now 15",
        chip: "Live",
        chipTone: "pale",
        dot: true,
      },
      {
        title: "Restricted categories · v9",
        meta: "Locksmith rule added 8 Sep",
        chip: "Live",
        chipTone: "pale",
        dot: true,
      },
    ],
  },
};

/* ---------- 82:4131 ---------- */
export const metrics: DetailSpec = {
  shell: { ...full, active: "metrics", period: "30 days" },
  head: {
    title: "Median setup is 14 minutes. The target is 15.",
    lead: "The measures PPCWay was built to move: time to a live campaign, campaigns live within a day, revenue, cancellations and how often merchants need a person.",
  },
  tiles: [
    {
      tone: "brand",
      label: "Signup to live campaign",
      value: "14 min",
      chip: "Median, time in PPCWay only",
    },
    { label: "Live within 24 hours", value: "86%", chip: "31 of 36 new merchants" },
    { label: "Monthly revenue", value: "$3,662", chip: "38 paying merchants" },
    { label: "Tickets per 100 accounts", value: "9.5", progress: 107 / 226 },
  ],
  why: {
    title: "Setup time, last 8 weeks",
    legend: "Target 15 minutes",
    summary:
      "Setup got faster once the site crawl ran while merchants answered the questions. That is 14 minutes in PPCWay. The 9 who had to add a card at Google waited a median 26 minutes more, outside our control.",
    bars: {
      height: 104,
      bars: [99, 85, 81, 72, 67, 67, 63, 63].map((h, i) => ({
        h: h / 99,
        tone: i === 7 ? "brand" : "soft",
      })),
      labels: ["Week of 20 July, 22 min", undefined, "This week, 14 min"],
    },
  },
  record: {
    title: "Where new merchants stall",
    action: "Full funnel",
    rows: [
      {
        icon: "bars",
        iconTone: "brand",
        title: "Adding a card at Google",
        meta: "5 of 36 waited more than a day",
        action: "View",
      },
      {
        icon: "plus",
        iconTone: "brand",
        title: "The call tracking check",
        meta: "3 needed the manual tag",
        action: "View",
      },
      {
        icon: "line",
        iconTone: "brand",
        title: "The business questions",
        meta: "1 left halfway and came back the next day",
      },
    ],
  },
  next: {
    title: "Results for merchants",
    action: "How we measure",
    mock: {
      kicker: "After 60 days",
      source: "The 19 merchants live for 60 days or more",
      headline: "Cost per result down 18% on their first month",
      body: "Each merchant is compared with their own first 30 days, not with an industry figure. Two got worse, both after cutting their budget below $400 a month.",
    },
    footnote: "Revenue comes from Stripe. Setup time comes from our own event log.",
  },
  notice: {
    tone: "brand",
    tag: "Plans",
    title: "3 upgrades and 2 cancellations this month",
    body: "Both cancellations said the budget was too small to see results. Below $300 to $500 a month there is not enough data to learn from, so a minimum at signup may help.",
    primary: { label: "Read the reasons" },
    secondary: { label: "Later" },
    className: "border-amber-line",
  },
  list: {
    title: "Plan mix",
    rows: [
      {
        title: "Growth · $99",
        meta: "20 merchants · $1,980 a month",
        chip: "53%",
        chipTone: "pale",
        dot: true,
      },
      {
        title: "Starter · $49",
        meta: "14 merchants · $686 a month",
        chip: "37%",
        chipTone: "pale",
        dot: true,
      },
      {
        title: "Agency · $249",
        meta: "4 agencies · $996 a month",
        chip: "10%",
        chipTone: "pale",
        dot: true,
      },
    ],
  },
};

/* ---------- 87:11170 ---------- */
export const aiQuality: DetailSpec = {
  shell: { ...full, active: "metrics" },
  head: {
    title: "The writer passed 96% of checks this week.",
    lead: "Everything the model writes goes through the same checker before anyone sees it. This is how often it passes, what the checker stops, and when we fall back to tested wording.",
  },
  tiles: [
    {
      tone: "brand",
      label: "Campaigns written",
      value: "41",
      chip: "Plus 1,204 log entries and emails",
    },
    { label: "Backup wording used", value: "2", chip: "1 timeout, 1 refusal", chipTone: "amber" },
    { label: "Keywords it invented", value: "0.4%", chip: "Dropped before anyone saw them" },
    { label: "AI spend today", value: "$18.40", progress: 28 / 226 },
  ],
  why: {
    title: "Lines passing first time",
    legend: "Last 14 days",
    summary:
      "Most rewrites are lines that run long. Unproven claims are rare now that the prompt names them. The one refusal came from a locksmith's page about lock picking.",
    bars: {
      height: 110,
      bars: [56, 70, 42, 84, 70, 98, 84, 56, 84, 98, 70, 84, 98, 84].map((h, i) => ({
        h: h / 98,
        tone: i === 13 ? "brand" : "soft",
      })),
      labels: ["28 Aug · 94%", undefined, "Today · 96%"],
    },
  },
  record: {
    title: "What the checker stopped",
    action: "All rules",
    rows: [
      {
        icon: "bars",
        iconTone: "brand",
        title: "Too long for Google",
        meta: "14 lines this week · rewritten with the limit stated",
        action: "View",
      },
      {
        icon: "plus",
        iconTone: "brand",
        title: "Claims that need proof",
        meta: "6 lines · 'best', 'cheapest', 'number one'",
        action: "View",
      },
      {
        icon: "line",
        iconTone: "brand",
        title: "Services not on the site",
        meta: "2 lines · 'free estimates' was nowhere on the page",
      },
    ],
  },
  next: {
    title: "Model and prompt in use",
    action: "Version history",
    mock: {
      kicker: "In production",
      source: "Claude Opus 5 · ad copy prompt version 14",
      headline: "Golden set: 212 of 214 passed on 3 Sep",
      body: "A model or prompt change ships only after it passes the golden set of 214 real campaigns. Every ad records the model and prompt version that wrote it.",
    },
    footnote:
      "Token use is capped per merchant per day, with an alert at 80% of the monthly budget.",
  },
  extra: (
    <Panel
      title="Trace any ad back to what wrote it"
      action={{ label: "Search runs" }}
      tone="plain"
    >
      <Rows className="mt-1">
        <ListRow
          title="'Emergency Plumber Mississauga' · Alpha Plumbing"
          meta="Claude Opus 5 · ad copy prompt v12 · 4 Aug 3:11 pm · passed first time"
          right={<span className="text-brand text-[14px] font-semibold">Open run</span>}
        />
        <ListRow
          title="'Price Agreed Before We Start' · Alpha Plumbing"
          meta="Claude Opus 5 · prompt v14 · 9 Sep · passed first time"
          right={<span className="text-brand text-[14px] font-semibold">Open run</span>}
        />
        <ListRow
          title="Token use today, Beacon Roofing"
          meta="41,000 of its 200,000 daily cap · alert at 80%"
          chip="21%"
          chipTone="pale"
        />
      </Rows>
    </Panel>
  ),
  notice: {
    tag: "Second super admin",
    title: "Ship ad copy prompt v15?",
    body: "Golden set: 213 of 214 passed, one more than v14. Headlines get shorter for trades. Omar has read the samples.",
    primary: { label: "Approve v15" },
    secondary: { label: "Later" },
  },
  list: {
    title: "Backups this week",
    rows: [
      {
        title: "Beacon Roofing",
        meta: "Writer timed out · fresh wording offered",
        chip: "Offered",
        chipTone: "pale",
        dot: true,
      },
      {
        title: "Keyway Locksmiths",
        meta: "Refused 'lock picking' text · logged",
        chip: "Logged",
        dot: true,
      },
    ],
  },
};

/* ---------- 82:3550 ---------- */
export function Runbook() {
  const play = (title: string, tone: "grey" | "red" | "amber", steps: [string, string][]) => (
    <Panel title={title} action={{ label: "Full playbook" }} tone="plain">
      <ol className="mt-1">
        {steps.map(([t, m], i) => (
          <Step key={t} n={i + 1} title={t} meta={m} tone={tone} />
        ))}
      </ol>
    </Panel>
  );
  return (
    <AppShell {...full} active="runbook">
      <PageHead
        title="When something breaks, start here."
        lead="Four failures can hurt every merchant at once. Each one has first steps, an owner and who to tell. We drill them every month; the last drill was 2 September."
      />
      <Tiles>
        <Tile tone="brand" label="Open incidents" value="0" chip="Last one closed today, 06:40" />
        <Tile label="On call now" value="Tom Adeyemi" chip="Until Friday, 9 am" chipTone="grey" />
        <Tile label="Last drill" value="2 Sep" chip="Token suspension, 41 min" chipTone="grey" />
        <Tile label="Pages this month" value="2" chip="Both closed" chipTone="pale" />
      </Tiles>
      <Columns
        aside={
          <>
            <Panel title="Who to call" tone="plain">
              <Rows className="mt-1">
                <ListRow
                  title="Tom Adeyemi"
                  meta="On call until Friday 9 am · pager"
                  chip="On call"
                  chipTone="pale"
                />
                <ListRow title="Rhea Castillo" meta="Super admin · can pause everything" />
                <ListRow title="Omar Haddad" meta="Super admin · second approver" />
                <ListRow
                  title="Google Ads API support"
                  meta="API Center, manager account owner only"
                />
              </Rows>
            </Panel>
            <Panel title="Recent incidents" action={{ label: "All" }} tone="plain">
              <Rows className="mt-1">
                <ListRow
                  title="Google outage, 19 calls failed"
                  meta="10 Sep 06:00 · all retried · closed by Tom"
                  chip="Closed"
                  chipTone="pale"
                />
                <ListRow
                  title="Northside Dental billing hold"
                  meta="3 Sep · one merchant, handled by support"
                  chip="Closed"
                  chipTone="pale"
                />
                <ListRow
                  title="Drill: token suspension"
                  meta="2 Sep · everyone paused and emailed in 41 min"
                  chip="Drill"
                />
              </Rows>
            </Panel>
          </>
        }
      >
        {play("Google Ads API outage", "grey", [
          [
            "Confirm it is Google",
            "Check Google's API status page and our Errors screen. Many merchants failing at once with TRANSIENT_ERROR means Google, not us.",
          ],
          [
            "Let the retries run",
            "Critical jobs retry with backoff and low-priority jobs wait. Do not restart workers; that loses their place.",
          ],
          [
            "Tell merchants only if it lasts",
            "After 2 hours, show a banner: ads keep running, reports may be late.",
          ],
          ["Close it with a note", "Link the spike on Errors and write down what happened."],
        ])}
        {play("Developer token warning or suspension", "red", [
          [
            "Pause automation for every merchant",
            "Platform, emergency pause. A second super admin confirms. Ads keep running as they are.",
          ],
          [
            "Read Google's notice with whoever owns policy",
            "Find the merchant or change behind it in the audit log and the change log.",
          ],
          [
            "Reply to Google from the API Center",
            "Only the manager account owner can. Keep it factual and say what we fixed.",
          ],
          [
            "Tell every merchant the same day",
            "In plain English: nothing is lost, changes are on hold, ads still run.",
          ],
        ])}
        {play("Many ads refused at once", "amber", [
          [
            "Stop new ads in that category",
            "Switch off writing for the category until the cause is clear.",
          ],
          [
            "Find the rule that let them through",
            "Compare the refused wording with the ad checker's test cases.",
          ],
          [
            "Fix it, test it, then rewrite",
            "Add each refused case to the checker's tests before resubmitting anything.",
          ],
          [
            "Tell the merchants affected",
            "One email each, saying what we changed and when their ads will return.",
          ],
        ])}
        {play("Personal data exposed", "red", [
          [
            "Contain it",
            "Revoke the affected keys and tokens in Platform, and pause automation if Google access is involved.",
          ],
          [
            "Work out whose data",
            "Use the audit log to list the merchants and the records involved.",
          ],
          [
            "Tell the regulator and the merchants",
            "Where there is a real risk of significant harm, report to the Privacy Commissioner and email each merchant affected.",
          ],
          [
            "Keep the record",
            "Every breach is logged and kept for 24 months, whether or not it was reported.",
          ],
        ])}
      </Columns>
    </AppShell>
  );
}

export function AdminSpec({ spec }: { spec: DetailSpec }) {
  return <DetailPage spec={spec} />;
}
