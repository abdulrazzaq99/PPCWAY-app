import type { Metadata } from "next";
import { LeadCalculator } from "@/components/pw/calculators";
import { Header, PwPage } from "@/components/pw/shell";

export const metadata: Metadata = { title: "Cost per lead & ROAS · PPCway" };

export default function LeadToolPage() {
  return (
    <>
      <Header eyebrow="Free tools" title="Cost per lead & ROAS" />
      <PwPage>
        <LeadCalculator />
      </PwPage>
    </>
  );
}
