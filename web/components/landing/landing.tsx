import Link from "next/link";
import {
  ArrowRight,
  CheckCircle,
  ChatCircleText,
  DeviceMobile,
  FileText,
  Gauge,
  ListChecks,
  Phone,
  ShieldCheck,
  Tag,
  Target,
} from "@phosphor-icons/react/dist/ssr";
import { Brand } from "@/components/ui/brand";
import { ActivityRow, Rows, Tile } from "@/components/app/blocks";
import { cn } from "@/lib/cn";
import { Reveal } from "./reveal";

/*
  The public landing page. One accent (brand blue), one theme (light, like the app),
  pill buttons, 16px cards, 12px inputs, Inter because it is the brand's type. The
  hero is a split: the audit form on the left, the real product on the right (the
  same Tile and ActivityRow components the dashboard uses, not a mock).
  CTA intent on this page is one label everywhere: "Get a free audit".
*/

const NAV = [
  { label: "What we check", href: "#checks" },
  { label: "How it works", href: "#how" },
  { label: "Pricing", href: "#pricing" },
];

/** The one call to action on the page. Same label everywhere, one destination. */
function AuditLink({
  size = "md",
  tone = "brand",
}: {
  size?: "md" | "lg";
  tone?: "brand" | "light";
}) {
  return (
    <Link
      href="/audit"
      className={cn(
        "inline-flex shrink-0 items-center justify-center gap-2 rounded-full font-semibold whitespace-nowrap transition-[background-color,transform] duration-[120ms] focus-visible:ring-4 focus-visible:outline-none active:scale-[0.98]",
        size === "lg" ? "h-[52px] px-7 text-[16px]" : "h-11 px-5 text-[15px]",
        tone === "brand"
          ? "bg-brand hover:bg-brand-dark focus-visible:ring-brand-bar text-white"
          : "bg-panel text-brand-dark hover:bg-brand-pale focus-visible:ring-brand-label",
      )}
    >
      Get a free audit
      <ArrowRight size={size === "lg" ? 18 : 16} weight="bold" aria-hidden />
    </Link>
  );
}

export function Landing() {
  return (
    <div className="bg-canvas text-ink">
      <Nav />
      <main>
        <Hero />
        <Checks />
        <How />
        <PlainWords />
        <Pricing />
        <Faq />
        <Final />
      </main>
      <Footer />
    </div>
  );
}

/* ---------- Nav: 72px, one line ---------- */
function Nav() {
  return (
    <header className="bg-canvas/85 border-line sticky top-0 z-20 border-b backdrop-blur">
      <div className="mx-auto flex h-[72px] max-w-[1200px] items-center justify-between gap-6 px-5 sm:px-8">
        <Brand tone="light" href="/" />
        <nav className="hidden items-center gap-7 md:flex" aria-label="Site">
          {NAV.map((n) => (
            <a
              key={n.href}
              href={n.href}
              className="text-muted hover:text-ink text-[15px] leading-[18px] font-medium transition-colors duration-[120ms]"
            >
              {n.label}
            </a>
          ))}
        </nav>
        <div className="flex items-center gap-3">
          <Link
            href="/login"
            className="text-ink hidden text-[15px] leading-[18px] font-semibold sm:block"
          >
            Sign in
          </Link>
          <a
            href="/audit"
            className="bg-brand hover:bg-brand-dark inline-flex h-11 items-center rounded-full px-5 text-[15px] font-semibold whitespace-nowrap text-white transition-colors duration-[120ms] active:scale-[0.98]"
          >
            Get a free audit
          </a>
        </div>
      </div>
    </header>
  );
}

/* ---------- Hero: split, form left, real product right ---------- */
function Hero() {
  return (
    <section className="mx-auto grid max-w-[1200px] gap-12 px-5 pt-14 pb-16 sm:px-8 lg:grid-cols-[minmax(0,1fr)_minmax(0,1.1fr)] lg:items-center lg:gap-16 lg:pt-20 lg:pb-24">
      <div className="hero-in">
        <h1 className="text-ink text-[38px] leading-[42px] font-semibold tracking-[-0.02em] text-balance sm:text-[48px] sm:leading-[52px] lg:text-[56px] lg:leading-[60px]">
          Google Ads that look after themselves.
        </h1>
        <p className="text-muted mt-5 max-w-[520px] text-[17px] leading-[24px] sm:text-[19px] sm:leading-[27px]">
          We write the campaign, watch it every day, and explain every change in plain words. Start
          with a free check of your website.
        </p>
        <div className="mt-8 flex flex-col gap-3 sm:flex-row sm:items-center sm:gap-5">
          <AuditLink size="lg" />
          <p className="text-muted text-[14px] leading-5">
            Eight checks, one working day. We change nothing on your site.
          </p>
        </div>
      </div>
      <div className="hero-in [transition-delay:120ms]">
        <ProductPreview />
      </div>
    </section>
  );
}

