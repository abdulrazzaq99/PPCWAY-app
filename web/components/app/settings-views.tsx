import { Button } from "@/components/ui/button";
import { AppShell, type Workspace } from "./shell";
import {
  ActionPanel,
  ActivityRow,
  Choice,
  Columns,
  Footnote,
  LinkRow,
  ListRow,
  NoticeCard,
  PageHead,
  Panel,
  PanelText,
  Rows,
  Step,
  Tile,
  Tiles,
  Toggle,
  ToggleRow,
  ValueRow,
} from "./blocks";
import { DetailPage, type DetailSpec } from "./detail-page";
import type { SettingsView } from "./view-names";

/*
  Settings, from the "V2 Dashboard · Desktop 1440" frames in the Settings section:
  autonomy and limits (three states), full-auto consent, plan and invoices (three
  states), team, cancel, delete, business facts, notifications, two-step sign-in,
  switching plan, a failed payment, the Google connection, what counts as a
  result, data handling, your data, and add-ons.
*/

const alpha: Workspace = { name: "Alpha Plumbing", meta: "Mississauga, Ontario" };

export function SettingsPage({ view }: { view: SettingsView }) {
  switch (view) {
    case "autonomy-early":
      return <Autonomy early />;
    case "full-auto":
      return <DetailPage spec={fullAuto} />;
    case "plan":
      return <Plan />;
    case "plan-owner-only":
      return <Plan ownerOnly />;
    case "team":
      return <DetailPage spec={team} />;
    case "cancel":
      return <DetailPage spec={cancel} />;
    case "delete":
      return <DetailPage spec={deleteAccount} />;
    case "business":
      return <DetailPage spec={business} />;
    case "notifications":
      return <Notifications />;
    case "two-step":
      return <TwoStep />;
    case "switch-plan":
      return <SwitchPlan />;
    case "payment-failed":
      return <PaymentFailed />;
    case "google":
      return <GoogleConnection />;
    case "results":
      return <Results />;
    case "data":
      return <DataHandling />;
    case "owner-only":
      return <Autonomy ownerOnly />;
    case "your-data":
      return <YourData />;
    case "add-ons":
      return <AddOns />;
    default:
      return <Autonomy />;
  }
}

/* ---------- 17:2639, 90:14738, 87:7815 ---------- */
function Autonomy({ early, ownerOnly }: { early?: boolean; ownerOnly?: boolean }) {
  const lead = ownerOnly
    ? "You can see every setting and approve day-to-day changes. Autonomy, limits and billing belong to the owner, so ask Dana if something should change."
    : early
      ? "Every automatic change is checked against these before it happens. Full-auto is in early access: we switch it on account by account while we watch the results."
      : "Every automatic change is checked against these before it happens, and written down in Activity afterwards.";
  return (
    <AppShell active="settings" workspace={alpha} initials={ownerOnly ? "MR" : "DW"}>
      <PageHead
        title={
          ownerOnly
            ? "Only Dana can change how PPCWay works."
            : "You decide what PPCWay may change."
        }
        lead={lead}
      />
      <Tiles>
        <Tile
          tone="brand"
          label="Your setting"
          value="Ask me first"
          chip="Nothing changes without your OK"
        />
        <Tile label="Most we'll spend in a day" value="$48" chip="A hard stop, never crossed" />
        <Tile label="Most we'll pay for one call" value="$35" chip="We stop bidding above this" />
        <Tile label="Biggest change in a day" value="20%" progress={0.2} />
      </Tiles>
      <Columns
        aside={
          <>
            <Panel title="Growth, $99 a month">
              <PanelText className="text-[15px] leading-[18px]">
                Next bill 1 October. Google bills you for the ads separately, on your own card.
              </PanelText>
              <div className="mt-[18px] flex flex-wrap gap-[10px]">
                <Button variant="secondary" className="border-line" disabled={ownerOnly}>
                  {ownerOnly ? "Owner only" : "Change plan"}
                </Button>
                <Button variant="secondary" className="border-line">
                  See invoices
                </Button>
              </div>
            </Panel>
            <Panel title="Who can see this account">
              <Rows className="mt-1">
                <ListRow
                  title="Dana Whitfield"
                  meta="dana@alphaplumbing.ca"
                  chip="Owner"
                  chipTone="pale"
                  dot
                />
                <ListRow
                  title="Marcus Reyes"
                  meta="office@alphaplumbing.ca"
                  chip="Can approve"
                  dot
                />
              </Rows>
            </Panel>
            {early ? (
              <Panel tone="amber" title="Full-auto is in early access">
                <PanelText>
                  We turn it on a few accounts at a time and check every change it makes. You would
                  still keep your limits, and you can switch back at any time.
                </PanelText>
                <Rows className="divide-amber-line mt-1">
                  <ListRow
                    title="37 days on Ask me first"
                    meta="Needs 30"
                    chip="Yes"
                    chipTone="pale"
                  />
                  <ListRow
                    title="Call tracking working"
                    meta="Last call counted 2 hours ago"
                    chip="Yes"
                    chipTone="pale"
                  />
                </Rows>
                <Button size="sm" className="mt-3 h-[42px]">
                  Ask to join
                </Button>
              </Panel>
            ) : null}
            {ownerOnly ? (
              <Panel title="Why can't I change this?">
                <PanelText>
                  Team members approve changes that come up each day. Owners set autonomy, limits,
                  billing and the Google connection, because those decide how much can be spent.
                </PanelText>
                <Button variant="secondary" size="sm" className="border-line mt-4 h-11">
                  Ask Dana
                </Button>
              </Panel>
            ) : null}
          </>
        }
      >
        <Panel
          title="How much can PPCWay do on its own?"
          action={ownerOnly ? { label: "Owner only", tone: "muted" } : { label: "Change limits" }}
        >
          <Rows>
            <ActivityRow
              icon="bars"
              iconTone="amber"
              title="Tell me, I'll decide"
              meta="We spot the problem and explain it. You make the change in Google Ads."
              action={ownerOnly ? "Owner only" : "Switch to this"}
              actionTone={ownerOnly ? "faint" : "brand"}
            />
            <ActivityRow
              selected
              title="Ask me first"
              meta="We propose the change with our reasons. Nothing happens until you approve it."
              action="In use"
            />
            <ActivityRow
              icon="line"
              iconTone="grey"
              muted
              title={early ? "Just get on with it · early access" : "Just get on with it"}
              meta={
                early
                  ? "Opens after 30 days on Ask me first with working call tracking. You have both."
                  : "We make changes inside your limits without asking, and tell you afterwards."
              }
            />
          </Rows>
        </Panel>
        <Panel title="What Ask-first can propose" tone="plain">
          <Rows className="mt-1">
            <ListRow
              title="Block searches that never bring calls"
              meta="After $30 spent with no call"
              chip="Asks you"
            />
            <ListRow
              title="Add searches that bring calls as keywords"
              meta="After 2 calls from the same search"
              chip="Asks you"
            />
            <ListRow
              title="Raise or lower bids"
              meta="Inside $14 a click and 20% a day"
              chip="Asks you"
            />
            <ListRow
              title="Move budget between your campaigns"
              meta="Never above $48 a day in total"
              chip="Asks you"
            />
            <ListRow
              title="Pause keywords that only cost money"
              meta="After 30 days with no calls"
              chip="Asks you"
            />
            <ListRow
              title="Rewrite an ad Google refused"
              meta="You see the new wording first"
              chip="Asks you"
            />
          </Rows>
        </Panel>
        <Panel title="More limits" tone="plain">
          <Rows className="mt-1">
            <ValueRow
              title="Lowest bid we will set"
              meta="So a keyword never drops out of sight completely"
              value="$1.00"
            />
            <ValueRow
              title="Biggest single change"
              meta="One change, on top of the 20% a day in total"
              value="10%"
            />
          </Rows>
        </Panel>
      </Columns>
    </AppShell>
  );
}

