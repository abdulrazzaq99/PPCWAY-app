import { notFound } from "next/navigation";
import { AdminMerchants } from "@/components/admin/live";
import type { MerchantRow, Whoami } from "@/lib/admin";

/*
  The merchant list with fixture rows, for measuring the design.

  It exists because the panel is behind sign-in, so neither a screenshot tool
  nor the inspector can reach a real one, and two rounds of design were done
  without anybody seeing the result. This renders the same components the real
  screen does, against data shaped like the real data, on localhost.

  Dev only. `notFound()` in any other environment, so it cannot be reached in
  production even by somebody who guesses the path.
*/
export const dynamic = "force-static";

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

export default function Preview() {
  if (process.env.NODE_ENV === "production") notFound();
  return <AdminMerchants who={WHO} rows={ROWS} trouble="" lookedFor="" />;
}
