import type { Metadata } from "next";
import { CampaignList } from "@/components/pw/campaigns";
import { Header, HeaderLink, PwPage } from "@/components/pw/shell";
import type { AdsSummary } from "@/lib/ads";
import { ask } from "@/lib/pw-fetch";

export const metadata: Metadata = { title: "Campaigns · PPCway" };

/** "Sep 20 to Oct 19", from the dates the figures actually cover. */
function span(summary: AdsSummary): string {
  const show = (iso: string) =>
    new Date(`${iso}T12:00:00`).toLocaleDateString(undefined, {
      month: "short",
      day: "numeric",
    });
  if (!summary.starts_on || !summary.ends_on) return "";
  return `${show(summary.starts_on)} to ${show(summary.ends_on)}`;
}

export default async function CampaignsPage() {
  // The window ends yesterday, the same as Google's own "last 30 days", so the
  // dates come with the figures rather than being worked out again here.
  const summary = await ask<AdsSummary>("/v1/ads/summary?days=30", { read: false });
  const covered = span(summary);

  return (
    <>
      <Header
        eyebrow={covered ? `Last 30 days · ${covered}` : "Last 30 days"}
        title="Campaigns"
        right={<HeaderLink href="/campaigns/new">+ New campaign</HeaderLink>}
      />
      <PwPage>
        <CampaignList initial={summary} days={30} />
      </PwPage>
    </>
  );
}
