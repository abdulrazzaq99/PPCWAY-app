"use client";

import { useState } from "react";
import { AsideCard, FormCard, OnboardingShell, SectionTitle } from "@/components/onboarding/shell";
import { ChoiceList, FactField, OptionCard, StatusStrip } from "@/components/onboarding/blocks";
import { CampaignCard } from "@/components/onboarding/extras";
import { GoogleButton } from "@/components/auth/google-button";
import { Field, Input } from "@/components/ui/field";
import { Button, LinkButton } from "@/components/ui/button";

import type { ConnectViewName } from "@/components/onboarding/view-names";
export type { ConnectViewName };

export function ConnectView({ view }: { view: ConnectViewName }) {
  switch (view) {
    case "route":
      return <RouteView />;
    case "pick":
      return <PickView />;
    case "accept":
      return <AcceptView />;
    case "accept-choice":
      return <AcceptChoiceView />;
    case "connected":
      return <ConnectedView />;
    case "queue":
      return <QueueView />;
    case "queue-full":
      return <QueueFullView />;
    case "existing":
      return <ExistingView />;
    default:
      return <ConnectStart />;
  }
}

/* Frame at (1600, 4778): the first Connect screen. */
function ConnectStart() {
  return (
    <OnboardingShell
      step="connect"
      headline="Connect your Google Ads account."
      subline="PPCWay only touches the account you pick. Nothing goes live until you approve it, and Google bills you for the ads directly."
      action={<LinkButton href="/onboarding/connect?view=route">Continue</LinkButton>}
      aside={
        <AsideCard
          title="Check the address bar"
          finePrint="No Google Ads account yet? We can make one for you."
        >
          The next page is on accounts.google.com. That page belongs to Google, not to us. We never
          see your Google password, and you can remove PPCWay from your Google account whenever you
          like.
        </AsideCard>
      }
    >
      <FormCard>
        <SectionTitle>Your Google account</SectionTitle>
        <GoogleButton label="Sign in with Google" />
        <Field label="Google Ads customer ID">
          {(id) => (
            <Input id={id} name="customerId" inputMode="numeric" defaultValue="742-118-9063" />
          )}
        </Field>
        <SectionTitle>What PPCWay will do</SectionTitle>
        <ChoiceList
          rows={[
            {
              id: "edit",
              name: "Create and edit campaigns",
              detail: "Only in the account you pick, and always after you approve.",
              status: "Needed",
              statusTone: "brand",
            },
            {
              id: "read",
              name: "Read your results",
              detail: "Clicks, calls and cost, so we can show you what is working.",
              status: "Needed",
              statusTone: "brand",
            },
            {
              id: "gtm",
              name: "Set up call tracking in Tag Manager",
              detail: "Optional, on the same Google screen. Saves a second sign-in later.",
              status: "Optional",
              statusTone: "ink",
            },
            {
              id: "billing",
              name: "Change your billing",
              detail: "We never do this. Your card stays with Google.",
              status: "Never",
              statusTone: "red",
            },
          ]}
        />
      </FormCard>
    </OnboardingShell>
  );
}

/* Frame at (3200, 4778): how PPCWay reaches the account. */
function RouteView() {
  const [choice, setChoice] = useState("have");
  return (
    <OnboardingShell
      step="connect"
      headline="How should we reach your Google Ads?"
      subline="PPCWay works from a manager account, the same way an agency does. You stay the owner and can remove us from Google Ads in two clicks."
      action={<LinkButton href="/onboarding/connect?view=pick">Send the link request</LinkButton>}
      aside={
        <AsideCard
          title="What linking does"
          finePrint="Unlink us from Google Ads whenever you like."
        >
          It lets PPCWay build and change campaigns inside this one account. It does not give us
          your Google password, your other Google services, or any way to spend past the daily
          budget you set.
        </AsideCard>
      }
    >
      <FormCard>
        <SectionTitle>Signed in as</SectionTitle>
        <StatusStrip>dana@alphaplumbing.ca</StatusStrip>
        <FactField
          label="The manager account you will see in Google Ads"
          value="PPCWay · 118-402-7751"
        />
        <SectionTitle>Which of these is you?</SectionTitle>
        <ChoiceList
          value={choice}
          onChange={setChoice}
          rows={[
            {
              id: "have",
              name: "I already have a Google Ads account",
              detail: "We send a link request and you accept it. About a minute.",
              status: "Choose",
            },
            {
              id: "agency",
              name: "Someone else runs it for me",
              detail: "Your agency has to release the account before we can link it.",
              status: "Choose",
            },
            {
              id: "none",
              name: "I do not have one yet",
              detail: "We can open one for you. There is a queue, so this is not instant.",
              status: "Join queue",
            },
          ]}
        />
      </FormCard>
    </OnboardingShell>
  );
}

