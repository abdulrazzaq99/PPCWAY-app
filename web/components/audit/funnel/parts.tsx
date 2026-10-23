import Link from "next/link";
import { Brand } from "@/components/ui/brand";

/*
  Everything on the free audit page that is not the card: the header, what the
  audit checks, the four promises, the questions people ask, and the footer.

  Four blocks the handoff draws are deliberately absent until there is real
  content for them: the rating line under the card, the proof strip
  ([Google Partner badge], [Rating], [Number] businesses audited), the
  specialist card ([Photo], [Specialist name], a quote to be confirmed) and the
  three testimonials. The handoff's own instruction is to fill them with real,
  approved content or remove the block, and never to ship invented numbers or
  quotes — so they are removed, not faked. Each is a self-contained section and
  drops back in whole.

  There is no login link here, by design, and no "Fix these with PPCway" button
  in the results.
*/
export function AuditHeader() {
  return (
    <header className="border-b border-[#E8E5DF] bg-white">
      <div className="mx-auto flex max-w-[1200px] items-center gap-4 px-6 py-[14px]">
        <Brand tone="light" size={26} href="/" />
        <span className="flex-1" />
        <span className="text-right text-[13px] text-[#6B6680] sm:text-[14px]">
          <span className="sm:hidden">Free · no card</span>
          <span className="hidden sm:inline">Free · no card · nothing changes in your account</span>
        </span>
      </div>
    </header>
  );
}

const CHECKS = [
  "Conversion tracking",
  "Wasted spend signals",
  "Landing page speed",
  "Search presence",
  "Ad readiness",
  "Competitor benchmarks",
];

export function WhatWeCheck() {
  return (
    <section>
      <div className="mx-auto max-w-[1200px] px-6 py-14 sm:py-18">
        <div className="flex max-w-[720px] flex-col gap-[18px]">
          <span className="text-[13px] font-bold tracking-[0.08em] text-[#2F5BEA]">
            HOW THE AUDIT WORKS
          </span>
          <h2 className="display text-[28px] leading-[1.1] font-semibold tracking-[-0.02em] sm:text-[40px]">
            40+ checks, built and reviewed by Google Ads specialists
          </h2>
          <p className="text-[16px] leading-[1.6] text-[#4A4560] sm:text-[17px]">
            Every check follows Google&apos;s own published best practices and the patterns our
            specialists see across accounts every week. Not a generic SEO scan.
          </p>
          <div className="grid grid-cols-1 gap-[10px] sm:grid-cols-2">
            {CHECKS.map((one) => (
              <span key={one} className="flex gap-[10px] text-[15px] font-medium">
                <span className="font-bold text-[#2F5BEA]">✓</span>
                {one}
              </span>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}

const PROMISES = [
  ["See your score first", "We only ask how to reach you when you want the full report."],
  ["Nothing changes", "We read your public website. No login, no access to your ads account."],
  ["Your data stays yours", "Never sold or shared. Unsubscribe from anything in one click."],
  ["Keep the report", "Fix it yourself or with anyone you like. No obligation."],
];

export function Promises() {
  return (
    <section className="border-y border-[#E8E5DF] bg-white">
      <div className="mx-auto grid max-w-[1200px] gap-5 px-6 py-12 sm:grid-cols-2 lg:grid-cols-4">
        {PROMISES.map(([title, body]) => (
          <div key={title} className="flex flex-col gap-2">
            <strong className="display text-[18px] font-semibold">{title}</strong>
            <p className="text-[14.5px] leading-[1.55] text-[#4A4560]">{body}</p>
          </div>
        ))}
      </div>
    </section>
  );
}

const QUESTIONS = [
  [
    "Is it really free?",
    "Yes. The audit and the full report are free. No card, and no trial that turns into a charge.",
  ],
  [
    "Do I need to run Google Ads already?",
    "No. If you're not advertising yet, the audit shows what to fix on your site and tracking before you spend.",
  ],
  [
    "Will you change anything?",
    "No. We only read your public website. We never log in to anything or change your ads.",
  ],
  [
    "Who reviews the checks?",
    "PPCway's Google Ads specialists write and review every check, based on Google's own published best practices.",
  ],
  [
    "Why do you ask for my phone number?",
    "So a specialist can walk you through your report if you want. You can tell them not to call, and we never sell your details.",
  ],
];

export function Questions() {
  return (
    <section>
      <div className="mx-auto max-w-[820px] px-6 py-14 sm:py-18">
        <h2 className="display text-[28px] leading-[1.1] font-semibold tracking-[-0.02em] sm:text-[36px]">
          Questions
        </h2>
        <div className="mt-6 flex flex-col">
          {QUESTIONS.map(([q, a]) => (
            <details key={q} className="group border-t border-[#E8E5DF] py-4">
              <summary className="flex cursor-pointer items-center justify-between gap-4 text-[16.5px] font-semibold marker:content-['']">
                {q}
                <span
                  aria-hidden
                  className="text-[#6B6680] transition-transform group-open:rotate-45"
                >
                  +
                </span>
              </summary>
              <p className="mt-3 text-[15px] leading-[1.6] text-[#4A4560]">{a}</p>
            </details>
          ))}
        </div>
      </div>
    </section>
  );
}

export function Closing() {
  return (
    <section className="bg-[#15112A] text-white">
      <div className="mx-auto flex max-w-[1000px] flex-col items-center gap-4 px-6 py-14 text-center sm:py-18">
        <h2 className="display max-w-[760px] text-[26px] leading-[1.15] font-semibold sm:text-[36px]">
          Every day of wasted spend is money you don&apos;t get back.
        </h2>
        <p className="text-[16px] text-[#C9C4D9]">
          Free audit, reviewed by specialists. About a minute to start.
        </p>
        <a
          href="#audit"
          className="tap mt-2 flex h-[54px] items-center rounded-[14px] bg-[#2F5BEA] px-7 text-[17px] font-semibold text-white hover:brightness-95"
        >
          Start my free audit
        </a>
      </div>
    </section>
  );
}

export function AuditFooter() {
  return (
    <footer className="border-t border-[#E8E5DF] bg-white">
      <div className="mx-auto flex max-w-[1200px] flex-wrap items-center justify-between gap-4 px-6 py-8">
        <Brand tone="light" size={26} href="/" />
        <span className="text-[13px] text-[#6B6680]">© 2026 PPCway</span>
        <nav className="flex gap-x-6 text-[14px] text-[#4A4560]" aria-label="Legal">
          <Link href="/privacy" className="tap hover:text-[#15112A]">
            Privacy
          </Link>
          <Link href="/terms" className="tap hover:text-[#15112A]">
            Terms
          </Link>
        </nav>
      </div>
    </footer>
  );
}
