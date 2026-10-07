import { ArrowRight, LockSimple } from "@phosphor-icons/react/dist/ssr";
import Link from "next/link";
import { LinkButton } from "@/components/ui/button";
import { cn } from "@/lib/cn";
import type { AuditLine, AuditPanel, AuditSample } from "./report-views";
import { FixBar } from "./fix-bar";
import { AuditPage, Card } from "./shell";

/*
  The report in the client's website design: a night panel with the score as a
  ring, one list of checks badged pass, warn, fail or information, then the four
  checks only their own Google Ads account can answer, then where each number came
  from. Their handoff fills this with sample data; ours fills it with the run.

  Four badges, their words: a tick for what is fine, an exclamation for what needs
  a small change, a cross for what is costing money, an "i" for what is only worth
  knowing.
*/
type Badge = "pass" | "warn" | "fail" | "info";

const BADGE: Record<Badge, { background: string; glyph: string; label: string }> = {
  pass: { background: "bg-pass", glyph: "✓", label: "Good" },
  warn: { background: "bg-amber", glyph: "!", label: "Needs a change" },
  fail: { background: "bg-red", glyph: "✕", label: "Costing you" },
  info: { background: "bg-brand", glyph: "i", label: "Worth knowing" },
};

/** The four an audit cannot see without their permission, in the client's words. */
const LOCKED = [
  "Wasted spend on search terms",
  "Quality Score by keyword",
  "Budget lost to impression share",
  "Ad disapprovals and policy issues",
];

const SOURCES: [string, string][] = [
  ["Business profile, rating, reviews and hours", "Your public Google Business Profile"],
  ["Mobile page speed", "A live mobile speed test of your website"],
  ["Conversion tracking", "A scan of your website for Google conversion tracking"],
  ["Your website's pages and wording", "The pages we read, up to twenty five of them"],
  ["The businesses you compete with", "Google Maps, for the same trade near you"],
  ["Wasted spend (locked)", "Your Google Ads search terms, with your permission"],
  ["Quality Score (locked)", "Your Google Ads keywords"],
  ["Lost impression share (locked)", "Your Google Ads campaigns"],
  ["Disapprovals (locked)", "Your ads and their policy status"],
];

function badgeOf(line: AuditLine): Badge {
  if (line.verdict === "good") return "pass";
  if (line.verdict === "cost") return "fail";
  return line.who === "us" ? "info" : "warn";
}

/** Their three verdicts, on our score. */
function verdict(score: number): string {
  if (score >= 75) return "Strong start";
  if (score >= 55) return "Good, with gaps";
  return "Leaking budget";
}

function ringColour(score: number): string {
  return score >= 75 ? "#22C55E" : score >= 55 ? "#F59E0B" : "#EF4444";
}

function Check({ line, source }: { line: AuditLine; source: string }) {
  const badge = BADGE[badgeOf(line)];
  return (
    <li className="flex items-start gap-4 px-5 py-5 sm:px-7">
      <span
        aria-hidden
        className={cn(
          "mt-[2px] flex size-[26px] shrink-0 items-center justify-center rounded-full text-[14px] font-extrabold text-white",
          badge.background,
        )}
      >
        {badge.glyph}
      </span>
      <span className="min-w-0 flex-1">
        <span className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1">
          <span className="text-[16px] leading-[21px] font-bold sm:text-[17px]">{line.title}</span>
          <span className="text-faint shrink-0 text-[12px] leading-4 font-semibold tracking-[0.06em] uppercase">
            {source}
          </span>
        </span>
        <span className="text-muted mt-1 block text-[15px] leading-[23px]">{line.meta}</span>
        {line.who ? (
          <span
            className={cn(
              "mt-2 inline-flex h-[24px] items-center rounded-full px-[10px] text-[12px] leading-4 font-semibold",
              line.who === "us" ? "bg-brand-pale text-brand-ink" : "bg-line-soft text-muted",
            )}
          >
            {line.who === "us" ? "PPCWay fixes this" : "Yours, with our steps"}
          </span>
        ) : null}
      </span>
    </li>
  );
}

