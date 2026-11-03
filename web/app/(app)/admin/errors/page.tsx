import type { Metadata } from "next";
import { AdminErrors } from "@/components/admin/live";
import { NotForYou } from "@/components/admin/staff-bar";
import { readErrors, readWhoami } from "@/lib/admin-server";

export const metadata: Metadata = { title: "Errors · PPCWay admin" };

/* Jobs and model calls that failed, in one list. */
export default async function AdminErrorsPage({
  searchParams,
}: {
  searchParams: Promise<{ window?: string }>;
}) {
  const window = (await searchParams).window ?? "7d";
  const { data: who, trouble: whoTrouble } = await readWhoami();
  if (!who?.staff) return <NotForYou trouble={whoTrouble} />;
  const { data, trouble } = await readErrors(window);
  return <AdminErrors who={who} faults={data?.faults ?? []} trouble={trouble} window={window} />;
}
