import type { Metadata } from "next";
import Link from "next/link";
import { Chip, PwCard } from "@/components/pw/shell";
import { Header, PwPage } from "@/components/pw/shell";
import { ask } from "@/lib/pw-fetch";

export const metadata: Metadata = { title: "Website audit · PPCway" };

type Run = {
  id: string;
  site: string;
  status: string;
  report?: { findings?: { status: string }[] } | null;
};

function scoreOf(run: Run): number | null {
  const findings = run.report?.findings;
  if (!findings?.length) return null;
  const good = findings.filter((f) => f.status === "good").length;
  return Math.round((good / findings.length) * 100);
}

export default async function AuditToolPage() {
  const runs = await ask<Run[]>("/v1/audits/mine", []);
  const done = runs.filter((r) => r.status === "done");
  const latest = done[0];
  const score = latest ? scoreOf(latest) : null;

  return (
    <>
      <Header eyebrow="Free tools" title="Website audit" />
      <PwPage>
        {latest ? (
          <PwCard className="flex flex-wrap items-center justify-between gap-5 p-5 sm:p-6">
            <div className="flex items-center gap-5">
              <div
                aria-hidden
                className="flex size-[86px] shrink-0 items-center justify-center rounded-full"
                style={{
                  background: `conic-gradient(${score !== null && score >= 75 ? "#16A34A" : score !== null && score >= 55 ? "#B45309" : "#DC2626"} ${(score ?? 0) * 3.6}deg, #F0EEEA 0)`,
                }}
              >
                <span className="bg-pw-card pw-num flex size-[68px] items-center justify-center rounded-full text-[24px] font-semibold">
                  {score ?? "—"}
                </span>
              </div>
              <div className="min-w-0">
                <p className="text-[17px] leading-[22px] font-semibold">
                  {latest.site.replace(/^https?:\/\//, "").replace(/\/$/, "")}
                </p>
                <p className="text-pw-ink-500 mt-1 text-[14px] leading-[21px]">
                  Your Google listing, your website and your competitors, as Google sees them.
                </p>
              </div>
            </div>
            <div className="flex flex-wrap gap-3">
              <Link
                href={`/audit/${latest.id}`}
                className="bg-pw-blue hover:bg-pw-blue-hover rounded-[10px] px-4 py-2 text-[14px] font-semibold text-white"
              >
                Open the report
              </Link>
              <Link
                href="/audit"
                className="border-pw-border-strong hover:bg-pw-muted rounded-[10px] border px-4 py-2 text-[14px] font-semibold"
              >
                Run it again
              </Link>
            </div>
          </PwCard>
        ) : (
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
              className="bg-pw-blue hover:bg-pw-blue-hover mt-5 inline-block rounded-[10px] px-4 py-2 text-[14px] font-semibold text-white"
            >
              Run my free audit
            </Link>
          </PwCard>
        )}

        {done.length > 1 ? (
          <PwCard className="overflow-hidden">
            <h2 className="px-5 py-5 text-[17px] leading-[22px] font-semibold sm:px-6">
              Every run
            </h2>
            <ul className="divide-pw-divider divide-y">
              {done.map((run) => (
                <li
                  key={run.id}
                  className="flex flex-wrap items-center justify-between gap-3 px-5 py-3 sm:px-6"
                >
                  <span className="min-w-0 truncate text-[15px] font-semibold">
                    {run.site.replace(/^https?:\/\//, "").replace(/\/$/, "")}
                  </span>
                  <span className="flex items-center gap-3">
                    <Chip tone="neutral">{scoreOf(run) ?? "—"} of 100</Chip>
                    <Link
                      href={`/audit/${run.id}`}
                      className="text-pw-blue text-[14px] font-semibold"
                    >
                      Open
                    </Link>
                  </span>
                </li>
              ))}
            </ul>
          </PwCard>
        ) : null}

        <PwCard className="p-5 sm:p-6">
          <p className="text-pw-ink-500 text-[15px] leading-[23px]">
            The audit does not re-run on its own yet, so each result is from the day you ran it.
            Scheduled checks, the score over time and an alert when something breaks are the next
            pieces of this tool.
          </p>
        </PwCard>
      </PwPage>
    </>
  );
}
