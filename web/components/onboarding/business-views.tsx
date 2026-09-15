"use client";

import { useState } from "react";
import { AsideCard, FormCard, OnboardingShell, SectionTitle } from "@/components/onboarding/shell";
import { ChoiceList, FactField, StatusStrip } from "@/components/onboarding/blocks";
import { Note, OptionalField } from "@/components/onboarding/extras";
import { Field, Input } from "@/components/ui/field";
import { LinkButton } from "@/components/ui/button";

import type { BusinessViewName } from "@/components/onboarding/view-names";

export function BusinessView({ view }: { view: BusinessViewName }) {
  switch (view) {
    case "basics":
      return <BasicsView />;
    case "money":
      return <MoneyView />;
    case "sources":
      return <SourcesView />;
    case "area":
      return <AreaBudgetView />;
    case "manual":
      return <ManualView />;
    default:
      return <AboutView />;
  }
}

/* Frame at (3200, 5838): the business, with the site already read. */
function AboutView() {
  const [goal, setGoal] = useState("calls");
  return (
    <OnboardingShell
      step="business"
      headline="Tell us about your business."
      subline="This is the part that matters. Your answers become the words in your ads, so the more exact you are, the fewer wasted clicks you pay for."
      action={<LinkButton href="/onboarding/business?view=basics">Continue</LinkButton>}
      aside={
        <AsideCard title="Why we ask" finePrint="You can change any of this later in Settings.">
          Google decides who sees your ad from the words in it. A plumber who says emergency drain
          cleaning in Mississauga pays less per call than one who says plumbing services.
        </AsideCard>
      }
    >
      <FormCard>
        <SectionTitle>About your business</SectionTitle>
        <StatusStrip tone="brand">We read alphaplumbing.ca and filled some of this in.</StatusStrip>
        <Field label="Business name">
          {(id) => <Input id={id} name="businessName" defaultValue="Alpha Plumbing" />}
        </Field>
        <SectionTitle>What should PPCWay chase?</SectionTitle>
        <ChoiceList
          value={goal}
          onChange={setGoal}
          rows={[
            {
              id: "calls",
              name: "Phone calls",
              detail: "Best when you book jobs over the phone.",
              status: "Choose",
            },
            {
              id: "bookings",
              name: "Booked jobs on your site",
              detail: "Best when you have an online booking form.",
              status: "Choose",
            },
            {
              id: "quotes",
              name: "Quote requests",
              detail: "Best when people fill in a form and you call back.",
              status: "Choose",
            },
          ]}
        />
        <OptionalField
          label="Who are your best customers? Optional"
          placeholder="For example, owners of older homes, or property managers"
        />
      </FormCard>
    </OnboardingShell>
  );
}

/* Audit frame 1: the basics, as the intake form an agency would run. */
function BasicsView() {
  const [existing, setExisting] = useState("no");
  return (
    <OnboardingShell
      step="business"
      headline="Tell us about your business."
      subline="We read your website and filled most of this in. Change anything that looks wrong. This is the main step, about three minutes."
      action={<LinkButton href="/onboarding/business?view=money">Continue</LinkButton>}
      aside={
        <AsideCard
          title="What we found on your site"
          finePrint="We only read pages your site allows, and we change nothing on it."
        >
          Alpha Plumbing, licensed plumbers in Mississauga since 2009. Emergency repairs, water
          heaters, drain cleaning and leak detection. A phone number on every page, and a contact
          form.
        </AsideCard>
      }
    >
      <FormCard>
        <SectionTitle>About your business</SectionTitle>
        <Field label="Your website">
          {(id) => <Input id={id} name="website" defaultValue="alphaplumbing.ca" />}
        </Field>
        <Field label="What you do">
          {(id) => <Input id={id} name="trade" defaultValue="Plumbing" />}
        </Field>
        <Field label="Where you work">
          {(id) => (
            <Input id={id} name="area" defaultValue="Within 25 km of Mississauga, Ontario" />
          )}
        </Field>
        <Field label="The number to ring">
          {(id) => <Input id={id} name="phone" type="tel" defaultValue="(905) 555-0142" />}
        </Field>
        <Field label="When you answer the phone">
          {(id) => <Input id={id} name="hours" defaultValue="Monday to Saturday, 7 am to 8 pm" />}
        </Field>
        <SectionTitle>Do you already run Google Ads?</SectionTitle>
        <ChoiceList
          value={existing}
          onChange={setExisting}
          rows={[
            {
              id: "no",
              name: "No, this is new",
              detail: "We set everything up from scratch",
              status: "Choose",
            },
            {
              id: "yes",
              name: "Yes, we already have an account",
              detail: "We check it for wasted spend before changing anything",
              status: "Choose",
            },
          ]}
        />
      </FormCard>
    </OnboardingShell>
  );
}

