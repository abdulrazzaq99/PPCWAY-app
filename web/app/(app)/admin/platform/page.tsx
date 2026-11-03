import type { Metadata } from "next";
import { AdminSpec, rules } from "@/components/app/admin-views";
import { AdminPlatform } from "@/components/admin/live";
import { NotForYou } from "@/components/admin/staff-bar";
import { readPlatform, readWhoami } from "@/lib/admin-server";
import { ADMIN_PLATFORM_VIEWS } from "@/components/app/view-names";
import { pickView } from "@/lib/view-param";

export const metadata: Metadata = { title: "Platform · PPCWay admin" };

/* The settings that govern behaviour, read from the deployment itself. */
export default async function AdminPlatformPage({
  searchParams,
}: {
  searchParams: Promise<{ view?: string }>;
}) {
  const view = pickView(ADMIN_PLATFORM_VIEWS, (await searchParams).view);
  const { data: who, trouble: whoTrouble } = await readWhoami();
  if (!who?.staff) return <NotForYou trouble={whoTrouble} />;
  if (view === "rules") return <AdminSpec spec={rules} />;
  const { data, trouble } = await readPlatform();
  return <AdminPlatform who={who} view={data} trouble={trouble} />;
}
