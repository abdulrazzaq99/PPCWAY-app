import type { Metadata } from "next";
import { Note } from "@/components/pw/create/kit";
import { ConversionSetup } from "@/components/pw/conversions/setup";
import type { Summary } from "@/components/pw/conversions/types";
import { Header, HeaderLink, PwPage } from "@/components/pw/shell";
import { NotConnected } from "@/components/pw/states";
import { ask } from "@/lib/pw-fetch";

export const metadata: Metadata = { title: "Set up conversions · PPCway" };

/*
  Google's Conversions setup (components/pw/conversions/setup.tsx): choose the
  data sources, create the conversion actions, then the summary and the tag.
  The summary read brings the goal list for each source, the website and its
  tag, and the names already taken.
*/
export default async function NewConversionPage({
  searchParams,
}: {
  searchParams: Promise<{ site?: string }>;
}) {
  const { site } = await searchParams;
  const query = site ? `?site=${encodeURIComponent(site)}` : "";
  const summary = await ask<Summary | null>(`/v1/conversions${query}`, null);

  return (
    <>
      <Header
        eyebrow="Goals · Conversions"
        title="Set up conversions"
        right={<HeaderLink href="/conversions">Back to conversions</HeaderLink>}
      />
      <PwPage>
        {summary === null ? (
          <Note tone="warn">
            PPCWay could not reach Google Ads just now, so setup cannot start. Try again in a
            minute.
          </Note>
        ) : !summary.connected ? (
          <NotConnected what="Conversion actions are created in your Google Ads account." />
        ) : !summary.may_change ? (
          <Note tone="info">
            Creating conversion actions needs someone who may approve changes on this account. Ask
            the account owner to give you that, or to set them up.
          </Note>
        ) : (
          <ConversionSetup summary={summary} />
        )}
      </PwPage>
    </>
  );
}
