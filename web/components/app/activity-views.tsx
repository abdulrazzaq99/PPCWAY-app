import { Button } from "@/components/ui/button";
import { AppShell, type Workspace } from "./shell";
import {
  ActivityRow,
  Columns,
  ListRow,
  PageHead,
  Panel,
  PanelText,
  Rows,
  Tile,
  Tiles,
} from "./blocks";
import { DetailPage, type DetailSpec } from "./detail-page";
import type { ActivityView } from "./view-names";

/*
  The Activity page, from the "V2 Dashboard · Desktop 1440" frames in the Activity
  section: the feed, one change opened, and the alerts (a refused change, a change
  made outside PPCWay, a refused headline, a spend spike, calls down, weak
  headlines, the alert list, the Monday emails), plus two for Summit Heating.
*/

const alpha: Workspace = { name: "Alpha Plumbing", meta: "Mississauga, Ontario" };
const summit: Workspace = { name: "Summit Heating & Cooling", meta: "Brampton, Ontario" };

export function ActivityView({ view }: { view: ActivityView }) {
  switch (view) {
    case "change":
      return <DetailPage spec={change} />;
    case "refused":
      return <DetailPage spec={refused} />;
    case "outside-change":
      return <DetailPage spec={outsideChange} />;
    case "headline-refused":
      return <DetailPage spec={headlineRefused} />;
    case "spike":
      return <DetailPage spec={spike} />;
    case "calls-down":
      return <DetailPage spec={callsDown} />;
    case "weak-headlines":
      return <DetailPage spec={weakHeadlines} />;
    case "alerts":
      return <Alerts />;
    case "emails":
      return <Emails />;
    case "batch":
      return <DetailPage spec={batch} />;
    case "switch-bidding":
      return <DetailPage spec={switchBidding} />;
    default:
      return <Feed />;
  }
}

/* ---------- 17:1848 ---------- */
function Feed() {
  return (
    <AppShell active="activity" workspace={alpha}>
      <PageHead
        title="Everything PPCWay did, in plain words."
        lead="Every change is written down before it happens and can be undone. Undo puts the setting back, not the money already spent."
      />
      <Tiles>
        <Tile tone="brand" label="Changes applied" value="14" chip="All of them this month" />
        <Tile label="Waiting for you" value="2" chip="Both expire within a week" />
        <Tile label="Undone by you" value="1" chip="Put back within minutes" />
        <Tile label="Held by your limits" value="3" progress={42 / 226} />
      </Tiles>
      <Columns
        aside={
          <>
            <Panel title="Your limits">
              <PanelText className="text-[15px] leading-[18px]">
                We check every change against these before it happens. The most we will spend in a
                day is $48. The most we will pay for one call is $35. The biggest change we will
                make in a day is 20%.
              </PanelText>
              <a
                href="/settings"
                className="text-brand mt-3 inline-block text-[14px] leading-[17px] font-semibold"
              >
                Change limits
              </a>
            </Panel>
            <Panel title="Held by your limits">
              <Rows className="mt-1">
                <ListRow
                  title="Raise a bid by 30%"
                  meta="Your limit is 20% in a day"
                  chip="Held"
                  dot
                />
                <ListRow
                  title="Pause 8 keywords at once"
                  meta="Your limit is 5 at a time"
                  chip="Held"
                  dot
                />
              </Rows>
            </Panel>
          </>
        }
      >
        <Panel title="Everything, newest first" action={{ label: "Filter" }}>
          <Rows>
            <ActivityRow
              icon="bars"
              iconTone="amber"
              title="Paused 3 search terms that spent $38 without a single call."
              meta="Applied Tuesday, saved about $38 a month"
              action="Undo"
            />
            <ActivityRow
              icon="plus"
              iconTone="brand"
              title={<>Added &ldquo;emergency plumber near me&rdquo; as a keyword.</>}
              meta="Applied Monday, after it brought 4 calls"
              action="Undo"
            />
            <ActivityRow
              icon="line"
              iconTone="grey"
              title="Kept your daily budget at $40."
              meta="Checked Sunday: a little ahead of pace, so we watched another day"
            />
            <ActivityRow
              icon="line"
              iconTone="grey"
              title="Held back: we wanted to raise a bid by 30%."
              meta="Held by your limits at 6:00 am, your limit is 20% a day"
            />
            <ActivityRow
              icon="bar"
              iconTone="amber"
              title="Proposed lowering the daily budget from $40 to $32."
              meta="Waiting for you, expires in 5 days"
              metaTone="amber"
              action="Review"
              actionTone="amber"
              href="/approvals"
            />
            <ActivityRow
              icon="none"
              iconTone="grey"
              title="You undid pausing the ad that mentions weekend rates."
              meta="Undone by you on Sunday, the ad is running again"
            />
          </Rows>
        </Panel>
      </Columns>
    </AppShell>
  );
}