/* Frame at (4800, 4778): pick the account. */
function PickView() {
  const [choice, setChoice] = useState("main");
  return (
    <OnboardingShell
      step="connect"
      headline="Which account should we manage?"
      subline="These are the Google Ads accounts on your Google login. Pick the one your ads should run in. We only list accounts you are an admin on."
      action={<LinkButton href="/onboarding/connect?view=accept">Send the link request</LinkButton>}
      aside={
        <AsideCard
          title="Two things Google locks"
          finePrint="An account can only have one manager at a time."
        >
          Currency and time zone are fixed when a Google Ads account is created and can never be
          changed. Every budget and every report will use them, so if the account you pick has the
          wrong currency, make a fresh one instead.
        </AsideCard>
      }
    >
      <FormCard>
        <SectionTitle>Signed in as</SectionTitle>
        <StatusStrip>dana@alphaplumbing.ca</StatusStrip>
        <FactField
          label="Currency and time zone on the account you picked"
          value="CAD · America/Toronto"
        />
        <SectionTitle>Accounts on this Google login</SectionTitle>
        <ChoiceList
          value={choice}
          onChange={setChoice}
          rows={[
            {
              id: "main",
              name: "Alpha Plumbing",
              detail: "742-118-9063 · CAD · active · no manager linked",
              status: "Choose",
            },
            {
              id: "test",
              name: "Alpha Plumbing Test",
              detail: "119-403-2288 · CAD · has never spent",
              status: "Choose",
            },
            {
              id: "old",
              name: "Alpha Plumbing (old)",
              detail: "556-201-7734 · managed by Northline Media",
              status: "Ask them to unlink",
              statusTone: "red",
              muted: true,
            },
          ]}
        />
      </FormCard>
    </OnboardingShell>
  );
}

/* Frame at (6400, 4778): the request is waiting in Google Ads. */
function AcceptView() {
  return (
    <OnboardingShell
      step="connect"
      headline="Now say yes inside Google Ads."
      subline="Google will not let us in until you accept from your own account. The request is already sitting there waiting for you."
      action={
        <LinkButton href="/onboarding/connect?view=accept-choice">Open Google Ads</LinkButton>
      }
      aside={
        <AsideCard title="Nothing has changed yet" finePrint="The request expires after 30 days.">
          Until you accept, we cannot see inside your account and cannot spend a cent in it. If you
          never accept, the request quietly expires. We never bill you for ads at any point. Google
          does that directly.
        </AsideCard>
      }
    >
      <FormCard>
        <SectionTitle>Where to click</SectionTitle>
        <StatusStrip tone="amber">Google Ads · Admin · Access and security · Managers</StatusStrip>
        <FactField label="The request will come from" value="PPCWay · manager 118-402-7751" />
        <SectionTitle>Where we are</SectionTitle>
        <ChoiceList
          rows={[
            {
              id: "sent",
              name: "We sent the request",
              detail: "Sent at 2:41 pm to account 742-118-9063.",
              status: "Done",
              statusTone: "brand",
              fill: "brand",
            },
            {
              id: "you",
              name: "You accept it in Google Ads",
              detail: "Sign in as an admin, open Managers, accept PPCWay.",
              status: "Waiting on you",
              statusTone: "amber",
              fill: "amber",
            },
            {
              id: "build",
              name: "We start building",
              detail: "Starts by itself within a minute of you accepting.",
              status: "Next",
            },
          ]}
        />
      </FormCard>
    </OnboardingShell>
  );
}