/** The dashboard, for real: the same blocks the signed-in app renders. */
function ProductPreview() {
  return (
    <div
      className="bg-panel border-line rounded-[20px] border p-4 shadow-[0_24px_60px_-30px_rgba(15,23,32,0.25)] sm:p-6"
      aria-label="A preview of the PPCWay overview page"
    >
      <p className="text-ink text-[18px] leading-[22px] font-semibold sm:text-[22px] sm:leading-[27px]">
        Your ads brought 58 calls this month.
      </p>
      <p className="text-muted mt-1 text-[13px] leading-4 sm:text-[14px] sm:leading-[17px]">
        12 more than last month, and each one cost you $4.60 less.
      </p>
      <div className="mt-4 grid grid-cols-2 gap-3">
        <Tile tone="brand" label="Cost per call" value="$21.40" chip="18% cheaper" />
        <Tile label="Calls" value="58" chip="12 more" />
      </div>
      <div className="border-line-soft mt-4 border-t pt-1">
        <Rows>
          <ActivityRow
            icon="bars"
            iconTone="amber"
            title="Paused 3 search terms that spent $38 without a call."
            meta="Applied Tuesday, saved about $38 a month"
            action="Undo"
          />
          <ActivityRow
            icon="plus"
            iconTone="brand"
            title={<>Added &ldquo;emergency plumber near me&rdquo; as a keyword.</>}
            meta="Applied Monday, after it brought 4 calls"
            action="Undo"
          />
        </Rows>
      </div>
    </div>
  );
}

/* ---------- What the free audit checks: headline stacked, then a 2x4 grid ---------- */
const CHECKS = [
  {
    icon: Phone,
    name: "Counting calls and forms",
    detail: "Whether a call or a form send can be counted at all. Without this, ads are guesswork.",
  },
  {
    icon: Gauge,
    name: "Speed on a phone",
    detail: "How long your home page takes on 4G. Google wants under 2.5 seconds.",
  },
  {
    icon: DeviceMobile,
    name: "Works on a phone",
    detail: "Text readable, buttons tappable, and the number is tap to call.",
  },
  {
    icon: Target,
    name: "Page matches the ad",
    detail: "Someone searching for water heaters should land on water heaters.",
  },
  {
    icon: FileText,
    name: "Contact form",
    detail: "Found, working, and with a thank-you page so a send can be counted.",
  },
  {
    icon: Tag,
    name: "Google's tags",
    detail: "Tag Manager, Analytics and Ads, present and firing.",
  },
  {
    icon: ShieldCheck,
    name: "Trust signals",
    detail: "Licence, reviews, address and hours, where people look for them.",
  },
  {
    icon: ChatCircleText,
    name: "Words Google may object to",
    detail: "Claims and guarantees that would get an ad refused.",
  },
];

function Checks() {
  return (
    <section id="checks" className="bg-panel border-line border-y">
      <div className="mx-auto max-w-[1200px] px-5 py-16 sm:px-8 lg:py-24">
        <Reveal>
          <h2 className="text-ink max-w-[640px] text-[30px] leading-[36px] font-semibold tracking-[-0.01em] text-balance sm:text-[38px] sm:leading-[44px]">
            The eight checks an agency runs before spending a dollar.
          </h2>
          <p className="text-muted mt-4 max-w-[600px] text-[17px] leading-[24px]">
            A click only pays off if the page turns it into a call. We run the same checks,
            automatically, and tell you what to fix in plain words.
          </p>
        </Reveal>
        <ul className="mt-12 grid gap-x-10 gap-y-9 sm:grid-cols-2 lg:grid-cols-4">
          {CHECKS.map((c, i) => (
            <Reveal key={c.name} delay={i * 50}>
              <li className="flex flex-col gap-3">
                <span className="bg-brand-pale text-brand-dark flex size-11 items-center justify-center rounded-[12px]">
                  <c.icon size={22} weight="regular" aria-hidden />
                </span>
                <span className="text-ink text-[16px] leading-[20px] font-semibold">{c.name}</span>
                <span className="text-muted text-[14px] leading-[20px]">{c.detail}</span>
              </li>
            </Reveal>
          ))}
        </ul>
      </div>
    </section>
  );
}