/* Audit frame 2: the money. */
function MoneyView() {
  const [goal, setGoal] = useState("calls");
  return (
    <OnboardingShell
      step="business"
      headline="What is a customer worth to you?"
      subline="These answers set your budget and what we aim for. Rough numbers are fine, and you can change them any time."
      action={<LinkButton href="/onboarding/business?view=sources">Continue</LinkButton>}
      aside={
        <AsideCard
          title="Why we ask"
          finePrint="Google bills the ads. PPCWay never spends more than your monthly total."
        >
          A job worth $450 means we can pay up to $35 for a call and still make you money. Eight
          jobs a week tells us when to stop spending. The goal decides what we count as a result.
        </AsideCard>
      }
    >
      <FormCard>
        <SectionTitle>The money</SectionTitle>
        <Field label="What a typical job is worth">
          {(id) => <Input id={id} name="jobValue" defaultValue="$450" />}
        </Field>
        <Field label="How many new jobs a week you could take">
          {(id) => <Input id={id} name="capacity" inputMode="numeric" defaultValue="8" />}
        </Field>
        <Field label="Monthly budget">
          {(id) => <Input id={id} name="budget" defaultValue="$1,200 a month, about $40 a day" />}
        </Field>
        <Field label="Who else shows up when people search, optional">
          {(id) => <Input id={id} name="competitors" defaultValue="Mr. Rooter, Drain King" />}
        </Field>
        <SectionTitle>What do you want from your ads?</SectionTitle>
        <ChoiceList
          value={goal}
          onChange={setGoal}
          rows={[
            {
              id: "calls",
              name: "Phone calls",
              detail: "Best when people need you the same day",
              status: "Choose",
            },
            {
              id: "forms",
              name: "Form enquiries",
              detail: "People send their details from your site",
              status: "Choose",
            },
            {
              id: "sales",
              name: "Online sales",
              detail: "People buy from your site",
              status: "Choose",
            },
          ]}
        />
      </FormCard>
    </OnboardingShell>
  );
}

/* Frame at (4800, 5838): what the campaign is built from. */
function SourcesView() {
  return (
    <OnboardingShell
      step="business"
      headline="Six things, and we already have three."
      subline="This is everything your campaign gets built from. Anything we take off your site, you get to correct before a single ad runs."
      action={<LinkButton href="/onboarding/business?view=area">Continue</LinkButton>}
      aside={
        <AsideCard
          title="What we never invent"
          finePrint="While we read your site, its text is sent to Anthropic, the company whose AI writes the ads. Nothing reaches Google until you approve it."
        >
          Keywords come from Google&rsquo;s own planner, not from a model making them up. Every term
          we show you was returned by Google for your trade and your area. The wording of the ads is
          written for you, then checked against Google&rsquo;s rules before you see it.
        </AsideCard>
      }
    >
      <FormCard>
        <SectionTitle>Reading your site now</SectionTitle>
        <StatusStrip tone="brand">Reading alphaplumbing.ca · 14 of 25 pages</StatusStrip>
        <FactField
          label="If your site is thin or built in JavaScript"
          value="We stop guessing and ask you instead"
        />
        <SectionTitle>What the campaign is built from</SectionTitle>
        <ChoiceList
          rows={[
            {
              id: "site",
              name: "Your website",
              detail: "Up to 25 pages, read once, for services and wording.",
              status: "From your site",
            },
            {
              id: "sell",
              name: "What you actually sell",
              detail: "Pulled from those pages, then you fix whatever we misread.",
              status: "From your site",
            },
            {
              id: "travel",
              name: "Where you will travel to",
              detail: "A radius or a list of towns. Decides who ever sees the ad.",
              status: "From you",
              statusTone: "ink",
            },
            {
              id: "win",
              name: "What counts as a win",
              detail: "Calls, forms or booked jobs. We optimise toward this one thing.",
              status: "From you",
              statusTone: "ink",
            },
            {
              id: "daily",
              name: "How much a day",
              detail: "Sets how many search terms we can afford to chase.",
              status: "From you",
              statusTone: "ink",
            },
            {
              id: "ads",
              name: "Your Google Ads account",
              detail: "Linked. Billing and call tracking come in later steps.",
              status: "Done",
              statusTone: "brand",
              fill: "brand",
            },
          ]}
        />
      </FormCard>
    </OnboardingShell>
  );
}

