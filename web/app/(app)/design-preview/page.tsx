import { notFound } from "next/navigation";
import { DraftReview } from "@/components/pw/campaign-builder";
import { CampaignStepper, type StepperStart } from "@/components/pw/campaign-stepper";
import { CampaignDetail, type Detail, type Suggestions } from "@/components/pw/campaign-detail";
import { CampaignList } from "@/components/pw/campaigns";
import { Report } from "@/components/pw/report";
import { ReportPaper } from "@/components/pw/report-paper";
import { Team } from "@/components/pw/team";
import { Header, HeaderLink, PwPage } from "@/components/pw/shell";
import type { AdsDay, AdsSummary } from "@/lib/ads";
import type { Draft, Prefill } from "@/lib/builder";
import type { ReportSaid } from "@/lib/reports";
import {
  AdminErrors,
  AdminJobs,
  AdminMerchant,
  AdminMerchants,
  AdminOverview,
  AdminPlatform,
  AdminQuota,
  AdminStaff,
} from "@/components/admin/live";
import {
  doorOf,
  type Change,
  type Chrome,
  type Fault,
  type Figure,
  type Grant,
  type JobRun,
  type Look,
  type Merchant,
  type MerchantRow,
  type Overview,
  type PlatformView,
  type Room,
  type Series,
  type Whoami,
} from "@/lib/admin";

/*
  Every internal screen with fixture data, for measuring the design.

  It exists because the console is behind sign-in, so neither a screenshot
  tool nor the inspector can reach a real one, and two rounds of design were
  once done without anybody seeing the result. This renders the same
  components the real screens do, against data shaped like the real data.

  `?screen=` picks the screen: merchants (the default), overview, merchant,
  jobs, errors, quota, platform, staff. `?state=empty` shows the first-run
  state where a screen has one.

  The figures agree with each other the way the real ones must: the
  merchants' waiting proposals sum to the overview's 17, the failures are the
  overview's 3 syncs and 4 model calls, and every date is counted back from
  now rather than written down, so the fixtures never go stale.

  Dev only. `notFound()` in any other environment, so it cannot be reached in
  production even by somebody who guesses the path.
*/

const MIN = 60_000;
const HOUR = 60 * MIN;
const DAY = 24 * HOUR;
const at = (msAgo: number) => new Date(Date.now() - msAgo).toISOString();

const WHO: Whoami = {
  staff: true,
  level: "principal",
  may: [
    "read_merchant",
    "read_support_queue",
    "read_platform",
    "run_job",
    "read_errors",
    "stop_writes",
    "set_flags",
    "grant_staff",
  ],
  levels: [
    { level: "support", what: "Reads one merchant at a time and changes nothing." },
    { level: "engineer", what: "Reads the whole platform and re-runs jobs." },
    { level: "principal", what: "Everything above, and stops writes and grants access." },
  ],
  who: "admin@ppcway.com",
};

/* Irish trades, uneven numbers. Waiting sums to 17. */
const ROWS: MerchantRow[] = [
  {
    organization_id: "9b2f6c1e-1",
    name: "Alpha Plumbing",
    customer_id: "2580586343",
    connected: true,
    account_status: "ENABLED",
    people: 3,
    waiting: 4,
    applied: 27,
    last_sync: at(11 * MIN),
    trouble: "",
  },
  {
    organization_id: "4d81a7e0-2",
    name: "Beacon Roofing",
    customer_id: "7741029388",
    connected: true,
    account_status: "SUSPENDED",
    people: 2,
    waiting: 1,
    applied: 9,
    last_sync: at(4 * HOUR),
    trouble: "Google says this account is suspended.",
  },
  {
    organization_id: "c03e9b52-3",
    name: "Northside Dental",
    customer_id: "4420917755",
    connected: true,
    account_status: "",
    people: 5,
    waiting: 0,
    applied: 63,
    last_sync: at(26 * MIN),
    trouble: "",
  },
  {
    organization_id: "71f0d4aa-4",
    name: "Kavanagh Electrical",
    customer_id: "",
    connected: false,
    account_status: "",
    people: 1,
    waiting: 0,
    applied: 0,
    last_sync: null,
    trouble: "No Google Ads account connected.",
  },
  {
    organization_id: "e5a2c918-5",
    name: "Hourihane Tiling",
    customer_id: "9013774820",
    connected: true,
    account_status: "ENABLED",
    people: 1,
    waiting: 12,
    applied: 4,
    last_sync: at(3 * DAY),
    trouble: "",
  },
  {
    organization_id: "2a9e47c3-6",
    name: "Corrib Heat Pumps",
    customer_id: "6630418827",
    connected: true,
    account_status: "ENABLED",
    people: 2,
    waiting: 0,
    applied: 18,
    last_sync: at(7 * MIN),
    trouble: "",
  },
  {
    organization_id: "8c6d1f05-7",
    name: "Liffey Locksmiths",
    customer_id: "",
    connected: false,
    account_status: "",
    people: 2,
    waiting: 0,
    applied: 0,
    last_sync: null,
    trouble: "No Google Ads account connected.",
  },
  {
    organization_id: "5e3b8a21-8",
    name: "Dodder Valley Landscaping",
    customer_id: "3318205561",
    connected: true,
    account_status: "ENABLED",
    people: 4,
    waiting: 0,
    applied: 41,
    last_sync: at(19 * MIN),
    trouble: "",
  },
];

/*
  More businesses for the paged list: 46 Irish trades after the eight above,
  three pages in all. None has anything waiting, so the overview's 17 still
  adds up, and a few are unconnected or stale so the tabs have something to
  count on every page.
*/
const SURNAMES = [
  "Brennan",
  "Byrne",
  "Callaghan",
  "Carroll",
  "Connolly",
  "Daly",
  "Doherty",
  "Doyle",
  "Duffy",
  "Fitzgerald",
  "Flanagan",
  "Gallagher",
  "Healy",
  "Keane",
  "Lynch",
  "Maguire",
  "McCarthy",
  "McGrath",
  "Moran",
  "Nolan",
  "O'Connor",
  "O'Neill",
  "Quinn",
  "Sheehan",
  "Walsh",
];
const TRADES = [
  "Plumbing",
  "Roofing",
  "Electrical",
  "Glazing",
  "Carpentry",
  "Plastering",
  "Heating",
  "Joinery",
  "Painting",
  "Gutters",
];
const MORE: MerchantRow[] = Array.from({ length: 46 }, (_, i) => {
  const unconnected = i % 9 === 3;
  const stale = i % 11 === 7;
  const id = String(3184620573 + i * 7919);
  return {
    organization_id: `fx-${String(i).padStart(3, "0")}`,
    name: `${SURNAMES[(i * 7) % SURNAMES.length]} ${TRADES[(i * 3) % TRADES.length]}`,
    customer_id: unconnected ? "" : id,
    connected: !unconnected,
    account_status: unconnected ? "" : "ENABLED",
    people: 1 + (i % 4),
    waiting: 0,
    applied: (i * 13) % 47,
    last_sync: unconnected ? null : at(stale ? (2 + (i % 3)) * DAY : (5 + ((i * 17) % 50)) * MIN),
    trouble: unconnected ? "No Google Ads account connected." : "",
  };
});

