import { CallsView } from "@/components/onboarding/calls-views";
import { CALLS_VIEWS } from "@/components/onboarding/view-names";
import { pickView } from "@/lib/view-param";

export default async function CallsStep({
  searchParams,
}: {
  searchParams: Promise<{ view?: string }>;
}) {
  const { view } = await searchParams;
  return <CallsView view={pickView(CALLS_VIEWS, view)} />;
}
