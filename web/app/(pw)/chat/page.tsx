import type { Metadata } from "next";
import { AskOtto } from "@/components/otto/ask";
import { Header, HeaderLink, PwPage } from "@/components/pw/shell";

export const metadata: Metadata = { title: "Chat with Otto · PPCway" };

/*
  Ask Otto. Read-only: it looks things up in your own account and explains
  them, and it cannot change anything from here. Where it has something worth
  doing it writes a card to the inbox, which is still your decision.
*/
export default function ChatPage() {
  return (
    <>
      <Header
        eyebrow="Otto"
        title="Chat with Otto"
        right={<HeaderLink href="/otto">See the inbox</HeaderLink>}
      />
      <PwPage>
        <p className="text-pw-ink-700 max-w-[680px] text-[15px] leading-[21px]">
          Ask about your own numbers — why calls dropped, which service brings the cheapest leads,
          whether you will go over budget this month. Otto shows the figures it used, so you can
          check it.
        </p>
        <div className="max-w-[760px]">
          <AskOtto />
        </div>
      </PwPage>
    </>
  );
}