function fig(label: string, value: number, window = "7d", change: number | null = null): Figure {
  return {
    label,
    value,
    window,
    known: true,
    change,
    words: `${value} ${label.toLowerCase()}${window ? ` in the last ${window.replace("d", " days")}` : ""}.`,
  };
}

/*
  Seven days of proposals, settling as they age: recent days are mostly still
  open, older ones applied, refused or expired.
*/
function series(): Series {
  const days: Record<string, number>[] = [
    { applied: 14, rejected: 4, expired: 2, reverted: 1 },
    { applied: 17, rejected: 3, expired: 1 },
    { applied: 12, rejected: 5, reverted: 1, failed: 1 },
    { applied: 19, rejected: 2, awaiting_approval: 1 },
    { applied: 15, rejected: 4, awaiting_approval: 2, reverted: 1 },
    { applied: 9, rejected: 3, awaiting_approval: 5, proposed: 1 },
    { applied: 2, rejected: 1, awaiting_approval: 5, proposed: 1 },
  ];
  const today = new Date();
  const midnight = Date.UTC(today.getUTCFullYear(), today.getUTCMonth(), today.getUTCDate());
  return {
    step: "day",
    points: days.map((counts, i) => ({
      start: new Date(midnight - (days.length - 1 - i) * DAY).toISOString(),
      counts,
    })),
  };
}

const OVERVIEW: Overview = {
  at: new Date().toISOString(),
  window: "7d",
  healthy: false,
  trouble: [
    "2 syncs started over an hour ago and never finished. Those accounts are working from old figures.",
    "3 syncs failed in the last 7 days.",
    "4 model calls came back with nothing in the last 7 days.",
  ],
  writes: {
    anything_can_be_written: false,
    words:
      "PPCWay is not writing to any Google Ads account. Writes were switched off here: Done testing the write path on the test account for today.",
    stops: [{ scope: "7741029388", because: "Suspended by Google", ours: true }],
  },
  figures: {
    merchants: fig("Businesses", ROWS.length, ""),
    connected: fig("Connected to Google Ads", ROWS.filter((r) => r.connected).length, ""),
    people: fig(
      "People",
      ROWS.reduce((n, r) => n + r.people, 0),
      "",
    ),
    proposed: fig("Changes proposed", 148, "7d", 31),
    waiting: fig(
      "Waiting for a merchant",
      ROWS.reduce((n, r) => n + r.waiting, 0),
      "",
    ),
    applied: fig("Changes applied", 88, "7d"),
    reverted: fig("Changes put back", 3, "7d"),
    refused: fig("Refused by a guardrail", 22, "7d"),
    model_calls: fig("Model calls", 412, "7d", 88),
    model_tokens: fig("Tokens used", 1_284_906, "7d"),
    model_trouble: fig("Model calls that failed", 4, "7d", 4),
    syncs_failed: fig("Syncs that failed", 3, "7d", -2),
    syncs_stuck: fig("Syncs still running", 2, ""),
  },
  series: series(),
};

const PLATFORM: PlatformView = {
  words: OVERVIEW.writes.words,
  anything_can_be_written: false,
  may_stop_writes: true,
  may_switch_writes: true,
  writes: {
    on: false,
    source: "panel",
    because: "Done testing the write path on the test account for today.",
    set_by: "admin@ppcway.com",
    set_at: at(2 * HOUR + 40 * MIN),
  },
  stops: [
    {
      scope: "7741029388",
      customer_id: "7741029388",
      because: "Google suspended the account. Nothing is sent until it is reinstated.",
      ours: true,
      pulled_at: at(4 * HOUR + 12 * MIN),
    },
  ],
  flags: [
    {
      name: "Writing to Google Ads",
      on: false,
      what_it_does:
        "Whether PPCWay may change anything in a merchant's Google Ads account. Off means every approved change is recorded and nothing is sent.",
      changeable: true,
      why_not: "",
    },
    {
      name: "Applying without asking",
      on: false,
      what_it_does:
        "Whether a merchant who has opted in may have low-risk changes applied without answering each one. Off by default for every new account.",
      changeable: false,
      why_not: "This comes from the deployment's settings; it takes a deploy to change.",
    },
    {
      name: "Open to everybody",
      on: false,
      what_it_does: "Whether anybody can make an account, or only people who were invited.",
      changeable: false,
      why_not: "This comes from the deployment's settings; it takes a deploy to change.",
    },
    {
      name: "Otto can talk",
      on: true,
      what_it_does: "Which service answers a merchant's questions: openrouter.",
      changeable: false,
      why_not: "This comes from the deployment's settings; it takes a deploy to change.",
    },
    {
      name: "Chat is screened",
      on: true,
      what_it_does:
        "Whether Model Armor checks what a merchant types before it is sent. With no template, chat refuses rather than sending anything unscreened.",
      changeable: false,
      why_not: "This comes from the deployment's settings; it takes a deploy to change.",
    },
  ],
};

/* 3 failed syncs and 4 failed model calls, newest first. */
const FAULTS: Fault[] = [
  {
    where: "model (chat)",
    what: "The model took longer than 30 seconds and the answer was dropped.",
    customer_id: "2580586343",
    at: at(38 * MIN),
  },
  {
    where: "sync (structure)",
    what: "Google Ads refused the token: the merchant revoked PPCWay's access.",
    customer_id: "9013774820",
    at: at(2 * HOUR + 4 * MIN),
  },
  {
    where: "model (nightly)",
    what: "Model Armor blocked the prompt as unsafe; nothing was sent to the model.",
    customer_id: "3318205561",
    at: at(9 * HOUR),
  },
  {
    where: "sync (metrics)",
    what: "Google Ads answered RESOURCE_EXHAUSTED: the account's daily operations ran out.",
    customer_id: "9013774820",
    at: at(DAY + 3 * HOUR),
  },
  {
    where: "model (chat)",
    what: "OpenRouter answered 503: no provider was available for the model.",
    customer_id: "6630418827",
    at: at(DAY + 7 * HOUR),
  },
  {
    where: "sync (structure)",
    what: "The job failed and said nothing.",
    customer_id: "7741029388",
    at: at(3 * DAY + 2 * HOUR),
  },
  {
    where: "model (nightly)",
    what: "The model's answer was not valid JSON, so no change was proposed from it.",
    customer_id: "2580586343",
    at: at(5 * DAY + 5 * HOUR),
  },
];