/* ---------- 67:1622 ---------- */
const fullAuto: DetailSpec = {
  shell: { active: "settings", workspace: alpha },
  head: {
    title: "Let PPCWay act without asking each time.",
    lead: "Full-auto means we make routine changes inside your limits and tell you afterwards. Read exactly what that covers before you switch it on.",
  },
  tiles: [
    {
      tone: "brand",
      label: "Changes you approved",
      value: "46",
      chip: "In 5 weeks on Approve-first",
    },
    { label: "Ones you turned down", value: "2", chip: "Both were bid raises" },
    { label: "Most for one click", value: "$14", chip: "Stays your limit" },
    { label: "Largest change in a day", value: "20%", progress: 0.2 },
  ],
  why: {
    title: "What you are agreeing to",
    legend: "Terms version 1.2",
    summary:
      "PPCWay may make the changes listed below without asking first, as long as each one stays inside your limits. We record every change before we make it, tell you in plain English afterwards, and you can undo any of them.",
  },
  record: {
    title: "What we will do on our own",
    action: "Change what is included",
    rows: [
      {
        icon: "bars",
        iconTone: "brand",
        title: "Block searches that never call",
        meta: "After at least $30 spent on a search with no calls",
        action: "Included",
      },
      {
        icon: "plus",
        iconTone: "brand",
        title: "Raise or lower bids inside your cap",
        meta: "Never above $14 a click, never more than 20% in a day",
        action: "Included",
      },
      {
        icon: "line",
        iconTone: "brand",
        title: "Pause keywords that only waste money",
        meta: "After 30 days of spend with no calls",
      },
    ],
  },
  next: {
    title: "What still always asks you first",
    action: "Why these",
    mock: {
      kicker: "Never automatic",
      source: "Budget increases · new campaign types · other companies' names",
      headline: "Anything that raises what you can spend",
      body: "Full-auto can move money around inside your limits. It can never raise the limits themselves. Those always come to Approvals, and wait for you.",
    },
    footnote:
      "Switch back to Approve-first at any time, and undo any single change from Activity. Both take effect straight away.",
  },
  notice: {
    tone: "brand",
    tag: "Your consent",
    title: "Switch on full-auto",
    body: "By switching this on you agree that PPCWay may make the changes above without asking first. We record your name, the time and these exact terms.",
    primary: { label: "I agree, switch on" },
    secondary: { label: "Not now" },
    className: "border-brand-bar",
  },
  list: {
    title: "Keep these manual",
    rows: [
      { title: "Water heaters ad group", meta: "Always ask me first", chip: "Pinned", dot: true },
      { title: "Daily budget", meta: "Never changes on its own", chip: "Locked", dot: true },
    ],
  },
};

/* ---------- 17:2816, 90:15930 ---------- */
function Plan({ ownerOnly }: { ownerOnly?: boolean }) {
  return (
    <AppShell active="settings" workspace={alpha} initials={ownerOnly ? "MR" : "DW"}>
      <PageHead
        title={
          ownerOnly ? "Only Dana can change the plan or the card." : "Your plan and your invoices."
        }
        lead={
          ownerOnly
            ? "You can see the plan and download invoices. Plans, cards and cancelling belong to the owner, because they decide what PPCWay costs."
            : "This is what PPCWay charges you. Google charges you separately for the ads themselves, on your own card."
        }
      />
      <Tiles>
        <Tile tone="brand" label="Your plan" value="Growth" chip="$99 a month, cancel any time" />
        <Tile label="Next bill" value="1 Oct" chip="On the Visa ending 4242" />
        <Tile label="Paid so far" value="$198" chip="Across two invoices" />
        <Tile label="Ad spend, last 30 days" value="$1,240" progress={140 / 226} />
      </Tiles>
      <Columns
        aside={
          <>
            <Panel title="Visa ending 4242">
              <PanelText className="text-[15px] leading-[18px]">
                This card pays for PPCWay only. It is never used for your ads, and we never see the
                full number.
              </PanelText>
              <div className="mt-[18px] flex flex-wrap gap-[10px]">
                <Button variant="secondary" className="border-line" disabled={ownerOnly}>
                  {ownerOnly ? "Owner only" : "Update card"}
                </Button>
                <Button variant="secondary" className="border-line">
                  Download all
                </Button>
              </div>
            </Panel>
            <Panel title="Recent invoices">
              <Rows className="mt-1">
                <ListRow
                  title="1 September 2026"
                  meta="Growth, paid on the Visa"
                  chip="$99.00"
                  dot
                />
                <ListRow title="1 August 2026" meta="Growth, paid on the Visa" chip="$99.00" dot />
              </Rows>
            </Panel>
            {ownerOnly ? (
              <Panel title="Need something changed?">
                <PanelText>
                  Ask Dana. Only owners change billing, invite people or connect Google Ads.
                </PanelText>
                <Button variant="secondary" size="sm" className="border-line mt-4 h-11">
                  Ask Dana
                </Button>
              </Panel>
            ) : null}
          </>
        }
      >
        <Panel title="Plans" action={{ label: "Compare plans" }}>
          <Rows>
            <ActivityRow
              icon="bars"
              iconTone="amber"
              title="Starter"
              meta="$49 a month, for up to $1,500 of ad spend"
              action={ownerOnly ? "Owner only" : "Switch to this"}
              actionTone={ownerOnly ? "faint" : "brand"}
            />
            <ActivityRow
              selected
              title="Growth"
              meta="$99 a month, for up to $5,000 of ad spend"
              action="In use"
            />
            <ActivityRow
              icon="line"
              iconTone="grey"
              title="Agency"
              meta="$249 a month, for up to ten businesses"
            />
          </Rows>
        </Panel>
      </Columns>
    </AppShell>
  );
}

