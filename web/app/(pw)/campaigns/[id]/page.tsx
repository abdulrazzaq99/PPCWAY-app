import type { Metadata } from "next";
import { CampaignDetail, type Detail } from "@/components/pw/campaign-detail";
import { Header, PwPage } from "@/components/pw/shell";
import { ask } from "@/lib/pw-fetch";

export const metadata: Metadata = { title: "Campaign · PPCway" };

const EMPTY: Detail = {
  read: false,
  trouble: "We could not read that campaign.",
  campaign_id: "",
  name: "",
  status: "",
  currency: "",
  days: 30,
  leads: 0,
  cost: 0,
  clicks: 0,
  impressions: 0,
  budget: 0,
  cost_per_lead: 0,
  lead_rate: 0,
  lost_to_budget: 0,
  lost_to_rank: 0,
  impression_share: 0,
  keywords: [],
  terms: [],
  ads: [],
};

export default async function CampaignPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const detail = await ask<Detail>(`/v1/ads/campaigns/${encodeURIComponent(id)}?days=30`, EMPTY);
  return (
    <>
      <Header eyebrow="Campaign" title={detail.name || "Campaign"} />
      <PwPage>
        <CampaignDetail detail={detail} />
      </PwPage>
    </>
  );
}