/*
  240 runs, ten pages: a structure sync every few minutes across the
  connected accounts, today's figures every ninth, one backfill, five
  failures, two that never finished and one running now.
*/
function runs(n = 240): JobRun[] {
  const accounts = ROWS.filter((r) => r.connected).map((r) => r.customer_id);
  const out: JobRun[] = [];
  for (let i = 0; i < n; i++) {
    const started = i * 13 * MIN + 2 * MIN;
    const customer = accounts[i % accounts.length];
    const kind = i % 9 === 4 ? "today" : i === 131 ? "backfill" : "structure";
    const failed = i === 6 || i === 23 || i === 41 || i === 77 || i === 152;
    const stuck = i === 9 || i === 10;
    const running = i === 0;
    const took =
      running || stuck ? null : kind === "structure" ? 6 + (i % 5) * 3 : 74 + (i % 7) * 9;
    out.push({
      id: `run-${i}`,
      customer_id: customer,
      kind,
      status: failed ? "failed" : running || stuck ? "running" : "finished",
      stage: "",
      stuck,
      took_seconds: failed ? 3 + (i % 4) : took,
      started_at: at(started),
      words: stuck
        ? `Started ${Math.round(started / HOUR)} h ago and never finished.`
        : failed
          ? "Google Ads refused the token: the merchant revoked PPCWay's access."
          : running
            ? "Still running."
            : `Finished in ${took} s.`,
    });
  }
  return out;
}

const QUOTA: Room[] = [
  { customer_id: "9013774820", used: 12_410, allowance: 15_000 },
  { customer_id: "2580586343", used: 4_377, allowance: 15_000 },
  { customer_id: "4420917755", used: 2_140, allowance: 15_000 },
  { customer_id: "3318205561", used: 1_208, allowance: 15_000 },
  { customer_id: "6630418827", used: 860, allowance: 15_000 },
  { customer_id: "7741029388", used: 0, allowance: 15_000 },
].map((one) => ({
  ...one,
  left: one.allowance - one.used,
  share_used: one.used / one.allowance,
  tight: one.used / one.allowance >= 0.8,
  words: `${one.used.toLocaleString("en-CA")} of ${one.allowance.toLocaleString("en-CA")} operations used today, ${(one.allowance - one.used).toLocaleString("en-CA")} left.`,
}));

const GRANTS: Grant[] = [
  {
    account_id: "a-niamh",
    who: "niamh@ppcway.com",
    level: "support",
    granted: true,
    because: "Covering the support inbox this week",
    by_account_id: "a-admin",
    by: "admin@ppcway.com",
    at: at(5 * HOUR),
  },
  {
    account_id: "a-ciaran",
    who: "ciaran@ppcway.com",
    level: "engineer",
    granted: true,
    because: "On call for the sync jobs",
    by_account_id: "a-admin",
    by: "admin@ppcway.com",
    at: at(DAY + 2 * HOUR),
  },
  {
    account_id: "a-dev",
    who: "contractor@ppcway.com",
    level: "",
    granted: false,
    because: "Contract ended",
    by_account_id: "a-admin",
    by: "admin@ppcway.com",
    at: at(DAY + 6 * HOUR),
  },
  {
    account_id: "a-dev",
    who: "contractor@ppcway.com",
    level: "engineer",
    granted: true,
    because: "Building the jobs screen",
    by_account_id: "a-admin",
    by: "admin@ppcway.com",
    at: at(3 * DAY),
  },
  {
    account_id: "a-admin",
    who: "admin@ppcway.com",
    level: "principal",
    granted: true,
    because: "First principal, made from the command line",
    by_account_id: null,
    by: "",
    at: at(4 * DAY),
  },
];

/* Alpha Plumbing's own screen. */
const KINDS: [string, string, string, string][] = [
  [
    "awaiting_approval",
    "add_negative_keyword",
    "low",
    "“plumbing apprenticeship” had 41 clicks and no calls in 30 days.",
  ],
  [
    "awaiting_approval",
    "lower_bid",
    "low",
    "“emergency plumber dublin 15” costs twice what its calls are worth.",
  ],
  [
    "proposed",
    "pause_keyword",
    "medium",
    "“boiler parts” has spent the most this month and brought one call.",
  ],
  [
    "awaiting_approval",
    "add_negative_keyword",
    "low",
    "“free plumbing advice” is people looking to fix it themselves.",
  ],
  [
    "applied",
    "raise_budget",
    "medium",
    "The campaign ran out of budget before noon on six of the last seven days.",
  ],
  ["applied", "add_negative_keyword", "low", "“plumber salary” is job seekers, not customers."],
  [
    "rejected",
    "raise_bid",
    "high",
    "Refused by a guardrail: the bid would rise more than 30% in one step.",
  ],
  ["applied", "add_sitelink", "low", "No sitelink sent people to the call-out prices page."],
  ["expired", "lower_bid", "low", "Nobody answered within 7 days, so the change went stale."],
  [
    "reverted",
    "pause_keyword",
    "medium",
    "Put back by the merchant: the keyword brought two calls the next day.",
  ],
  ["applied", "add_negative_keyword", "low", "“diy drain unblock” is people fixing it themselves."],
  ["applied", "lower_bid", "low", "Evening clicks cost 40% more and convert half as often."],
  ["rejected", "pause_keyword", "medium", "Refused by the merchant."],
  ["applied", "add_negative_keyword", "low", "“plumbing course” is students, not customers."],
];

const CHANGES: Change[] = KINDS.map(([status, kind, risk, reason], i) => ({
  id: `chg-${i}`,
  kind,
  status,
  risk,
  reason,
  created_at: at(i * 19 * HOUR + 3 * HOUR),
}));

const MERCHANT: Merchant = {
  organization_id: ROWS[0].organization_id,
  name: ROWS[0].name,
  created_at: at(62 * DAY),
  connection: {
    customer_id: ROWS[0].customer_id,
    customer_name: "Alpha Plumbing & Heating Ltd",
    currency: "EUR",
    account_status: "ENABLED",
  },
  changes: CHANGES,
};

const LOOKS: Look[] = [
  {
    at: at(0),
    looked_at: "merchant",
    level: "principal",
    account_id: "a-admin",
    who: "admin@ppcway.com",
  },
  {
    at: at(2 * HOUR),
    looked_at: "merchant",
    level: "support",
    account_id: "a-niamh",
    who: "niamh@ppcway.com",
  },
  {
    at: at(DAY + 4 * HOUR),
    looked_at: "merchant",
    level: "engineer",
    account_id: "a-ciaran",
    who: "ciaran@ppcway.com",
  },
  {
    at: at(6 * DAY),
    looked_at: "merchant",
    level: "principal",
    account_id: "a-admin",
    who: "admin@ppcway.com",
  },
];

