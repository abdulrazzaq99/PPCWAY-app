"use client";

import { useState } from "react";
import { AsideCard, FormCard, OnboardingShell, SectionTitle } from "@/components/onboarding/shell";
import { ChoiceList, FactField, OptionCard, StatusStrip } from "@/components/onboarding/blocks";
import { ChipRows } from "@/components/onboarding/extras";
import { Field, Input } from "@/components/ui/field";
import { LinkButton } from "@/components/ui/button";

import type { CallsViewName } from "@/components/onboarding/view-names";

export function CallsView({ view }: { view: CallsViewName }) {
  switch (view) {
    case "verify":
      return <VerifyView />;
    case "tag":
      return <TagView />;
    case "sales":
      return <SalesView />;
    case "existing":
      return <ExistingConversionsView />;
    case "quotes":
      return <QuotesView />;
    default:
      return <NumberView />;
  }
}

/* Frame at (9600, 5838): the tracking number. */
function NumberView() {
  const [rule, setRule] = useState("30s");
  return (
    <OnboardingShell
      step="calls"
      headline="Let's count the calls."
      subline="A tracking number forwards straight to your phone, so we can tell which ads made it ring. Your own number stays out of the ad."
      action={<LinkButton href="/onboarding/calls?view=verify">Continue</LinkButton>}
      aside={
        <AsideCard title="About the number" finePrint="The number is included in your plan.">
          The tracking number shows up only in your ads. Anyone who already has your real number
          reaches you the same way as before. Call recording stays off unless you turn it on.
        </AsideCard>
      }
    >
      <FormCard>
        <SectionTitle>Your tracking number</SectionTitle>
        <StatusStrip tone="brand">Your new number is (905) 555-0142.</StatusStrip>
        <Field label="Ring this phone">
          {(id) => <Input id={id} name="ring" type="tel" defaultValue="(416) 555-0198" />}
        </Field>
        <SectionTitle>How calls get counted</SectionTitle>
        <ChoiceList
          value={rule}
          onChange={setRule}
          rows={[
            {
              id: "30s",
              name: "Every call over 30 seconds",
              detail: "The usual choice. Wrong numbers rarely last that long.",
              status: "Choose",
            },
            {
              id: "any",
              name: "Every call, any length",
              detail: "Counts more, but hang-ups start to look like wins.",
              status: "Choose",
            },
            {
              id: "marked",
              name: "Only calls you mark as jobs",
              detail: "Most exact. You tag the good ones in Activity.",
              status: "Choose",
            },
          ]}
        />
      </FormCard>
    </OnboardingShell>
  );
}

/* Frame at (11200, 5838): one real result before launch. */
function VerifyView() {
  return (
    <OnboardingShell
      step="calls"
      headline="We need to see one real result first."
      subline="A tag that exists is not proof that it works. We wait for one genuine call or form before letting anything go live, because optimising on broken tracking is worse than not advertising at all."
      action={<LinkButton href="/onboarding/review">Send a test enquiry</LinkButton>}
      aside={
        <AsideCard
          title="If this breaks later"
          finePrint="Consent banners hide some results, so Google counts slightly low."
        >
          Tracking usually breaks during a site redesign or a plugin update, and it breaks quietly.
          We watch for a sudden drop to zero and treat it as a tracking fault rather than a
          performance one, so we stop changing bids until it is fixed.
        </AsideCard>
      }
    >
      <FormCard>
        <SectionTitle>How we are tracking</SectionTitle>
        <StatusStrip tone="brand">Tag Manager found on your site · GTM-5K2QF8</StatusStrip>
        <FactField
          label="What counts as a result for you"
          value="A call over 30 seconds, or a form sent"
        />
        <SectionTitle>Three checks before launch</SectionTitle>
        <ChoiceList
          rows={[
            {
              id: "tag",
              name: "The tag is on every page",
              detail: "We checked 14 pages and found it on all of them.",
              status: "Passed",
              statusTone: "brand",
              fill: "brand",
            },
            {
              id: "call",
              name: "A call is recorded",
              detail: "We rang your tracking number and Google counted it.",
              status: "Passed",
              statusTone: "brand",
              fill: "brand",
            },
            {
              id: "form",
              name: "A form is recorded",
              detail: "Send one test enquiry from your site and we will watch for it.",
              status: "Waiting on you",
              statusTone: "amber",
              fill: "amber",
            },
          ]}
        />
      </FormCard>
    </OnboardingShell>
  );
}

