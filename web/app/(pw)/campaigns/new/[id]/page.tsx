import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { DraftReview } from "@/components/pw/campaign-builder";
import { Header, HeaderLink, PwPage } from "@/components/pw/shell";
import type { Draft, Prefill } from "@/lib/builder";
import { ask } from "@/lib/pw-fetch";

export const metadata: Metadata = { title: "Your new campaign · PPCway" };

/* Here's the campaign we built for you (Figma 17:2048). */
export default async function DraftPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  if (!/^[0-9a-f-]{36}$/.test(id)) notFound();
  const [draft, prefill] = await Promise.all([
    ask<Draft | null>(`/v1/campaigns/drafts/${id}`, null),
    ask<Prefill>("/v1/campaigns/start", { connected: false }),
  ]);
  if (!draft) notFound();
  const launched = draft.status === "launched";
  return (
    <>
      <Header
        eyebrow="New campaign"
        title={launched ? `${draft.plan.name} is live.` : "Here's the campaign we built for you."}
        right={<HeaderLink href="/campaigns">Back to campaigns</HeaderLink>}
      />
      <PwPage>
        <p className="text-pw-ink-700 max-w-[720px] text-[15px] leading-[21px]">
          {launched
            ? "It is in your Google Ads account. Google needs about a week of its own data before its figures mean much."
            : "Read it in plain English and change anything you like. Nothing goes live, and nothing costs money, until you launch it."}
        </p>
        <DraftReview initial={draft} mayLaunch={Boolean(prefill.may_launch)} />
      </PwPage>
    </>
  );
}
