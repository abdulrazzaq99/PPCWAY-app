import { ArrowRight, Check, CheckCircle, LockSimple } from "@phosphor-icons/react/dist/ssr";
import Link from "next/link";
import { StatusPill } from "@/components/app/blocks";
import type { ChipTone } from "@/components/app/blocks";
import { LinkButton } from "@/components/ui/button";
import { cn } from "@/lib/cn";
import { FixBar } from "./fix-bar";
import { AuditPage, Card, Pill } from "./shell";

/*
  Frames 181:6011 (Report, already advertising), 181:6215 (Report, not advertising
  yet) and 181:6419 (Mobile · Audit report). Header with the readiness score, four
  panels (listing, website, ads today, competition), what it costs, the first three
  fixes, and the close. On a phone the panels stack and the score sits under the
  headline, as the mobile frame draws it.

  Built ahead of the frames, to be drawn back into Figma: who fixes each line (us,
  or the owner with our help), the score after our fixes, the cost per day, the
  full list behind a free account, and the bar that follows the reader. Every
  number is the report's own; nothing counts down and nothing runs out.
*/
type Verdict = "good" | "fix" | "cost";
/** Who fixes a line that is not good: PPCWay, or the owner with our instructions. */
type Who = "us" | "you";
type Line = { title: string; meta: string; verdict: Verdict; who?: Who };
type Panel = { title: string; score: string; lines: Line[] };
type Sample = {
  date: string;
  business: string;
  summary: string;
  readiness: number;
  /** The score once the lines marked "us" are fixed. */
  after: number;
  panels: Panel[];
  /** The fourth card. Only the account owner can open it, which is the point. */
  ads: { title: string; note: string; rows: string[]; button: string };
  /** Left out when a real run has no money line it can stand behind. */
  cost?: { title: string; body: string; daily: string; basis: string };
  /** A list the audit found, two rows shown and the rest with a free account. */
  locked?: { title: string; note: string; shown: string[]; total: number };
  /** The sentence on the bar that follows the reader. */
  bar: string;
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
    "Your reviews are better than most of your neighbours'. Your listing shuts at five, your website cannot prove a single call happened, and your phone number cannot be tapped.",
  readiness: 62,
  after: 86,
  panels: [
    {
      title: "Your Google listing",
      score: "7 of 10",
      lines: [
        {
          title: "Your hours end at 5 pm, Monday to Friday",
          meta: "Burst pipes do not wait for Monday. Two plumbers near you are open all night, so Google sends them the 2 am searches.",
          verdict: "cost",
          who: "you",
        },
        {
          title: "Four photos",
          meta: "The plumbers ranking above you average twenty four. Photos cost nothing and they move the Maps ranking.",
          verdict: "fix",
          who: "you",
        },
        {
          title: "Plumber, the category people actually type",
          meta: "Half the listings we check sit under a category nobody searches for.",
          verdict: "good",
        },
        {
          title: "4.6 out of 5, from 87 reviews",
          meta: "Ahead of four of the six plumbers nearby.",
          verdict: "good",
        },
      ],
    },
    {
      title: "Your website",
      score: "5 of 10",
      lines: [
        {
          title: "No conversion tracking found",
          meta: "Nothing on the site tells Google a call or a form happened, so Google is bidding blind on every click you pay for.",
          verdict: "cost",
          who: "us",
        },
        {
          title: "Your phone number is an image on mobile",
          meta: "It cannot be tapped. On a phone, for an emergency plumber, that is the whole job.",
          verdict: "fix",
          who: "you",
        },
        {
          title: "The emergency page takes 4.8 seconds on a phone",
          meta: "Half the people who tap an ad leave before three.",
          verdict: "fix",
          who: "you",
        },
        {
          title: "Six service pages, one per job",
          meta: "Emergency, drains, water heaters, taps, toilets and repiping. That is the shape ads like.",
          verdict: "good",
        },
      ],
    },
    {
      title: "How you compare nearby",
      score: "For information",
      lines: [
        {
          title: "Two of the six are open twenty four hours",
          meta: "Nights and weekends are when the expensive jobs happen, and when nobody is answering yours.",
          verdict: "fix",
          who: "you",
        },
        {
          title: "Three of them have more photos than you",
          meta: "Thirty one, twenty six and twenty two, against your four.",
          verdict: "fix",
          who: "you",
        },
        {
          title: "You have more reviews than four of them",
          meta: "That is the expensive thing to build, and you already have it.",
          verdict: "good",
        },
        {
          title: "Yours is the second best rating of the six",
          meta: "4.6, behind one at 4.7. The other four sit between 3.9 and 4.4.",
          verdict: "good",
        },
      ],
    },
  ],
  ads: {
    title: "Your ads today",
    note: "Which searches you showed for this morning, what each one cost, and how many were never going to call. Google shows this to the account owner and to nobody else, so we cannot read it and neither can your competitors.",
    rows: [
      "Searches you paid for today",
      "Money spent on people who cannot buy",
      "Where your ad sat against the six nearby",
    ],
    button: "Connect Google Ads, read only",
  },
  cost: {
    basis: "Estimate",
    title: "About $180 to $320 a month sits in front of you in Mississauga.",
    daily: "That is roughly $6 to $11 a day, taken or missed, while the tracking is blind.",
    body: "Around 1,900 people a month search for a plumber here, and the top of the page costs what it costs. Those are Google's own numbers for your town and trade, not yours: connect your account, read only, and the average becomes your real figure.",
  },
  locked: {
    title: "How you stand against the six plumbers nearby",
    note: "Rating, reviews, photos and hours, side by side. Two of the six are shown here.",
    shown: [
      "Northgate Plumbing · 4.2 from 51 reviews · 31 photos · open 24 hours",
      "Lakeshore Drain Co · 4.7 from 120 reviews · 18 photos · closes at 6 pm",
    ],
    total: 6,
  },
  bar: "Your listing shuts at 5 pm and your website counts nothing. We can fix both by tomorrow morning.",
  fixes: [
    {
      when: "Day one",
      title: "Count your calls",
      body: "A tracking number that forwards to your phone, and the Google tag on your site. Until this exists, everything else is guesswork.",
    },
    {
      when: "Day one",
      title: "Open the hours that pay",
      body: "Your listing says nine to five. The night and weekend calls are the expensive ones, and right now two neighbours take them all.",
    },
    {
      when: "Week one",
      title: "Give Google something to show",
      body: "Twenty more photos, a number that can be tapped on every page, and the emergency page under three seconds.",
    },
  ],
  close: {
    title: "We can have the first two fixed by tomorrow morning.",
    body: "Tracking and the tappable number go in on day one. The hours are two taps on your listing, and we send you exactly where. Then we watch it every morning, and nothing changes without your yes.",
  },
};

