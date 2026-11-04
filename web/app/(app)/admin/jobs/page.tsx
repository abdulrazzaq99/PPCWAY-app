import type { Metadata } from "next";
import { AdminJobs } from "@/components/admin/live";
import { NotForYou } from "@/components/admin/staff-bar";
import { readChrome, readJobs, readWhoami } from "@/lib/admin-server";

export const metadata: Metadata = { title: "Jobs · PPCWay internal" };

/* Twenty-five runs a page: about two screens of rows, with the pager in reach. */
const PER = 25;

/*
  The scheduled reads of Google Ads, a page at a time.

  Four reads, side by side: the page asked for; the latest hundred for the
  run-by-run strip, which shows the platform now whichever page is open; and
  a count for the other tab, so both tabs say how many they hold. A page
  number that is not a whole number above zero is page 1: a URL somebody typed
  must not break the screen they typed it on.

  An older backend sends no total and ignores the page. Then the hundred it
  does send are paged here, which is honest about what can be seen.
*/
export default async function AdminJobsPage({
  searchParams,
}: {
  searchParams: Promise<{ failed?: string; page?: string }>;
}) {
  const asked = await searchParams;
  const failed = asked.failed === "1";
  const page = /^\d+$/.test(asked.page ?? "") ? Math.max(1, Number(asked.page)) : 1;
  const { data: who, trouble: whoTrouble } = await readWhoami();
  if (!who?.staff) return <NotForYou trouble={whoTrouble} />;

  const [rows, strip, other, chrome] = await Promise.all([
    readJobs(failed, { limit: PER, offset: (page - 1) * PER }),
    failed ? Promise.resolve(null) : readJobs(false, { limit: 100, offset: 0 }),
    readJobs(!failed, { limit: 1, offset: 0 }),
    readChrome(who),
  ]);

  const paged = typeof rows.data?.total === "number";
  const runs = paged
    ? (rows.data?.runs ?? [])
    : (rows.data?.runs ?? []).slice((page - 1) * PER, page * PER);
  const total = paged ? (rows.data?.total ?? 0) : (rows.data?.runs.length ?? 0);

  return (
    <AdminJobs
      who={who}
      chrome={chrome}
      runs={runs}
      strip={strip?.data?.runs ?? null}
      total={total}
      totals={{
        all: failed ? other.data?.total : total,
        failed: failed ? total : other.data?.total,
      }}
      page={page}
      per={PER}
      trouble={rows.trouble}
      failedOnly={failed}
    />
  );
}
