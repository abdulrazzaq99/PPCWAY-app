import type { Metadata } from "next";
import { CampaignList } from "@/components/pw/campaigns";
import { Header, PwPage } from "@/components/pw/shell";
import { ask } from "@/lib/pw-fetch";

export const metadata: Metadata = { title: "Campaigns · PPCway" };

export default async function CampaignsPage() {
  const summary = await ask("/v1/ads/summary?days=30", { read: false as const });
  return (
    <>
      <Header eyebrow="Your account, read from Google Ads" title="Campaigns" />
      <PwPage>
        <CampaignList initial={summary} />
      </PwPage>
    </>
  );
}
