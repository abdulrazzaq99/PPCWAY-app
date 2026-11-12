import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { DraftReview } from "@/components/pw/campaign-builder";
import { CampaignEditor } from "@/components/pw/create/editor";
import { Header, HeaderLink, PwPage } from "@/components/pw/shell";
import type { Draft, Prefill } from "@/lib/builder";
import type { Setup, SpecDraft } from "@/lib/creation";
import { ask } from "@/lib/pw-fetch";

export const metadata: Metadata = { title: "New campaign · PPCway" };

const OFFLINE: Setup = {
  connected: false,
  objectives: {} as Setup["objectives"],
  types: {},
  steps: {},
  step_labels: {},
  built: [],
};

/*
  A campaign being created on Google's steps (components/pw/create/editor.tsx),
  or, for a draft the first builder made, its review screen (Figma 17:2048).
*/
export default async function DraftPage({
  params,
  searchParams,
}: {
  params: Promise<{ id: string }>;
  searchParams: Promise<{ step?: string }>;
}) {
  const [{ id }, { step }] = await Promise.all([params, searchParams]);
  if (!/^[0-9a-f-]{36}$/.test(id)) notFound();
  const draft = await ask<SpecDraft | null>(`/v1/campaigns/v2/${id}`, null);
  if (draft) {
    const setup = await ask<Setup>("/v1/campaigns/setup", OFFLINE);
    return (
      <>
        <Header
          eyebrow="Campaigns"
          title={draft.status === "launched" ? "Campaign published" : "New campaign"}
          right={<HeaderLink href="/campaigns">Back to campaigns</HeaderLink>}
        />
        <PwPage>
          <CampaignEditor initial={draft} setup={setup} startAt={step} />
        </PwPage>
      </>
    );
  }

  const [old, prefill] = await Promise.all([
    ask<Draft | null>(`/v1/campaigns/drafts/${id}`, null),
    ask<Prefill>("/v1/campaigns/start", { connected: false }),
  ]);
  if (!old) notFound();
  const launched = old.status === "launched";
  return (
    <>
      <Header
        eyebrow="New campaign"
        title={launched ? `${old.plan.name} is live.` : "Here's the campaign we built for you."}
        right={<HeaderLink href="/campaigns">Back to campaigns</HeaderLink>}
      />
      <PwPage>
        <p className="text-pw-ink-700 max-w-[720px] text-[15px] leading-[21px]">
          {launched
            ? "It is in your Google Ads account. Google needs about a week of its own data before its figures mean much."
            : "Read it in plain English and change anything you like. Nothing goes live, and nothing costs money, until you launch it."}
        </p>
        <DraftReview initial={old} mayLaunch={Boolean(prefill.may_launch)} />
      </PwPage>
    </>
  );
}
