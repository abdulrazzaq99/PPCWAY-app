import Link from "next/link";
import { LinkButton } from "@/components/ui/button";
import { OnboardingShell } from "@/components/onboarding/shell";
import { ListRow, Rows } from "@/components/app/blocks";

/* 87:8668, "Welcome back": picking onboarding up where it stopped. */
export default function ResumeOnboarding() {
  return (
    <OnboardingShell
      step="calls"
      headline="Welcome back, Dana"
      subline="You stopped at step 4 yesterday. It's all saved."
      progress="Step 4 of 6"
      action={
        <>
          <Link href="/onboarding" className="text-brand text-[14px] leading-[17px] font-semibold">
            Start again instead
          </Link>
          <LinkButton href="/onboarding/calls">Carry on from step 4</LinkButton>
        </>
      }
    >
      <section className="bg-panel border-line rounded-[16px] border px-5 py-2 sm:px-[29px]">
        <Rows className="mt-0">
          <ListRow title="Account and plan" chip="Done" chipTone="pale" />
          <ListRow title="Connect Google Ads" chip="Done" chipTone="pale" />
          <ListRow title="Your business" chip="Done" chipTone="pale" />
          <ListRow
            title="Count your calls"
            meta="About 2 minutes"
            chip="Next"
            chipTone="amber"
            titleWeight="semibold"
          />
          <ListRow title="Review and launch" />
        </Rows>
      </section>
    </OnboardingShell>
  );
}