const FRESH: Sample = {
  date: "Audit, 16 September 2026",
  business: "Maple Street Bistro, Hamilton",
  summary:
    "Your rating is the best in town and your photos are better than anyone's. Google cannot read your menu, nothing on the site counts a booking, and your holiday hours have not moved since Easter.",
  readiness: 48,
  after: 79,
  panels: [
    {
      title: "Your Google listing",
      score: "6 of 10",
      lines: [
        {
          title: "No holiday hours since Easter",
          meta: "Wrong hours on a long weekend is the most common reason a good kitchen collects a one star review.",
          verdict: "cost",
          who: "you",
        },
        {
          title: "No price range on the listing",
          meta: "Diners filter by price before they read a word. Three of the four restaurants near you show one.",
          verdict: "fix",
          who: "you",
        },
        {
          title: "Forty six photos, most of them recent",
          meta: "This is the part most restaurants get wrong, and you have it.",
          verdict: "good",
        },
        {
          title: "4.4 out of 5, from 212 reviews",
          meta: "The best rating, and the most reviews, of the five restaurants nearby.",
          verdict: "good",
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
          who: "you",
        },
        {
          title: "Nothing counts a booking or a call",
          meta: "No tracking of any kind, so there is no way to tell which ad, post or search brought a table.",
          verdict: "cost",
          who: "us",
        },
        {
          title: "The booking link goes to a third party",
          meta: "Fine for taking the booking, but the confirmation happens on their domain, so it cannot be counted without one extra step.",
          verdict: "fix",
          who: "us",
        },
        {
          title: "Loads in 2.1 seconds on a phone",
          meta: "Faster than most restaurant sites we check.",
          verdict: "good",
        },
      ],
    },
    {
      title: "How you compare nearby",
      score: "For information",
      lines: [
        {
          title: "Two of the four take bookings on their own site",
          meta: "Every booking they take is one they can count, and yours happen on somebody else's domain.",
          verdict: "fix",
          who: "us",
        },
        {
          title: "Three of them show a price range, you do not",
          meta: "It is the first thing a diner filters by in Maps.",
          verdict: "fix",
          who: "you",
        },
        {
          title: "You have the best rating of the five",
          meta: "4.4 against an average of 4.0.",
          verdict: "good",
        },
        {
          title: "You have more photos than any of them",
          meta: "Forty six, against an average of nineteen.",
          verdict: "good",
        },
      ],
    },
  ],
  ads: {
    title: "Your ads today",
    note: "You told us you do not advertise yet. The moment you connect Google Ads, read only, we can show what your own name is worth, who is buying it on Friday nights, and what an evening table costs to win.",
    rows: [
      "What your name is worth a month",
      "Who else is bidding on it",
      "What an evening booking costs to win",
    ],
    button: "Connect Google Ads, read only",
  },
  cost: {
    basis: "Estimate",
    title: "About 320 people a month type your name into Google.",
    daily:
      "That is roughly 10 people a day, and defending your own name costs about $40 to $70 a month.",
    body: "That is Google's own search volume for Maple Street Bistro and its misspellings, and the going rate for those clicks in Hamilton. Nobody can outbid you on your own name for long, which is why it is usually the cheapest campaign a restaurant ever runs.",
  },
  locked: {
    title: "How you stand against the four restaurants nearby",
    note: "Rating, reviews, photos, price range and hours, side by side. Two of the four are shown here.",
    shown: [
      "Il Forno Hamilton · 4.1 from 168 reviews · 22 photos · $$ · books on its own site",
      "The Dundurn Table · 3.9 from 94 reviews · 12 photos · $$$ · no online booking",
    ],
    total: 4,
  },
  bar: "Google cannot read your menu and nothing counts a booking. We can fix both by tomorrow morning.",
  fixes: [
    {
      when: "Day one",
      title: "Count bookings and calls",
      body: "Tracking on the booking confirmation and a number that forwards to the host stand, so we can tell which nights were filled by which search.",
    },
    {
      when: "Week one",
      title: "Put the menu on the page",
      body: "The same menu as text, one section per course. This is what lets Google match a dish to a search.",
    },
    {
      when: "Week one",
      title: "Finish the listing",
      body: "A price range, holiday hours set for the year, and the booking link where Google expects it.",
    },
  ],
  close: {
    title: "We can have the first two fixed by tomorrow morning.",
    body: "Restaurants are welcome here. We start with the menu and the counting, and the ads follow once the listing is in shape.",
  },
};

