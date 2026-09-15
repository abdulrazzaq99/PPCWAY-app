import { WebsiteView } from "@/components/onboarding/website-views";
import { WEBSITE_VIEWS } from "@/components/onboarding/view-names";
import { pickView } from "@/lib/view-param";

export default async function WebsiteStep({
  searchParams,
}: {
  searchParams: Promise<{ view?: string }>;
}) {
  const { view } = await searchParams;
  return <WebsiteView view={pickView(WEBSITE_VIEWS, view)} />;
}
