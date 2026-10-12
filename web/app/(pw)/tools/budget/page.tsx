import type { Metadata } from "next";
import { BudgetCalculator } from "@/components/pw/calculators";
import { Header, PwPage } from "@/components/pw/shell";

export const metadata: Metadata = { title: "Budget calculator · PPCway" };

export default function BudgetToolPage() {
  return (
    <>
      <Header eyebrow="Free tools" title="Budget calculator" />
      <PwPage>
        <BudgetCalculator />
      </PwPage>
    </>
  );
}