const WORDS = ["no", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine"];
function say(n: number): string {
  return WORDS[n] ?? String(n);
}
function sayFirst(n: number): string {
  const w = say(n);
  return w.charAt(0).toUpperCase() + w.slice(1);
}

/** The panel's score out of ten, or null for "For information". */
function scoreOf(panel: Panel): number | null {
  const m = /^(\d+) of 10$/.exec(panel.score);
  return m ? Number(m[1]) : null;
}

/** Blue when it is fine, amber when it needs work, red when it is losing money. */
function band(score: number): "good" | "fix" | "cost" {
  return score >= 7 ? "good" : score >= 4 ? "fix" : "cost";
}

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
            <div className="mt-3">
              <div className="bg-track relative h-2 overflow-hidden rounded-full">
                <div
                  className="bg-brand-bar absolute inset-y-0 left-0 rounded-full"
                  style={{ width: `${sample.after}%` }}
                />
                <div
                  className="bg-brand absolute inset-y-0 left-0 rounded-full"
                  style={{ width: `${sample.readiness}%` }}
                />
              </div>
              <div className="mt-2 flex items-center justify-between gap-3 text-[13px] leading-4 font-semibold">
                <span className="text-ink flex items-center gap-[6px]">
                  <span aria-hidden className="bg-brand size-2 rounded-full" />
                  Now {sample.readiness}
                </span>
                <span className="text-brand flex items-center gap-[6px]">
                  <span aria-hidden className="bg-brand-bar size-2 rounded-full" />
                  After our fixes {sample.after}
                </span>
              </div>
            </div>
            <p className="text-faint mt-3 text-[13px] leading-4">
              The {sample.after - sample.readiness} points between are the problems we fix for you.
              Most local businesses we check land between 50 and 70 before anything is fixed.
            </p>
          </div>
        </div>
      </section>

      <section className="mt-8 grid gap-5 lg:grid-cols-2 lg:items-start">
        {sample.panels.map((p) => (
          <PanelCard key={p.title} panel={p} />
        ))}
        <AdsCard ads={sample.ads} />
      </section>

      {sample.cost ? (
        <section className="bg-amber-tint border-amber-line mt-8 rounded-[16px] border p-6 sm:p-8">
          <span className="flex flex-wrap items-center gap-2">
            <Pill tone="amber">What this is likely costing you</Pill>
            <Pill tone="grey">{sample.cost.basis}</Pill>
          </span>
          <p className="mt-3 text-[19px] leading-6 font-bold sm:text-[26px] sm:leading-8">
            {sample.cost.title}
          </p>
          <p className="text-red mt-2 text-[15px] leading-5 font-bold sm:text-[18px] sm:leading-6">
            {sample.cost.daily}
          </p>
          <p className="text-amber-dark mt-3 max-w-[1100px] text-[13px] leading-4 sm:text-[16px] sm:leading-[22px]">
            {sample.cost.body}
          </p>
        </section>
      ) : null}

      {sample.locked ? <LockedList locked={sample.locked} /> : null}

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
          <div className="flex w-full flex-col gap-[10px] lg:w-[220px]">
            <LinkButton href="/signup" full>
              Fix these for me
            </LinkButton>
            <LinkButton href="/audit?view=checking" variant="secondary" full>
              Email me this audit
            </LinkButton>
            <p className="text-brand-dark/80 text-center text-[13px] leading-4">
              Free for 14 days.
            </p>
          </div>
        </div>
      </section>

      <FixBar text={sample.bar} />
    </AuditPage>
  );
}

