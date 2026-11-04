import type { Metadata } from "next";
import { AdminErrors } from "@/components/admin/live";
import { NotForYou } from "@/components/admin/staff-bar";
import { readChrome, readErrors, readOverview, readWhoami } from "@/lib/admin-server";

export const metadata: Metadata = { title: "Failures · PPCWay internal" };

/* Jobs and model calls that failed, in one list. */
export default async function AdminErrorsPage({
  searchParams,
}: {
  searchParams: Promise<{ window?: string }>;
}) {
  const asked = (await searchParams).window ?? "7d";
  const window = ["today", "7d", "30d", "90d"].includes(asked) ? asked : "7d";
  const { data: who, trouble: whoTrouble } = await readWhoami();
  if (!who?.staff) return <NotForYou trouble={whoTrouble} />;
  const [{ data, trouble }, chrome, overview] = await Promise.all([
    readErrors(window),
    readChrome(who),
    /* What ran in the window, so an empty list can say it is a quiet one. */
    who.may.includes("read_platform") ? readOverview(window) : Promise.resolve(null),
  ]);
  const figures = overview?.data?.figures;
  return (
    <AdminErrors
      who={who}
      chrome={chrome}
      faults={data?.faults ?? []}
      trouble={trouble}
      window={window}
      ran={
        figures ? { modelCalls: figures.model_calls, syncsStuck: figures.syncs_stuck } : undefined
      }
    />
  );
}