/* ---------- 66:439 ---------- */
const change: DetailSpec = {
  shell: { active: "activity", workspace: alpha },
  head: {
    title: "We lowered your top bid on Drains and blocked toilets.",
    lead: "Applied on 8 September at 6:12 am, after you approved it. Here is exactly what changed, why, and what undoing it would and would not do.",
  },
  tiles: [
    {
      tone: "brand",
      label: "Now, most for one click",
      value: "$11.50",
      chip: "Down $2.50, or 18%",
    },
    { label: "Before", value: "$14.00", chip: "Set on 4 August at launch" },
    { label: "Calls since", value: "2", chip: "In 2 days" },
    { label: "Cost per call since", value: "$23.00", progress: 84 / 226 },
  ],
  why: {
    title: "Why we did it",
    legend: "Rule 4.2, version 3",
    summary:
      "Drains and blocked toilets spent $114 over 14 days for 3 calls, which is $38 a call against $21 for the rest of your account. Lowering the top bid by 18% stays inside your limits and usually cuts the dearest clicks first.",
  },
  record: {
    title: "The record",
    action: "Download",
    rows: [
      {
        icon: "bars",
        iconTone: "brand",
        title: "Proposed by the daily bid check",
        meta: "7 Sep, 6:00 am · based on the 14 days to 7 Sep",
        action: "Details",
      },
      {
        icon: "plus",
        iconTone: "brand",
        title: "Approved by Dana Whitfield",
        meta: "7 Sep, 7:41 pm · from the Approvals page",
        action: "Details",
      },
      {
        icon: "line",
        iconTone: "brand",
        title: "Checked against your limits, version 4",
        meta: "7 Sep, 7:41 pm · $48 a day, $14 a click, 20% a day · passed",
      },
      {
        icon: "line",
        iconTone: "brand",
        title: "Applied in Google Ads",
        meta: "8 Sep, 6:12 am · Google confirmed the change",
      },
    ],
  },
  next: {
    title: "What undo will and will not do",
    action: "Read more",
    mock: {
      kicker: "Undo sets it back to",
      source: "$14.00 most for one click, on Drains and blocked toilets only",
      headline: "It will not give back the $46 already spent",
      body: "Undo restores the setting, not the results. Google also restarts its learning for this ad group, so expect a few uneven days afterwards. The undo is recorded as its own change, right next to this one.",
    },
    footnote: "Every change is kept for 7 years, including undos.",
  },
  notice: {
    tone: "brand",
    tag: "Reversible",
    title: "Undo this change",
    body: "Your top bid on Drains and blocked toilets goes back to $14.00. Nothing else in your account changes.",
    primary: { label: "Undo change" },
    secondary: { label: "Keep it" },
  },
  list: {
    title: "Your limits at the time",
    rows: [
      {
        title: "$14 most for one click",
        meta: "This change stayed under it",
        chip: "Inside",
        chipTone: "pale",
        dot: true,
      },
      {
        title: "20% largest change in a day",
        meta: "This one was 18%",
        chip: "Inside",
        chipTone: "pale",
        dot: true,
      },
    ],
  },
};

