import { OverviewView } from "@/components/app/overview-views";
import { OVERVIEW_VIEWS } from "@/components/app/view-names";
import { pickView } from "@/lib/view-param";

/* Overview has thirteen drawn states. `?view=` picks one until the backend drives it. */
export default async function OverviewPage({
  searchParams,
}: {
  searchParams: Promise<{ view?: string }>;
}) {
  const { view } = await searchParams;
  return <OverviewView view={pickView(OVERVIEW_VIEWS, view)} />;
}
