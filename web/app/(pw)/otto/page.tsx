import type { Metadata } from "next";
import { OttoInbox } from "@/components/otto/inbox";
import { Header, HeaderLink, PwPage } from "@/components/pw/shell";
import { readInbox } from "@/lib/otto-server";

export const metadata: Metadata = { title: "Otto inbox · PPCway" };

/*
  The inbox. The client's brief calls it the product, and this is the screen
  that stopped being a placeholder: one card per change worth making, with the
  figures behind it, what it should be worth, and how to put it back.

  Read on the server while the page renders rather than fetched on mount, so a
  merchant opening it sees the cards rather than a blank panel and then a flash.
*/
export default async function OttoPage() {
  const { inbox, trouble } = await readInbox();
  return (
    <>
      <Header
        eyebrow="Otto"
        title="Otto inbox"
        right={<HeaderLink href="/chat">Ask Otto a question</HeaderLink>}
      />
      <PwPage>
        <p className="text-pw-ink-700 max-w-[680px] text-[15px] leading-[21px]">
          Each of these is a change worth making, with the figures behind it. Nothing happens until
          you say so, and anything that does can be put back.
        </p>
        <OttoInbox inbox={inbox} trouble={trouble} />
      </PwPage>
    </>
  );
}