/* ---------- 87:4643 ---------- */
const refused: DetailSpec = {
  shell: { active: "activity", workspace: alpha },
  head: {
    title: "Google refused one of our changes, so nothing changed.",
    lead: "At 6:02 am we tried to lower the bid on 'water heater repair'. Google said the keyword no longer exists: it was removed in Google Ads yesterday. Your account is exactly as it was.",
  },
  tiles: [
    { tone: "brand", label: "What we tried", value: "Lower a bid", chip: "water heater repair" },
    {
      label: "Google said",
      value: "Not found",
      valueTone: "red",
      chip: "Removed in Google Ads on 9 Sep",
      chipTone: "red",
    },
    { label: "What changed", value: "Nothing", chip: "No money spent on this", chipTone: "grey" },
    { label: "We will retry", value: "No", chip: "Only temporary errors retry", chipTone: "grey" },
  ],
  why: {
    title: "Why it failed",
    legend: "Google's code: RESOURCE_NOT_FOUND",
    summary:
      "The keyword was removed directly in Google Ads on 9 September, outside PPCWay. Our copy still had it, so the change had nothing to act on. We have updated our copy.",
  },
  record: {
    title: "The record",
    action: "Download",
    rows: [
      {
        icon: "bars",
        iconTone: "brand",
        title: "Proposed by the daily bid check",
        meta: "10 Sep, 6:00 am · based on the 14 days to 9 Sep",
        action: "Details",
      },
      {
        icon: "plus",
        iconTone: "brand",
        title: "Checked against your limits, version 4",
        meta: "10 Sep, 6:00 am · passed",
        action: "Details",
      },
      {
        icon: "line",
        iconTone: "brand",
        title: "Sent to Google, refused",
        meta: "10 Sep, 6:02 am · the keyword no longer exists",
      },
      {
        icon: "line",
        iconTone: "brand",
        title: "Our copy updated",
        meta: "10 Sep, 6:03 am · keyword marked as removed",
      },
    ],
  },
  next: {
    title: "What happens now",
    action: "Keywords",
    mock: {
      kicker: "Nothing to undo",
      source: "Your account is exactly as it was before",
      headline: "We will not try this change again",
      body: "Changes Google refuses for a reason like this are not retried. If you want the keyword back, add it again from Keywords and it goes through the usual checks.",
    },
    footnote: "Every attempt is kept for 7 years, including the ones Google refused.",
  },
  notice: {
    tone: "brand",
    tag: "Nothing to do",
    title: "No action needed",
    body: "We only tell you because it is your account. If someone on your team removed the keyword on purpose, all is well.",
    primary: { label: "See the keyword" },
    secondary: { label: "OK" },
  },
  list: {
    title: "Where it came from",
    rows: [
      {
        title: "Removed in Google Ads",
        meta: "9 Sep, 4:31 pm · by Marcus Reyes",
        chip: "Outside",
        chipTone: "amber",
        dot: true,
      },
      {
        title: "Found by our daily check",
        meta: "10 Sep, 6:00 am",
        chip: "Synced",
        chipTone: "pale",
        dot: true,
      },
    ],
  },
};

/* ---------- 87:4821 ---------- */
const outsideChange: DetailSpec = {
  shell: { active: "activity", workspace: alpha },
  head: {
    title: "Someone changed your budget directly in Google Ads.",
    lead: "Marcus raised Plumbing repairs from $28 to $35 a day at 4:18 pm yesterday, in Google Ads itself. We have not undone it. PPCWay now works from the new number.",
  },
  tiles: [
    { tone: "brand", label: "Now", value: "$35 a day", chip: "Set in Google Ads" },
    { label: "Before", value: "$28 a day", chip: "Set by PPCWay on 4 Aug", chipTone: "grey" },
    {
      label: "Changed by",
      value: "Marcus Reyes",
      chip: "office@alphaplumbing.ca",
      chipTone: "grey",
    },
    { label: "Your limit, both campaigns", value: "$47 of $48", progress: 221 / 226 },
  ],
  why: {
    title: "What we did about it",
    legend: "From Google's change history",
    summary:
      "We updated our copy and kept your change. If a change made outside PPCWay went past one of your limits, we would ask you before doing anything. This one stays inside them.",
  },
  record: {
    title: "The record",
    action: "Download",
    rows: [
      {
        icon: "bars",
        iconTone: "brand",
        title: "Changed in Google Ads by Marcus Reyes",
        meta: "9 Sep, 4:18 pm · found by our check at 6:00 am",
        action: "Details",
      },
      {
        icon: "plus",
        iconTone: "brand",
        title: "Compared with your limits",
        meta: "$47 of $48 a day across both campaigns · inside",
        action: "Details",
      },
      {
        icon: "line",
        iconTone: "brand",
        title: "Our copy updated",
        meta: "10 Sep, 6:01 am · nothing sent to Google",
      },
    ],
  },
  next: {
    title: "Want PPCWay to leave this alone?",
    action: "Manual only",
    mock: {
      kicker: "Manual only",
      source: "For budgets, campaigns or keywords you manage yourself",
      headline: "Pin this budget so we never touch it",
      body: "Pinned settings are skipped by every automatic check and never proposed for change. You can unpin them any time from the campaign's settings.",
    },
    footnote:
      "Our limits apply to PPCWay's changes only. Changes you make yourself are never blocked.",
  },
  notice: {
    tone: "brand",
    tag: "Your choice",
    title: "Keep $35 a day?",
    body: "Keeping it is the default. Put it back and we set $28 again, which shows in Activity with an undo.",
    primary: { label: "Keep $35" },
    secondary: { label: "Put back $28" },
  },
  list: {
    title: "Your limits",
    rows: [
      {
        title: "$48 a day at most",
        meta: "Both campaigns now $47",
        chip: "Inside",
        chipTone: "pale",
        dot: true,
      },
      {
        title: "Changes made by you",
        meta: "Never blocked by our limits",
        chip: "Yours",
        dot: true,
      },
    ],
  },
};