/* ---------- 67:1115 ---------- */
const team: DetailSpec = {
  shell: { active: "settings", workspace: alpha },
  head: {
    title: "Who can see and change this account.",
    lead: "Owners change money and settings. Team members approve day to day changes but never budgets. Agency viewers can look and change nothing.",
  },
  tiles: [
    { tone: "brand", label: "People", value: "3", chip: "Of 5 on Growth" },
    { label: "Owners", value: "1", chip: "Only owners change billing" },
    { label: "Invites waiting", value: "1", chip: "Expires 14 Sep" },
    { label: "Two-step sign in", value: "1 of 2", progress: 0.5 },
  ],
  why: {
    title: "What each role can do",
    legend: "Compare roles",
    summary:
      "Owners approve anything and change budgets, limits, billing and people. Team members approve changes up to your limits. Agency viewers see results and activity, and cannot change a thing.",
  },
  record: {
    title: "Team",
    action: "Invite someone",
    rows: [
      {
        icon: "bars",
        iconTone: "brand",
        title: "Dana Whitfield · Owner",
        meta: "dana@alphaplumbing.ca · two-step on · this is you",
        action: "Manage",
      },
      {
        icon: "bar",
        iconTone: "amber",
        title: "Marcus Reyes · Team member",
        meta: "office@alphaplumbing.ca · two-step off · last seen today",
        metaTone: "amber",
        action: "Manage",
      },
      {
        icon: "line",
        iconTone: "brand",
        title: "Priya Shah · Agency viewer",
        meta: "priya@brightpath.ca · view only, through Brightpath Media",
      },
    ],
  },
  next: {
    title: "Invite someone",
    action: "Cancel",
    mock: {
      kicker: "New invite",
      source: "jess@alphaplumbing.ca",
      headline: "Team member · approves changes, never budgets",
      body: "They get an email with a link that works for 7 days. Anyone who can approve changes must turn on two-step sign in before their first approval.",
    },
    footnote: "Owners always have to use two-step sign in.",
  },
  notice: {
    tag: "Needs a fix",
    title: "Marcus can approve without two-step",
    body: "Anyone who can approve changes that move money should use two-step sign in. We have emailed Marcus a reminder. You can also make it required for everyone.",
    primary: { label: "Require it" },
    secondary: { label: "Later" },
  },
  list: {
    title: "Recent sign ins",
    rows: [
      {
        title: "Dana · Mississauga",
        meta: "Today 8:14 am · Chrome on Mac",
        chip: "You",
        dot: true,
      },
      {
        title: "Marcus · Brampton",
        meta: "Today 7:02 am · Safari on iPhone",
        chip: "Active",
        chipTone: "pale",
        dot: true,
      },
    ],
  },
};

/* ---------- 67:1284 ---------- */
const cancel: DetailSpec = {
  shell: { active: "settings", workspace: alpha },
  head: {
    title: "Before you cancel, here is what happens.",
    lead: "Your campaigns belong to you and live in your own Google Ads account. Cancelling stops PPCWay looking after them. It does not stop your ads.",
  },
  tiles: [
    { tone: "brand", label: "Your plan", value: "Growth", chip: "$99 a month" },
    { label: "Paid until", value: "1 Oct", chip: "Full access until then" },
    { label: "Calls in the last 30 days", value: "58", chip: "From your 2 live campaigns" },
    { label: "Changes we made", value: "46", progress: 180 / 226 },
  ],
  why: {
    title: "What cancelling does",
    legend: "Read the terms",
    summary:
      "On 1 October we stop checking your campaigns, stop suggesting changes and stop the weekly email. Your ads, keywords and history stay in your Google Ads account, and you can download everything we recorded.",
  },
  record: {
    title: "Choose what happens to your ads",
    action: "Why this matters",
    rows: [
      {
        icon: "bars",
        iconTone: "brand",
        title: "Keep them running, with nobody watching",
        meta: "They keep spending up to $40 a day after 1 October",
        action: "Choose",
      },
      {
        selected: true,
        title: "Pause them on 1 October",
        meta: "Spend stops. You can switch them back on in Google Ads",
        action: "Selected",
      },
      {
        icon: "line",
        iconTone: "brand",
        title: "Pause them today",
        meta: "Spend stops within minutes, and you keep PPCWay until 1 October",
      },
    ],
  },
  next: {
    title: "Or take a smaller step",
    action: "Compare plans",
    mock: {
      kicker: "Starter · $49 a month",
      source: "One campaign, up to $1,500 ad spend a month",
      headline: "Halve the bill and keep the watching",
      body: "If money is tight, Starter keeps the daily checks and the approvals on your one campaign. Or switch to Tell me, I'll decide, where we tell you about problems and change nothing.",
    },
    footnote: "A plan change takes effect at renewal on 1 October.",
  },
  notice: {
    tone: "red",
    tag: "Cancelling",
    title: "Cancel Growth on 1 October",
    body: "You keep everything until then. We email you a copy of all we recorded, and your account can be restored for 30 days after.",
    primary: { label: "Cancel plan" },
    primaryTone: "red",
    secondary: { label: "Keep my plan" },
  },
  list: {
    title: "Download first",
    rows: [
      {
        title: "Everything we recorded",
        meta: "Activity, changes and reports · CSV",
        chip: "Ready",
        chipTone: "pale",
        dot: true,
      },
      {
        title: "Invoices",
        meta: "Every invoice so far · PDF",
        chip: "Ready",
        chipTone: "pale",
        dot: true,
      },
    ],
  },
};

