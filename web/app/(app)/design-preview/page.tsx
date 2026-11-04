import { notFound } from "next/navigation";
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
      "PPCWay is not writing to any Google Ads account. That is this deployment's setting, not a switch, and it takes a deploy to change.",
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
      changeable: false,
      why_not: "This comes from the deployment's settings; it takes a deploy to change.",
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

export default async function Preview({
  searchParams,
}: {
  searchParams: Promise<{ screen?: string; state?: string; page?: string }>;
}) {
  if (process.env.NODE_ENV === "production") notFound();
  const { screen, state, page } = await searchParams;
  const empty = state === "empty";
  const chrome: Chrome = { door: doorOf(PLATFORM), failures: empty ? 0 : FAULTS.length };

  switch (screen) {
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
    default:
      return (
        <AdminMerchants
          who={WHO}
          chrome={chrome}
          rows={empty ? [] : ROWS}
          trouble=""
          lookedFor=""
          show=""
        />
      );
  }
}
