import { BusinessView } from "@/components/onboarding/business-views";
import { BUSINESS_VIEWS } from "@/components/onboarding/view-names";
import { pickView } from "@/lib/view-param";

export default async function BusinessStep({
  searchParams,
}: {
  searchParams: Promise<{ view?: string }>;
}) {
  const { view } = await searchParams;
  return <BusinessView view={pickView(BUSINESS_VIEWS, view)} />;
}