/* ---------- 67:1453 ---------- */
const deleteAccount: DetailSpec = {
  shell: { active: "settings", workspace: alpha },
  head: {
    title: "Delete your PPCWay account.",
    lead: "This removes you from PPCWay. It does not delete your Google Ads account, your campaigns, or anything Google holds. Deletion finishes within 30 days.",
  },
  tiles: [
    { tone: "brand", label: "Profile and settings", value: "Erased", chip: "Within 30 days" },
    { label: "Copy of your website", value: "Erased", chip: "We only ever keep it 30 days" },
    { label: "Record of changes", value: "Kept 7 years", chip: "Locked, used only for audit" },
    { label: "Days to finish", value: "30", progress: 1 },
  ],
  why: {
    title: "Why one record stays",
    legend: "Privacy policy",
    summary:
      "The log of every change we made to your Google Ads account is kept for 7 years. It is the proof of what happened with your money if anyone ever asks. It is locked, used for nothing else, and never shared.",
  },
  record: {
    title: "What happens, in order",
    action: "Download your data first",
    rows: [
      {
        icon: "bars",
        iconTone: "brand",
        title: "We stop all changes",
        meta: "Nothing else is proposed or applied from this moment",
        action: "Today",
      },
      {
        icon: "plus",
        iconTone: "brand",
        title: "We remove our access to Google Ads",
        meta: "Your campaigns stay in your Google account, untouched",
        action: "Today",
      },
      {
        icon: "line",
        iconTone: "brand",
        title: "Your data is erased",
        meta: "Within 30 days · profile, settings, reports and team access",
      },
    ],
  },
  next: {
    title: "Your campaigns will keep running",
    action: "Pause them first",
    mock: {
      kicker: "Before you go",
      source: "2 live campaigns · up to $40 a day",
      headline: "Deleting PPCWay does not stop your ads",
      headlineTone: "red",
      body: "Your campaigns live in Google Ads and keep spending once we are gone. If you want them stopped, pause them here before you delete, or pause them yourself in Google Ads afterwards.",
    },
    footnote: "Data and privacy has the full download: profile, activity, changes and reports.",
  },
  notice: {
    tone: "red",
    tag: "Cannot be undone",
    title: "Delete Alpha Plumbing's account",
    body: "Type DELETE to confirm. You are signed out straight away, and everyone on your team loses access.",
    primary: { label: "Delete account" },
    primaryTone: "red",
    secondary: { label: "Cancel" },
    children: (
      <input
        aria-label="Type DELETE to confirm"
        defaultValue="DELETE"
        className="border-red-strong text-ink mt-3 h-12 w-full rounded-[12px] border bg-white px-[18px] text-[15px] font-semibold outline-none"
      />
    ),
  },
  list: {
    title: "Also ends today",
    rows: [
      {
        title: "Growth plan",
        meta: "No further charges",
        chip: "Ends",
        chipTone: "red",
        dot: true,
      },
      {
        title: "Team access",
        meta: "3 people lose access",
        chip: "Ends",
        chipTone: "red",
        dot: true,
      },
    ],
  },
};

/* ---------- 74:644 ---------- */
const business: DetailSpec = {
  shell: { active: "settings", workspace: alpha },
  head: {
    title: "What PPCWay knows about your business.",
    lead: "This is what we write your ads from. Fix anything that is wrong or out of date, and we will use it the next time we write or change an ad.",
  },
  tiles: [
    { tone: "brand", label: "Last checked", value: "Today", chip: "Against your website" },
    { label: "Services we advertise", value: "3", chip: "From your services page" },
    { label: "Area", value: "25 km", chip: "Plus Oakville and Brampton" },
    { label: "Phone shown in ads", value: "Tracked", progress: 1 },
  ],
  why: {
    title: "In one sentence",
    legend: "Edit",
    summary:
      "Alpha Plumbing is a licensed plumber in Mississauga, open 24 hours for emergencies, fixing burst pipes, water heaters, drains and leaks within 25 km, plus Oakville and Brampton.",
  },
  record: {
    title: "Services we advertise",
    action: "Add a service",
    rows: [
      {
        icon: "bars",
        iconTone: "brand",
        title: "Emergency repairs, 24 hours",
        meta: "Burst pipes, leaks and flooding",
        action: "Edit",
      },
      {
        icon: "plus",
        iconTone: "brand",
        title: "Water heaters",
        meta: "Repair and install, tank and tankless",
        action: "Edit",
      },
      {
        icon: "line",
        iconTone: "brand",
        title: "Drains",
        meta: "Cleaning and blocked toilets. You told us you do not do septic work.",
      },
    ],
  },
  next: {
    title: "Things we must never say",
    action: "Add one",
    mock: {
      kicker: "Your rules",
      source: <>No prices in ads · never &ldquo;cheapest&rdquo; · no septic work</>,
      headline: "Every ad is checked against these, and Google's rules",
      body: "Anything here beats what we read on your site. If you stop offering a service, remove it above and we will propose pausing its keywords the same day.",
    },
    footnote: "Every edit here is recorded in Activity, like any other change.",
  },
  notice: {
    tone: "brand",
    tag: "Out of date?",
    title: "Your site changed on 2 Sep",
    body: "We found a new page for commercial plumbing. Want it added as a service? Nothing changes until you say yes.",
    primary: { label: "Add it" },
    secondary: { label: "Ignore" },
  },
  list: {
    title: "Where this came from",
    rows: [
      {
        title: "Your website",
        meta: "Read on 4 Aug, checked every week",
        chip: "Source",
        dot: true,
      },
      { title: "You", meta: "3 edits since launch", chip: "Source", dot: true },
    ],
  },
};

/* ---------- 80:975 ---------- */
function Notifications() {
  return (
    <AppShell active="settings" workspace={alpha}>
      <PageHead
        title="Choose how we reach you."
        lead="Alerts about money or your account always reach you. Everything else is up to you, alert by alert and person by person."
      />
      <Tiles>
        <Tile tone="brand" label="Always on" value="5 alerts" chip="Money and account safety" />
        <Tile label="Your choice" value="5 alerts" chip="Set below" chipTone="pale" />
        <Tile label="Monday email" value="On" chip="8 am, to Dana and Marcus" chipTone="pale" />
        <Tile label="Sent this month" value="9" chip="3 of them by email" chipTone="grey" />
      </Tiles>
      <Columns
        aside={
          <>
            <Panel
              title="Who gets what"
              action={{ label: "Change", href: "/settings?view=team" }}
              tone="plain"
            >
              <Rows className="mt-1">
                <ListRow
                  title="Dana Whitfield"
                  meta="dana@alphaplumbing.ca · everything"
                  chip="Owner"
                  chipTone="pale"
                />
                <ListRow title="Marcus Reyes" meta="office@ · urgent and approvals" chip="Team" />
              </Rows>
            </Panel>
            <Panel title="Monday email" tone="plain">
              <Rows className="mt-1">
                <ListRow
                  title="Every Monday at 8 am"
                  meta="What happened, what we did, one thing to do"
                  right={<Toggle on label="Monday email" />}
                />
              </Rows>
            </Panel>
            <NoticeCard
              tone="amber"
              compact
              title="Check it works"
              body="Send yourself a sample alert by email and in the app. It is marked as a test and changes nothing."
              secondary={{ label: "Send a test alert" }}
            />
          </>
        }
      >
        <Panel title="Always sent, in the app and by email" tone="plain">
          <PanelText>
            These are about money or your account, so they cannot be turned off.
          </PanelText>
          <Rows className="mt-1">
            <ListRow
              title="Your card was declined by Google"
              meta="Your ads stop until the card works"
              chip="Always on"
            />
            <ListRow
              title="Google suspended your account"
              meta="Nothing can run until Google lifts it"
              chip="Always on"
            />
            <ListRow
              title="Google disconnected PPCWay"
              meta="We can't see or change anything"
              chip="Always on"
            />
            <ListRow
              title="Call tracking stopped counting calls"
              meta="We pause changes until it works again"
              chip="Always on"
            />
            <ListRow
              title="Your PPCWay payment failed"
              meta="Automation pauses after a grace period"
              chip="Always on"
            />
          </Rows>
        </Panel>
        <Panel
          title="You choose"
          tone="plain"
          action={
            <span className="text-faint flex gap-7 text-[13px] leading-4 font-semibold">
              <span>In app</span>
              <span>Email</span>
            </span>
          }
        >
          <Rows className="mt-1">
            <ToggleRow
              title="A change needs your OK"
              meta="Ask-first ideas · they expire after 7 days"
              toggles={[true, true]}
            />
            <ToggleRow
              title="Google turned down an ad"
              meta="We usually rewrite it ourselves"
              toggles={[true, true]}
            />
            <ToggleRow
              title="Budget nearly used up"
              meta="When 90% of a day's budget is gone by 3 pm"
              toggles={[true, false]}
            />
            <ToggleRow
              title="Your campaign is live"
              meta="After Google approves it"
              toggles={[true, true]}
            />
            <ToggleRow
              title="A big change in results"
              meta="In the Monday email unless it is severe"
              toggles={[true, false]}
            />
          </Rows>
        </Panel>
      </Columns>
    </AppShell>
  );
}

