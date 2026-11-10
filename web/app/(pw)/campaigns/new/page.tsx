import type { Metadata } from "next";
import { CampaignStepper } from "@/components/pw/campaign-stepper";
import { Header, HeaderLink, PwPage } from "@/components/pw/shell";
import type { Prefill } from "@/lib/builder";
import { ask } from "@/lib/pw-fetch";

export const metadata: Metadata = { title: "New campaign · PPCway" };

/*
  Start a new campaign, as a stepper that works for any kind of business
  (`components/pw/campaign-stepper.tsx`). The account's currency, the kinds
  of business and their promises, and the website the ads already use are
  filled in before anybody types; the rest is the merchant's to say.
*/
export default async function NewCampaignPage() {
  const [prefill, business] = await Promise.all([
    ask<Prefill>("/v1/campaigns/start", { connected: false }),
    ask<{ site?: string; trade?: string }>("/v1/ads/business", {}),
  ]);
  return (
    <>
      <Header
        eyebrow="Campaigns"
        title="Start a new campaign."
        right={<HeaderLink href="/campaigns">Back to campaigns</HeaderLink>}
      />
      <PwPage>
        <CampaignStepper
          prefill={prefill}
          site={business.site ?? ""}
          trade={business.trade ?? ""}
        />
      </PwPage>
    </>
  );
}
