"use client";

import { useState } from "react";
import { AsideCard, FormCard, OnboardingShell, SectionTitle } from "@/components/onboarding/shell";
import { ChoiceList, FactField, StatusStrip } from "@/components/onboarding/blocks";
import { ChipRows } from "@/components/onboarding/extras";
import { Checkbox } from "@/components/ui/checkbox";
import { Button, LinkButton } from "@/components/ui/button";

import type { ReviewViewName } from "@/components/onboarding/view-names";

export function ReviewView({ view }: { view: ReviewViewName }) {
  switch (view) {
    case "ready":
      return <ReadyView variant="ready" />;
    case "backup":
      return <BackupView />;
    case "billing-done":
      return <ReadyView variant="billing-done" />;
    case "live":
      return <LiveView />;
    default:
      return <WritingView />;
  }
}

/* Frame at (6400, 7030): the campaign is being written. */
function WritingView() {
  return (
    <OnboardingShell
      step="review"
      headline="Writing your campaign. About a minute."
      subline="Watch it happen or go and make a coffee. If you close this we will email you the moment it is ready to read."
      action={<LinkButton href="/onboarding/review?view=ready">Read the campaign</LinkButton>}
      aside={
        <AsideCard
          title="Where the writing comes from"
          finePrint="Every term is one Google gave us for your trade."
        >
          A language model writes the wording and groups the search terms. It is not allowed to
          invent a keyword, choose your budget, pick your bidding, or decide what campaign you get.
          Those are fixed rules we can show you, so the same answers come out every time.
        </AsideCard>
      }
    >
      <FormCard>
        <SectionTitle>Working on</SectionTitle>
        <StatusStrip tone="brand">Step 5 of 8 · writing your ad wording</StatusStrip>
        <FactField label="Time so far" value="38 seconds" />
        <SectionTitle>What happens, in order</SectionTitle>
        <ChoiceList
          rows={[
            {
              id: "read",
              name: "Read your website",
              detail: "14 pages. Services, service area and phone number pulled out.",
              status: "Done",
              statusTone: "brand",
            },
            {
              id: "ask",
              name: "Ask Google what people type",
              detail: "Google returns real search terms and how often they are used.",
              status: "Done",
              statusTone: "brand",
            },
            {
              id: "drop",
              name: "Throw out the bad ones",
              detail: "Too rare, too dear for your budget, or a competitor's name.",
              status: "214 dropped",
              statusTone: "brand",
            },
            {
              id: "group",
              name: "Group what survived",
              detail: "Into a few tight themes, one ad group each.",
              status: "4 themes",
              statusTone: "brand",
            },
            {
              id: "write",
              name: "Write the ads",
              detail: "Headlines and descriptions, in your words, taken from your pages.",
              status: "Working",
              statusTone: "brand",
              fill: "brand",
            },
            {
              id: "check",
              name: "Check them against Google's rules",
              detail: "Length, claims and trademarks. Anything that fails is rewritten.",
              status: "Next",
            },
            {
              id: "block",
              name: "Add the words to block",
              detail: "So you never pay for jobs, salary, courses or free advice.",
              status: "Next",
            },
            {
              id: "google",
              name: "Have Google check it before you see it",
              detail: "So nothing you approve can fail at the moment you launch.",
              status: "Next",
            },
          ]}
        />
      </FormCard>
    </OnboardingShell>
  );
}

/* Frames at (9600, 7030) and (11200, 7030): the campaign, before and after billing is done. */
function ReadyView({ variant }: { variant: "ready" | "billing-done" }) {
  const [agreed, setAgreed] = useState(true);
  const [launching, setLaunching] = useState(false);
  const billed = variant === "billing-done";
  return (
    <OnboardingShell
      step="review"
      headline={
        billed
          ? "Welcome back. Billing is done, so you can launch."
          : "Here is your campaign. Nothing is live yet."
      }
      subline={
        billed
          ? "Google confirmed your card at 3:05 pm. Everything else was ready before you left, so this is the last click."
          : "Read it the way a customer would. If a word is wrong, go back and fix it. Launching starts your spend the same day."
      }
      footnote={billed ? "This is the last step." : undefined}
      progress={billed ? "Step 6 of 6 · all set" : undefined}
      action={
        <Button
          disabled={!agreed}
          working={launching && "Sending to Google"}
          onClick={() => setLaunching(true)}
        >
          Launch my campaign
        </Button>
      }
      aside={
        billed ? (
          <AsideCard
            title="While you were at Google"
            finePrint="Launching sends 2 campaigns to Google for review."
          >
            We kept your campaign exactly as you approved it, and checked your card with Google the
            moment you came back. Nothing has gone to Google yet.
          </AsideCard>
        ) : (
          <AsideCard
            title="What happens at launch"
            finePrint="You can pause everything from the dashboard."
          >
            Your ads go to Google for review, which usually takes a few hours. We email you when
            they are live. Expect a few calls in week one; the numbers settle in two to four weeks.
          </AsideCard>
        )
      }
    >
      <FormCard>
        <SectionTitle>Your ad</SectionTitle>
        <StatusStrip tone="brand">
          Emergency Plumber Mississauga | Alpha Plumbing | Open 24 Hours
        </StatusStrip>
        <FactField label="Daily budget" value="$40 a day, about $1,200 a month" />
        <SectionTitle>Before it goes live</SectionTitle>
        <ChoiceList
          rows={[
            {
              id: "ads",
              name: "Ads and keywords written",
              detail: "47 keywords, 12 headlines, 4 descriptions.",
              status: "Ready",
              statusTone: "brand",
              fill: "brand",
            },
            {
              id: "calls",
              name: "Call tracking connected",
              detail: "Calls to (905) 555-0142 forward to your mobile.",
              status: "Ready",
              statusTone: "brand",
            },
            billed
              ? {
                  id: "bill",
                  name: "Google billing set up",
                  detail: "Card added in Google Ads at 3:05 pm. Checked just now.",
                  status: "Ready",
                  statusTone: "brand",
                }
              : {
                  id: "bill",
                  name: "Google billing set up",
                  detail: "Add your card in Google Ads before ads can run.",
                  status: "Needs you",
                  statusTone: "amber",
                  fill: "amber",
                },
          ]}
        />
        <p className="text-ink text-[15px] leading-[18px] font-semibold">How PPCWay will run</p>
        <ChipRows
          rows={[
            {
              title: "Ask first",
              meta: "We propose each change with our reason. Nothing happens until you say yes.",
              chip: "Your setting",
              tone: "brand",
            },
            {
              title: "Your limits",
              meta: "At most $48 a day and $35 a call, and never more than $14 for one click.",
              chip: "",
              link: "Change",
            },
          ]}
        />
        <Checkbox checked={agreed} onChange={setAgreed}>
          <span className="text-ink text-[14px] leading-[17px]">
            I have read the ads. I am responsible for what they say about my business, and I can
            change them at any time.
          </span>
        </Checkbox>
        {!agreed ? <p className="text-meta text-faint">Tick the box above to launch.</p> : null}
      </FormCard>
    </OnboardingShell>
  );
}

