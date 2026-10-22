import type { Metadata } from "next";
import Link from "next/link";
import { LandingPages } from "@/components/pw/landing-pages";
import { ScoreOverTime, WhatChanged } from "@/components/pw/score-history";
import { SendFixes } from "@/components/pw/send-fixes";
import { Chip, Header, HeaderLink, PwCard, PwPage } from "@/components/pw/shell";
import type { History, LandingPage } from "@/lib/audit";
import { ask } from "@/lib/pw-fetch";

export const metadata: Metadata = { title: "Website audit · PPCway" };

/*
  The audit, in the handoff's shape: the score, the four parts it is made of,
  every check with what to do about it, and now the two panels that make it a
  tool rather than a document.

  "Score over time" is the history of the nightly runs, with a marker on the day
  each fix landed. "Page by page" is every page the ads actually send people to,
  taken from the mirror rather than guessed at. Both are read from what is
  already stored, so this page costs a database query.
*/
type Finding = {
  key: string;
  title: string;
  status: "good" | "needs_you" | "ours" | "unknown";
  summary: string;
  detail: string[];
  fix: string | null;
  group: "checks" | "more";
};

type Run = {
  id: string;
  site: string;
  status: string;
  score?: number | null;
  report?: { findings?: Finding[]; pages?: LandingPage[] } | null;
};

/** The three families the public report already groups its checks into. */
const PARTS: { name: string; keys: string[]; what: string }[] = [
  {
    name: "Google listing",
    keys: ["hours", "photos", "reviews", "rating", "phone", "category", "website", "listing"],
    what: "Hours, photos, reviews and categories",
  },
  {
    name: "Website",
    keys: ["speed", "mobile", "https", "headline", "services", "forms_found", "trust"],
    what: "Speed, pages and what they say",
  },
  {
    name: "Ready for ads",
    keys: ["counting", "tags", "phone_above_fold", "policy", "conversion"],
    what: "Whether a click can be counted",
  },
];

function partScore(findings: Finding[], keys: string[]): { score: number; of: number } {
  const mine = findings.filter(
    (f) => keys.some((k) => f.key.includes(k)) && f.status !== "unknown",
  );
  if (!mine.length) return { score: 0, of: 0 };
  return {
    score: Math.round((mine.filter((f) => f.status === "good").length / mine.length) * 100),
    of: mine.length,
  };
}

