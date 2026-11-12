import type { Metadata } from "next";
import { NewCampaign } from "@/components/pw/create/new-campaign";
import { Header, HeaderLink, PwPage } from "@/components/pw/shell";
import type { Setup } from "@/lib/creation";
import { ask } from "@/lib/pw-fetch";

export const metadata: Metadata = { title: "New campaign · PPCway" };

/*
  Google's "New campaign" page (components/pw/create/new-campaign.tsx): the
  objective, the account's conversion goals, the campaign type, the ways to
  reach the goal and the name. The client asked on 12 November for creation
  to follow Google's flow exactly; the research is in
  docs/reference/campaign-creation/.
*/
const OFFLINE: Setup = {
  connected: false,
  objectives: {} as Setup["objectives"],
  types: {},
  steps: {},
  step_labels: {},
  built: [],
};

export default async function NewCampaignPage() {
  const [setup, business] = await Promise.all([
    ask<Setup>("/v1/campaigns/setup", OFFLINE),
    ask<{ site?: string }>("/v1/ads/business", {}),
  ]);
  return (
    <>
      <Header
        eyebrow="Campaigns"
        title="New campaign"
        right={<HeaderLink href="/campaigns">Back to campaigns</HeaderLink>}
      />
      <PwPage>
        <NewCampaign setup={setup} website={business.site ?? ""} />
      </PwPage>
    </>
  );
}
