import type { Metadata } from "next";
import { Header, PwPage } from "@/components/pw/shell";
import { NotBuilt } from "@/components/pw/states";

export const metadata: Metadata = { title: "Otto inbox · PPCway" };

export default function OttoPage() {
  return (
    <>
      <Header eyebrow="Otto" title="Otto inbox" />
      <PwPage>
        <NotBuilt title="Otto is not watching your account yet">
          <p>
            When it is, this is where its work arrives: one card per change worth making, with the
            reason in plain words, the evidence behind it, what it should be worth, and how to put
            it back if it is not.
          </p>
          <p>
            Small, safe changes — blocking a search that wastes money, pausing an ad Google has
            disapproved — go through on your standing yes and are reported here. Anything that moves
            money waits for your tap. Anything large waits for your expert first.
          </p>
        </NotBuilt>
      </PwPage>
    </>
  );
}
