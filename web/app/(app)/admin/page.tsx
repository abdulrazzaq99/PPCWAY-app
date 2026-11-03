import type { Metadata } from "next";
import { AdminSpec, changeLog, merchantDetail } from "@/components/app/admin-views";
import { NotForYou } from "@/components/admin/staff-bar";
import { AdminMerchants } from "@/components/admin/live";
import { readMerchants, readWhoami } from "@/lib/admin-server";

export const metadata: Metadata = { title: "Merchants · PPCWay admin" };

/*
  The internal merchant list, with the real businesses in it.

  `whoami` is asked first and answers 200 with `staff: false` for everybody who
  is not staff, so a merchant who followed a link gets a plain sentence rather
  than a console full of errors. The other two views are still the Figma
  mockups: they are next, and leaving them visibly static is more honest than
  wiring half of each.
*/
export default async function AdminMerchantsPage({
  searchParams,
}: {
  searchParams: Promise<{ view?: string; q?: string; id?: string }>;
}) {
  const { view, q } = await searchParams;
  const { data: who, trouble: whoTrouble } = await readWhoami();

  if (!who?.staff) return <NotForYou trouble={whoTrouble} />;

  if (view === "merchant") return <AdminSpec spec={merchantDetail} />;
  if (view === "change-log") return <AdminSpec spec={changeLog} />;

  const { data, trouble } = await readMerchants(q ?? "");
  return (
    <AdminMerchants who={who} rows={data?.merchants ?? []} trouble={trouble} lookedFor={q ?? ""} />
  );
}
