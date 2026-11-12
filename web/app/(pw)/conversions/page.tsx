import type { Metadata } from "next";
import Link from "next/link";
import { Note } from "@/components/pw/create/kit";
import { ConversionsSummary } from "@/components/pw/conversions/summary";
import type { Summary } from "@/components/pw/conversions/types";
import { Header, PwPage } from "@/components/pw/shell";
import { NotConnected } from "@/components/pw/states";
import type { ConversionGoal } from "@/lib/creation";
import { ask } from "@/lib/pw-fetch";

export const metadata: Metadata = { title: "Conversions · PPCway" };

/*
  Google's Goals, Conversions, Summary (components/pw/conversions/summary.tsx):
  the Google tag, every conversion action by goal, what can be imported and
  the account's default goals. The goals come from the campaign setup read,
  which already lists them the way Google's step 1 does.
*/
type GoalsRead = {
  connected?: boolean;
  conversion?: { goals: ConversionGoal[]; tracking: boolean; reason?: string };
  trouble?: string;
};

export default async function ConversionsPage({
  searchParams,
}: {
  searchParams: Promise<{ site?: string }>;
}) {
  const { site } = await searchParams;
  const query = site ? `?site=${encodeURIComponent(site)}` : "";
  const [summary, setup] = await Promise.all([
    ask<Summary | null>(`/v1/conversions${query}`, null),
    ask<GoalsRead | null>("/v1/campaigns/setup", null),
  ]);
  // A goals read that failed is said in the Goals card, not shown as an empty list.
  const read = setup?.conversion;
  const goals = read && !(read.reason && !read.goals.length) ? read.goals : null;
  const goalsReason = setup?.trouble || setup?.conversion?.reason || "";
  const canAdd = Boolean(summary?.connected && summary.may_change);

  return (
    <>
      <Header
        eyebrow="Goals"
        title="Conversions"
        right={
          canAdd ? (
            <Link
              href="/conversions/new"
              className="bg-pw-blue hover:bg-pw-blue-hover flex h-[42px] items-center gap-2 rounded-[12px] px-4 text-[15px] font-semibold text-white"
            >
              <span aria-hidden className="text-[18px] leading-none">
                +
              </span>
              New conversion action
            </Link>
          ) : null
        }
      />
      <PwPage>
        {summary === null ? (
          <Note tone="warn">
            PPCWay could not read your conversions just now. Try again in a minute.
          </Note>
        ) : !summary.connected ? (
          <NotConnected what="Conversions are counted in your Google Ads account, so PPCWay reads them from there." />
        ) : (
          <ConversionsSummary summary={summary} goals={goals} goalsReason={goalsReason} />
        )}
      </PwPage>
    </>
  );
}