/* Frame at (8000, 4778): accept it yourself, or let PPCWay. */
function AcceptChoiceView() {
  const [choice, setChoice] = useState<"us" | "me">("us");
  return (
    <OnboardingShell
      step="connect"
      headline="Accept the link yourself, or let us."
      subline="Google needs an admin of your account to accept our request. Do it in Google Ads, or give us your OK and we accept it for you now, using the Google sign-in you just gave us."
      action={
        <LinkButton href="/onboarding/connect?view=connected">
          {choice === "us" ? "Accept for me" : "Open Google Ads"}
        </LinkButton>
      }
      aside={
        <AsideCard
          title="What 'for me' means"
          finePrint="The request expires after 30 days either way."
        >
          PPCWay accepts the request on your behalf, once. You stay the owner, and you can remove
          PPCWay as a manager in Google Ads at any time.
        </AsideCard>
      }
    >
      <FormCard>
        <SectionTitle>Where we are</SectionTitle>
        <ChoiceList
          rows={[
            {
              id: "sent",
              name: "We sent the request",
              detail: "Sent at 2:41 pm to account 742-118-9063.",
              status: "Done",
              statusTone: "brand",
              fill: "brand",
            },
            {
              id: "accept",
              name: "Accept the request: you, or us with your OK",
              detail: "Your OK is recorded with your name and the time.",
              status: "Your choice",
              statusTone: "amber",
              fill: "amber",
            },
            {
              id: "build",
              name: "We start building",
              detail: "Starts by itself within a minute of you accepting.",
              status: "Next",
            },
          ]}
        />
        <OptionCard
          name="accept"
          title="Accept it for me"
          meta="Takes a few seconds. We press Accept once and change nothing else."
          selected={choice === "us"}
          onSelect={() => setChoice("us")}
        />
        <OptionCard
          name="accept"
          title="I'll accept it in Google Ads"
          meta="Admin, then Access and security, then Managers, then Accept."
          selected={choice === "me"}
          onSelect={() => setChoice("me")}
        />
      </FormCard>
    </OnboardingShell>
  );
}

/* Frame at (9600, 4778): linked, and what was found. */
function ConnectedView() {
  return (
    <OnboardingShell
      step="connect"
      headline="Connected. Here is what we found."
      subline="We checked your account the second it linked. Two things need you, and both are far quicker to do now than after we have written your ads."
      action={
        <>
          <LinkButton href="/onboarding/business" variant="secondary">
            Do it later
          </LinkButton>
          <LinkButton href="/onboarding/business">Add a card on Google</LinkButton>
        </>
      }
      aside={
        <AsideCard title="Why we ask now" finePrint="We never see or store your card details.">
          Adding a card on Google takes about three minutes, and it is the one part of this we are
          not allowed to do for you. Getting it out of the way now means that when your campaign is
          ready, launching is one click instead of a detour.
        </AsideCard>
      }
    >
      <FormCard>
        <SectionTitle>Your account</SectionTitle>
        <StatusStrip tone="brand">Alpha Plumbing · 742-118-9063 · linked and active</StatusStrip>
        <FactField
          label="Google Ads account status"
          value="Serving · no suspensions · no policy strikes"
        />
        <SectionTitle>Before anything can go live</SectionTitle>
        <ChoiceList
          rows={[
            {
              id: "card",
              name: "A payment method on Google",
              detail: "Google takes card details on their own site, and only they can.",
              status: "Needs you",
              statusTone: "amber",
              fill: "amber",
            },
            {
              id: "conv",
              name: "Conversion tracking",
              detail: "Without it we would be guessing, so we will not launch blind.",
              status: "Needs you",
              statusTone: "amber",
              fill: "amber",
            },
            {
              id: "cur",
              name: "Currency and time zone",
              detail: "CAD and America/Toronto, which match where you work.",
              status: "Ready",
              statusTone: "brand",
            },
          ]}
        />
      </FormCard>
    </OnboardingShell>
  );
}

/* Frame at (11200, 4778): a new account is being opened. */
function QueueView() {
  return (
    <OnboardingShell
      step="connect"
      headline="We are opening a Google Ads account for you."
      subline="Google limits how many new accounts we can open each week, so there is a short queue. You can finish everything else while you wait."
      footnote="About 15 minutes of your time. Google opens the account in 1 to 2 days."
      action={<LinkButton href="/onboarding/business">Carry on with your business</LinkButton>}
      aside={
        <AsideCard title="Why there is a wait" finePrint="We email you the moment it is ready.">
          Google caps how many accounts one manager can open in a week. We would rather tell you now
          than promise a minute and leave you waiting. If you already have an account, linking it is
          instant.
        </AsideCard>
      }
    >
      <FormCard>
        <SectionTitle>Your place in the queue</SectionTitle>
        <StatusStrip tone="amber">
          Number 6 of 14 this week · usually ready within 2 days
        </StatusStrip>
        <FactField
          label="The account will be opened for"
          value="dana@alphaplumbing.ca · CAD · America/Toronto"
        />
        <SectionTitle>What happens next</SectionTitle>
        <ChoiceList
          rows={[
            {
              id: "answer",
              name: "Answer the questions about your business",
              detail: "You can do this now. It is the longest step anyway.",
              status: "Now",
              statusTone: "brand",
              fill: "brand",
            },
            {
              id: "open",
              name: "We open the account and link it",
              detail: "It arrives already connected, with no request to accept.",
              status: "1 to 2 days",
              statusTone: "amber",
            },
            {
              id: "card",
              name: "You add a card on Google's own site",
              detail: "The one step only you can do. About three minutes.",
              status: "Then",
            },
          ]}
        />
      </FormCard>
    </OnboardingShell>
  );
}