/* ---------- 87:4997 ---------- */
const headlineRefused: DetailSpec = {
  shell: { active: "activity", workspace: alpha },
  head: {
    title: "Google turned down one of your headlines. Pick a fix.",
    lead: "Google refused 'The Best Drain Service in Town' because it cannot check that you are the best. Your other headlines are still showing, so the ad keeps running.",
  },
  tiles: [
    { tone: "brand", label: "Refused", value: "1 headline", chip: "Drains and blocked toilets" },
    {
      label: "Google's reason",
      value: "No proof",
      valueTone: "red",
      chip: "Claims like 'best' need proof",
      chipTone: "red",
    },
    { label: "Ad still running", value: "Yes", chip: "11 other headlines", chipTone: "pale" },
    { label: "Found at", value: "7:40 am", chip: "We check twice a day", chipTone: "grey" },
  ],
  why: {
    title: "What Google said",
    legend: "Policy: unproven claims",
    summary:
      "Words like 'best' or 'number one' need proof from someone else that Google can see on your site. You do not have that yet, so this line has to change.",
  },
  record: {
    title: "Pick a replacement",
    action: "Write your own",
    rows: [
      {
        icon: "bars",
        iconTone: "brand",
        title: "Same-Day Drain Service",
        meta: "22 of 30 characters · matches your services page",
        action: "Use this",
      },
      {
        icon: "plus",
        iconTone: "brand",
        title: "Drain Cleaning You Can Trust",
        meta: "28 of 30 characters · no claim to prove",
        action: "Use this",
      },
      {
        icon: "line",
        iconTone: "brand",
        title: "Rated 4.8 by 212 Customers",
        meta: "26 of 30 · only if the rating is on your site",
      },
    ],
  },
  next: {
    title: "Why we ask first",
    action: "Autonomy",
    mock: {
      kicker: "Your setting: Ask first",
      source: "On Full-auto we would swap in our pick straight away",
      headline: "Each fix goes back to Google for review",
      body: "Google usually reviews a changed headline within a day. Until then the other 11 keep your ad running, so nothing stops while you decide.",
    },
    footnote:
      "Refused lines are kept in your history so the same wording is never suggested again.",
  },
  notice: {
    tone: "brand",
    tag: "Needs your OK",
    title: "Use 'Same-Day Drain Service'?",
    body: "Our pick: plain, true, and it matches your services page. Google checks it again, usually within a day.",
    primary: { label: "Use this one" },
    secondary: { label: "Remove the line" },
  },
  list: {
    title: "Other headlines",
    rows: [
      {
        title: "Blocked Drain? Same-Day Fix",
        meta: "Approved by Google",
        chip: "Showing",
        chipTone: "pale",
        dot: true,
      },
      {
        title: "Licensed Plumbers, 24 Hours",
        meta: "Approved by Google",
        chip: "Showing",
        chipTone: "pale",
        dot: true,
      },
    ],
  },
};

/* ---------- 87:5175 ---------- */
const spike: DetailSpec = {
  shell: { active: "activity", workspace: alpha },
  head: {
    title: "Spend jumped at 11 am: $19 in one hour.",
    lead: "That is 3.2 times what Plumbing repairs usually spends at that hour. On Ask first we do not act alone, so here is what we found and what we suggest.",
  },
  tiles: [
    { tone: "brand", label: "Spent 11 am to noon", value: "$19.20", chip: "Usually about $6" },
    { label: "Calls in that hour", value: "0", chip: "Usually 0 or 1", chipTone: "grey" },
    { label: "Spent today", value: "$31", chip: "Of $40, gone by about 3 pm", chipTone: "amber" },
    { label: "Your daily limit", value: "$48", progress: 147 / 226 },
  ],
  why: {
    title: "Spend by hour today",
    legend: "Spike rule: 3 times usual",
    summary:
      "Most of it came from one search, 'plumbing supplies near me'. It matches your 'plumber near me' keyword, but these people are shopping for parts.",
    bars: {
      height: 100,
      bars: [10, 15, 25, 30, 35, 30, 95, 20].map((h, i) => ({
        h: h / 95,
        tone: i === 6 ? ("brand" as const) : ("soft" as const),
      })),
      labels: ["5 am", undefined, "Now, noon"],
    },
  },
  record: {
    title: "What we suggest",
    action: "See the searches",
    rows: [
      {
        icon: "bars",
        iconTone: "brand",
        title: "Block 'plumbing supplies near me'",
        meta: "$14 of it this hour, no calls",
        action: "Approve",
      },
      {
        icon: "plus",
        iconTone: "brand",
        title: "Keep today's budget at $40",
        meta: "Raising it would buy more of the same",
        action: "OK",
      },
      {
        icon: "line",
        iconTone: "brand",
        title: "Check again at 3 pm",
        meta: "We look for spikes four times a day",
      },
    ],
  },
  next: {
    title: "Why we did not act",
    action: "Autonomy",
    mock: {
      kicker: "Your setting: Ask first",
      source: "On Full-auto this would already be handled",
      headline: "Full-auto would have capped today at your limit",
      body: "Blocking a search and capping spend are both allowed on Full-auto. On Ask first, a spike like this waits for you, and we email you straight away.",
    },
    footnote:
      "A spike is 3 times the usual spend for that hour, compared with the same hour over the last 28 days.",
  },
  notice: {
    tone: "brand",
    tag: "Needs your OK",
    title: "Block 'plumbing supplies near me'?",
    body: "People shopping for parts, not plumbers. It costs about $2 a click and has never brought a call.",
    primary: { label: "Block it" },
    secondary: { label: "Not now" },
  },
  list: {
    title: "Your limits",
    rows: [
      {
        title: "$48 a day at most",
        meta: "$31 so far today",
        chip: "Inside",
        chipTone: "pale",
        dot: true,
      },
      { title: "Spike checks", meta: "Four times a day", chip: "On", dot: true },
    ],
  },
};

