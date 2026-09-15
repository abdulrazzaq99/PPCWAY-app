import { AdminSpec, Merchants, changeLog, merchantDetail } from "@/components/app/admin-views";
import { ADMIN_MERCHANT_VIEWS } from "@/components/app/view-names";
import { pickView } from "@/lib/view-param";

export default async function AdminMerchants({
  searchParams,
}: {
  searchParams: Promise<{ view?: string }>;
}) {
  const view = pickView(ADMIN_MERCHANT_VIEWS, (await searchParams).view);
  if (view === "merchant") return <AdminSpec spec={merchantDetail} />;
  if (view === "change-log") return <AdminSpec spec={changeLog} />;
  return <Merchants />;
}
