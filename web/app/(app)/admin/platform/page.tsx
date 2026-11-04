import type { Metadata } from "next";
import { AdminSpec, rules } from "@/components/app/admin-views";
import { AdminPlatform } from "@/components/admin/live";
import { NotForYou } from "@/components/admin/staff-bar";
import { ADMIN_PLATFORM_VIEWS } from "@/components/app/view-names";
import { doorOf } from "@/lib/admin";
import { readChrome, readPlatform, readWhoami } from "@/lib/admin-server";
import { pickView } from "@/lib/view-param";

export const metadata: Metadata = { title: "Settings · PPCWay internal" };

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
  const [{ data, trouble }, chrome] = await Promise.all([
    readPlatform(),
    readChrome(who, { door: false }),
  ]);
  return (
    <AdminPlatform
      who={who}
      chrome={{ ...chrome, door: doorOf(data) ?? chrome.door }}
      view={data}
      trouble={trouble}
    />
  );
}
