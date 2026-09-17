import Link from "next/link";
import { StatusPill } from "@/components/app/blocks";
import type { ChipTone } from "@/components/app/blocks";
import { LinkButton } from "@/components/ui/button";
import { AuditPage, Card, Pill } from "./shell";

/*
  Frames 181:6011 (Report, already advertising), 181:6215 (Report, not advertising
  yet) and 181:6419 (Mobile · Audit report). Header with the readiness score, four
  panels (listing, website, ads today, competition), what it costs, the first three
  fixes, and the close. On a phone the panels stack and the score sits under the
  headline, as the mobile frame draws it.
*/
type Verdict = "good" | "fix" | "cost";
type Line = { title: string; meta: string; verdict: Verdict };
type Panel = { title: string; score: string; lines: Line[] };
type Sample = {
  date: string;
  business: string;
  summary: string;
  readiness: number;
  panels: Panel[];
  cost: { title: string; body: string };
  fixes: { when: string; title: string; body: string }[];
  close: { title: string; body: string };
};

const CHIP: Record<Verdict, { label: string; tone: ChipTone }> = {
  good: { label: "Good", tone: "pale" },
  fix: { label: "Fix", tone: "amber" },
  cost: { label: "Costing you", tone: "red" },
};

const ADVERTISING: Sample = {
  date: "Audit, 16 September 2026",
  business: "Alpha Plumbing, Mississauga",
  summary:
    "Your listing is strong. Your website cannot prove a call happened, and your ads are paying for searches that were never going to call you.",
  readiness: 62,
  panels: [
    {
      title: "Your Google listing",
      score: "8 of 10",
      lines: [
        {
          title: "Verified, with the right category",
          meta: "Plumber, which is what people search for. Half the listings we check use a category nobody searches.",
          verdict: "good",
        },
        {
          title: "4.6 out of 5, from 87 reviews",
          meta: "Ahead of four of the six plumbers advertising in Mississauga.",
          verdict: "good",
        },
        {
          title: "Four photos",
          meta: "The plumbers above you average twenty four. Photos are free and they move the Maps ranking.",
          verdict: "fix",
        },
        {
          title: "No services listed on the listing",
          meta: "Google shows these under your name, and they feed the Maps ads you are not running yet.",
          verdict: "fix",
        },
      ],
    },
    {
      title: "Your website",
      score: "5 of 10",
      lines: [
        {
          title: "Six service pages, one per job",
          meta: "Emergency, drains, water heaters, taps, toilets and repiping. That is the shape ads like.",
          verdict: "good",
        },
        {
          title: "No conversion tracking found",
          meta: "Nothing on the site tells Google a call or a form happened, so Google is bidding blind on every click you pay for.",
          verdict: "cost",
        },
        {
          title: "Your phone number is an image on mobile",
          meta: "It cannot be tapped. On a phone, for an emergency plumber, that is the whole job.",
          verdict: "fix",
        },
        {
          title: "The emergency page takes 4.8 seconds on a phone",
          meta: "Half the people who tap an ad leave before three.",
          verdict: "fix",
        },
      ],
    },
    {
      title: "Your ads today",
      score: "4 of 10",
      lines: [
        {
          title: "You showed for plumber mississauga this morning",
          meta: "Seen at 11:02, third position, above the map.",
          verdict: "good",
        },
        {
          title: "You also showed for plumbing courses mississauga",
          meta: "That is a student, not a customer. We saw three searches like it in one morning.",
          verdict: "cost",
        },
        {
          title: "Your ad uses three headlines",
          meta: "Google can rotate fifteen. Fewer headlines means fewer auctions you can win.",
          verdict: "fix",
        },
        {
          title: "No call button on the ad we saw",
          meta: "For emergency work, the call button is usually the cheapest conversion on the account.",
          verdict: "fix",
        },
      ],
    },
    {
      title: "Who you are up against",
      score: "For information",
      lines: [
        {
          title: "Six plumbers advertise here",
          meta: "Two of them run ads all night, which is when burst pipes happen.",
          verdict: "fix",
        },
        {
          title: "You have more reviews than four of them",
          meta: "That is the expensive thing to build, and you already have it.",
          verdict: "good",
        },
        {
          title: "Three say a price in the headline",
          meta: "“$49 callout” sets the expectation before anyone clicks yours.",
          verdict: "fix",
        },
        {
          title: "The busiest one answers in under ten minutes",
          meta: "Speed is a ranking signal in Maps, and a closing signal on the phone.",
          verdict: "fix",
        },
      ],
    },
  ],
  cost: {
    title: "About $210 a month, and every call Google cannot see.",
    body: "Judging by the searches we watched you appear for, roughly a fifth of your clicks were never going to call. That part is fixable in a day. The tracking is the bigger cost: with no way to see a call, Google keeps buying the wrong clicks and you cannot tell it otherwise.",
  },
  fixes: [
    {
      when: "Day one",
      title: "Count your calls",
      body: "A tracking number that forwards to your phone, and the Google tag on your site. Until this exists, everything else is guesswork.",
    },
    {
      when: "Day one",
      title: "Block what cannot buy",
      body: "Twelve searches about courses, salaries, jobs and do-it-yourself fixes. Each one is a click you paid for that was never a customer.",
    },
    {
      when: "Week one",
      title: "Give Google more to work with",
      body: "Nine more headlines, a call button, and your service list on the listing so the Maps ads can run.",
    },
  ],
  close: {
    title: "We can have the first two fixed by tomorrow morning.",
    body: "Tracking and the blocked searches go in on day one. Then we watch it every morning, and nothing changes without your yes.",
  },
};

