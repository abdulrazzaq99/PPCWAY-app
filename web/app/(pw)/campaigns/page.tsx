import type { Metadata } from "next";
import { CampaignList } from "@/components/pw/campaigns";
import { Header, HeaderLink, PwPage } from "@/components/pw/shell";
import { ask } from "@/lib/pw-fetch";

export const metadata: Metadata = { title: "Campaigns · PPCway" };

export default async function CampaignsPage() {
  const summary = await ask("/v1/ads/summary?days=30", { read: false as const });
  const today = new Date();
  const from = new Date(today.getTime() - 29 * 86_400_000);
  const span = `${from.toLocaleDateString(undefined, { month: "short", day: "numeric" })} to ${today.toLocaleDateString(undefined, { month: "short", day: "numeric" })}`;

  return (
    <>
      <Header
        eyebrow={`Last 30 days · ${span}`}
        title="Campaigns"
        right={<HeaderLink href="/campaigns/new">+ New campaign</HeaderLink>}
      />
      <PwPage>
        <CampaignList initial={summary} days={30} />
      </PwPage>
    </>
  );
}
