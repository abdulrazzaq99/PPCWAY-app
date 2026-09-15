import { CampaignsView } from "@/components/app/campaigns";
import { CAMPAIGN_VIEWS } from "@/components/app/view-names";
import { pickView } from "@/lib/view-param";

export default async function CampaignsPage({
  searchParams,
}: {
  searchParams: Promise<{ view?: string }>;
}) {
  const { view } = await searchParams;
  return <CampaignsView view={pickView(CAMPAIGN_VIEWS, view)} />;
}
