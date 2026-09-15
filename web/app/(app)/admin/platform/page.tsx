import { AdminSpec, platform, rules } from "@/components/app/admin-views";
import { ADMIN_PLATFORM_VIEWS } from "@/components/app/view-names";
import { pickView } from "@/lib/view-param";

export default async function Platform({
  searchParams,
}: {
  searchParams: Promise<{ view?: string }>;
}) {
  const view = pickView(ADMIN_PLATFORM_VIEWS, (await searchParams).view);
  return <AdminSpec spec={view === "rules" ? rules : platform} />;
}