/* ---------- 89:12926 ---------- */
const callsDown: DetailSpec = {
  shell: { active: "activity", workspace: alpha },
  head: {
    title: "Calls are down 40% this week, and tracking is fine.",
    lead: "We checked the usual suspects first. Tracking counts calls, your ads are approved and the budget is not the limit. A new competitor is outbidding you on one of your best searches.",
  },
  tiles: [
    {
      label: "Calls this week",
      value: "6",
      valueTone: "red",
      chip: "Usually 10 by Thursday",
      chipTone: "red",
    },
    { label: "Shown for 'near me'", value: "44%", chip: "Was 71% last week", chipTone: "amber" },
    { label: "Tracking", value: "Working", chip: "Test call counted 9:10 am", chipTone: "pale" },
    { label: "Your top bid cap, $14", value: "$11", progress: 179 / 226 },
  ],
  why: {
    title: "Calls each day, last 14 days",
    legend: "Drop since Monday",
    summary:
      "Calls fell from Monday, when a new plumbing company started bidding on 'emergency plumber near me'. Your ad now shows for fewer than half of those searches.",
    bars: {
      height: 95,
      bars: [60, 60, 30, 90, 60, 60, 60, 30, 60, 30, 30, 30, 6, 30].map((h, i) => ({
        h: h / 90,
        tone: i >= 10 ? ("brand" as const) : ("soft" as const),
      })),
      labels: ["28 Aug", undefined, "Today"],
    },
  },
  record: {
    title: "What we checked",
    action: "Details",
    rows: [
      {
        icon: "bars",
        iconTone: "brand",
        title: "Tracking: a test call counted at 9:10 am",
        meta: "So calls are really down, not uncounted",
        action: "Details",
      },
      {
        icon: "plus",
        iconTone: "brand",
        title: "Ads and budget: all approved, budget not limiting",
        meta: "Nothing on our side stopped your ads",
        action: "Details",
      },
      {
        icon: "line",
        iconTone: "brand",
        title: "Found it: 'near me' searches, shown 44% instead of 71%",
        meta: "Since Monday · a new advertiser is bidding higher",
      },
    ],
  },
  next: {
    title: "What we suggest",
    action: "Your limits",
    mock: {
      kicker: "Inside your limits",
      source: "Near me ad group · top bid $11 today",
      headline: "Raise the Near me top bid from $11 to $13",
      body: "That is under your $14 cap and inside the 20% a day limit. We expect you back to about two thirds of those searches. If calls do not recover in a week, we will tell you and suggest stopping.",
    },
    footnote: "We never raise your cap or your daily budget without asking.",
  },
  notice: {
    tone: "brand",
    tag: "Needs your OK",
    title: "Raise the Near me bid to $13?",
    body: "It brings about a quarter of your calls. Everything else is working normally.",
    primary: { label: "Approve" },
    secondary: { label: "Wait a week" },
  },
  list: {
    title: "Your limits",
    rows: [
      {
        title: "$14 top bid cap",
        meta: "$13 stays inside it",
        chip: "Inside",
        chipTone: "pale",
        dot: true,
      },
      {
        title: "$48 a day at most",
        meta: "No budget change needed",
        chip: "Inside",
        chipTone: "pale",
        dot: true,
      },
    ],
  },
};