const FRESH: Sample = {
  date: "Audit, 16 September 2026",
  business: "Maple Street Bistro, Hamilton",
  summary:
    "People are searching for you by name and finding your competitors' ads instead. Your menu is a PDF, which Google cannot read, and nothing on the site counts a booking.",
  readiness: 48,
  panels: [
    {
      title: "Your Google listing",
      score: "7 of 10",
      lines: [
        {
          title: "Verified, with 212 reviews at 4.4",
          meta: "More reviews than any restaurant advertising in Hamilton right now.",
          verdict: "good",
        },
        {
          title: "Forty six photos, most of them recent",
          meta: "This is the part most restaurants get wrong, and you have it.",
          verdict: "good",
        },
        {
          title: "No menu link on the listing",
          meta: "Google shows a menu button for restaurants that have one. Yours sends people hunting.",
          verdict: "fix",
        },
        {
          title: "Holiday hours have not been set since Easter",
          meta: "Wrong hours is the single most common reason for a one star review of a good kitchen.",
          verdict: "fix",
        },
      ],
    },
    {
      title: "Your website",
      score: "4 of 10",
      lines: [
        {
          title: "The menu is a PDF",
          meta: "Google cannot read it, so none of your dishes can ever match a search. It is also unreadable on a phone.",
          verdict: "cost",
        },
        {
          title: "Nothing counts a booking or a call",
          meta: "No tracking of any kind, so there is no way to tell which ad, post or search brought a table.",
          verdict: "cost",
        },
        {
          title: "The booking link goes to a third party",
          meta: "Fine for taking the booking, but the confirmation happens on their domain, so you cannot count it without one extra step.",
          verdict: "fix",
        },
        {
          title: "Loads in 2.1 seconds on a phone",
          meta: "Faster than most restaurant sites we check.",
          verdict: "good",
        },
      ],
    },
    {
      title: "Your ads today",
      score: "0 of 10",
      lines: [
        {
          title: "You are not advertising",
          meta: "Nobody searching italian restaurant hamilton tonight will see you above the map.",
          verdict: "cost",
        },
        {
          title: "Three competitors bid on your own name",
          meta: "About 320 people a month search Maple Street Bistro. Right now the first thing they see is somebody else.",
          verdict: "cost",
        },
        {
          title: "No Maps ads at the times you are busiest",
          meta: "Thursday to Saturday, 5 pm to 8 pm, is when those searches happen.",
          verdict: "fix",
        },
        {
          title: "Your name is searched 320 times a month",
          meta: "That is demand you already built. It is the cheapest thing any restaurant can buy back.",
          verdict: "good",
        },
      ],
    },
    {
      title: "Who you are up against",
      score: "For information",
      lines: [
        {
          title: "Four restaurants advertise in Hamilton",
          meta: "Two of them only at lunch, which leaves the evening cheaper than it should be.",
          verdict: "fix",
        },
        {
          title: "You have the best rating of the five",
          meta: "4.4 against an average of 4.0.",
          verdict: "good",
        },
        {
          title: "Two show a set menu price in the ad",
          meta: "It sets the expectation before anyone clicks.",
          verdict: "fix",
        },
        {
          title: "One runs ads on your name every Friday",
          meta: "That is legal, it is common, and it is answerable for a few dollars a day.",
          verdict: "fix",
        },
      ],
    },
  ],
  cost: {
    title: "About 320 people a month look for you by name and meet a competitor first.",
    body: "Defending your own name is usually the cheapest campaign a restaurant can run, because nobody can outbid you on your own brand for long. Every month without it is a month of tables that walked in somewhere else.",
  },
  fixes: [
    {
      when: "Day one",
      title: "Claim your own name",
      body: "A small campaign on Maple Street Bistro and its misspellings. Cheap clicks, and the people clicking already want you.",
    },
    {
      when: "Week one",
      title: "Put the menu on the page",
      body: "The same menu as text, one section per course. This is what lets Google match a dish to a search.",
    },
    {
      when: "Week one",
      title: "Count bookings and calls",
      body: "Tracking on the booking confirmation and a number that forwards to the host stand, so we can tell which nights the ads filled.",
    },
  ],
  close: {
    title: "We can have the first two fixed by tomorrow morning.",
    body: "Restaurants are welcome here. We start with your name and your menu, and the Maps ads follow once the listing is in shape.",
  },
};