const BAND = {
  good: { fill: "bg-brand", text: "text-brand" },
  fix: { fill: "bg-amber", text: "text-amber-dark" },
  cost: { fill: "bg-red", text: "text-red" },
} as const;

/** Ten steps, filled to the score, in the colour of its band. */
function Meter({ score }: { score: number }) {
  const tone = BAND[band(score)];
  return (
    <span className="flex items-center gap-2" role="img" aria-label={`${score} out of 10`}>
      <span aria-hidden className="flex gap-[2px] sm:gap-[3px]">
        {Array.from({ length: 10 }, (_, i) => (
          <span
            key={i}
            className={cn(
              "h-[6px] w-[6px] rounded-full sm:w-[9px]",
              i < score ? tone.fill : "bg-track",
            )}
          />
        ))}
      </span>
      <span
        aria-hidden
        className={cn("text-[14px] leading-[17px] font-bold sm:text-[15px]", tone.text)}
      >
        {score}/10
      </span>
    </span>
  );
}

/**
  One area of the audit. Problems lead, the costly ones first with a red edge, then
  the fixes with an amber one; each says who fixes it. What already works sits
  underneath, smaller. One way in at the foot of the card, so the reader is asked
  once per area rather than once per line.
*/
function PanelCard({ panel }: { panel: Panel }) {
  const score = scoreOf(panel);
  const open = panel.lines
    .filter((l) => l.verdict !== "good")
    .sort((a, b) => Number(b.verdict === "cost") - Number(a.verdict === "cost"));
  const working = panel.lines.filter((l) => l.verdict === "good");
  const costing = open.filter((l) => l.verdict === "cost").length;
  const ours = open.filter((l) => l.who === "us").length;

  const summary =
    open.length === 0
      ? "Nothing to fix here."
      : `${sayFirst(open.length)} ${open.length === 1 ? "problem" : "problems"}` +
        (costing > 0 ? `, ${say(costing)} costing you money.` : " to fix.");
  const foot =
    ours === 0
      ? `${sayFirst(open.length)} for you to do. We send the steps.`
      : ours === open.length
        ? open.length === 1
          ? "We fix this one for you."
          : `We fix all ${say(open.length)} of these.`
        : `We fix ${say(ours)} of these ${say(open.length)}.`;

  return (
    <Card className="flex flex-col overflow-hidden">
      <div className="flex-1 px-5 pt-5 pb-5 sm:px-7 sm:pt-6">
        <div className="flex flex-wrap items-center justify-between gap-x-4 gap-y-2">
          <h2 className="text-[17px] leading-[21px] font-bold sm:text-[20px] sm:leading-6">
            {panel.title}
          </h2>
          {score === null ? (
            <span className="text-muted text-[13px] leading-4 font-bold sm:text-[15px]">
              {panel.score}
            </span>
          ) : (
            <Meter score={score} />
          )}
        </div>
        <p className="text-muted mt-1 text-[14px] leading-[17px]">{summary}</p>

        {open.length > 0 ? (
          <ul className="mt-4 flex flex-col gap-2">
            {open.map((l) => (
              <li
                key={l.title}
                className={cn(
                  "rounded-[12px] border-l-[3px] py-3 pr-3 pl-4",
                  l.verdict === "cost" ? "border-l-red bg-red-pale/60" : "border-l-amber",
                )}
              >
                <div className="flex items-start justify-between gap-4">
                  <p className="text-[15px] leading-5 font-semibold sm:text-[16px]">{l.title}</p>
                  <StatusPill tone={CHIP[l.verdict].tone} className="shrink-0">
                    {CHIP[l.verdict].label}
                  </StatusPill>
                </div>
                <p className="text-muted mt-1 text-[13px] leading-4 sm:text-[14px] sm:leading-[18px]">
                  {l.meta}
                </p>
                {l.who ? <WhoChip who={l.who} /> : null}
              </li>
            ))}
          </ul>
        ) : null}

        {working.length > 0 ? (
          <div className="mt-5">
            <p className="text-faint text-[12px] leading-[15px] font-bold tracking-[0.06em] uppercase">
              Working well
            </p>
            <ul className="mt-2 flex flex-col gap-3">
              {working.map((l) => (
                <li key={l.title} className="flex items-start gap-2">
                  <Check
                    aria-hidden
                    size={16}
                    weight="bold"
                    className="text-brand mt-[2px] shrink-0"
                  />
                  <span className="min-w-0">
                    <span className="block text-[14px] leading-[18px] font-semibold sm:text-[15px]">
                      {l.title}
                    </span>
                    <span className="text-faint block text-[13px] leading-4">{l.meta}</span>
                  </span>
                </li>
              ))}
            </ul>
          </div>
        ) : null}
      </div>

      {open.length > 0 ? (
        <div className="border-brand-line bg-brand-tint flex flex-wrap items-center justify-between gap-3 border-t px-5 py-4 sm:px-7">
          <p className="text-brand-dark text-[14px] leading-[18px] font-semibold sm:text-[15px]">
            {foot}
          </p>
          <LinkButton href="/signup" size="sm" variant={ours === 0 ? "secondary" : "primary"}>
            {ours === 0 ? "Show me how" : ours === 1 ? "Fix it for me" : "Fix these for me"}
            <ArrowRight aria-hidden size={15} weight="bold" />
          </LinkButton>
        </div>
      ) : null}
    </Card>
  );
}