/* Frame at (0, 7030): no Tag Manager, so the tag goes in by hand. */
function TagView() {
  return (
    <OnboardingShell
      step="calls"
      headline="Add one small tag to your website."
      subline="We did not find Google Tag Manager on your site, so the tag goes in by hand. It takes about five minutes, or send these steps to whoever built your site."
      action={<LinkButton href="/onboarding/calls?view=verify">Email my web designer</LinkButton>}
      aside={
        <AsideCard
          title="Not comfortable editing code?"
          finePrint="The tag only tells Google when someone calls or sends a form."
        >
          Send these steps to your web designer in one click. We include the tag, exactly where it
          goes, and a way for them to check it worked. Nothing goes live until it does.
        </AsideCard>
      }
    >
      <FormCard>
        <SectionTitle>Your site</SectionTitle>
        <StatusStrip tone="brand">
          Built with WordPress, going by your site&rsquo;s code
        </StatusStrip>
        <div className="flex flex-col gap-2">
          <p className="text-label text-ink">Your tag, ready to paste</p>
          <pre className="bg-rail text-brand-bar flex h-[46px] items-center overflow-x-auto rounded-[12px] px-[17px] font-mono text-[14px]">
            gtag(&apos;config&apos;, &apos;AW-11705584239&apos;)
          </pre>
        </div>
        <SectionTitle>Three steps</SectionTitle>
        <ChoiceList
          rows={[
            {
              id: "copy",
              name: "Copy the tag",
              detail: "One click copies it. It is the same on every page.",
              status: "Copy",
              statusTone: "brand",
              fill: "brand",
            },
            {
              id: "paste",
              name: "Paste it into your site's header",
              detail: "WordPress: Appearance, Theme File Editor, header.php",
              status: "Show me",
              statusTone: "brand",
            },
            {
              id: "test",
              name: "Send us a test enquiry",
              detail: "We watch for it and tell you the moment it counts.",
              status: "Then",
            },
          ]}
        />
      </FormCard>
    </OnboardingShell>
  );
}

/* Frame at (1600, 7030): an online shop counts sales. */
function SalesView() {
  const [mode, setMode] = useState<"value" | "once">("value");
  return (
    <OnboardingShell
      step="calls"
      headline="Let's count your sales."
      subline="Your shop already sends sales to Google Analytics. We bring them into Google Ads with the order value, so PPCWay can aim for revenue, not just clicks."
      action={<LinkButton href="/onboarding/review">Continue</LinkButton>}
      aside={
        <AsideCard
          title="Why the value matters"
          finePrint="Refunded test orders are removed from your results."
        >
          With order values, Google learns which searches bring bigger baskets. It works best from
          about 15 sales a month; below that we aim for sales, not value.
        </AsideCard>
      }
    >
      <FormCard>
        <p className="text-ink text-[15px] leading-[18px] font-semibold">
          What we found on birchandwick.ca
        </p>
        <ChipRows
          rows={[
            {
              title: "Google Analytics 4",
              meta: "G-7QX2LM41 · on every page",
              chip: "Found",
              tone: "brand",
            },
            {
              title: "Purchase event",
              meta: "Sends the order value in CAD with each sale",
              chip: "Found",
              tone: "brand",
            },
            {
              title: "Tag Manager",
              meta: "GTM-P9HF2C · we can add the Google Ads tag for you",
              chip: "Found",
              tone: "brand",
            },
          ]}
        />
        <p className="text-ink text-[15px] leading-[18px] font-semibold">How sales are counted</p>
        <OptionCard
          name="sales"
          title="Every purchase, with its value"
          meta="Lets Google bid more for a $90 gift set than an $18 candle."
          selected={mode === "value"}
          onSelect={() => setMode("value")}
        />
        <OptionCard
          name="sales"
          title="One per customer"
          meta="For shops where the first order is what matters."
          selected={mode === "once"}
          onSelect={() => setMode("once")}
        />
        <ChipRows
          rows={[
            {
              title: "Test sale",
              meta: "Place a small order, then refund it. It shows here within about 10 minutes.",
              chip: "Waiting",
              tone: "amber",
            },
          ]}
        />
      </FormCard>
    </OnboardingShell>
  );
}