/*
  The Campaigns screen's figures, shaped like a real two-campaign account: an
  old campaign spending steadily for a few leads, and a two-day-old one that
  has already brought more leads for far less. Totals are summed from the rows.
*/
function campaignDays(spend: number[], leads: number[]): AdsDay[] {
  return spend.map((cost, n) => ({
    date: new Date(Date.now() - (spend.length - n) * 86_400_000).toISOString().slice(0, 10),
    calls: 0,
    forms: leads[n] ?? 0,
    leads: leads[n] ?? 0,
    cost,
    clicks: Math.round(cost * 1.6),
    impressions: Math.round(cost * 40),
  }));
}
const OLD_SPEND = [
  4.9, 5.1, 4.8, 5.2, 5.0, 4.7, 5.3, 5.1, 4.9, 5.0, 5.2, 4.8, 5.1, 5.0, 4.9, 5.3, 5.0, 4.8, 5.2,
  5.1, 4.9, 5.0, 5.4, 5.1, 4.9, 5.2, 5.0, 5.1, 5.3, 6.31,
];
const OLD_LEADS = [
  0, 1, 0, 0, 1, 0, 0, 0, 1, 0, 0, 1, 0, 0, 0, 1, 0, 0, 1, 0, 0, 1, 0, 0, 2, 3, 4, 5, 4, 0,
];
const NEW_SPEND = [...Array(28).fill(0), 0.0, 20.48];
const NEW_LEADS = [...Array(29).fill(0), 38];
const OLD_DAYS = campaignDays(OLD_SPEND, OLD_LEADS);
const NEW_DAYS = campaignDays(NEW_SPEND, NEW_LEADS);
/* The builder's catalogue, as /v1/campaigns/start serves it (builder/kinds.py).
   A copy for the preview only; the live screen reads the API. */
const BUILDER_PREFILL: Prefill = {
  connected: true,
  currency: "USD",
  account_name: "PDFezy",
  may_launch: true,
  kinds: [
    {
      id: "at_their_place",
      label: "We go to our customers",
      examples: "Plumbers, cleaners, movers, repairs, landscaping",
      noun: "a business that goes to its customers",
      services_hint: "emergency plumber, end of tenancy cleaning…",
      win: "calls and enquiries",
      promises: [
        "free_quotes",
        "same_day",
        "emergency_callout",
        "open_all_hours",
        "licensed_insured",
        "family_owned",
      ],
      negatives: ["jobs", "careers", "salary", "diy", "how to"],
    },
    {
      id: "they_visit",
      label: "Customers come to us",
      examples: "Shops, salons, restaurants, clinics, gyms",
      noun: "a place customers visit",
      services_hint: "haircut and colour, dental check-up…",
      win: "visits and bookings",
      promises: ["book_online", "free_consultation", "open_all_hours", "family_owned"],
      negatives: ["jobs", "careers", "salary"],
    },
    {
      id: "professional",
      label: "We advise or do work for clients",
      examples: "Lawyers, accountants, consultants, agencies",
      noun: "a professional service",
      services_hint: "small business tax returns, immigration lawyer…",
      win: "enquiries",
      promises: ["free_consultation", "licensed_insured", "book_online", "family_owned"],
      negatives: ["jobs", "careers", "salary", "course", "template"],
    },
    {
      id: "online_shop",
      label: "We sell products online",
      examples: "Clothing, gifts, parts, home goods",
      noun: "an online shop",
      services_hint: "linen bedding, bike lights…",
      win: "sales",
      promises: ["free_shipping", "next_day", "money_back"],
      negatives: ["jobs", "careers", "salary", "wholesale", "used"],
    },
    {
      id: "software",
      label: "We offer software or an online tool",
      examples: "Apps, online tools, software for businesses",
      noun: "an online tool",
      services_hint: "pdf to word, invoicing software…",
      win: "sign-ups",
      promises: ["free_plan", "free_trial", "no_card", "money_back"],
      negatives: ["jobs", "careers", "salary", "crack", "torrent"],
    },
    {
      id: "other",
      label: "Something else",
      examples: "Charities, events, classes, anything not listed",
      noun: "a business",
      services_hint: "weekend pottery class, wedding photography…",
      win: "enquiries",
      promises: ["free_consultation", "book_online", "money_back"],
      negatives: ["jobs", "careers", "salary"],
    },
  ],
  promises: [
    { id: "free_quotes", label: "We give free quotes or estimates", short: "free quotes" },
    {
      id: "free_consultation",
      label: "The first consultation is free",
      short: "a free first consultation",
    },
    { id: "open_all_hours", label: "We're open 24 hours, 7 days a week", short: "24/7 opening" },
    { id: "same_day", label: "We offer same-day service", short: "same-day service" },
    { id: "emergency_callout", label: "We take emergency callouts", short: "emergency callouts" },
    {
      id: "licensed_insured",
      label: "We're licensed and insured",
      short: "licensed and insured work",
    },
    { id: "family_owned", label: "We're family-owned", short: "a family-owned business" },
    { id: "book_online", label: "Customers can book online", short: "online booking" },
    { id: "free_shipping", label: "Shipping is free", short: "free shipping" },
    { id: "next_day", label: "We deliver the next day", short: "next-day delivery" },
    { id: "money_back", label: "There's a money-back guarantee", short: "a money-back guarantee" },
    { id: "free_plan", label: "There's a free version", short: "a free version" },
    { id: "free_trial", label: "There's a free trial", short: "a free trial" },
    { id: "no_card", label: "No credit card needed to start", short: "no card to start" },
  ],
};

/* Where the stepper preview opens, by ?state=: each question, with the ones
   before it answered, as a real visit would have them. */
const ANSWERED_BUSINESS: StepperStart = {
  kind: "software",
  url: "https://pdfezy.com/",
  site: { name: "PDFezy", title: "PDFezy - Free Online PDF Converter & Editor" },
};
const ANSWERED_SELL: StepperStart = {
  ...ANSWERED_BUSINESS,
  themes: ["pdf to word", "compress pdf"],
};
const ANSWERED_WHO: StepperStart = {
  ...ANSWERED_SELL,
  places: [
    { resource: "geoTargetConstants/2616", name: "Poland", kind: "Country" },
    { resource: "geoTargetConstants/2642", name: "Romania", kind: "Country" },
  ],
};
const ANSWERED_ALL: StepperStart = {
  ...ANSWERED_WHO,
  promises: ["free_plan", "no_card"],
  budget: "20",
};
const STEPPER_STATES: Record<string, StepperStart | undefined> = {
  business: { ...ANSWERED_BUSINESS, at: 0 },
  sell: { ...ANSWERED_BUSINESS, at: 1 },
  who: { ...ANSWERED_SELL, at: 2 },
  promise: { ...ANSWERED_WHO, promises: ["free_plan", "no_card"], at: 3 },
  budget: { ...ANSWERED_ALL, at: 4 },
  check: { ...ANSWERED_ALL, at: 5 },
};

