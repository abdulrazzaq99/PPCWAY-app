import { notFound } from "next/navigation";
import { AdminMerchants, AdminOverview } from "@/components/admin/live";
import type { Figure, MerchantRow, Overview, Whoami } from "@/lib/admin";

/*
  The merchant list with fixture rows, for measuring the design.

  It exists because the panel is behind sign-in, so neither a screenshot tool
  nor the inspector can reach a real one, and two rounds of design were done
  without anybody seeing the result. This renders the same components the real
  screen does, against data shaped like the real data, on localhost.

  Dev only. `notFound()` in any other environment, so it cannot be reached in
  production even by somebody who guesses the path.
*/
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
  levels: [],
  who: "admin@ppcway.com",
};

/* Names and figures shaped like the real ones: Irish trades, uneven numbers. */
const ROWS: MerchantRow[] = [
  {
    organization_id: "1",
    name: "Alpha Plumbing",
    customer_id: "2580586343",
    connected: true,
    account_status: "ENABLED",
    people: 3,
    waiting: 4,
    applied: 27,
    last_sync: new Date(Date.now() - 11 * 60000).toISOString(),
    trouble: "",
  },
  {
    organization_id: "2",
    name: "Beacon Roofing",
    customer_id: "7741029388",
    connected: true,
    account_status: "SUSPENDED",
    people: 2,
    waiting: 1,
    applied: 9,
    last_sync: new Date(Date.now() - 4 * 3600000).toISOString(),
    trouble: "Google says this account is suspended.",
  },
  {
    organization_id: "3",
    name: "Northside Dental",
    customer_id: "4420917755",
    connected: true,
    account_status: "",
    people: 5,
    waiting: 0,
    applied: 63,
    last_sync: new Date(Date.now() - 26 * 60000).toISOString(),
    trouble: "",
  },
  {
    organization_id: "4",
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
    organization_id: "5",
    name: "Byte9 Inc",
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
    organization_id: "6",
    name: "Hourihane Tiling",
    customer_id: "9013774820",
    connected: true,
    account_status: "ENABLED",
    people: 1,
    waiting: 12,
    applied: 4,
    last_sync: new Date(Date.now() - 3 * 86400000).toISOString(),
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
    words: `${value} ${label.toLowerCase()} in the last ${window}`,
  };
}

const OVERVIEW: Overview = {
  at: new Date().toISOString(),
  window: "7d",
  healthy: false,
  trouble: [
    "2 syncs started over an hour ago and never finished. Those accounts are working from old figures.",
    "4 model calls came back with nothing in the last 7d.",
  ],
  writes: {
    anything_can_be_written: false,
    words:
      "PPCWay is not writing to any Google Ads account. That is this deployment's setting, not a switch, and it takes a deploy to change.",
    stops: [],
  },
  figures: {
    merchants: fig("Businesses", 6, ""),
    connected: fig("Connected to Google Ads", 4, ""),
    people: fig("People", 14, ""),
    proposed: fig("Changes proposed", 148, "7d", 31),
    waiting: fig("Waiting for a merchant", 17, ""),
    applied: fig("Changes applied", 103, "7d"),
    reverted: fig("Changes put back", 6, "7d"),
    refused: fig("Refused by a guardrail", 22, "7d"),
    model_calls: fig("Model calls", 412, "7d", 88),
    model_tokens: fig("Tokens used", 1_284_900, "7d"),
    model_trouble: fig("Model calls that failed", 4, "7d", 4),
    syncs_failed: fig("Syncs that failed", 3, "7d", -2),
    syncs_stuck: fig("Syncs still running", 2, ""),
  },
};

export default async function Preview({
  searchParams,
}: {
  searchParams: Promise<{ screen?: string }>;
}) {
  if (process.env.NODE_ENV === "production") notFound();
  const { screen } = await searchParams;
  if (screen === "overview") {
    return <AdminOverview who={WHO} view={OVERVIEW} trouble="" />;
  }
  return <AdminMerchants who={WHO} rows={ROWS} trouble="" lookedFor="" />;
}
