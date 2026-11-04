import type { Metadata } from "next";
import { AdminSpec, changeLog } from "@/components/app/admin-views";
import { AdminMerchant, AdminMerchants } from "@/components/admin/live";
import { NotForYou } from "@/components/admin/staff-bar";
import { doorOf } from "@/lib/admin";
import {
  readChrome,
  readMerchant,
  readMerchants,
  readPlatform,
  readQuota,
  readWhoami,
  readWhoLooked,
} from "@/lib/admin-server";

export const metadata: Metadata = { title: "Merchants · PPCWay internal" };

/*
  The merchant list, and one merchant's own screen.

  `whoami` is asked first and answers 200 with `staff: false` for everybody who
  is not staff, so a merchant who followed a link gets a plain sentence rather
  than a console full of errors.

  One merchant is read before who looked at it, not beside it: opening the
  business is what writes the record, so reading the two at once could show a
  list that does not include the visit being made. And the list endpoint is
  not called from a merchant's screen at all, because calling it writes a
  "looked through the customer list" record that nobody made.
*/
export default async function AdminMerchantsPage({
  searchParams,
}: {
  searchParams: Promise<{ view?: string; q?: string; id?: string; show?: string; all?: string }>;
}) {
  const { view, q, id, show, all } = await searchParams;
  const { data: who, trouble: whoTrouble } = await readWhoami();
  if (!who?.staff) return <NotForYou trouble={whoTrouble} />;

  if (view === "merchant" && id) {
    const { data: merchant, trouble } = await readMerchant(id);
    const customer = merchant?.connection?.customer_id ?? "";
    const reads = who.may.includes("read_platform");
    const [looks, platform, quota, chrome] = await Promise.all([
      merchant ? readWhoLooked(id) : Promise.resolve(null),
      reads ? readPlatform() : Promise.resolve(null),
      merchant && customer && reads ? readQuota(customer) : Promise.resolve(null),
      readChrome(who, { door: !reads }),
    ]);
    return (
      <AdminMerchant
        who={who}
        chrome={{ ...chrome, door: doorOf(platform?.data) ?? chrome.door }}
        merchant={merchant}
        looks={looks?.data?.looks ?? []}
        quota={quota?.data ?? null}
        stopped={Boolean(
          customer && platform?.data?.stops.some((one) => one.customer_id === customer),
        )}
        all={all === "1"}
        trouble={trouble}
      />
    );
  }
  if (view === "change-log") return <AdminSpec spec={changeLog} />;

  const [{ data, trouble }, chrome] = await Promise.all([readMerchants(q ?? ""), readChrome(who)]);
  return (
    <AdminMerchants
      who={who}
      chrome={chrome}
      rows={data?.merchants ?? []}
      trouble={trouble}
      lookedFor={q ?? ""}
      show={show === "attention" || show === "unconnected" ? show : ""}
    />
  );
}
