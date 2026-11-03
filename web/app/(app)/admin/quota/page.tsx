import type { Metadata } from "next";
import { AdminQuota } from "@/components/admin/live";
import { NotForYou } from "@/components/admin/staff-bar";
import { readQuotaAll, readWhoami } from "@/lib/admin-server";

export const metadata: Metadata = { title: "Quota · PPCWay admin" };

/* How much of Google's daily allowance each account has used. */
export default async function AdminQuotaPage() {
  const { data: who, trouble: whoTrouble } = await readWhoami();
  if (!who?.staff) return <NotForYou trouble={whoTrouble} />;
  const { data, trouble } = await readQuotaAll();
  return <AdminQuota who={who} accounts={data?.accounts ?? []} trouble={trouble} />;
}
