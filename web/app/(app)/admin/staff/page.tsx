import type { Metadata } from "next";
import { AdminStaff } from "@/components/admin/live";
import { NotForYou } from "@/components/admin/staff-bar";
import { readChrome, readGrants, readWhoami } from "@/lib/admin-server";

export const metadata: Metadata = { title: "Access · PPCWay internal" };

/*
  Who has internal access, and every grant and withdrawal there has ever been.
  Only principal access can read this: knowing who can see what is itself
  something not everybody needs.
*/
export default async function AdminStaffPage() {
  const { data: who, trouble: whoTrouble } = await readWhoami();
  if (!who?.staff) return <NotForYou trouble={whoTrouble} />;
  const [{ data, trouble }, chrome] = await Promise.all([readGrants(), readChrome(who)]);
  return <AdminStaff who={who} chrome={chrome} grants={data?.grants ?? []} trouble={trouble} />;
}