/* ---------- How it works: three columns, hairline above each, no cards ---------- */
const STEPS = [
  {
    title: "Check the site",
    body: "Type your address. In about a minute you get the eight checks, green, amber or grey, with what to fix first.",
  },
  {
    title: "We write the campaign",
    body: "Keywords from real searches near you, ads from your own pages, every line checked against Google's rules. Nothing goes live until you approve it.",
  },
  {
    title: "Every change explained",
    body: "We watch it every day. When something should change, we propose it with the numbers behind it, and you say yes or no.",
  },
];

function How() {
  return (
    <section id="how" className="mx-auto max-w-[1200px] px-5 py-16 sm:px-8 lg:py-24">
      <Reveal>
        <h2 className="text-ink max-w-[640px] text-[30px] leading-[36px] font-semibold tracking-[-0.01em] text-balance sm:text-[38px] sm:leading-[44px]">
          About 15 minutes from here to your first live campaign.
        </h2>
      </Reveal>
      <ol className="mt-12 grid gap-10 md:grid-cols-3 md:gap-8">
        {STEPS.map((s, i) => (
          <Reveal key={s.title} delay={i * 80}>
            <li className="border-brand flex flex-col gap-3 border-t-2 pt-5">
              <span className="text-ink text-[20px] leading-[24px] font-semibold">{s.title}</span>
              <span className="text-muted text-[15px] leading-[22px]">{s.body}</span>
            </li>
          </Reveal>
        ))}
      </ol>
    </section>
  );
}

/* ---------- Plain words: a photo and the real approvals card ---------- */
function PlainWords() {
  return (
    <section className="bg-rail text-white">
      <div className="mx-auto grid max-w-[1200px] items-center gap-12 px-5 py-16 sm:px-8 lg:grid-cols-2 lg:gap-16 lg:py-24">
        <Reveal>
          <h2 className="max-w-[520px] text-[30px] leading-[36px] font-semibold tracking-[-0.01em] text-balance sm:text-[38px] sm:leading-[44px]">
            Nothing changes without your OK.
          </h2>
          <p className="text-rail-icon mt-4 max-w-[520px] text-[17px] leading-[24px]">
            Every change is written down before it happens, in a sentence you can read on your
            phone, with an undo. Budgets, limits and your card stay with you.
          </p>
          <ul className="mt-8 flex flex-col gap-4">
            {[
              "A hard stop on daily spend, never crossed",
              "The most we will pay for one call, set by you",
              "Anything you leave alone expires. Nothing changes.",
            ].map((t) => (
              <li key={t} className="flex items-start gap-3 text-[15px] leading-[22px]">
                <CheckCircle
                  size={22}
                  weight="fill"
                  className="text-brand-label mt-[1px] shrink-0"
                  aria-hidden
                />
                <span>{t}</span>
              </li>
            ))}
          </ul>
        </Reveal>
        <Reveal
          delay={120}
          className="grid gap-4 sm:grid-cols-[1fr_1.1fr] lg:grid-cols-1 xl:grid-cols-[1fr_1.1fr]"
        >
          {/* Photo placeholder from Picsum, seeded so it stays the same. Replace with a real photo of a customer at work. */}
          {/* eslint-disable-next-line @next/next/no-img-element -- placeholder slot until a real photo is chosen */}
          <img
            src="https://picsum.photos/seed/ppcway-plumber-van-mississauga/720/900"
            alt="A tradesperson at work"
            width={720}
            height={900}
            loading="lazy"
            className="aspect-[4/5] w-full rounded-[16px] object-cover"
          />
          <div className="bg-amber-tint border-amber-line text-ink self-center rounded-[16px] border p-5">
            <span className="bg-amber-pale text-amber-dark inline-flex h-[26px] items-center rounded-full px-3 text-[13px] font-semibold">
              Waiting for you
            </span>
            <p className="mt-3 text-[18px] leading-[22px] font-semibold">
              Lower the daily budget from $40 to $32
            </p>
            <p className="text-muted mt-2 text-[14px] leading-[20px]">
              Spend has run ahead of pace for six days. This keeps the month on budget without
              pausing anything.
            </p>
            <div className="mt-4 flex gap-[10px]">
              <span className="bg-brand inline-flex h-10 items-center rounded-full px-5 text-[14px] font-semibold text-white">
                Approve
              </span>
              <span className="text-amber-dark inline-flex h-10 items-center rounded-full border border-[#e6cea4] px-5 text-[14px] font-semibold">
                Skip this
              </span>
            </div>
          </div>
        </Reveal>
      </div>
    </section>
  );
}