/**
  The fourth card, and the only one we cannot fill. What their ads did today sits
  inside their Google Ads account, where Google shows it to the owner alone. Saying
  so plainly, with the rows named and the numbers missing, asks for the connection
  better than any invented figure would.
*/
function AdsCard({ ads }: { ads: Sample["ads"] }) {
  return (
    <Card className="flex flex-col overflow-hidden">
      <div className="flex-1 px-5 pt-5 pb-5 sm:px-7 sm:pt-6">
        <div className="flex flex-wrap items-center justify-between gap-x-4 gap-y-2">
          <h2 className="text-[17px] leading-[21px] font-bold sm:text-[20px] sm:leading-6">
            {ads.title}
          </h2>
          <span className="text-muted inline-flex items-center gap-1 text-[13px] leading-4 font-bold sm:text-[15px]">
            <LockSimple aria-hidden size={15} weight="bold" />
            Locked
          </span>
        </div>
        <p className="text-muted mt-1 max-w-[560px] text-[14px] leading-[18px]">{ads.note}</p>
        <ul className="mt-4 flex flex-col gap-2">
          {ads.rows.map((row) => (
            <li
              key={row}
              className="bg-line-soft/70 flex items-center justify-between gap-4 rounded-[12px] px-4 py-3"
            >
              <span className="text-muted text-[15px] leading-5 font-semibold sm:text-[16px]">
                {row}
              </span>
              <span aria-hidden className="bg-line block h-[10px] w-[54px] shrink-0 rounded-full" />
            </li>
          ))}
        </ul>
      </div>
      <div className="border-brand-line bg-brand-tint flex flex-wrap items-center justify-between gap-3 border-t px-5 py-4 sm:px-7">
        <p className="text-brand-dark text-[14px] leading-[18px] font-semibold sm:text-[15px]">
          Only you can open this.
        </p>
        <LinkButton href="/signup" size="sm">
          {ads.button}
          <ArrowRight aria-hidden size={15} weight="bold" />
        </LinkButton>
      </div>
    </Card>
  );
}

