"use client";

import { useState } from "react";
import { AsideCard, FormCard, OnboardingShell, SectionTitle } from "@/components/onboarding/shell";
import { ChoiceList } from "@/components/onboarding/blocks";
import { GoogleButton } from "@/components/auth/google-button";
import { Field, Input } from "@/components/ui/field";
import { LinkButton } from "@/components/ui/button";

const PLANS = [
  {
    id: "starter",
    name: "Starter",
    detail: "One campaign, up to $1,500 ad spend a month.",
    status: "$49 / mo",
    statusTone: "ink" as const,
  },
  {
    id: "growth",
    name: "Growth",
    detail: "Up to four campaigns, call tracking and the Monday email.",
    status: "$99 / mo",
    statusTone: "ink" as const,
  },
  {
    id: "agency",
    name: "Agency",
    detail: "Up to ten businesses, one view of every client, white label.",
    status: "$249 / mo",
    statusTone: "ink" as const,
  },
];

export default function AccountStep() {
  const [plan, setPlan] = useState("starter");
  return (
    <OnboardingShell
      step="account"
      headline="Create your account and pick a plan."
      subline="Your plan pays for PPCWay. Google bills the ads separately, straight to your card, and you can cancel any time."
      action={<LinkButton href="/onboarding/connect">Continue</LinkButton>}
      aside={
        <AsideCard
          title="What happens next"
          finePrint="Free for 14 days. Cancel from Settings whenever you like."
        >
          Connect your Google Ads account, or let us make one for you. Then answer a few questions
          about your business, which is the main step and takes about three minutes. We write the
          campaign and show it to you. Nothing goes live until you approve it.
        </AsideCard>
      }
    >
      <FormCard>
        <SectionTitle>Your account</SectionTitle>
        <GoogleButton />
        <Field label="Email">
          {(id) => (
            <Input
              id={id}
              name="email"
              type="email"
              autoComplete="email"
              defaultValue="dana@alphaplumbing.ca"
            />
          )}
        </Field>
        <SectionTitle>Your plan</SectionTitle>
        <ChoiceList rows={PLANS} value={plan} onChange={setPlan} ariaLabel="Your plan" />
      </FormCard>
    </OnboardingShell>
  );
}