export function AuditReportSample({ view }: { view: "advertising" | "fresh" }) {
  return <AuditReport sample={view === "fresh" ? FRESH : ADVERTISING} />;
}

export function AuditReport({ sample }: { sample: Sample }) {
  return (
    <AuditPage
      wide
      navLeft={
        <Link
          href="#close"
          className="text-ink hidden text-[15px] leading-[18px] font-semibold sm:block"
        >
          Email me this audit
        </Link>
      }
    >
      <section className="bg-panel -mx-5 px-5 py-8 sm:-mx-8 sm:px-8 lg:-mt-16 lg:px-[72px] lg:py-10">
        <div className="mx-auto grid max-w-[1296px] gap-6 lg:grid-cols-[1fr_320px] lg:items-start">
          <div>
            <Pill tone="grey">{sample.date}</Pill>
            <h1 className="mt-4 text-[28px] leading-[34px] font-bold sm:text-[38px] sm:leading-[46px]">
              {sample.business}
            </h1>
            <p className="text-muted mt-3 max-w-[700px] text-[15px] leading-[22px] sm:text-[18px] sm:leading-[22px]">
              {sample.summary}
            </p>
          </div>
          <div className="bg-canvas rounded-[16px] p-6">
            <p className="text-muted text-[13px] leading-4 font-semibold">Ads readiness</p>
            <p className="mt-2 flex items-baseline gap-2">
              <span className="text-[36px] leading-[44px] font-bold sm:text-[44px] sm:leading-[53px]">
                {sample.readiness}
              </span>
              <span className="text-faint text-[15px]">out of 100</span>
            </p>
            <div className="mt-3 hidden lg:block">
              <div className="flex items-center justify-between text-[14px] leading-[17px]">
                <span className="text-ink font-medium">Where you sit</span>
              </div>
              <div className="bg-track mt-2 h-2 overflow-hidden rounded-full">
                <div
                  className="bg-brand h-full rounded-full"
                  style={{ width: `${sample.readiness}%` }}
                />
              </div>
            </div>
            <p className="text-faint mt-3 text-[13px] leading-4">
              Most local businesses we check land between 50 and 70 before anything is fixed.
            </p>
          </div>
        </div>
      </section>

      <section className="mt-8 grid gap-5 lg:grid-cols-2">
        {sample.panels.map((p) => (
          <Card key={p.title} className="px-5 py-5 sm:px-7">
            <div className="flex items-center justify-between gap-4">
              <h2 className="text-[17px] leading-[21px] font-bold sm:text-[20px] sm:leading-6">
                {p.title}
              </h2>
              <span className="text-muted text-[13px] leading-4 font-bold sm:text-[15px]">
                {p.score}
              </span>
            </div>
            <div className="divide-line-soft mt-2 divide-y">
              {p.lines.map((l) => (
                <div key={l.title} className="flex items-start justify-between gap-4 py-[14px]">
                  <div className="min-w-0">
                    <p className="text-[15px] leading-5 font-semibold sm:text-[16px]">{l.title}</p>
                    <p className="text-faint mt-1 text-[13px] leading-4 sm:text-[14px] sm:leading-[17px]">
                      {l.meta}
                    </p>
                  </div>
                  <StatusPill tone={CHIP[l.verdict].tone}>{CHIP[l.verdict].label}</StatusPill>
                </div>
              ))}
            </div>
          </Card>
        ))}
      </section>

      <section className="bg-amber-tint border-amber-line mt-8 rounded-[16px] border p-6 sm:p-8">
        <Pill tone="amber">What this is likely costing you</Pill>
        <p className="mt-3 text-[19px] leading-6 font-bold sm:text-[26px] sm:leading-8">
          {sample.cost.title}
        </p>
        <p className="text-amber-dark mt-3 max-w-[1100px] text-[13px] leading-4 sm:text-[16px] sm:leading-[22px]">
          {sample.cost.body}
        </p>
      </section>

      <section className="mt-10">
        <h2 className="text-[20px] leading-6 font-bold sm:text-[30px] sm:leading-9">
          The first three things we would fix
        </h2>
        <p className="text-muted mt-2 hidden text-[17px] leading-[21px] sm:block">
          In this order, because each one makes the next one cheaper.
        </p>
        <ol className="mt-5 grid gap-4 lg:grid-cols-3">
          {sample.fixes.map((f, i) => (
            <Card key={f.title} className="p-5 sm:p-7">
              <div className="flex items-center gap-3">
                <span className="bg-ink flex size-[34px] items-center justify-center rounded-full text-[15px] font-bold text-white">
                  {i + 1}
                </span>
                <Pill tone="grey">{f.when}</Pill>
              </div>
              <p className="mt-4 text-[17px] leading-[21px] font-bold sm:text-[19px] sm:leading-[23px]">
                {f.title}
              </p>
              <p className="text-muted mt-2 text-[14px] leading-[17px] sm:text-[15px] sm:leading-[18px]">
                {f.body}
              </p>
            </Card>
          ))}
        </ol>
      </section>

      <section id="close" className="bg-brand-pale mt-10 rounded-[20px] p-6 sm:p-9">
        <div className="flex flex-col gap-6 lg:flex-row lg:items-center lg:justify-between">
          <div className="max-w-[640px]">
            <p className="text-brand-dark text-[20px] leading-6 font-bold sm:text-[28px] sm:leading-[34px]">
              {sample.close.title}
            </p>
            <p className="text-brand-dark/80 mt-3 text-[14px] leading-[17px] sm:text-[15px] sm:leading-[18px]">
              {sample.close.body}
            </p>
          </div>
          <div className="flex w-full flex-col gap-[10px] lg:w-[203px]">
            <LinkButton href="/signup" full>
              Start free for 14 days
            </LinkButton>
            <LinkButton href="/audit?view=checking" variant="secondary" full>
              Email me this audit
            </LinkButton>
          </div>
        </div>
      </section>
    </AuditPage>
  );
}

export type { Sample as AuditSample, Panel as AuditPanel, Line as AuditLine };
