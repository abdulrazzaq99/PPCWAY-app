import type { Metadata } from "next";
import { AdminJobs } from "@/components/admin/live";
import { NotForYou } from "@/components/admin/staff-bar";
import { readChrome, readJobs, readWhoami } from "@/lib/admin-server";

export const metadata: Metadata = { title: "Jobs · PPCWay internal" };

/* The scheduled reads of Google Ads, and which of them did not come back. */
export default async function AdminJobsPage({
  searchParams,
}: {
  searchParams: Promise<{ failed?: string }>;
}) {
  const failed = (await searchParams).failed === "1";
  const { data: who, trouble: whoTrouble } = await readWhoami();
  if (!who?.staff) return <NotForYou trouble={whoTrouble} />;
  const [{ data, trouble }, chrome] = await Promise.all([readJobs(failed), readChrome(who)]);
  return (
    <AdminJobs
      who={who}
      chrome={chrome}
      runs={data?.runs ?? []}
      trouble={trouble}
      failedOnly={failed}
    />
  );
}