/* ---------- 89:13357 ---------- */
const weakHeadlines: DetailSpec = {
  shell: { active: "activity", workspace: alpha },
  head: {
    title: "Two headlines are rarely shown. Here are replacements.",
    lead: "Google rates 'Upfront Prices, No Call-out Fee' and 'Family Owned in Mississauga' as low after more than 5,000 views each. We wrote replacements from your site; they wait for your OK.",
  },
  tiles: [
    {
      tone: "brand",
      label: "Weak headlines",
      value: "2",
      chip: "In the Burst pipes ad",
      chipTone: "amber",
    },
    { label: "Views each", value: "5,000+", chip: "Enough to judge them", chipTone: "grey" },
    { label: "Headlines left", value: "10", chip: "More than Google's minimum", chipTone: "pale" },
    { label: "Ad strength after", value: "Excellent", progress: 1 },
  ],
  why: {
    title: "Why these two",
    legend: "Rule: low after 5,000 views",
    summary:
      "Google tries every headline, then shows the ones that get calls. These two have had a fair chance and are still rarely picked, so they are taking up space.",
  },
  record: {
    title: "Old and new",
    action: "Write your own",
    rows: [
      {
        icon: "bars",
        iconTone: "brand",
        title: "'Upfront Prices, No Call-out Fee' → 'Price Agreed Before We Start'",
        meta: "28 of 30 characters · from your pricing page",
        action: "Edit",
      },
      {
        icon: "plus",
        iconTone: "brand",
        title: "'Family Owned in Mississauga' → 'Local Plumbers Since 2009'",
        meta: "25 of 30 characters · from your about page",
        action: "Edit",
      },
      {
        icon: "line",
        iconTone: "brand",
        title: "Both checked against Google's rules",
        meta: "Passed: length, claims and trademarks",
      },
    ],
  },
  next: {
    title: "What happens next",
    action: "The Ads tab",
    mock: {
      kicker: "After you approve",
      source: "The old lines are paused, not deleted",
      headline: "Google reviews the new lines, usually within a day",
      body: "Your ad keeps running with its other 10 headlines while Google reviews. In two weeks we check whether the new lines are being picked.",
    },
    footnote: "The writer suggests; the rule decides which lines are weak.",
  },
  notice: {
    tone: "brand",
    tag: "Needs your OK",
    title: "Replace both headlines?",
    body: "You can approve one and keep the other, or write your own wording instead.",
    primary: { label: "Replace both" },
    secondary: { label: "Keep them" },
  },
  list: {
    title: "Headlines doing well",
    rows: [
      {
        title: "Emergency Plumber Mississauga",
        meta: "Shown most often",
        chip: "Best",
        chipTone: "pale",
        dot: true,
      },
      {
        title: "Licensed & Insured Since 2009",
        meta: "Shown often",
        chip: "Good",
        chipTone: "pale",
        dot: true,
      },
    ],
  },
};

/* ---------- 17:3118 ---------- */
function Alerts() {
  return (
    <AppShell active="activity" workspace={alpha}>
      <PageHead
        title="One thing needs you today."
        lead="We only interrupt you when money or your account is at stake. Everything else waits quietly in Activity."
      />
      <Tiles>
        <Tile tone="brand" label="Needs you now" value="1" chip="Your ads are stopped" />
        <Tile label="Sorted for you" value="1" chip="We rewrote the ad Google refused" />
        <Tile label="Good news" value="1" chip="A strong week so far" />
        <Tile label="Alerts this month" value="6" progress={70 / 226} />
      </Tiles>
      <Columns
        aside={
          <>
            <Panel title="How we tell you">
              <PanelText className="text-[15px] leading-[18px]">
                We email you straight away when money or your account is at risk. Everything else
                waits for the Monday summary, so your inbox stays quiet.
              </PanelText>
              <div className="mt-[18px] flex flex-wrap gap-[10px]">
                <Button variant="secondary" className="border-line">
                  Change this
                </Button>
                <Button variant="secondary" className="border-line">
                  Test an alert
                </Button>
              </div>
            </Panel>
            <Panel title="Who gets these">
              <Rows className="mt-1">
                <ListRow
                  title="dana@alphaplumbing.ca"
                  meta="Owner"
                  chip="Everything"
                  chipTone="pale"
                  dot
                />
                <ListRow
                  title="office@alphaplumbing.ca"
                  meta="Shared inbox"
                  chip="Urgent only"
                  dot
                />
              </Rows>
            </Panel>
          </>
        }
      >
        <Panel title="Needs your attention" action={{ label: "Mark all as read" }}>
          <Rows>
            <ActivityRow
              icon="bars"
              iconTone="red"
              title="Your card was declined by Google"
              meta="Your ads stopped at 6:12 this morning. Google needs a working card before they start again."
              action="Fix on Google"
              actionTone="red"
            />
            <ActivityRow
              icon="plus"
              iconTone="amber"
              title="An ad was turned down, and we fixed it"
              meta={
                <>
                  Google objected to &ldquo;best price guaranteed&rdquo;. You approved our rewrite
                  and the new ad is running.
                </>
              }
              action="See the change"
              actionTone="amber"
            />
            <ActivityRow
              icon="line"
              iconTone="brand"
              title="A strong week so far"
              meta="Fourteen calls by Thursday, one more than all of last week. Nothing needed from you."
            />
          </Rows>
        </Panel>
      </Columns>
    </AppShell>
  );
}