/* ---------- 80:1256 ---------- */
function TwoStep() {
  const codes = [
    "4F7K-2QX9",
    "8MNP-5TR2",
    "C3WD-7HJ4",
    "9LBV-6YE1",
    "K2RT-8QS5",
    "P6ZN-3FU7",
    "T1GX-4WM8",
    "W5HC-9KD3",
  ];
  return (
    <AppShell active="settings" workspace={alpha} initials="MR">
      <PageHead
        title="Marcus, turn on two-step sign-in."
        lead="Dana asked everyone who can approve changes to use it. It takes two minutes with an app such as Google Authenticator. Changing your password or two-step signs you out everywhere else."
      />
      <Tiles>
        <Tile tone="brand" label="Two-step sign-in" value="Off" chip="The owner requires it" />
        <Tile label="Password" value="12 Aug" chip="Last changed" chipTone="pale" />
        <Tile
          label="Recovery codes"
          value="None yet"
          chip="Made when you turn it on"
          chipTone="amber"
        />
        <Tile label="Signed in on" value="2 devices" chip="Chrome and Safari" chipTone="grey" />
      </Tiles>
      <Columns
        aside={
          <>
            <Panel title="Password" tone="plain">
              <Rows className="mt-1">
                <ListRow
                  title="Changed 12 August"
                  meta="Signs you out on other devices"
                  right={
                    <Button variant="secondary" size="sm" className="border-line h-11">
                      Change
                    </Button>
                  }
                />
              </Rows>
            </Panel>
            <Panel title="Where you're signed in" tone="plain">
              <Rows className="mt-1">
                <ListRow
                  title="Chrome on Windows"
                  meta="Mississauga · now"
                  chip="This device"
                  chipTone="pale"
                />
                <LinkRow title="Safari on iPhone" meta="Brampton · today 7:02 am" link="Sign out" />
              </Rows>
              <Button variant="secondary" size="sm" className="border-line mt-3 h-11">
                Sign out everywhere else
              </Button>
            </Panel>
            <Panel title="Sign in with Google" tone="plain">
              <Rows className="mt-1">
                <LinkRow
                  title="Not connected"
                  meta="Use your Google account instead of a password"
                  link="Connect"
                />
              </Rows>
            </Panel>
          </>
        }
      >
        <Panel title="Set up two-step sign-in" tone="plain">
          <ol className="mt-2">
            <Step
              n={1}
              title="Scan this code with your phone"
              meta="Use Google Authenticator, 1Password or any app that shows six-digit codes."
            />
          </ol>
          <div className="mt-2 flex flex-col gap-6 sm:flex-row sm:items-center sm:pl-[42px]">
            <QrCode />
            <div>
              <p className="text-muted text-[13px] leading-4 font-semibold">
                Can&rsquo;t scan it? Type this key instead
              </p>
              <p className="text-ink mt-[6px] text-[18px] leading-[22px] font-semibold tracking-wide">
                JBSW Y3DP EHPK 3PXP
              </p>
              <p className="text-faint mt-[6px] text-[13px] leading-4">
                Account name: PPCWay (office@alphaplumbing.ca)
              </p>
            </div>
          </div>
          <ol className="mt-4">
            <Step
              n={2}
              title="Type the six-digit code the app shows"
              meta="The code changes every 30 seconds. Any current one works."
            />
          </ol>
          <div className="mt-2 flex flex-wrap items-end gap-3 sm:pl-[42px]">
            <label className="block w-[220px]">
              <span className="text-muted block text-[13px] leading-4 font-semibold">
                Code from the app
              </span>
              <input
                inputMode="numeric"
                className="border-line mt-[7px] h-[46px] w-full rounded-[12px] border px-[15px] text-[15px] outline-none"
              />
            </label>
            <Button size="sm" className="h-[42px]">
              Turn on two-step
            </Button>
          </div>
          <ol className="mt-4">
            <Step
              n={3}
              title="Save your recovery codes"
              meta="Each one gets you in once if you lose your phone. They are shown here once, after you turn two-step on."
            />
          </ol>
        </Panel>
        <Panel title="Recovery codes" action={{ label: "Download · Copy" }} tone="plain">
          <ul className="text-faint mt-4 grid grid-cols-2 gap-x-6 gap-y-[10px] font-mono text-[16px] leading-[19px] font-semibold">
            {codes.map((c) => (
              <li key={c}>{c}</li>
            ))}
          </ul>
          <Footnote>
            Greyed until two-step is on. Keep them somewhere other than your phone.
          </Footnote>
        </Panel>
      </Columns>
    </AppShell>
  );
}

