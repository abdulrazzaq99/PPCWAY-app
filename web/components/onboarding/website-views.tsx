"use client";

import { useState } from "react";
import { AsideCard, FormCard, OnboardingShell, SectionTitle } from "@/components/onboarding/shell";
import { ChoiceList, FactField } from "@/components/onboarding/blocks";
import { Button, LinkButton } from "@/components/ui/button";

import type { WebsiteViewName } from "@/components/onboarding/view-names";

export function WebsiteView({ view }: { view: WebsiteViewName }) {
  if (view === "report") return <ReportView />;
  if (view === "finding") return <FindingView />;
  return <RunningView />;
}

/* Audit frame 3: the checks running. */
function RunningView() {
  return (
    <OnboardingShell
      step="website"
      headline="Checking your website."
      subline="This takes about a minute. We look at what an ads agency would check before spending your money, and we change nothing on your site."
      action={
        <>
          <Button disabled>Checking, about a minute</Button>
          <LinkButton href="/onboarding/website?view=report" variant="quiet" size="sm">
            Skip ahead
          </LinkButton>
        </>
      }
      aside={
        <AsideCard title="Why we do this" finePrint="Nothing goes live until you approve it.">
          An ads agency audits a website before it spends a dollar, because a click only pays off if
          the page turns it into a call. We run the same checks, automatically.
        </AsideCard>
      }
    >
      <FormCard>
        <SectionTitle>Reading alphaplumbing.ca</SectionTitle>
        <SectionTitle>What we are checking</SectionTitle>
        <ChoiceList
          rows={[
            {
              id: "pages",
              name: "Pages we can read",
              detail: "14 pages found, none blocked",
              status: "Done",
              statusTone: "brand",
            },
            {
              id: "phone",
              name: "Your phone number",
              detail: "On every page, tap to call on a phone",
              status: "Done",
              statusTone: "brand",
            },
            {
              id: "form",
              name: "Contact form",
              detail: "Found on the contact page",
              status: "Done",
              statusTone: "brand",
            },
            {
              id: "speed",
              name: "How fast it loads on a phone",
              detail: "2.9 seconds on 4G",
              status: "Done",
              statusTone: "brand",
            },
            {
              id: "tags",
              name: "Google's tags",
              detail: "Looking for Tag Manager, Analytics and Ads",
              status: "Checking",
              statusTone: "amber",
              fill: "amber",
            },
            {
              id: "words",
              name: "Words that match your ads",
              detail: "Emergency, water heater, drain",
              status: "Waiting",
            },
            {
              id: "trust",
              name: "Trust signals",
              detail: "Licence, reviews, address and hours",
              status: "Waiting",
            },
            {
              id: "policy",
              name: "Words Google may object to",
              detail: "Claims and guarantees",
              status: "Waiting",
            },
          ]}
        />
      </FormCard>
    </OnboardingShell>
  );
}

/* Audit frame 4: the report. */
function ReportView() {
  return (
    <OnboardingShell
      step="website"
      headline="Your site is ready for ads, with two things to fix first."
      subline="Eight checks, the same ones an agency runs. Green is fine. Amber needs a small change from you. Grey is ours to handle."
      action={<LinkButton href="/onboarding/calls">Continue to counting calls</LinkButton>}
      aside={
        <AsideCard
          title="Fix before launch"
          finePrint="Both take under ten minutes. Everything else is fine as it is."
          action={<LinkButton href="/onboarding/calls?view=verify">Add the tag for me</LinkButton>}
        >
          <ol className="flex list-decimal flex-col gap-3 pl-5">
            <li>
              Add the counting tag. One click if you use Tag Manager, and we send a test visit to
              confirm it works.
            </li>
            <li>Give your contact form a thank-you page, or let us count the send another way.</li>
          </ol>
        </AsideCard>
      }
    >
      <FormCard>
        <SectionTitle>What we found</SectionTitle>
        <SectionTitle>The eight checks</SectionTitle>
        <ChoiceList
          rows={[
            {
              id: "count",
              name: "Counting calls and forms",
              detail: "No tag for calls or forms yet, so results can't be counted",
              status: "Needs you",
              statusTone: "amber",
              fill: "amber",
            },
            {
              id: "speed",
              name: "Speed on a phone",
              detail: "2.9 seconds on 4G. Good, and faster is better",
              status: "Good",
              statusTone: "brand",
            },
            {
              id: "mobile",
              name: "Works on a phone",
              detail: "Text readable, buttons tappable, number is tap to call",
              status: "Good",
              statusTone: "brand",
            },
            {
              id: "match",
              name: "Page matches the ad",
              detail: "Emergency plumbing on the home page, water heaters on its own",
              status: "Good",
              statusTone: "brand",
            },
            {
              id: "form",
              name: "Contact form",
              detail: "Found, but no thank-you page, so a form send can't be counted",
              status: "Needs you",
              statusTone: "amber",
              fill: "amber",
            },
            {
              id: "trust",
              name: "Trust signals",
              detail: "Licence number, 214 Google reviews, address and hours",
              status: "Good",
              statusTone: "brand",
            },
            {
              id: "policy",
              name: "Words Google may object to",
              detail: "“Best price guaranteed” found. We keep it out of your ads",
              status: "We'll handle it",
            },
            {
              id: "privacy",
              name: "Privacy policy",
              detail: "Found. Google requires one for lead forms",
              status: "Good",
              statusTone: "brand",
            },
          ]}
        />
      </FormCard>
    </OnboardingShell>
  );
}

/* Audit frame 5: one finding, opened. */
function FindingView() {
  const [choice, setChoice] = useState("thanks");
  return (
    <OnboardingShell
      step="website"
      headline="Your contact form has no thank-you page."
      subline="So a form send cannot be counted as a result, and we would be guessing which searches bring you work. Here is what we saw and what to do."
      action={<LinkButton href="/onboarding/website?view=report">Back to the report</LinkButton>}
      aside={
        <AsideCard
          title="Why it matters"
          finePrint="We change nothing on your site. You or your web person make this change."
        >
          Agencies call counting the single point of failure. Without it, ads are tuned on clicks,
          not on work. A thank-you page fixes it in about ten minutes on most website builders.
        </AsideCard>
      }
    >
      <FormCard>
        <SectionTitle>What we saw</SectionTitle>
        <FactField label="Page" value="alphaplumbing.ca/contact" />
        <div className="bg-line-soft text-muted flex h-[200px] items-center justify-center rounded-[12px] px-6 text-center text-[14px] leading-[17px] font-medium">
          Screenshot of alphaplumbing.ca/contact, with the form outlined
        </div>
        <SectionTitle>What to do, pick one</SectionTitle>
        <ChoiceList
          value={choice}
          onChange={setChoice}
          rows={[
            {
              id: "thanks",
              name: "Option 1, add a thank-you page",
              detail: "Show a /thanks page after the send. We count visits to it.",
              status: "Recommended",
              statusTone: "brand",
            },
            {
              id: "tag",
              name: "Option 2, keep the form as it is",
              detail: "We count the send with a small tag. Needs Tag Manager.",
              status: "Also fine",
              statusTone: "brand",
            },
            {
              id: "skip",
              name: "Option 3, skip it for now",
              detail: "Phone calls only. Fewer results, ads tuned on less.",
              status: "Not ideal",
              statusTone: "amber",
            },
          ]}
        />
      </FormCard>
    </OnboardingShell>
  );
}