export function ScoreReport({ sample }: { sample: AuditSample }) {
  const checks: { line: AuditLine; source: string }[] = sample.panels.flatMap((panel: AuditPanel) =>
    panel.lines.map((line) => ({ line, source: panel.title.replace(/^Your /, "") })),
  );
  // Problems first, and the costly ones before those: the order money is lost in.
  const ordered = [...checks].sort(
    (a, b) =>
      Number(a.line.verdict === "good") - Number(b.line.verdict === "good") ||
      Number(b.line.verdict === "cost") - Number(a.line.verdict === "cost"),
  );
  const colour = ringColour(sample.readiness);

  return (
    <AuditPage wide>
      <p className="text-brand text-[13px] leading-4 font-semibold tracking-[0.08em] uppercase">
        {sample.date}
      </p>
      <h1 className="mt-3 text-[34px] leading-[40px] font-semibold text-balance sm:text-[44px] sm:leading-[52px]">
        {sample.business}
      </h1>
      <p className="text-muted mt-4 max-w-[760px] text-[17px] leading-[27px]">{sample.summary}</p>

      <section className="bg-night mt-8 rounded-[26px] p-6 text-white sm:p-9">
        <div className="flex flex-col gap-7 sm:flex-row sm:items-center">
          <div
            aria-hidden
            className="flex size-[132px] shrink-0 items-center justify-center rounded-full"
            style={{
              background: `conic-gradient(${colour} ${sample.readiness * 3.6}deg, #2C2645 0)`,
            }}
          >
            <span className="bg-night flex size-[108px] flex-col items-center justify-center rounded-full">
              <span className="display text-[38px] leading-none font-semibold">
                {sample.readiness}
              </span>
              <span className="text-night-faint mt-1 text-[12px]">out of 100</span>
            </span>
          </div>
          <div className="min-w-0">
            <p className="text-brand-sky text-[13px] leading-4 font-semibold tracking-[0.08em] uppercase">
              Google visibility score
            </p>
            <p className="display mt-2 text-[26px] leading-[32px] font-semibold">
              {verdict(sample.readiness)}
            </p>
            <p className="text-night-faint mt-2 text-[15px] leading-[23px]">
              {sample.after > sample.readiness
                ? `${sample.after} once the ${sample.after - sample.readiness} points marked "PPCWay fixes this" are done.`
                : "Nothing here is dragging the score down."}
            </p>
            <p className="sr-only">
              Your Google visibility score is {sample.readiness} out of 100.
            </p>
          </div>
        </div>
      </section>

      <section className="mt-8">
        <Card className="overflow-hidden">
          <ul className="divide-line-soft divide-y">
            {ordered.map(({ line, source }) => (
              <Check key={line.title} line={line} source={source} />
            ))}
          </ul>
        </Card>
      </section>

      <section className="mt-8">
        <Card className="overflow-hidden">
          <div className="border-line-soft flex flex-wrap items-center justify-between gap-3 border-b px-5 py-5 sm:px-7">
            <div>
              <h2 className="text-[20px] leading-[26px] font-semibold">
                Four more, locked to your account
              </h2>
              <p className="text-muted mt-1 max-w-[620px] text-[15px] leading-[23px]">
                These read your own Google Ads account. Google shows them to the account owner and
                to nobody else, so we cannot see them and neither can your competitors.
              </p>
            </div>
            <LinkButton href="/signup" size="sm">
              Connect Google Ads, read only
              <ArrowRight aria-hidden size={15} weight="bold" />
            </LinkButton>
          </div>
          <ul className="divide-line-soft divide-y">
            {LOCKED.map((row) => (
              <li key={row} className="flex items-center gap-4 px-5 py-4 sm:px-7">
                <span
                  aria-hidden
                  className="bg-red flex size-[26px] shrink-0 items-center justify-center rounded-full text-white"
                >
                  <LockSimple size={14} weight="bold" />
                </span>
                <span className="text-[16px] leading-[21px] font-bold">{row}</span>
              </li>
            ))}
          </ul>
        </Card>
      </section>

      {sample.locked ? (
        <section className="mt-8">
          <Card className="px-5 py-5 sm:px-7">
            <h2 className="text-[20px] leading-[26px] font-semibold">{sample.locked.title}</h2>
            <p className="text-muted mt-1 text-[15px] leading-[23px]">{sample.locked.note}</p>
            <ul className="divide-line-soft border-line-soft mt-4 divide-y border-t">
              {sample.locked.shown.map((row) => (
                <li key={row} className="py-3 text-[15px] leading-[21px] font-semibold">
                  {row}
                </li>
              ))}
            </ul>
            <div className="mt-4 flex flex-wrap items-center gap-3">
              <LinkButton href="/signup" size="sm" variant="secondary">
                See all {sample.locked.total} with a free account
              </LinkButton>
            </div>
          </Card>
        </section>
      ) : null}

      <section className="mt-10">
        <p className="text-brand text-[13px] leading-4 font-semibold tracking-[0.08em] uppercase">
          Where the numbers come from
        </p>
        <h2 className="mt-2 text-[26px] leading-[32px] font-semibold sm:text-[32px] sm:leading-[38px]">
          Built on Google&rsquo;s own data.
        </h2>
        <Card className="mt-5 overflow-hidden">
          <div className="grid grid-cols-1 sm:grid-cols-2">
            <div className="bg-panel-alt text-faint border-line-soft hidden border-b px-5 py-3 text-[13px] font-semibold tracking-[0.06em] uppercase sm:block sm:px-7">
              What you see
            </div>
            <div className="bg-panel-alt text-faint border-line-soft hidden border-b px-5 py-3 text-[13px] font-semibold tracking-[0.06em] uppercase sm:block sm:px-7">
              Where it comes from
            </div>
            {SOURCES.map(([what, where]) => (
              <div key={what} className="contents">
                <div className="border-line-soft border-t px-5 pt-4 pb-1 text-[15px] leading-[21px] font-semibold sm:px-7 sm:py-4">
                  {what}
                </div>
                <div className="text-muted border-line-soft px-5 pb-4 text-[15px] leading-[21px] sm:border-t sm:px-7 sm:py-4">
                  {where}
                </div>
              </div>
            ))}
          </div>
        </Card>
      </section>

      <section id="close" className="bg-night mt-10 rounded-[26px] p-6 text-white sm:p-9">
        <div className="flex flex-col gap-7 lg:flex-row lg:items-center lg:justify-between">
          <div className="max-w-[640px]">
            <h2 className="display text-[26px] leading-[32px] font-semibold sm:text-[32px] sm:leading-[38px]">
              Get this audit every day, not just once.
            </h2>
            <p className="text-night-faint mt-3 text-[15px] leading-[23px]">
              {sample.close.body} We rerun these checks every morning and propose the fixes you
              approve in one tap.
            </p>
          </div>
          <div className="flex w-full flex-col gap-3 sm:w-auto sm:flex-row lg:w-[240px] lg:flex-col">
            <LinkButton href="/signup" full>
              Fix these for me
            </LinkButton>
            <Link
              href="/audit?view=checking"
              className="border-night-line hover:bg-night-raised inline-flex h-[46px] items-center justify-center rounded-[12px] border px-7 text-[15px] font-semibold text-white"
            >
              Email me this audit
            </Link>
          </div>
        </div>
      </section>

      <FixBar text={sample.bar} />
    </AuditPage>
  );
}