/** A drawn placeholder for the QR code: three finders and a scatter of modules. */
function QrCode() {
  const cells = [
    [8, 0],
    [10, 0],
    [11, 0],
    [9, 1],
    [11, 2],
    [12, 2],
    [10, 3],
    [10, 4],
    [8, 6],
    [9, 6],
    [11, 6],
    [12, 6],
    [8, 7],
    [9, 7],
    [10, 7],
    [2, 8],
    [3, 8],
    [6, 8],
    [7, 8],
    [9, 8],
    [10, 8],
    [11, 8],
    [15, 8],
    [16, 8],
    [17, 8],
    [18, 8],
    [19, 8],
    [20, 8],
    [2, 9],
    [12, 9],
    [14, 9],
    [16, 9],
    [17, 9],
    [18, 9],
    [0, 10],
    [2, 10],
    [3, 10],
    [4, 10],
    [5, 10],
    [7, 10],
    [9, 10],
    [12, 10],
    [19, 10],
    [20, 10],
    [0, 11],
    [1, 11],
    [2, 11],
    [4, 11],
    [8, 11],
    [10, 11],
    [11, 11],
    [13, 11],
    [15, 11],
    [19, 11],
    [0, 12],
    [4, 12],
    [5, 12],
    [6, 12],
    [8, 12],
    [13, 12],
    [14, 12],
    [16, 12],
    [19, 12],
    [12, 13],
    [13, 13],
    [16, 13],
    [17, 13],
    [18, 13],
    [8, 14],
    [11, 14],
    [13, 14],
    [14, 14],
    [15, 14],
    [8, 15],
    [10, 15],
    [16, 15],
    [17, 15],
    [18, 15],
    [11, 16],
    [13, 16],
    [14, 16],
    [16, 16],
    [18, 16],
    [19, 16],
    [8, 17],
    [9, 17],
    [16, 17],
    [8, 18],
    [9, 18],
    [10, 18],
    [11, 18],
    [12, 18],
    [13, 18],
    [16, 18],
    [17, 18],
    [18, 18],
    [20, 18],
    [10, 19],
    [13, 19],
    [14, 19],
    [15, 19],
    [16, 19],
    [19, 19],
    [9, 20],
    [10, 20],
    [12, 20],
    [13, 20],
    [14, 20],
    [19, 20],
    [20, 20],
  ];
  const finder = (x: number, y: number) => (
    <g key={`${x}-${y}`}>
      <rect x={x} y={y} width={7} height={7} fill="#0f1720" />
      <rect x={x + 1} y={y + 1} width={5} height={5} fill="#fff" />
      <rect x={x + 2} y={y + 2} width={3} height={3} fill="#0f1720" />
    </g>
  );
  return (
    <svg
      viewBox="-2 -2 25 25"
      width={150}
      height={150}
      aria-label="Two-step set-up code"
      className="border-line shrink-0 rounded-[10px] border bg-white"
    >
      {finder(0, 0)}
      {finder(14, 0)}
      {finder(0, 14)}
      {cells.map(([x, y]) => (
        <rect key={`${x}.${y}`} x={x} y={y} width={1} height={1} fill="#0f1720" />
      ))}
    </svg>
  );
}

/* ---------- 80:1615 ---------- */
function SwitchPlan() {
  return (
    <AppShell active="settings" workspace={alpha}>
      <PageHead
        title="Switch from Growth to Starter?"
        lead="Starter is $49 a month and covers one campaign. Here is exactly what changes for Alpha Plumbing before you decide."
      />
      <Tiles>
        <Tile tone="brand" label="New price" value="$49" chip="From 1 Oct, $50 less" />
        <Tile label="Campaigns" value="1 of 2" chip="Google Maps (Local) pauses" chipTone="red" />
        <Tile label="Ad spend limit" value="$1,500" chip="You spend about $1,240" chipTone="pale" />
        <Tile
          label="Call tracking"
          value="Off"
          valueTone="red"
          chip="Calls stop being counted"
          chipTone="red"
        />
      </Tiles>
      <Columns
        aside={
          <>
            <ActionPanel
              title="Confirm the switch"
              body="You keep Growth until 1 October, the end of what you have paid for. Nothing is charged today and there is no refund for the rest of September."
              primary="Switch to Starter"
              primaryTone="ink"
              secondary="Keep Growth"
            />
            <Panel title="Saving money?" tone="plain">
              <PanelText>
                Lowering your daily budget from $40 to $32 saves about $240 a month and keeps both
                campaigns and call tracking.
              </PanelText>
              <Button variant="secondary" size="sm" className="border-line mt-4 h-11">
                Lower my budget instead
              </Button>
            </Panel>
          </>
        }
      >
        <Panel title="Choose your plan" action={{ label: "Compare every feature" }} tone="plain">
          <Choice
            name="plan"
            selected
            title="Starter · $49 a month"
            meta="One campaign and up to $1,500 of ad spend a month. No call tracking."
            chip="Chosen"
          />
          <Choice
            name="plan"
            title="Growth · $99 a month"
            meta="Up to four campaigns, call tracking and the Monday email."
            chip="Current"
            chipTone="grey"
          />
          <Choice
            name="plan"
            title="Agency · $249 a month"
            meta="Up to ten businesses, one view of every client and reports under your own name."
          />
        </Panel>
        <Panel title="What changes on 1 October" tone="plain">
          <Rows className="mt-1">
            <ListRow
              title="Google Maps (Local) pauses"
              meta="It brought 17 calls last month. Its settings are kept if you switch back."
              chip="Pauses"
              chipTone="red"
            />
            <ListRow
              title="Calls stop being counted"
              meta="Without call tracking we can only aim for clicks, so your cost per call will likely rise."
              chip="Stops"
              chipTone="red"
            />
            <ListRow
              title="Your limits, history and ads stay"
              meta="Autonomy, limits and every past change are kept exactly as they are."
              chip="Kept"
              chipTone="pale"
            />
          </Rows>
        </Panel>
      </Columns>
    </AppShell>
  );
}

/* ---------- 81:1833 ---------- */
function PaymentFailed() {
  return (
    <AppShell active="settings" workspace={alpha}>
      <PageHead
        title="Your PPCWay payment did not go through."
        lead="This is the $99 for PPCWay, not your ads. Your ads keep running and Google keeps billing you as normal. Update the card by 8 October to keep automation on."
      />
      <Tiles>
        <Tile
          label="Payment"
          value="Failed"
          valueTone="red"
          chip="Visa ending 4242 declined"
          chipTone="red"
        />
        <Tile label="Tried on" value="1 and 3 Oct" chip="Next try 6 Oct" chipTone="grey" />
        <Tile
          label="Automation pauses"
          value="8 Oct"
          chip="Your ads keep running"
          chipTone="amber"
        />
        <Tile label="Owed" value="$99.00" chip="Growth, October" chipTone="grey" />
      </Tiles>
      <Columns
        aside={
          <>
            <NoticeCard
              tone="red"
              compact
              title="Update your card"
              body="Stripe keeps the card details. PPCWay never sees the number, and this card is never used for your ads."
              primary={{ label: "Update card" }}
              primaryTone="red"
              secondary={{ label: "Use another card" }}
              className="border-red-pale"
            />
            <Panel title="Common reasons" tone="plain">
              <Rows className="mt-1">
                <ListRow title="The card expired" meta="Check the date on the Visa" />
                <ListRow
                  title="Your bank blocked it"
                  meta="Banks sometimes stop a new monthly charge"
                />
                <ListRow title="Not enough funds" meta="We retry twice before pausing" />
              </Rows>
            </Panel>
          </>
        }
      >
        <Panel title="What happens next" tone="plain">
          <ol className="mt-1">
            <Step
              n={1}
              title="6 October: we try the card again"
              meta="Automatic. You get an email either way."
            />
            <Step
              n={2}
              title="8 October: automation pauses"
              meta="No new changes and no ask-first ideas. Your ads keep running exactly as they are, and Google keeps billing you directly."
            />
            <Step
              n={3}
              title="Update the card whenever you like"
              meta="We charge it straight away and switch everything back on. Nothing is lost."
            />
          </ol>
        </Panel>
        <Panel title="Invoices" action={{ label: "Download all" }} tone="plain">
          <Rows className="mt-1">
            <ListRow
              title="1 October 2026 · Growth"
              meta="Visa ending 4242 · declined on 1 and 3 Oct"
              chip="Failed"
              chipTone="red"
            />
            <ValueRow title="1 September 2026 · Growth" meta="Paid on the Visa" value="$99.00" />
            <ValueRow title="1 August 2026 · Growth" meta="Paid on the Visa" value="$99.00" />
          </Rows>
        </Panel>
      </Columns>
    </AppShell>
  );
}

