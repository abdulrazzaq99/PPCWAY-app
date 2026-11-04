import type { Metadata } from "next";
import { AdminSpec, aiQuality } from "@/components/app/admin-views";
import { AdminOverview } from "@/components/admin/live";
import { NotForYou } from "@/components/admin/staff-bar";
import { ADMIN_METRIC_VIEWS } from "@/components/app/view-names";
import { doorOf } from "@/lib/admin";
import { readChrome, readErrors, readOverview, readPlatform, readWhoami } from "@/lib/admin-server";
import { pickView } from "@/lib/view-param";

export const metadata: Metadata = { title: "Overview · PPCWay internal" };

/*
  The platform at a glance. The window is a query parameter so a link can
  carry it, and an unknown one falls back rather than taking the panel down: a
  URL somebody typed must not break the screen they typed it on.

  The figures, the settings and the failures are read together, because the
  screen shows them together and a stale one beside a fresh one would be two
  different moments presented as one.
*/
export default async function AdminMetricsPage({
  searchParams,
}: {
  searchParams: Promise<{ view?: string; window?: string }>;
}) {
  const asked = await searchParams;
  const view = pickView(ADMIN_METRIC_VIEWS, asked.view);
  const { data: who, trouble: whoTrouble } = await readWhoami();
  if (!who?.staff) return <NotForYou trouble={whoTrouble} />;
  if (view === "ai") return <AdminSpec spec={aiQuality} />;

  const window = ["today", "7d", "30d", "90d"].includes(asked.window ?? "")
    ? (asked.window as string)
    : "7d";
  const [overview, platform, errors, chrome] = await Promise.all([
    readOverview(window),
    readPlatform(),
    who.may.includes("read_errors") ? readErrors(window) : Promise.resolve(null),
    readChrome(who, { door: false }),
  ]);
  return (
    <AdminOverview
      who={who}
      chrome={{ ...chrome, door: doorOf(platform.data) ?? chrome.door }}
      view={overview.data}
      platform={platform.data}
      faults={errors?.data?.faults ?? null}
      trouble={overview.trouble}
      window={window}
    />
  );
}