/* ---------- 87:8030 ---------- */
function Emails() {
  const rows = [
    [
      "Good week: 13 calls for $282",
      "31 Aug to 6 Sep · blocked 2 searches, raised one bid · opened Mon 8:14 am",
    ],
    ["11 calls for $276, steady", "24 to 30 Aug · one change waiting for you · opened Mon 9:02 am"],
    ["12 calls for $268", "17 to 23 Aug · learning finished on the 18th · opened Mon 7:55 am"],
    [
      "Week two: 10 calls, still learning",
      "10 to 16 Aug · numbers still settling · opened Tue 6:40 pm",
    ],
    ["You are live", "4 to 9 Aug · 3 calls in your first days · opened Mon 8:30 am"],
  ];
  return (
    <AppShell active="activity" workspace={alpha}>
      <PageHead
        title="Every Monday email, in one place."
        lead="The same short summary we send you, kept here so you can look back. A week with a problem says so, instead of showing numbers that mislead."
      />
      <Tiles>
        <Tile tone="brand" label="Emails so far" value="5" chip="Since your first week" />
        <Tile label="Best week" value="13 calls" chip="31 Aug to 6 Sep" />
        <Tile label="Opened" value="5 of 5" chip="By Dana" />
        <Tile label="Next one" value="Mon 14 Sep" chip="8 am, as usual" chipTone="grey" />
      </Tiles>
      <Columns
        aside={
          <>
            <Panel title="This week so far">
              <Rows className="mt-1">
                <ListRow title="Calls" meta="Monday to Thursday" chip="14" chipTone="pale" />
                <ListRow
                  title="Waiting for you"
                  meta="Goes in the email if still open"
                  chip="2"
                  chipTone="amber"
                />
              </Rows>
            </Panel>
            <Panel
              title="Who gets it"
              action={{ label: "Change", href: "/settings?view=notifications" }}
            >
              <PanelText>
                Dana and Marcus, every Monday at 8 am. Turn it off or add people in Notifications.
              </PanelText>
            </Panel>
          </>
        }
      >
        <Panel title="Past emails" action={{ label: "Download all" }}>
          <Rows className="mt-1">
            {rows.map(([t, m]) => (
              <ListRow
                key={t}
                title={t}
                meta={m}
                right={
                  <a href="/emails" className="text-brand text-[14px] leading-[17px] font-semibold">
                    Read
                  </a>
                }
              />
            ))}
          </Rows>
        </Panel>
      </Columns>
    </AppShell>
  );
}