/* Frame at (8000, 7030): the writer used backup wording. */
function BackupView() {
  return (
    <OnboardingShell
      step="review"
      headline="Your campaign is ready. One step used backup wording."
      subline="The writer did not answer in time, so your ads use our tested wording for plumbers, filled in with your details. It passed every check, and you can ask for fresh wording any time."
      action={<LinkButton href="/onboarding/review?view=ready">Read the campaign</LinkButton>}
      aside={
        <AsideCard
          title="What backup wording means"
          finePrint="Every line passed the same checks as fresh wording."
        >
          Nothing is wrong with your campaign. Tested wording is plainer than a fresh draft. After
          launch, open Ads and choose Write fresh wording to try again.
        </AsideCard>
      }
    >
      <FormCard>
        <SectionTitle>Working on</SectionTitle>
        <StatusStrip tone="brand">All 8 steps done</StatusStrip>
        <FactField label="Time so far" value="72 seconds" />
        <SectionTitle>What happens, in order</SectionTitle>
        <ChoiceList
          rows={[
            {
              id: "read",
              name: "Read your website",
              detail: "14 pages. Services, service area and phone number pulled out.",
              status: "Done",
              statusTone: "brand",
            },
            {
              id: "ask",
              name: "Ask Google what people type",
              detail: "Google returns real search terms and how often they are used.",
              status: "Done",
              statusTone: "brand",
            },
            {
              id: "drop",
              name: "Throw out the bad ones",
              detail: "Too rare, too dear for your budget, or a competitor's name.",
              status: "214 dropped",
              statusTone: "brand",
            },
            {
              id: "group",
              name: "Group what survived",
              detail: "Into a few tight themes, one ad group each.",
              status: "4 themes",
              statusTone: "brand",
            },
            {
              id: "write",
              name: "Write the ads",
              detail: "The writer timed out, so tested wording was filled in with your details.",
              status: "Backup used",
              statusTone: "amber",
              fill: "amber",
            },
            {
              id: "check",
              name: "Check them against Google's rules",
              detail: "Length, claims and trademarks. Anything that fails is rewritten.",
              status: "Done",
            },
            {
              id: "block",
              name: "Add the words to block",
              detail: "So you never pay for jobs, salary, courses or free advice.",
              status: "Done",
            },
            {
              id: "google",
              name: "Have Google check it before you see it",
              detail: "So nothing you approve can fail at the moment you launch.",
              status: "Done",
            },
          ]}
        />
      </FormCard>
    </OnboardingShell>
  );
}

/* Frame at (0, 8370): live, and Google is reviewing. */
function LiveView() {
  return (
    <OnboardingShell
      step="review"
      headline="You are live. Google is checking your ads."
      subline="Google reviews every new ad before it shows, which usually takes a few hours. You do not need to do anything. We will email you the moment your first ad is showing."
      footnote="Setup took you 14 minutes in PPCWay."
      progress="All 6 steps done"
      action={<LinkButton href="/">Go to your dashboard</LinkButton>}
      aside={
        <AsideCard
          title="If Google says no to an ad"
          finePrint="You can pause everything from the dashboard at any time."
        >
          Sometimes Google refuses a line even after our checks. If that happens we rewrite it, show
          you what changed and send it back. Your other ads keep running in the meantime.
        </AsideCard>
      }
    >
      <FormCard>
        <SectionTitle>Right now</SectionTitle>
        <StatusStrip tone="brand">2 campaigns sent to Google at 3:12 pm</StatusStrip>
        <FactField label="Your first Monday email" value="Monday 10 August, 8 am" />
        <SectionTitle>What happens next</SectionTitle>
        <ChoiceList
          rows={[
            {
              id: "review",
              name: "Google reviews your ads",
              detail: "Usually a few hours, sometimes up to a day.",
              status: "In review",
              statusTone: "amber",
              fill: "amber",
            },
            {
              id: "learn",
              name: "Your first weeks are for learning",
              detail: "A few calls in week one; numbers settle in 2 to 4 weeks.",
              status: "4 weeks",
            },
            {
              id: "daily",
              name: "We check everything every day",
              detail: "Anything that needs you lands in Approvals first.",
              status: "Every day",
            },
          ]}
        />
      </FormCard>
    </OnboardingShell>
  );
}
