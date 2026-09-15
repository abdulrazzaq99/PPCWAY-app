import { AdminSpec, aiQuality, metrics } from "@/components/app/admin-views";
import { ADMIN_METRIC_VIEWS } from "@/components/app/view-names";
import { pickView } from "@/lib/view-param";

export default async function Metrics({
  searchParams,
}: {
  searchParams: Promise<{ view?: string }>;
}) {
  const view = pickView(ADMIN_METRIC_VIEWS, (await searchParams).view);
  return <AdminSpec spec={view === "ai" ? aiQuality : metrics} />;
}
