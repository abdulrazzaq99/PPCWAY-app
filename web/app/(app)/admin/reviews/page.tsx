import { AdminSpec, accessRequest, blockList, categories } from "@/components/app/admin-views";
import { ADMIN_REVIEW_VIEWS } from "@/components/app/view-names";
import { pickView } from "@/lib/view-param";

export default async function Reviews({
  searchParams,
}: {
  searchParams: Promise<{ view?: string }>;
}) {
  const view = pickView(ADMIN_REVIEW_VIEWS, (await searchParams).view);
  return (
    <AdminSpec
      spec={view === "access" ? accessRequest : view === "block-list" ? blockList : categories}
    />
  );
}
