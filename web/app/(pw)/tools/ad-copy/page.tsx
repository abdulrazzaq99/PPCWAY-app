import type { Metadata } from "next";
import { AdCopyChecker } from "@/components/pw/calculators";
import { Header, PwPage } from "@/components/pw/shell";

export const metadata: Metadata = { title: "Ad copy checker · PPCway" };

export default function AdCopyToolPage() {
  return (
    <>
      <Header eyebrow="Free tools" title="Ad copy checker" />
      <PwPage>
        <AdCopyChecker />
      </PwPage>
    </>
  );
}
