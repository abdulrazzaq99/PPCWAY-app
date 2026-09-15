import { ActivityView } from "@/components/app/activity-views";
import { ACTIVITY_VIEWS } from "@/components/app/view-names";
import { pickView } from "@/lib/view-param";

export default async function ActivityPage({
  searchParams,
}: {
  searchParams: Promise<{ view?: string }>;
}) {
  const { view } = await searchParams;
  return <ActivityView view={pickView(ACTIVITY_VIEWS, view)} />;
}