/* ---------- Pricing: three plans, the middle one tinted ---------- */
const PLANS = [
  {
    name: "Starter",
    price: "$49",
    per: "a month",
    line: "One campaign and up to $1,500 of ad spend a month.",
    items: ["The eight-check audit", "Campaign written for you", "Daily checks and approvals"],
    tone: "panel",
  },
  {
    name: "Growth",
    price: "$99",
    per: "a month",
    line: "Up to four campaigns and $5,000 of ad spend a month.",
    items: [
      "Everything in Starter",
      "Call tracking, so calls are counted",
      "The Monday email",
      "Up to five people",
    ],
    tone: "brand",
  },
  {
    name: "Agency",
    price: "$249",
    per: "a month",
    line: "Up to ten businesses, one view of every client.",
    items: [
      "Everything in Growth",
      "Reports under your own name",
      "Clients sign in at your address",
    ],
    tone: "panel",
  },
] as const;

function Pricing() {
  return (
    <section id="pricing" className="mx-auto max-w-[1200px] px-5 py-16 sm:px-8 lg:py-24">
      <Reveal>
        <h2 className="text-ink max-w-[640px] text-[30px] leading-[36px] font-semibold tracking-[-0.01em] text-balance sm:text-[38px] sm:leading-[44px]">
          One monthly price. Google bills your ads separately, on your own card.
        </h2>
        <p className="text-muted mt-4 max-w-[600px] text-[17px] leading-[24px]">
          Free for 14 days. No card needed to look around, and you can cancel at the end of any
          month.
        </p>
      </Reveal>
      <div className="mt-12 grid gap-4 lg:grid-cols-3">
        {PLANS.map((p, i) => (
          <Reveal
            key={p.name}
            delay={i * 80}
            className={cn(
              "rounded-[16px] p-6 sm:p-7",
              p.tone === "brand" ? "bg-brand text-white" : "bg-panel border-line border",
            )}
          >
            <p
              className={cn(
                "text-[15px] leading-[18px] font-semibold",
                p.tone === "brand" ? "text-brand-label" : "text-muted",
              )}
            >
              {p.name}
            </p>
            <p className="mt-3 flex items-baseline gap-2">
              <span className="text-[40px] leading-[44px] font-semibold tracking-[-0.02em]">
                {p.price}
              </span>
              <span
                className={cn(
                  "text-[15px]",
                  p.tone === "brand" ? "text-brand-label" : "text-muted",
                )}
              >
                {p.per}
              </span>
            </p>
            <p
              className={cn(
                "mt-3 text-[15px] leading-[22px]",
                p.tone === "brand" ? "text-white/90" : "text-muted",
              )}
            >
              {p.line}
            </p>
            <ul className="mt-6 flex flex-col gap-3">
              {p.items.map((it) => (
                <li key={it} className="flex items-start gap-[10px] text-[15px] leading-[20px]">
                  <ListChecks
                    size={20}
                    className={cn(
                      "mt-[1px] shrink-0",
                      p.tone === "brand" ? "text-brand-label" : "text-brand",
                    )}
                    aria-hidden
                  />
                  <span>{it}</span>
                </li>
              ))}
            </ul>
            <a
              href="/audit"
              className={cn(
                "mt-7 inline-flex h-11 items-center gap-2 rounded-full px-5 text-[15px] font-semibold transition-colors duration-[120ms] active:scale-[0.98]",
                p.tone === "brand"
                  ? "bg-panel text-brand-dark hover:bg-brand-pale"
                  : "bg-brand hover:bg-brand-dark text-white",
              )}
            >
              Get a free audit
              <ArrowRight size={16} weight="bold" aria-hidden />
            </a>
          </Reveal>
        ))}
      </div>
    </section>
  );
}