/* One campaign opened, with what Otto has for it: a search to exclude that is
   on offer, a refused ad found since the last nightly pass, and a change
   already made. Figures as the rules would write them. */
const PANEL: Detail = {
  read: true,
  campaign_id: "23251884470",
  name: "pdfezy",
  status: "ENABLED",
  currency: "USD",
  days: 30,
  leads: 26,
  cost: 153.76,
  clicks: 412,
  impressions: 9120,
  budget: 5,
  cost_per_lead: 5.91,
  lead_rate: 6.3,
  leads_before: 19,
  cost_before: 141.3,
  cost_per_lead_before: 7.44,
  lost_to_budget: 2,
  lost_to_rank: 31,
  impression_share: 54,
  series: campaignDays(
    [4, 5, 5, 4, 6, 5, 5, 4, 5, 6, 5, 5, 4, 5, 5, 6, 5, 4, 5, 5, 6, 5, 5, 5, 4, 6, 5, 5, 6, 5],
    [0, 1, 0, 1, 1, 0, 1, 0, 1, 1, 0, 1, 1, 0, 1, 1, 0, 1, 1, 1, 0, 1, 1, 2, 1, 1, 2, 1, 2, 3],
  ),
  keywords: [],
  terms: [],
  ads: [],
};

const ASOF = "2026-11-05T09:12:00+00:00";

const PANEL_OTTO: Suggestions = {
  trouble: "",
  inbox: {
    connected: true,
    notes: [
      {
        campaign: "23251884470",
        words:
          "PDFezy | Search loses 60% of its searches to its budget, while its leads cost 0.40 USD each against 2.69 USD for the rest of your account. Otto would suggest a bigger budget for it, but no daily budget ceiling is set for this account. Set one in Settings and Otto will offer it.",
      },
    ],
    cards: [
      {
        id: "8c2d4e6f-1a3b-4c5d-9e7f-0a1b2c3d4e5f",
        status: "awaiting_approval",
        answerable: true,
        expires_at: "2026-11-17T04:07:00+00:00",
        rule_id: "R7",
        rule_version: 1,
        kind: "decrease_daily_budget",
        title: "A campaign whose leads cost far more",
        about: "",
        target: { kind: "campaign", id: "23251884470", label: "pdfezy" },
        reason:
          "pdfezy's leads cost 2.69 USD each over the last 30 days, 6.7 times the 0.40 USD the rest of your account pays. Lowering its daily budget from 5.00 USD to 4.00 USD puts less money where leads cost most.",
        reason_from: "template",
        reason_is_ours: true,
        impact: {
          money_a_month: 30.4,
          currency: "USD",
          confidence: 0.98,
          words:
            "About 30.40 USD a month less spent there. Expect fewer leads from this campaign; the ones it still brings should cost about the same or less.",
          blocking: false,
        },
        evidence: [
          {
            id: "campaign_spend:campaign-23251884470",
            value: 137.2,
            unit: "money",
            as_of: ASOF,
            verdict: "real",
          },
          {
            id: "campaign_leads:campaign-23251884470",
            value: 51,
            unit: "count",
            as_of: ASOF,
            verdict: "real",
          },
          {
            id: "campaign_cost_per_lead:campaign-23251884470",
            value: 2.69,
            unit: "money",
            as_of: ASOF,
            verdict: "real",
          },
          {
            id: "rest_of_account_cost_per_lead:account",
            value: 0.4,
            unit: "money",
            as_of: ASOF,
            verdict: "real",
          },
        ],
        undo: "Set the daily budget back to 5.00 USD. Google uses the amount from the moment it is changed.",
        reversible: true,
        risk: "low",
        route: "owner",
        priority: 29.8,
        as_of: "2026-11-09",
        campaigns: ["23251884470"],
      },
      {
        id: "6b1f0c2e-1d4a-4e8b-9a51-6f2b7c9d0e11",
        status: "awaiting_approval",
        answerable: true,
        expires_at: "2026-11-12T04:07:00+00:00",
        rule_id: "R1",
        rule_version: 1,
        kind: "add_negative_keyword",
        title: "Money going on the wrong searches",
        about: "",
        target: { kind: "search_term", id: "a1", label: "pdf editor jobs" },
        reason:
          'People searching for "pdf editor jobs" clicked 104 times in the last 30 days and cost you 38.20 USD. None of them got in touch.',
        reason_from: "template",
        reason_is_ours: true,
        impact: {
          money_a_month: 38.2,
          currency: "USD",
          confidence: 0.62,
          words:
            "Excluding it stops about 38.20 USD a month going on this search. Some of that spend may move to better searches rather than disappear.",
          blocking: false,
        },
        evidence: [
          { id: "search_term_spend:a1", value: 38.2, unit: "money", as_of: ASOF, verdict: "real" },
          { id: "search_term_clicks:a1", value: 104, unit: "count", as_of: ASOF, verdict: "real" },
          { id: "search_term_leads:a1", value: 0, unit: "count", as_of: ASOF, verdict: "real" },
        ],
        undo: "Remove the negative keyword and this search can match your ads again from that moment. The clicks you did not pay for in between do not come back.",
        reversible: true,
        risk: "low",
        route: "owner",
        priority: 38.2,
        as_of: "2026-11-05",
        campaigns: ["23251884470"],
      },
      {
        id: "",
        status: "found",
        answerable: false,
        rule_id: "R4",
        rule_version: 1,
        kind: "pause_ad",
        title: "Ads Google has refused",
        about: "",
        target: { kind: "ad", id: "7", label: "Free PDF to Word converter" },
        reason:
          "Google has refused this ad, so it is not being shown to anybody. Your other ads in the group are still running.",
        reason_from: "template",
        reason_is_ours: true,
        impact: {
          money_a_month: 0,
          currency: "USD",
          confidence: 1,
          words:
            "Nothing is being lost. Pausing it keeps the account tidy and stops it looking live.",
          blocking: false,
        },
        evidence: [],
        undo: "Turn the ad back on. It stays refused until its wording is changed, so it still will not be shown.",
        reversible: true,
        risk: "low",
        route: "owner",
        priority: 0,
        as_of: "2026-11-05",
        campaigns: ["23251884470"],
      },
    ],
    changes: [
      {
        id: "0d9e8f7a-6b5c-4d3e-8f21-0a9b8c7d6e5f",
        status: "applied",
        rule_id: "R1",
        title: "Money going on the wrong searches",
        target: { kind: "search_term", id: "b2", label: "ilovepdf login" },
        words: "Made on 2 November. You can undo it until 2 December.",
        may_undo: true,
        undo: "",
        approved_at: "2026-11-02T10:00:00+00:00",
        applied_at: "2026-11-02T10:00:04+00:00",
        reverted_at: null,
        campaigns: ["23251884470"],
      },
    ],
    held_back: 0,
    used_this_week: 1,
    room_left: 9,
    nothing_because: "",
    ran: ["R1", "R4"],
    not_specified: ["R2", "R3", "R5"],
    ran_at: ASOF,
  },
};

