import type { Metadata } from "next";
import { AdminSpec, aiQuality } from "@/components/app/admin-views";
import { AdminOverview } from "@/components/admin/live";
import { NotForYou } from "@/components/admin/staff-bar";
import { readOverview, readWhoami } from "@/lib/admin-server";
import { ADMIN_METRIC_VIEWS } from "@/components/app/view-names";
import { pickView } from "@/lib/view-param";

export const metadata: Metadata = { title: "Overview · PPCWay admin" };

/*
  Every figure the platform can be counted by. The window is a query parameter
  so a link can carry it, and an unknown one falls back rather than taking the
  panel down -- a URL somebody typed must not break the screen they typed it on.
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
  const { data, trouble } = await readOverview(asked.window ?? "7d");
  return <AdminOverview who={who} view={data} trouble={trouble} />;
}