/* ---------- FAQ: native disclosure ---------- */
const FAQ = [
  [
    "Why did PPCWay change my bid?",
    "Every change has its reason in Activity: the rule that decided it, the numbers it looked at, and an undo. On Ask first, we propose the change and nothing happens until you approve it.",
  ],
  [
    "Why don't Google's numbers match my phone?",
    "Google counts only calls that came from your ads and lasted over 30 seconds. Consent banners and its own counting rules explain the rest. We show both figures side by side.",
  ],
  [
    "What happens if my card is declined at Google?",
    "Google pauses your ads, not us. We email you straight away, hold every change, and show the one link that fixes it. PPCWay never sees your Google card.",
  ],
  [
    "Can I pause for a holiday?",
    "One click. Spend stops within minutes and Google keeps everything it has learned. Switch back on when you are back.",
  ],
  [
    "Who can see my data?",
    "You, and anyone you invite. Support can look only if you ask, every look is written down, and you get an email saying who and when. Data is stored in Canada.",
  ],
];

function Faq() {
  return (
    <section className="bg-panel border-line border-y">
      <div className="mx-auto max-w-[760px] px-5 py-16 sm:px-8 lg:py-24">
        <Reveal>
          <h2 className="text-ink text-[30px] leading-[36px] font-semibold tracking-[-0.01em] sm:text-[38px] sm:leading-[44px]">
            Questions people ask most
          </h2>
        </Reveal>
        <div className="divide-line-soft mt-8 divide-y">
          {FAQ.map(([q, a]) => (
            <details key={q} className="group py-5">
              <summary className="text-ink flex cursor-pointer list-none items-center justify-between gap-4 text-[17px] leading-[22px] font-semibold [&::-webkit-details-marker]:hidden">
                {q}
                <span
                  aria-hidden
                  className="text-faint text-[22px] leading-none transition-transform duration-[120ms] group-open:rotate-45"
                >
                  +
                </span>
              </summary>
              <p className="text-muted mt-3 max-w-[65ch] text-[15px] leading-[22px]">{a}</p>
            </details>
          ))}
        </div>
      </div>
    </section>
  );
}

/* ---------- Final: the same form, on the navy band ---------- */
function Final() {
  return (
    <section className="bg-rail">
      <div className="mx-auto max-w-[1200px] px-5 py-16 sm:px-8 lg:py-24">
        <Reveal className="grid items-center gap-8 lg:grid-cols-[1fr_auto]">
          <div>
            <h2 className="max-w-[560px] text-[30px] leading-[36px] font-semibold tracking-[-0.01em] text-balance text-white sm:text-[38px] sm:leading-[44px]">
              See what an agency would fix, before you spend anything.
            </h2>
            <p className="text-rail-icon mt-4 max-w-[520px] text-[17px] leading-[24px]">
              The report is yours whether or not you sign up.
            </p>
          </div>
          <AuditLink size="lg" tone="light" />
        </Reveal>
      </div>
    </section>
  );
}

function Footer() {
  return (
    <footer className="mx-auto flex max-w-[1200px] flex-wrap items-center justify-between gap-4 px-5 py-8 sm:px-8">
      <Brand tone="light" size={26} href="/" />
      <nav
        className="text-muted flex flex-wrap gap-x-6 gap-y-2 text-[14px] leading-[17px]"
        aria-label="Footer"
      >
        <a href="#checks" className="hover:text-ink">
          What we check
        </a>
        <a href="#pricing" className="hover:text-ink">
          Pricing
        </a>
        <Link href="/help" className="hover:text-ink">
          Help
        </Link>
        <Link href="/settings?view=your-data" className="hover:text-ink">
          Privacy
        </Link>
        <Link href="/login" className="hover:text-ink">
          Sign in
        </Link>
      </nav>
      <p className="text-faint text-[13px] leading-4">PPCWay · Mississauga, Ontario</p>
    </footer>
  );
}