/* Frame at (6400, 5838): where you work and what you can spend. */
function AreaBudgetView() {
  const [budget, setBudget] = useState("40");
  return (
    <OnboardingShell
      step="business"
      headline="Where you work, and what you can spend."
      subline="These two answers decide who sees your ad and how often. You can change both later, and we will tell you what each change is likely to do."
      action={<LinkButton href="/onboarding/website">Continue</LinkButton>}
      aside={
        <AsideCard
          title="About these estimates"
          finePrint="Google bills your own card for this, not us."
        >
          They come from Google&rsquo;s own planner for plumbers near Mississauga, not from us, and
          real weeks vary. We never go past the daily amount you pick, and Google never charges more
          than about 30 times it in a month.
        </AsideCard>
      }
    >
      <FormCard>
        <SectionTitle>Your trade and your area</SectionTitle>
        <StatusStrip tone="brand">Plumber · taken from your website</StatusStrip>
        <Field label="Where you will travel to">
          {(id) => (
            <Input
              id={id}
              name="travel"
              defaultValue="25 km around Mississauga, plus Oakville and Brampton"
            />
          )}
        </Field>
        <SectionTitle>How much a day</SectionTitle>
        <ChoiceList
          value={budget}
          onChange={setBudget}
          rows={[
            {
              id: "25",
              name: "$25 a day",
              detail: "About $760 a month · Google expects 30 to 40 calls",
              status: "Choose",
            },
            {
              id: "40",
              name: "$40 a day",
              detail: "About $1,200 a month · Google expects 45 to 60 calls",
              status: "Choose",
            },
            {
              id: "60",
              name: "$60 a day",
              detail: "About $1,800 a month · Google expects 60 to 80 calls",
              status: "Choose",
            },
          ]}
        />
        <Note>
          Below about $12 a day, roughly $350 a month, Google gets too few clicks to learn from, so
          results come slowly.
        </Note>
      </FormCard>
    </OnboardingShell>
  );
}

/* Frame at (8000, 5838): the site could not be read. */
function ManualView() {
  const [services, setServices] = useState<string[]>(["emergency", "drains"]);
  const toggle = (id: string) =>
    setServices((s) => (s.includes(id) ? s.filter((x) => x !== id) : [...s, id]));
  return (
    <OnboardingShell
      step="business"
      headline="We couldn't read your website, so tell us yourself."
      subline="Our reader can't see into alphaplumbing.ca. Five quick answers instead, and you can change anything later."
      action={<LinkButton href="/onboarding/business?view=area">Continue</LinkButton>}
      aside={
        <AsideCard
          title="Why we couldn't read it"
          finePrint="We never guess. What you type here is what your ads are built from."
        >
          Some sites only show their words after a script runs, so our reader sees a blank page. It
          is common and nothing is wrong with your site.
        </AsideCard>
      }
    >
      <FormCard>
        <SectionTitle>About your business</SectionTitle>
        <StatusStrip tone="amber" icon="none">
          Our reader stopped: the site loads its words with a script.
        </StatusStrip>
        <Field label="Business name">
          {(id) => <Input id={id} name="businessName" defaultValue="Alpha Plumbing" />}
        </Field>
        <SectionTitle>What do you do? Pick all that apply</SectionTitle>
        <div
          role="group"
          aria-label="What you do"
          className="border-line overflow-hidden rounded-[12px] border"
        >
          {[
            { id: "emergency", name: "Emergency repairs", detail: "Burst pipes, leaks, no water" },
            { id: "drains", name: "Drains", detail: "Blocked toilets, slow drains, camera checks" },
            { id: "heaters", name: "Water heaters", detail: "Repairs and new installs" },
          ].map((row, i) => {
            const on = services.includes(row.id);
            return (
              <label
                key={row.id}
                className={
                  "relative flex min-h-[69px] cursor-pointer items-center gap-4 px-[18px] py-4 " +
                  (i > 0 ? "border-line border-t " : "") +
                  (on ? "bg-brand-pale" : "bg-panel hover:bg-line-soft")
                }
              >
                <input
                  type="checkbox"
                  checked={on}
                  onChange={() => toggle(row.id)}
                  className="absolute inset-0 cursor-pointer opacity-0"
                />
                <span className="min-w-0 flex-1">
                  <span className="text-ink block text-[15px] leading-[18px] font-semibold">
                    {row.name}
                  </span>
                  <span className="text-muted mt-[3px] block text-[13px] leading-4">
                    {row.detail}
                  </span>
                </span>
                <span
                  className={
                    "shrink-0 text-[15px] leading-[18px] font-semibold " +
                    (on ? "text-brand" : "text-faint")
                  }
                >
                  {on ? "Selected" : "Choose"}
                </span>
              </label>
            );
          })}
        </div>
        <OptionalField
          label="What makes you different?"
          defaultValue="Licensed since 2009, same-day visits, price agreed first"
        />
        <OptionalField label="Phone number for your ads" defaultValue="(416) 555-0198" />
        <OptionalField
          label="Address, if customers come to you"
          placeholder="Leave blank if you go to them"
        />
      </FormCard>
    </OnboardingShell>
  );
}