/** Who fixes a problem: PPCWay, or the owner with our steps. */
function WhoChip({ who }: { who: Who }) {
  return (
    <span
      className={cn(
        "mt-2 inline-flex h-[22px] items-center gap-1 rounded-full px-2 text-[12px] leading-[15px] font-semibold",
        who === "us" ? "bg-brand-tint text-brand" : "bg-line-soft text-muted",
      )}
    >
      {who === "us" ? <CheckCircle aria-hidden size={13} weight="fill" /> : null}
      {who === "us" ? "PPCWay fixes this" : "Yours, with our steps"}
    </span>
  );
}

/**
  Two rows of what the audit found, the rest behind a free account. The hidden rows
  are drawn as blurred bars, not blurred text, so nothing is sent that the page does
  not show.
*/
function LockedList({ locked }: { locked: NonNullable<Sample["locked"]> }) {
  const more = locked.total - locked.shown.length;
  return (
    <section className="mt-8">
      <Card className="overflow-hidden">
        <div className="px-5 pt-5 sm:px-7 sm:pt-7">
          <h2 className="text-[17px] leading-[21px] font-bold sm:text-[20px] sm:leading-6">
            {locked.title}
          </h2>
          <p className="text-muted mt-2 max-w-[760px] text-[14px] leading-[17px] sm:text-[15px] sm:leading-5">
            {locked.note}
          </p>
        </div>
        <ul className="divide-line-soft border-line-soft mt-4 divide-y border-t">
          {locked.shown.map((row) => (
            <li
              key={row}
              className="px-5 py-3 text-[15px] leading-5 font-semibold sm:px-7 sm:text-[16px]"
            >
              {row}
            </li>
          ))}
        </ul>
        <div className="border-line-soft relative border-t">
          <ul aria-hidden className="divide-line-soft divide-y blur-[3px] select-none">
            {["62%", "44%", "70%"].map((w) => (
              <li key={w} className="px-5 py-[18px] sm:px-7">
                <span className="bg-line block h-[10px] rounded-full" style={{ width: w }} />
              </li>
            ))}
          </ul>
          <div className="bg-panel/60 absolute inset-0 flex flex-col items-center justify-center gap-3 px-5 text-center">
            <p className="text-ink flex items-center gap-2 text-[15px] leading-5 font-semibold">
              <LockSimple aria-hidden size={16} weight="bold" />
              {more} more, with a free account
            </p>
            <LinkButton href="/signup" size="sm">
              See all {locked.total}
            </LinkButton>
          </div>
        </div>
      </Card>
    </section>
  );
}

export type { Sample as AuditSample, Panel as AuditPanel, Line as AuditLine };