/* ---------- 90:15752, Summit ---------- */
const batch: DetailSpec = {
  shell: { active: "activity", workspace: summit, initials: "RK" },
  head: {
    title: "63 of 65 keyword changes went through.",
    lead: "Google refused 2 because Raj had already removed those keywords in Google Ads. Everything else in the AC Install tidy-up is live, and one undo still puts all 63 back.",
  },
  tiles: [
    { tone: "brand", label: "Applied", value: "63", chip: "Confirmed by Google" },
    { label: "Refused by Google", value: "2", chip: "Already removed", chipTone: "red" },
    { label: "Undo", value: "One click", chip: "Puts all 63 back", chipTone: "grey" },
    { label: "Retried", value: "No", chip: "Nothing left to do", chipTone: "grey" },
  ],
  why: {
    title: "What happened",
    legend: "Batch sent 6:02 am",
    summary:
      "We send changes to Google in one batch and record each one. When a few fail, the rest still count, so we show you exactly which went through.",
  },
  record: {
    title: "The batch, by group",
    action: "Download",
    rows: [
      {
        icon: "bars",
        iconTone: "brand",
        title: "Paused 41 keywords with no clicks",
        meta: "41 of 41 applied",
        action: "Details",
      },
      {
        icon: "plus",
        iconTone: "brand",
        title: "Changed 12 broad keywords to phrase",
        meta: "12 of 12 applied",
        action: "Details",
      },
      {
        icon: "line",
        iconTone: "brand",
        title: "Kept 7 shared keywords in one campaign",
        meta: "5 applied · 2 refused: removed in Google Ads on 8 Sep",
      },
      {
        icon: "line",
        iconTone: "brand",
        title: "Added 5 searches that brought calls",
        meta: "5 of 5 applied",
      },
    ],
  },
  next: {
    title: "The two that failed",
    action: "See them",
    mock: {
      kicker: "Refused by Google",
      source: "'hvac brampton' and 'hvac repair brampton', in AC Install",
      headline: "They were already gone, so there was nothing to change",
      body: "Raj removed them in Google Ads on 8 September. We have updated our copy. The goal, keeping them in one campaign only, is met anyway.",
    },
    footnote:
      "Every operation in a batch is logged on its own, so a partial result is never a mystery.",
  },
  notice: {
    tone: "brand",
    tag: "Nothing to do",
    title: "No action needed",
    body: "We tell you because it is your account. Your keywords are now where the tidy-up meant them to be.",
    primary: { label: "See AC Install" },
    secondary: { label: "OK" },
  },
  list: {
    title: "Batch",
    rows: [
      { title: "65 changes sent", meta: "6:02 am, one request", chip: "Sent", dot: true },
      { title: "63 confirmed", meta: "6:02 am", chip: "Applied", chipTone: "pale", dot: true },
    ],
  },
};

/* ---------- 88:12203, Summit ---------- */
const switchBidding: DetailSpec = {
  shell: { active: "activity", workspace: summit, initials: "RK", badges: { approvals: 3 } },
  head: {
    title: "Switch Furnace Repair to a target cost per call?",
    lead: "Northline Media set every bid by hand. With 38 calls a month, Google now has enough to bid for you, aiming at the $29 a call you already get.",
  },
  tiles: [
    { tone: "brand", label: "Calls, last 30 days", value: "38", chip: "A target needs 30" },
    {
      label: "Your cost per call",
      value: "$29.47",
      chip: "The target starts here",
      chipTone: "grey",
    },
    {
      label: "Learning period",
      value: "14 days",
      chip: "Numbers swing meanwhile",
      chipTone: "amber",
    },
    { label: "Your limit, $35 a call", value: "84%", progress: 0.84 },
  ],
  why: {
    title: "Cost per call, last 12 weeks",
    legend: "Bids set by hand",
    summary:
      "Hand-set bids kept cost per call between $26 and $34. A target lets Google raise bids on searches likely to call, and drop them on the rest, auction by auction.",
    bars: {
      height: 100,
      bars: [77, 56, 98, 63, 49, 70, 91, 42, 63, 77, 56, 63].map((h) => ({ h: h / 98 })),
      labels: ["Mid June", undefined, "Last week, $29"],
    },
  },
  record: {
    title: "What changes",
    action: "Bidding report",
    rows: [
      {
        icon: "bars",
        iconTone: "brand",
        title: "Bidding: set by hand → target cost per call $29",
        meta: "Starts at your own average from the last 30 days",
        action: "Details",
      },
      {
        icon: "plus",
        iconTone: "brand",
        title: "Top bid cap stays at $14",
        meta: "No single click can cost more than today",
        action: "Details",
      },
      {
        icon: "line",
        iconTone: "brand",
        title: "Other bid changes wait 14 days",
        meta: "So we do not fight Google while it learns",
      },
    ],
  },
  next: {
    title: "If it goes badly",
    action: "Your limits",
    mock: {
      kicker: "Checked daily from day 15",
      source: "Same rule as every campaign we manage",
      headline: "If cost per call runs over $36 for 14 days, we propose a lower target",
      body: "We lower the target by at most 15% at a time. Switching back to hand-set bids also restarts learning, so we only suggest it when the numbers are clear.",
    },
    footnote: "Your $35 a call limit applies the whole time.",
  },
  notice: {
    tone: "brand",
    tag: "Needs your OK",
    title: "Approve the switch for 18 September?",
    body: "It is planned for week 3, after the quick wins settle. Approve now and we apply it on the 18th.",
    primary: { label: "Approve for 18 Sep" },
    secondary: { label: "Not yet" },
  },
  list: {
    title: "Why not straight away",
    rows: [
      {
        title: "Quick wins first",
        meta: "They change what the bids see",
        chip: "Week 1",
        chipTone: "pale",
        dot: true,
      },
      { title: "One learning reset", meta: "Not two", chip: "Week 3", dot: true },
    ],
  },
};
