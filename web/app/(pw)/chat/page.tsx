import type { Metadata } from "next";
import { Header, PwPage } from "@/components/pw/shell";
import { NotBuilt } from "@/components/pw/states";

export const metadata: Metadata = { title: "Chat with Otto · PPCway" };

export default function ChatPage() {
  return (
    <>
      <Header eyebrow="Otto" title="Chat with Otto" />
      <PwPage>
        <NotBuilt
          title="Ask Otto is not switched on yet"
          needs="It waits on the same machinery as the Otto inbox: the tools that let it read your account safely, and the change pipeline that means a suggestion can only become a change with your yes."
        >
          <p>
            It will answer plain questions about your own numbers — why calls dropped on Sunday,
            which service brings the cheapest leads, whether you will go over budget this month —
            and show the figures it used, so you can check it.
          </p>
          <p>
            It will never change anything on its own. When it suggests something, you get the same
            card you would get from the inbox, and nothing happens until you approve it.
          </p>
        </NotBuilt>
      </PwPage>
    </>
  );
}