/* ---------- 87:6993 ---------- */
function GoogleConnection() {
  return (
    <AppShell active="settings" workspace={alpha}>
      <PageHead
        title="Your Google Ads connection."
        lead="PPCWay works in one Google Ads account, linked under our manager account. This is what we can do there, and how to switch it off."
      />
      <Tiles>
        <Tile tone="brand" label="Status" value="Connected" chip="Checked today at 10:52" />
        <Tile label="Account" value="742-118-9063" chip="Alpha Plumbing, in CAD" chipTone="grey" />
        <Tile
          label="Linked since"
          value="4 Aug"
          chip="Dana accepted the invitation"
          chipTone="grey"
        />
        <Tile label="Sign-in token" value="Fresh" chip="Renewed 6 hours ago" chipTone="pale" />
      </Tiles>
      <Columns
        aside={
          <>
            <NoticeCard
              tone="red"
              compact
              title="Disconnect Google Ads"
              body="We stop every change straight away and remove our access in Google. Your campaigns keep running in Google Ads, and keep spending, until you pause them there."
              primary={{ label: "Disconnect" }}
              primaryTone="red"
              className="border-red-pale"
            />
            <Panel title="If the connection breaks" tone="plain">
              <PanelText>
                If Google cuts us off, we email you, pause every change and show a banner here.
                Reconnecting takes about a minute.
              </PanelText>
            </Panel>
          </>
        }
      >
        <Panel title="What PPCWay can do there" tone="plain">
          <Rows className="mt-1">
            <ListRow
              title="Create and edit campaigns"
              meta="Only in this account, and only what your autonomy setting allows"
              chip="Allowed"
              chipTone="pale"
            />
            <ListRow
              title="Read your results"
              meta="Clicks, calls and cost, four times a day"
              chip="Allowed"
              chipTone="pale"
            />
            <ListRow
              title="Set up tracking in Tag Manager"
              meta="Container GTM-5K2QF8 on alphaplumbing.ca"
              chip="Allowed"
              chipTone="pale"
            />
            <ListRow
              title="Change billing or your payment card"
              meta="Never. Your card stays with Google."
              chip="Never"
            />
          </Rows>
        </Panel>
        <Panel title="How it is linked" tone="plain">
          <Rows className="mt-1">
            <LinkRow
              title="dana@alphaplumbing.ca"
              meta="The Google account that approved the connection on 4 Aug"
              link="Details"
            />
            <ListRow
              title="PPCWay manager account"
              meta="118-402-7751 · your account sits under it, like with an agency"
              chip="Our manager"
            />
          </Rows>
        </Panel>
      </Columns>
    </AppShell>
  );
}

/* ---------- 87:7262 ---------- */
function Results() {
  return (
    <AppShell active="settings" workspace={alpha}>
      <PageHead
        title="What counts as a result."
        lead="These are the conversions Google records for you. We only aim for the one marked main, so it has to keep working."
      />
      <Tiles>
        <Tile tone="brand" label="Main result" value="Calls" chip="Longer than 30 seconds" />
        <Tile label="Last one counted" value="2 hrs ago" chip="Working" chipTone="pale" />
        <Tile label="Counted, last 30 days" value="58" chip="All from your ads" chipTone="grey" />
        <Tile label="Last test" value="4 Aug" chip="A real call at setup" chipTone="grey" />
      </Tiles>
      <Columns
        aside={
          <>
            <NoticeCard
              tone="amber"
              compact
              title="Check it still works"
              body="Call (905) 555-0142 from a phone that is not yours and stay on for 30 seconds. It shows here within about 10 minutes."
              secondary={{ label: "Start a test" }}
            />
            <Panel title="If it stops" tone="plain">
              <PanelText>
                If Google records no calls for two days while clicks carry on, we hold every bid
                change and tell you straight away.
              </PanelText>
            </Panel>
          </>
        }
      >
        <Panel title="Conversions Google records" action={{ label: "Add one" }} tone="plain">
          <Rows className="mt-1">
            <ListRow
              title="Calls from your ads"
              meta="Google forwarding number · over 30 seconds · 58 in 30 days"
              chip="Main"
              chipTone="pale"
            />
            <ListRow
              title="Calls from your website"
              meta="Tag Manager, Call button taps · 23 in 30 days"
              chip="Counted, not main"
            />
            <LinkRow
              title="Quote form sent"
              meta="Not set up · worth it if people ask for quotes online"
              link="Set up"
            />
          </Rows>
        </Panel>
        <Panel title="How a call is counted" tone="plain">
          <Choice
            name="count"
            selected
            title="Calls longer than 30 seconds"
            meta="The usual choice. Wrong numbers rarely last that long."
          />
          <Choice
            name="count"
            title="Every call, any length"
            meta="Counts more, but hang-ups start to look like wins."
          />
          <Choice
            name="count"
            title="Only calls you mark as jobs"
            meta="The most exact. You tag the good ones in Activity."
          />
        </Panel>
      </Columns>
    </AppShell>
  );
}