/* Frame at (3200, 7030): conversions already exist in the account. */
function ExistingConversionsView() {
  const [aim, setAim] = useState<"calls" | "form">("calls");
  return (
    <OnboardingShell
      step="calls"
      headline="You already count some results. Let's check them."
      subline="Your account has three conversions set up. One works, one looks broken and one counts far too much. We aim only for the one that works."
      action={<LinkButton href="/onboarding/review">Continue</LinkButton>}
      aside={
        <AsideCard title="Why this matters" finePrint="Nothing is deleted in Google Ads.">
          If page views counted as results, Google would think you get about 260 a month and bid far
          too high. Cleaning this up first is the cheapest win we can give you.
        </AsideCard>
      }
    >
      <FormCard>
        <p className="text-ink text-[15px] leading-[18px] font-semibold">
          Found in your Google Ads account
        </p>
        <ChipRows
          rows={[
            {
              title: "Calls from ads",
              meta: "Google forwarding number · 47 in 30 days · last one 2 days ago",
              chip: "Working",
              tone: "brand",
            },
            {
              title: "Contact form, from Google Analytics",
              meta: "Last counted 41 days ago · the form may have changed",
              chip: "Looks broken",
              tone: "amber",
            },
            {
              title: "Thank-you page viewed",
              meta: "212 in 30 days against 47 calls · counts every visit",
              chip: "Counts too much",
              tone: "red",
            },
          ]}
        />
        <p className="text-ink text-[15px] leading-[18px] font-semibold">What PPCWay aims for</p>
        <OptionCard
          name="aim"
          title="Calls from ads"
          meta="Proven, and it is what Summit wants: booked service calls."
          selected={aim === "calls"}
          onSelect={() => setAim("calls")}
        />
        <OptionCard
          name="aim"
          title="Contact form"
          meta="Fix it first. We can check the form with a test submission."
          selected={aim === "form"}
          onSelect={() => setAim("form")}
        />
        <ChipRows
          rows={[
            {
              title: "Stop aiming for 'Thank-you page viewed'",
              meta: "It stays in Google Ads, just not as a result",
              chip: "Suggested",
              tone: "amber",
            },
          ]}
        />
      </FormCard>
    </OnboardingShell>
  );
}

/* Frame at (4800, 7030): count quote requests too. */
function QuotesView() {
  const [mode, setMode] = useState<"both" | "forms">("both");
  return (
    <OnboardingShell
      step="calls"
      headline="And count the quote requests."
      subline="Your plan counts calls and forms. We found the quote form on your site and can count each one sent, through the Tag Manager access you gave us."
      action={<LinkButton href="/onboarding/review">Continue</LinkButton>}
      aside={
        <AsideCard title="Why a test" finePrint="Test requests are removed from your results.">
          A form tag can look fine and count nothing. One real test proves it, just like the test
          call. We do not launch until both have counted.
        </AsideCard>
      }
    >
      <FormCard>
        <p className="text-ink text-[15px] leading-[18px] font-semibold">
          What we found on alphaplumbing.ca
        </p>
        <ChipRows
          rows={[
            {
              title: "'Get a quote' form",
              meta: "alphaplumbing.ca/quote · sends people to a thank-you page",
              chip: "Found",
              tone: "brand",
            },
            {
              title: "Tag Manager container",
              meta: "GTM-5K2QF8 · we add one tag, nothing else changes",
              chip: "Ready",
              tone: "brand",
            },
          ]}
        />
        <p className="text-ink text-[15px] leading-[18px] font-semibold">
          How the two count together
        </p>
        <OptionCard
          name="quotes"
          title="Calls first, forms as well"
          meta="PPCWay aims for calls, and a quote request counts as a result too."
          selected={mode === "both"}
          onSelect={() => setMode("both")}
        />
        <OptionCard
          name="quotes"
          title="Forms only"
          meta="For businesses that do not take calls. Not for you."
          selected={mode === "forms"}
          onSelect={() => setMode("forms")}
        />
        <ChipRows
          rows={[
            {
              title: "Test request",
              meta: "Send the form once with 'TEST' in the name. It shows here within about 10 minutes.",
              chip: "Waiting",
              tone: "amber",
            },
          ]}
        />
      </FormCard>
    </OnboardingShell>
  );
}