export default async function AuditToolPage() {
  const runs = await ask<Run[]>("/v1/audits/mine", []);
  const done = runs.filter((r) => r.status === "done");
  const latest = done[0];
  // The listing carries the score; the checks themselves live on the run.
  const full = latest ? await ask<Run | null>(`/v1/audits/${latest.id}`, null) : null;
  const findings = full?.report?.findings ?? [];
  const pages = full?.report?.pages ?? [];
  const history = await ask<History>("/v1/audits/history", {
    site: "",
    points: [],
    changed: null,
  });
  const score = latest?.score ?? null;
  const site = latest ? latest.site.replace(/^https?:\/\//, "").replace(/\/$/, "") : "";

  if (!latest) {
    return (
      <>
        <Header eyebrow="Free tools" title="Website audit" />
        <PwPage>
          <PwCard className="p-6 sm:p-8">
            <h2 className="display text-[22px] leading-[28px] font-semibold">
              You have not run an audit yet
            </h2>
            <p className="text-pw-ink-500 mt-2 max-w-[620px] text-[16px] leading-[25px]">
              It takes about a minute, needs no account details, and checks your Google listing,
              your website and the businesses you compete with.
            </p>
            <Link
              href="/audit"
              className="bg-pw-blue hover:bg-pw-blue-hover mt-5 inline-block rounded-[10px] px-4 py-2 text-[15px] font-semibold text-white"
            >
              Run my free audit
            </Link>
          </PwCard>
        </PwPage>
      </>
    );
  }

  const colour =
    score === null ? "#C9C4D9" : score >= 75 ? "#16A34A" : score >= 55 ? "#B45309" : "#DC2626";
  const problems = findings.filter((f) => f.status === "needs_you" || f.status === "ours");
  const passing = findings.filter((f) => f.status === "good");

  return (
    <>
      <Header
        eyebrow={`Free tools · ${site}`}
        title="Website audit"
        right={
          <>
            <HeaderLink href={`/api/audit/${latest.id}/pdf`}>Download PDF</HeaderLink>
            <HeaderLink href={`/audit/${latest.id}`}>Open the full report</HeaderLink>
            <Link
              href="/audit"
              className="bg-pw-blue hover:bg-pw-blue-hover flex h-[42px] items-center rounded-[12px] px-4 text-[15px] font-semibold text-white"
            >
              Re-run now
            </Link>
          </>
        }
      />
      <PwPage>
        <div className="grid grid-cols-1 gap-4 xl:grid-cols-[1fr_1fr]">
          <PwCard className="flex items-center gap-6 p-6">
            <div
              aria-hidden
              className="flex size-[132px] shrink-0 items-center justify-center rounded-full"
              style={{
                background: `conic-gradient(${colour} ${(score ?? 0) * 3.6}deg, #F0EEEA 0)`,
              }}
            >
              <span className="bg-pw-card flex size-[108px] flex-col items-center justify-center rounded-full">
                <span className="pw-num display text-[38px] leading-none font-semibold">
                  {score ?? "—"}
                </span>
                <span className="text-pw-ink-400 mt-1 text-[12px]">of 100</span>
              </span>
            </div>
            <div className="min-w-0">
              <p className="text-pw-ink-500 text-[14px]">Google Visibility Score</p>
              <p className="display mt-1 text-[22px] leading-[28px] font-semibold">
                {score === null
                  ? "Not scored yet"
                  : score >= 75
                    ? "Good, and climbing"
                    : score >= 55
                      ? "Good, with gaps"
                      : "Leaking budget"}
              </p>
              <p className="text-pw-ink-500 mt-2 text-[14px] leading-[21px]">
                {problems.length === 0
                  ? "Nothing here needs fixing."
                  : `${problems.length} ${problems.length === 1 ? "thing needs" : "things need"} doing on ${site}.`}
              </p>
            </div>
          </PwCard>

          <ScoreOverTime points={history.points} />
        </div>

        <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
          {PARTS.map((part) => {
            const { score: s, of } = partScore(findings, part.keys);
            if (!of) return null;
            const bar = s >= 75 ? "#16A34A" : s >= 55 ? "#B45309" : "#DC2626";
            return (
              <PwCard key={part.name} className="p-5">
                <div className="flex items-baseline justify-between gap-3">
                  <p className="text-[15px] font-semibold">{part.name}</p>
                  <p className="pw-num display text-[22px] font-semibold">{s}</p>
                </div>
                <span className="bg-pw-track mt-3 block h-[6px] overflow-hidden rounded-full">
                  <span
                    className="block h-full rounded-full"
                    style={{ width: `${s}%`, background: bar }}
                  />
                </span>
                <p className="text-pw-ink-500 mt-2 text-[13px] leading-[19px]">{part.what}</p>
              </PwCard>
            );
          })}
        </div>

        <WhatChanged changed={history.changed} site={history.site || latest.site} />

        <LandingPages pages={pages} />

        <PwCard className="overflow-hidden">
          <h2 className="px-5 py-5 text-[17px] leading-[22px] font-semibold sm:px-6">
            Every check
          </h2>
          <ul className="divide-pw-divider divide-y border-t border-[color:var(--pw-divider)]">
            {[...problems, ...passing].map((finding) => (
              <li key={finding.key} className="flex items-start gap-4 px-5 py-4 sm:px-6">
                <span
                  aria-hidden
                  className={`mt-[2px] flex size-[26px] shrink-0 items-center justify-center rounded-full text-[13px] font-bold text-white ${
                    finding.status === "good"
                      ? "bg-pw-good-solid"
                      : finding.status === "ours"
                        ? "bg-pw-blue"
                        : "bg-pw-warn"
                  }`}
                >
                  {finding.status === "good" ? "✓" : finding.status === "ours" ? "i" : "!"}
                </span>
                <div className="min-w-0 flex-1">
                  <p className="text-[16px] leading-[21px] font-semibold">{finding.title}</p>
                  <p className="text-pw-ink-500 mt-1 text-[15px] leading-[22px]">
                    {finding.summary}
                  </p>
                  {finding.fix ? (
                    <p className="text-pw-ink-600 mt-1 text-[14px] leading-[21px]">{finding.fix}</p>
                  ) : null}
                </div>
                {finding.status === "ours" ? <Chip tone="info">PPCway fixes this</Chip> : null}
              </li>
            ))}
          </ul>
        </PwCard>

        <PwCard className="p-5 sm:p-6">
          <SendFixes runId={latest.id} jobs={problems.length} />
        </PwCard>

        <PwCard className="flex flex-wrap items-center justify-between gap-4 p-5 sm:p-6">
          <p className="text-pw-ink-500 max-w-[720px] text-[15px] leading-[23px]">
            This audit now re-runs on its own every night. If a check that was passing stops
            passing, you get an email the same day — a website change is the usual cause, and the
            person who made it will not know it happened.
          </p>
          {done.length > 1 ? (
            <Link href="/audit/mine" className="text-pw-blue text-[15px] font-semibold">
              All {done.length} runs →
            </Link>
          ) : null}
        </PwCard>
      </PwPage>
    </>
  );
}