/* ---------- 87:7528 ---------- */
function DataHandling() {
  const out = "Outside Canada";
  return (
    <AppShell active="settings" workspace={alpha}>
      <PageHead
        title="Who handles your data, and your choices."
        lead="Your data is stored in Canada. A few companies process parts of it for us, some outside Canada. They are all listed here, with exactly what each one gets."
      />
      <Tiles>
        <Tile tone="brand" label="Stored in" value="Canada" chip="Montreal and Toronto" />
        <Tile label="Companies we use" value="7" chip="Listed below" chipTone="grey" />
        <Tile label="Optional sharing" value="Off" chip="You decide, below" chipTone="amber" />
        <Tile label="List last changed" value="1 Sep" chip="We email you first" chipTone="grey" />
      </Tiles>
      <Columns
        aside={
          <>
            <Panel title="Your choices" tone="plain">
              <Rows className="mt-1">
                <ListRow
                  title="Help improve our ad writing"
                  meta="Use copies of your ads with names and contact details removed"
                  right={<Toggle on={false} label="Help improve our ad writing" />}
                />
                <ListRow
                  title="Anonymous category averages"
                  meta="Include your results in how plumbers do on average"
                  right={<Toggle on={false} label="Anonymous category averages" />}
                />
              </Rows>
              <Footnote>
                Both are off unless you turn them on. Turning one off later stops it straight away.
              </Footnote>
            </Panel>
            <Panel title="If something goes wrong" tone="plain">
              <PanelText>
                If your data is ever exposed, we tell you and the Privacy Commissioner of Canada, as
                the law requires, and explain what we are doing about it.
              </PanelText>
            </Panel>
          </>
        }
      >
        <Panel
          title="Companies that process your data"
          action={{ label: "Privacy notice" }}
          tone="plain"
        >
          <Rows className="mt-1">
            <ListRow title="Google" meta="Runs your ads · your Google Ads data" chip={out} />
            <ListRow
              title="Anthropic"
              meta="Writes ad text from your website · site text only, not used for training"
              chip={out}
            />
            <ListRow
              title="Stripe"
              meta="Takes your PPCWay payment · card details, never seen by us"
              chip={out}
            />
            <ListRow title="Postmark" meta="Sends our emails · your email address" chip={out} />
            <ListRow
              title="Google Cloud"
              meta="Hosts PPCWay · everything, encrypted"
              chip="In Canada"
              chipTone="pale"
            />
            <ListRow
              title="Temporal"
              meta="Runs our scheduled checks · account IDs only"
              chip={out}
            />
            <ListRow
              title="Sentry"
              meta="Catches errors · technical logs, no card data"
              chip={out}
            />
          </Rows>
        </Panel>
      </Columns>
    </AppShell>
  );
}

/* ---------- 17:2967 ---------- */
function YourData() {
  return (
    <AppShell active="settings" workspace={alpha}>
      <PageHead
        title="Your data belongs to you."
        lead="Take a copy whenever you like, or close the account and have everything deleted. We have never sold data and do not intend to."
      />
      <Tiles>
        <Tile
          tone="brand"
          label="Where your data lives"
          value="Canada"
          chip="Montreal and Toronto"
        />
        <Tile label="Results we keep" value="13 months" chip="Then deleted automatically" />
        <Tile label="Change records" value="7 years" chip="Required for the audit trail" />
        <Tile label="Your card number" value="Never" progress={4 / 226} />
      </Tiles>
      <Columns
        aside={
          <>
            <Panel title="Who can see it">
              <PanelText className="text-[15px] leading-[18px]">
                You, and anyone you invite. PPCWay support can look only if you ask, and every look
                is written down.
              </PanelText>
              <div className="mt-[18px] flex flex-wrap gap-[10px]">
                <Button variant="secondary" className="border-line">
                  Access log
                </Button>
                <Button variant="secondary" className="border-line">
                  Privacy notice
                </Button>
              </div>
            </Panel>
            <Panel title="Rules we follow">
              <Rows className="mt-1">
                <ListRow
                  title="Canadian privacy law"
                  meta="PIPEDA, for every merchant"
                  chip="Followed"
                  chipTone="pale"
                  dot
                />
                <ListRow
                  title="Google Ads API terms"
                  meta="Reviewed every release"
                  chip="Followed"
                  dot
                />
              </Rows>
            </Panel>
          </>
        }
      >
        <Panel title="What you can do" action={{ label: "Privacy notice" }}>
          <Rows>
            <ActivityRow
              icon="bars"
              iconTone="amber"
              title="Download everything we hold"
              meta="A spreadsheet of your details, campaigns and every change. Ready in about an hour."
              action="Request it"
            />
            <ActivityRow
              icon="plus"
              iconTone="grey"
              title="Stop the automatic tuning"
              meta="We keep showing you results, but we stop proposing and making changes."
              action="Turn it off"
            />
            <ActivityRow
              icon="line"
              iconTone="grey"
              title="Close the account and delete it"
              meta="Everything goes within 30 days. Your Google Ads account and its history stay with you."
            />
          </Rows>
        </Panel>
      </Columns>
    </AppShell>
  );
}

/* ---------- 90:15292 ---------- */
function AddOns() {
  return (
    <AppShell active="settings" workspace={alpha}>
      <PageHead
        title="Add more to your plan."
        lead="Growth covers one Google Ads account and one service area. Add more when you need them. Each is billed monthly with your plan and can be removed at the end of any month."
      />
      <Tiles>
        <Tile tone="brand" label="Your plan" value="Growth" chip="$99 a month" />
        <Tile
          label="Google Ads accounts"
          value="1 of 1"
          chip="Included in Growth"
          chipTone="grey"
        />
        <Tile label="Service areas" value="1 of 1" chip="Mississauga and around" chipTone="grey" />
        <Tile label="Next bill" value="1 Oct" chip="$118 with the new area" chipTone="amber" />
      </Tiles>
      <Columns
        aside={
          <Panel tone="amber" title="Your next bill">
            <Rows className="divide-amber-line mt-1">
              <ValueRow title="Growth" value="$99.00" />
              <ValueRow
                title="Hamilton service area"
                meta="From today, so $12 for the rest of September"
                value="$19.00"
              />
              <ListRow
                title="From 1 October"
                right={<span className="text-ink text-[15px] font-bold">$118.00</span>}
              />
            </Rows>
            <div className="mt-3 flex gap-[10px]">
              <Button size="sm" className="h-[42px]">
                Confirm
              </Button>
              <button
                type="button"
                className="text-amber-dark hover:bg-amber-pale border-amber-line inline-flex h-11 items-center rounded-full border px-[21px] text-[15px] font-semibold"
              >
                Cancel
              </button>
            </div>
          </Panel>
        }
      >
        <Panel title="Add-ons" tone="plain">
          <Rows className="mt-1">
            <ListRow
              title="Another service area"
              meta="$19 a month · its own budget, ads and results, for example Hamilton"
              chip="Adding"
              chipTone="amber"
            />
            <ListRow
              title="Another Google Ads account"
              meta="$29 a month · for a second business or brand"
              right={
                <Button variant="secondary" size="sm" className="border-line h-11">
                  Add
                </Button>
              }
            />
            <ListRow
              title="More team members"
              meta="$9 a month each after the 5 included"
              right={
                <Button variant="secondary" size="sm" className="border-line h-11">
                  Add
                </Button>
              }
            />
          </Rows>
        </Panel>
        <Panel title="What a new area includes" tone="plain">
          <PanelText>
            Its own campaign, written the same way as your first, with its own budget inside your
            overall limits. Results show separately and together.
          </PanelText>
        </Panel>
      </Columns>
    </AppShell>
  );
}