const CAMPAIGNS: AdsSummary = {
  read: true,
  currency: "USD",
  days: 30,
  starts_on: OLD_DAYS[0].date,
  ends_on: OLD_DAYS[29].date,
  cost: 174.24,
  leads: 64,
  not_leads: 37,
  clicks: 312,
  impressions: 6970,
  cost_per_lead: 2.72,
  cost_before: 141.3,
  leads_before: 19,
  cost_per_lead_before: 7.44,
  month_cost: 61.4,
  month_day: 6,
  month_days: 30,
  monthly_budget: 760,
  series: OLD_DAYS.map((one, n) => ({
    ...one,
    cost: one.cost + NEW_DAYS[n].cost,
    leads: one.leads + NEW_DAYS[n].leads,
    forms: one.forms + NEW_DAYS[n].forms,
    clicks: one.clicks + NEW_DAYS[n].clicks,
  })),
  campaigns: [
    {
      campaign_id: "21",
      name: "pdfezy",
      status: "ENABLED",
      budget: 5,
      cost: 153.76,
      leads: 26,
      clicks: 246,
      cost_per_lead: 5.91,
      days: OLD_DAYS,
    },
    {
      campaign_id: "22",
      name: "PDFezy | Search | PDF Tools | GeoA-11 | PL RO CZ HU GR PT MY ZA PH TR MX",
      status: "ENABLED",
      budget: 20,
      cost: 20.48,
      leads: 38,
      clicks: 38,
      cost_per_lead: 0.54,
      starts_at: new Date(Date.now() - 86_400_000).toISOString().slice(0, 10) + " 00:00:00",
      days: NEW_DAYS,
    },
  ],
  needs: [
    {
      kind: "changed_in_google",
      label: "Changed in Google Ads",
      what: "The daily budget of pdfezy went from $4.00 to $5.00 on 3 November.",
      campaign_id: "21",
    },
  ],
};

/* A drafted campaign, as the builder writes one. */
const BUILT: Draft = {
  id: "00000000-0000-4000-8000-000000000001",
  status: "draft",
  sentence:
    "We'll show your ads to people in Poland and Romania who search for things like pdf to word and compress pdf. You'll spend up to 20.00 USD a day, and every click goes to https://pdfezy.com/.",
  missing: ["Google needs you to confirm the campaign is not political advertising in the EU."],
  outcome: null,
  campaign: "",
  created_at: null,
  plan: {
    name: "PDF tools",
    daily_budget: 20,
    currency: "USD",
    final_url: "https://pdfezy.com/",
    places: [
      { resource: "geoTargetConstants/2616", name: "Poland", kind: "Country" },
      { resource: "geoTargetConstants/2642", name: "Romania", kind: "Country" },
    ],
    language: { resource: "languageConstants/1000", name: "English" },
    bidding: "clicks",
    negatives: ["jobs", "careers", "salary"],
    ai_written: true,
    not_political: false,
    themes: [
      {
        name: "pdf to word",
        short: "",
        dropped: [],
        keywords: [
          {
            text: "pdf to word",
            monthly: 90500,
            competition: "LOW",
            top_of_page_low: 0.12,
            top_of_page_high: 0.61,
          },
          {
            text: "pdf to word converter",
            monthly: 33100,
            competition: "LOW",
            top_of_page_low: 0.1,
            top_of_page_high: 0.55,
          },
          {
            text: "convert pdf to word",
            monthly: 27100,
            competition: "LOW",
            top_of_page_low: 0.1,
            top_of_page_high: 0.5,
          },
          {
            text: "pdf to word online",
            monthly: 8100,
            competition: "LOW",
            top_of_page_low: 0.08,
            top_of_page_high: 0.42,
          },
        ],
        headlines: [
          "PDF to Word in Seconds",
          "Convert PDF Files Online",
          "Keep Your Layout Intact",
          "No Software to Install",
          "Works in Your Browser",
          "Edit PDFs as Word Files",
          "Fast and Simple PDF Tools",
          "Turn PDFs Into Documents",
          "Convert on Any Device",
          "PDFezy PDF Converter",
        ],
        descriptions: [
          "Turn any PDF into an editable Word file in your browser. Nothing to install.",
          "Upload, convert and download. Your formatting stays where it was.",
        ],
      },
      {
        name: "compress pdf",
        short: "",
        dropped: [],
        keywords: [
          {
            text: "compress pdf",
            monthly: 74000,
            competition: "LOW",
            top_of_page_low: 0.1,
            top_of_page_high: 0.48,
          },
          {
            text: "compress pdf file",
            monthly: 12100,
            competition: "LOW",
            top_of_page_low: 0.09,
            top_of_page_high: 0.4,
          },
        ],
        headlines: [
          "Compress PDF Files Online",
          "Smaller PDFs in Seconds",
          "Shrink a PDF for Email",
        ],
        descriptions: [
          "Make large PDFs small enough to email, in your browser.",
          "Pick a file, choose a size, download.",
        ],
      },
    ],
  },
};

/* ---------- the report, with figures shaped like PDFezy's ---------- */

// Sample data for measuring the design: thirty days ending 10 Nov.
const REPORT_LEADS = [
  9, 11, 8, 12, 10, 6, 5, 9, 12, 13, 11, 10, 7, 6, 10, 12, 14, 11, 9, 5, 4, 11, 13, 15, 12, 10, 6,
  7, 14, 10,
];
const REPORT_COST = [
  7.8, 8.4, 7.1, 9.2, 8.8, 5.6, 4.9, 8.1, 9.4, 9.9, 9.1, 8.6, 6.2, 5.8, 8.9, 9.6, 10.4, 9.0, 8.2,
  4.7, 4.1, 9.3, 10.1, 11.2, 9.8, 8.7, 5.9, 6.4, 10.6, 8.9,
];
const REPORT_SERIES: AdsDay[] = REPORT_LEADS.map((leads, i) => {
  const at = new Date(Date.UTC(2026, 9, 12 + i, 12));
  return {
    date: at.toISOString().slice(0, 10),
    calls: 0,
    forms: leads,
    leads,
    cost: REPORT_COST[i],
    clicks: Math.round(leads * 2.1),
    impressions: Math.round(leads * 38),
  };
});