/* Frame at (0, 5838): Google will not open a new account this week. */
function QueueFullView() {
  return (
    <OnboardingShell
      step="connect"
      headline="Google won't let us open a new account this week."
      subline="Google limits how many accounts a manager can open while it builds up spending history, and ours has hit this week's limit. Your answers are saved, and here are three ways forward."
      footnote="About 15 minutes of your time once an account is linked."
      action={
        <LinkButton href="/onboarding/connect?view=route">Link an existing account</LinkButton>
      }
      aside={
        <AsideCard title="Why this happens" finePrint="Nothing has been charged.">
          Google applies its own sign-up rules when a manager opens accounts, and newer managers get
          lower limits. It is not about your business.
        </AsideCard>
      }
    >
      <FormCard>
        <SectionTitle>What Google said</SectionTitle>
        <StatusStrip tone="amber" icon="none">
          New accounts paused for our manager account until Monday
        </StatusStrip>
        <FactField
          label="The account will be opened for"
          value="dana@alphaplumbing.ca · CAD · America/Toronto"
        />
        <SectionTitle>Your options</SectionTitle>
        <ChoiceList
          rows={[
            {
              id: "link",
              name: "Link an account you already have",
              detail: "Instant. Any Google Ads account you are an admin on.",
              status: "Fastest",
              statusTone: "brand",
              fill: "brand",
            },
            {
              id: "wait",
              name: "Wait for our next slot",
              detail: "We open it the moment the limit resets and email you.",
              status: "Mon 14 Sep",
              statusTone: "amber",
            },
            {
              id: "self",
              name: "Open one yourself at ads.google.com",
              detail: "About ten minutes, then come back and link it.",
              status: "Also works",
            },
          ]}
        />
      </FormCard>
    </OnboardingShell>
  );
}

/* Frame at (1600, 5838): the account already has campaigns. */
function ExistingView() {
  const [choices, setChoices] = useState<Record<string, string>>({
    furnace: "Let PPCWay manage it",
    ac: "Let PPCWay manage it",
    display: "Pause it",
    promo: "Leave it to me",
  });
  const set = (key: string) => (next: string) => setChoices((c) => ({ ...c, [key]: next }));
  return (
    <OnboardingShell
      step="connect"
      headline="Your account already has 4 campaigns."
      subline="Northline Media set these up before. Tell us what to do with each one. Anything you keep for yourself, we never touch."
      action={<LinkButton href="/onboarding/business">Continue</LinkButton>}
      aside={
        <AsideCard title="Why we ask" finePrint="Changes you make in Google Ads are always kept.">
          Two campaigns bidding on the same searches push your own prices up, so we check for
          overlap. You can hand a campaign over, or take it back, at any time in Settings.
        </AsideCard>
      }
    >
      <FormCard>
        <p className="text-muted text-[13px] leading-4 font-semibold">
          Summit Heating &amp; Cooling · 318-775-2046 · last 30 days
        </p>
        <CampaignCard
          title="Furnace Repair – Search"
          meta="Search · $1,120 · 38 calls · by Northline Media"
          suggestion="We suggest managing"
          suggestionTone="brand"
          note="Works well, with enough calls to start on a target cost per call."
          value={choices.furnace}
          onChange={set("furnace")}
        />
        <CampaignCard
          title="AC Install Brampton"
          meta="Search · $640 · 9 calls at $71 · by Northline"
          suggestion="We suggest managing"
          suggestionTone="brand"
          note="Calls cost too much. We would tighten its keywords first."
          value={choices.ac}
          onChange={set("ac")}
        />
        <CampaignCard
          title="Display – Remarketing"
          meta="Display · $410 · no calls in 90 days"
          suggestion="We suggest pausing"
          suggestionTone="amber"
          note="PPCWay does not run display ads, and this one has not brought a call in 90 days."
          value={choices.display}
          onChange={set("display")}
        />
        <CampaignCard
          title="Spring Promo 2026"
          meta="Search · paused since 31 May"
          suggestion="We suggest leaving it"
          suggestionTone="grey"
          note="Stays paused, and we never touch it."
          value={choices.promo}
          onChange={set("promo")}
        />
      </FormCard>
    </OnboardingShell>
  );
}

export function WorkingButton({ label, working }: { label: string; working: string }) {
  const [busy, setBusy] = useState(false);
  return (
    <Button onClick={() => setBusy(true)} working={busy && working}>
      {label}
    </Button>
  );
}
