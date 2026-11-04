import type { Metadata } from "next";
import { AdminQuota } from "@/components/admin/live";
import { NotForYou } from "@/components/admin/staff-bar";
import { readChrome, readMerchants, readQuotaAll, readWhoami } from "@/lib/admin-server";

export const metadata: Metadata = { title: "Quota · PPCWay internal" };

/*
  How much of Google's daily allowance each account has used.

  The quota rows carry only a Google Ads id, so the business list is read too
  and each id is shown with the name a person would recognise. That read is a
  look through the customer list and is recorded as one, which is honest: this
  screen shows the list's names.
*/
export default async function AdminQuotaPage() {
  const { data: who, trouble: whoTrouble } = await readWhoami();
  if (!who?.staff) return <NotForYou trouble={whoTrouble} />;
  const [{ data, trouble }, list, chrome] = await Promise.all([
    readQuotaAll(),
    who.may.includes("read_merchant") ? readMerchants("") : Promise.resolve(null),
    readChrome(who),
  ]);
  const names: Record<string, { name: string; id: string }> = {};
  for (const one of list?.data?.merchants ?? []) {
    if (one.customer_id) names[one.customer_id] = { name: one.name, id: one.organization_id };
  }
  return (
    <AdminQuota
      who={who}
      chrome={chrome}
      accounts={data?.accounts ?? []}
      names={names}
      trouble={trouble}
    />
  );
}