const REPORT: ReportSaid = {
  read: true,
  currency: "USD",
  days: 30,
  held_days: 74,
  starts_on: "2026-10-12",
  ends_on: "2026-11-10",
  business: "PDFezy",
  customer_id: "2580586343",
  looked_at: new Date(Date.now() - 14 * 60_000).toISOString(),
  year_held: false,
  sentence: "You spent $246.70 and it brought 307 enquiries, which is $0.80 each.",
  figures: [
    {
      key: "leads",
      label: "Leads",
      kind: "count",
      value: 307,
      before: 271,
      year_ago: null,
      change: 13.3,
      verdict: "normal",
      words: "The number moved, but not by more than two periods of this size normally differ.",
      test: "two Poisson counts",
    },
    {
      key: "cost_per_lead",
      label: "Cost per lead",
      kind: "money",
      value: 0.8,
      before: 0.86,
      year_ago: null,
      change: -7,
      verdict: "normal",
      words: "Within the normal range.",
      test: "two Poisson counts",
    },
    {
      key: "cost",
      label: "Spend",
      kind: "money",
      value: 246.7,
      before: 233.1,
      year_ago: null,
      change: 5.8,
      verdict: "none",
      words: "Spend is a decision, not a measurement, so it gets no verdict.",
      test: "",
    },
    {
      key: "lead_rate",
      label: "Lead rate",
      kind: "rate",
      value: 47.6,
      before: 51.2,
      year_ago: null,
      change: -7,
      verdict: "real",
      words: "A real change.",
      test: "a two-proportion test",
    },
    {
      key: "clicks",
      label: "Clicks",
      kind: "count",
      value: 645,
      before: 529,
      year_ago: null,
      change: 21.9,
      verdict: "none",
      words: "How many people clicked, for context rather than judgement.",
      test: "",
    },
    {
      key: "click_rate",
      label: "Click rate",
      kind: "rate",
      value: 5.5,
      before: null,
      year_ago: null,
      change: null,
      verdict: "none",
      words: "Of the people shown your ad, the share who clicked it.",
      test: "",
    },
  ],
  campaigns: [
    {
      campaign_id: "12",
      name: "PDFezy | Search",
      status: "ENABLED",
      budget: 20,
      leads: 262,
      cost: 104.8,
      cost_per_lead: 0.4,
    },
    {
      campaign_id: "11",
      name: "pdfezy",
      status: "ENABLED",
      budget: 5,
      leads: 42,
      cost: 112.98,
      cost_per_lead: 2.69,
    },
    {
      campaign_id: "13",
      name: "ai pdf tools",
      status: "ENABLED",
      budget: 20,
      leads: 3,
      cost: 28.92,
      cost_per_lead: 9.64,
    },
  ],
  series: REPORT_SERIES,
  changes: [
    {
      id: "c1",
      status: "applied",
      title: "Stop paying for a search that brings nobody",
      target: { kind: "search_term", id: "a", label: "pdf to jpg converter offline" },
      words: "Made on 7 Nov. It can be undone until 7 Dec.",
      approved_at: "2026-11-07T10:02:00Z",
      applied_at: "2026-11-07T10:03:00Z",
      reverted_at: null,
    },
    {
      id: "c2",
      status: "applied",
      title: "Lower the budget of a campaign whose leads cost far more",
      target: { kind: "campaign", id: "11", label: "pdfezy" },
      words: "The daily budget of pdfezy is now 4.00. It can be undone until 4 Dec.",
      approved_at: "2026-11-04T09:12:00Z",
      applied_at: "2026-11-04T09:13:00Z",
      reverted_at: null,
    },
    {
      id: "c3",
      status: "reverted",
      title: "Stop paying for a search that brings nobody",
      target: { kind: "search_term", id: "b", label: "free pdf editor" },
      words: "Made on 29 Oct and undone by you on 30 Oct.",
      approved_at: "2026-10-29T15:40:00Z",
      applied_at: "2026-10-29T15:41:00Z",
      reverted_at: "2026-10-30T08:00:00Z",
    },
  ],
  changes_in_all: 3,
  definitions: [
    {
      term: "Lead",
      what: "Somebody who called you or sent a form, as counted by Google's conversion tracking. If that tracking is not set up, this number is zero however many times your phone rang.",
    },
    {
      term: "Cost per lead",
      what: "What you spent in the period divided by the leads it brought.",
    },
    {
      term: "Lead rate",
      what: "Of the people who clicked your ad, the share who then called or sent a form.",
    },
    { term: "Click rate", what: "Of the people who were shown your ad, the share who clicked it." },
    {
      term: "A real change",
      what: "The difference is bigger than the ordinary wobble between two periods of this size: it would happen by chance less than about one time in twenty. It is worth looking into.",
    },
    {
      term: "Within the normal range",
      what: "The number moved, but not by more than two periods of this size normally differ. Nothing has been proved either way, and acting on it is guesswork.",
    },
    {
      term: "Too little data to tell",
      what: "There were not enough leads or clicks in the two periods for any comparison to mean anything. More time, not more analysis, is what this needs.",
    },
    {
      term: "Why spend has no verdict",
      what: "Spend is a decision you made, not a measurement with noise in it. Asking whether a budget change is statistically significant answers a question nobody asked.",
    },
  ],
  shares: [],
};

export default async function Preview({
  searchParams,
}: {
  searchParams: Promise<{ screen?: string; state?: string; page?: string; show?: string }>;
}) {
  if (process.env.NODE_ENV === "production") notFound();
  const { screen, state, page, show } = await searchParams;
  const empty = state === "empty";
  const chrome: Chrome = { door: doorOf(PLATFORM), failures: empty ? 0 : FAULTS.length };

  switch (screen) {
    // The campaign builder, in the merchant portal's own skin.
    case "report":
      return (
        <div className="bg-pw-ground text-pw-ink flex min-h-dvh">
          <div
            aria-hidden
            className="border-pw-border bg-pw-card hidden w-[252px] shrink-0 border-r lg:block"
          />
          <div className="min-w-0 flex-1">
            <Header
              eyebrow="PDFezy, 12 Oct to 10 Nov 2026"
              title="Reports"
              right={<HeaderLink href="/reports/pdf">Download PDF</HeaderLink>}
            />
            <PwPage>
              <Report
                said={state === "empty" ? { ...REPORT, changes: [], changes_in_all: 0 } : REPORT}
                share={<span className="text-pw-ink-500 text-[14px]">(share controls)</span>}
              />
            </PwPage>
          </div>
        </div>
      );
    case "report-paper":
      return (
        <div className="bg-pw-ground min-h-dvh px-4 py-8 print:bg-white print:p-0">
          <div className="mx-auto max-w-[794px] shadow-[0_1px_3px_rgba(21,17,42,0.08),0_12px_32px_-12px_rgba(21,17,42,0.12)] print:max-w-none print:shadow-none">
            <ReportPaper
              said={state === "empty" ? { ...REPORT, changes: [], changes_in_all: 0 } : REPORT}
            />
          </div>
        </div>
      );
    case "team":
      // Settings' people and invitations: the role dropdowns are the thing to see.
      return (
        <div className="bg-pw-ground text-pw-ink min-h-dvh">
          <Header eyebrow="Settings" title="People" />
          <PwPage>
            <Team
              org={{
                id: "preview",
                name: "PDFezy",
                plan: "starter",
                currency: "CAD",
                your_role: "owner",
                can: ["view", "propose", "approve", "invite", "billing"],
                people: [
                  {
                    account_id: "a",
                    email: "abdulrazzaq0621@gmail.com",
                    name: "Abdul Razzaq",
                    role: "owner",
                    is_you: true,
                  },
                  {
                    account_id: "b",
                    email: "webalive.ca@gmail.com",
                    name: "Web Alive",
                    role: "admin",
                    is_you: false,
                  },
                ],
              }}
            />
          </PwPage>
        </div>
      );
    case "new-campaign":
      return (
        <div className="bg-pw-ground text-pw-ink flex min-h-dvh">
          <div
            aria-hidden
            className="border-pw-border bg-pw-card hidden w-[252px] shrink-0 border-r lg:block"
          />
          <div className="min-w-0 flex-1">
            <Header eyebrow="Campaigns" title="Start a new campaign." />
            <PwPage>
              <CampaignStepper
                key={state ?? "start"}
                prefill={BUILDER_PREFILL}
                site="pdfezy.com"
                trade=""
                start={STEPPER_STATES[state ?? ""]}
              />
            </PwPage>
          </div>
        </div>
      );
    case "campaigns":
      // A stand-in for the portal's 252px sidebar, so the canvas is the width
      // a merchant actually sees.
      return (
        <div className="bg-pw-ground text-pw-ink flex min-h-dvh">
          <div
            aria-hidden
            className="border-pw-border bg-pw-card hidden w-[252px] shrink-0 border-r lg:block"
          />
          <div className="min-w-0 flex-1">
            <Header
              eyebrow="Last 30 days · Oct 7 to Nov 5"
              title="Campaigns"
              right={<HeaderLink href="/campaigns/new">+ New campaign</HeaderLink>}
            />
            <PwPage>
              <CampaignList initial={CAMPAIGNS} days={30} />
            </PwPage>
          </div>
        </div>
      );
    case "campaign-suggestions":
    case "campaign-panel": {
      // The chosen campaign's panel, as it opens under the list.
      return (
        <div className="bg-pw-ground text-pw-ink flex min-h-dvh">
          <div
            aria-hidden
            className="border-pw-border bg-pw-card hidden w-[252px] shrink-0 border-r lg:block"
          />
          <div className="min-w-0 flex-1">
            <Header eyebrow="Last 30 days · Oct 7 to Nov 5" title="Campaigns" />
            <PwPage>
              <CampaignDetail
                detail={PANEL}
                suggestions={PANEL_OTTO}
                startOn={screen === "campaign-suggestions" ? "Suggestions" : "Overview"}
              />
            </PwPage>
          </div>
        </div>
      );
    }
    case "built-campaign":
      return (
        <div className="bg-pw-ground text-pw-ink flex min-h-dvh">
          <div
            aria-hidden
            className="border-pw-border bg-pw-card hidden w-[252px] shrink-0 border-r lg:block"
          />
          <div className="min-w-0 flex-1">
            <Header eyebrow="New campaign" title="Here's the campaign we built for you." />
            <PwPage>
              <DraftReview initial={BUILT} mayLaunch />
            </PwPage>
          </div>
        </div>
      );
    case "overview":
      return (
        <AdminOverview
          who={WHO}
          chrome={chrome}
          view={
            empty
              ? {
                  ...OVERVIEW,
                  healthy: true,
                  trouble: [],
                  figures: {
                    ...OVERVIEW.figures,
                    syncs_failed: fig("Syncs that failed", 0, "7d", -3),
                    syncs_stuck: fig("Syncs still running", 0, ""),
                    model_trouble: fig("Model calls that failed", 0, "7d", 0),
                  },
                  series: {
                    step: "day",
                    points: series().points.map((p) => ({ ...p, counts: {} })),
                  },
                }
              : OVERVIEW
          }
          platform={PLATFORM}
          faults={empty ? [] : FAULTS}
          trouble=""
          window="7d"
        />
      );
    case "merchant":
      return (
        <AdminMerchant
          who={WHO}
          chrome={chrome}
          merchant={MERCHANT}
          looks={LOOKS}
          quota={{ ...QUOTA[1], day: new Date().toISOString().slice(0, 10) }}
          stopped={false}
          all={false}
          trouble=""
        />
      );
    case "jobs": {
      const every = empty ? [] : runs();
      const at = /^\d+$/.test(page ?? "") ? Math.max(1, Number(page)) : 1;
      return (
        <AdminJobs
          who={WHO}
          chrome={chrome}
          runs={every.slice((at - 1) * 25, at * 25)}
          strip={every.slice(0, 100)}
          total={every.length}
          totals={{ all: every.length, failed: every.filter((r) => r.status === "failed").length }}
          page={at}
          per={25}
          trouble=""
          failedOnly={false}
        />
      );
    }
    case "errors":
      return (
        <AdminErrors
          who={WHO}
          chrome={chrome}
          faults={empty ? [] : FAULTS}
          trouble=""
          window="7d"
          ran={{
            modelCalls: OVERVIEW.figures.model_calls,
            syncsStuck: fig("Syncs still running", 0, ""),
          }}
        />
      );
    case "quota":
      return (
        <AdminQuota
          who={WHO}
          chrome={chrome}
          accounts={empty ? [] : QUOTA}
          names={Object.fromEntries(
            ROWS.filter((r) => r.customer_id).map((r) => [
              r.customer_id,
              { name: r.name, id: r.organization_id },
            ]),
          )}
          trouble=""
        />
      );
    case "platform":
      return <AdminPlatform who={WHO} chrome={chrome} view={PLATFORM} trouble="" />;
    case "staff":
      return <AdminStaff who={WHO} chrome={chrome} grants={GRANTS} trouble="" />;
    default: {
      const every = empty ? [] : [...ROWS, ...MORE];
      const tab = show === "attention" || show === "unconnected" ? show : "";
      const inTab =
        tab === "attention"
          ? every.filter((r) => r.trouble)
          : tab === "unconnected"
            ? every.filter((r) => !r.connected)
            : every;
      const atPage = /^\d+$/.test(page ?? "") ? Math.max(1, Number(page)) : 1;
      return (
        <AdminMerchants
          who={WHO}
          chrome={chrome}
          rows={inTab.slice((atPage - 1) * 25, atPage * 25)}
          total={inTab.length}
          counts={{
            all: every.length,
            attention: every.filter((r) => r.trouble).length,
            unconnected: every.filter((r) => !r.connected).length,
          }}
          page={atPage}
          per={25}
          trouble=""
          lookedFor=""
          show={tab}
        />
      );
    }
  }
}
