"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { AuditPage } from "@/components/audit/shell";
import { CheckingRows } from "@/components/audit/find-views";
import { ListRow, Rows } from "@/components/app/blocks";
import type { ChipTone } from "@/components/app/blocks";

/*
  The public report for one audit run. Polls the API every three seconds until
  the run is done, then draws the eight checks the same way step 4 of onboarding
  does: green is fine, amber needs the merchant, grey is ours.
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
type Report = {
  site: string;
  business_name: string;
  pages_read: number;
  findings: Finding[];
  notes: string[];
  screenshot_urls: Record<string, string>;
  headline: string;
};
type Run = {
  id: string;
  site: string;
  status: "queued" | "running" | "done" | "failed";
  report: Report | null;
  error: string | null;
};

const CHIP: Record<Finding["status"], { label: string; tone: ChipTone }> = {
  good: { label: "Good", tone: "pale" },
  needs_you: { label: "Needs you", tone: "amber" },
  ours: { label: "We'll handle it", tone: "grey" },
  unknown: { label: "Could not check", tone: "grey" },
};

export function AuditReportView({ id }: { id: string }) {
  const [run, setRun] = useState<Run | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let stop = false;
    let timer: number | undefined;
    async function tick() {
      try {
        const res = await fetch(`/api/audit/${id}`, { cache: "no-store" });
        const data = (await res.json()) as Run & { error?: string };
        if (stop) return;
        if (!res.ok) {
          setError(data.error ?? "We could not find that audit.");
          return;
        }
        setRun(data);
        if (data.status === "queued" || data.status === "running")
          timer = window.setTimeout(tick, 3000);
      } catch {
        if (!stop) setError("We could not reach the audit service.");
      }
    }
    tick();
    return () => {
      stop = true;
      if (timer) window.clearTimeout(timer);
    };
  }, [id]);

  const report = run?.report ?? null;
  const counts = report
    ? report.findings.reduce(
        (a, f) => ({ ...a, [f.status]: (a[f.status] ?? 0) + 1 }),
        {} as Record<string, number>,
      )
    : null;

  return (
    <AuditPage>
      <div>
        {error ? (
          <p className="text-red-strong text-[16px] leading-6 font-medium" role="alert">
            {error}
          </p>
        ) : !run ? (
          <p className="text-muted text-[16px] leading-6">Loading your check…</p>
        ) : run.status === "failed" ? (
          <div>
            <h1 className="text-[28px] leading-[34px] font-semibold">
              We could not finish checking {run.site}.
            </h1>
            <p className="text-muted mt-3 text-[16px] leading-6">
              The site did not answer the way we expected. We will look at it by hand and email you.
              Nothing more to do on your side.
            </p>
          </div>
        ) : run.status !== "done" || !report ? (
          <div>
            <h1 className="text-[32px] leading-[38px] font-bold text-balance sm:text-[42px] sm:leading-[51px]">
              Checking {run.site.replace(/^https?:\/\//, "").replace(/\/$/, "")}.
            </h1>
            <p className="text-muted mt-6 max-w-[700px] text-[18px] leading-[22px]">
              About a minute. You can stay on this page. We read your pages, load the home page on a
              phone, ask Google how fast it is, and look for the tags. We change nothing on your
              site.
            </p>
            <div className="bg-panel border-line mt-6 rounded-[16px] border px-5 py-1 sm:px-7">
              <CheckingRows
                steps={[
                  {
                    title: "Your website",
                    meta: "Reading up to 25 pages: services, areas, phone numbers and tracking tags",
                    state: run.status === "running" ? "running" : "todo",
                  },
                  {
                    title: "On a phone and a laptop",
                    meta: "What loads, what fires, and what the first screen shows",
                    state: "todo",
                  },
                  {
                    title: "Speed, from Google",
                    meta: "Lighthouse on a mid-range phone on 4G",
                    state: "todo",
                  },
                  {
                    title: "Your Google listing and your ads",
                    meta: "Coming soon: category, reviews, hours, and whether you show for the searches that matter",
                    state: "todo",
                  },
                ]}
              />
            </div>
          </div>
        ) : (
          <div>
            <h1 className="text-[28px] leading-[34px] font-semibold text-balance sm:text-[34px] sm:leading-[40px]">
              {headline(counts ?? {}, report)}
            </h1>
            <p className="text-muted mt-3 text-[16px] leading-6">
              Eight checks on {report.site}, {report.pages_read} pages read. Green is fine. Amber
              needs a small change from you. Grey is ours to handle.
            </p>
            {report.screenshot_urls?.phone || report.screenshot_urls?.laptop ? (
              <section className="mt-8">
                <h2 className="text-[22px] leading-[27px] font-semibold">What people see first</h2>
                <p className="text-muted mt-1 text-[15px] leading-[22px]">
                  Your home page the moment it opens, on a phone and on a laptop. This is the whole
                  first impression an ad buys.
                </p>
                <div className="mt-4 grid gap-4 sm:grid-cols-[minmax(0,200px)_1fr]">
                  {report.screenshot_urls.phone ? (
                    // eslint-disable-next-line @next/next/no-img-element
                    <img
                      src={`/api/audit/${id}/screenshot/phone`}
                      alt="The home page on a phone"
                      width={390}
                      height={844}
                      className="border-line aspect-[390/844] w-full max-w-[200px] rounded-[16px] border object-cover object-top"
                    />
                  ) : null}
                  {report.screenshot_urls.laptop ? (
                    // eslint-disable-next-line @next/next/no-img-element
                    <img
                      src={`/api/audit/${id}/screenshot/laptop`}
                      alt="The home page on a laptop"
                      width={1440}
                      height={900}
                      className="border-line aspect-[1440/900] w-full rounded-[16px] border object-cover object-top"
                    />
                  ) : null}
                </div>
              </section>
            ) : null}
            <h2 className="mt-10 text-[22px] leading-[27px] font-semibold">The eight checks</h2>
            <div className="bg-panel border-line mt-4 rounded-[16px] border px-5 sm:px-6">
              <Rows className="mt-0">
                {report.findings
                  .filter((f) => f.group !== "more")
                  .map((f) => (
                    <ListRow
                      key={f.key}
                      title={f.title}
                      meta={f.summary}
                      chip={CHIP[f.status].label}
                      chipTone={CHIP[f.status].tone}
                      dot
                    />
                  ))}
              </Rows>
            </div>
            {report.findings.some((f) => f.group === "more") ? (
              <section className="mt-10">
                <h2 className="text-[22px] leading-[27px] font-semibold">Under the hood</h2>
                <p className="text-muted mt-1 text-[15px] leading-[22px]">
                  Three more looks an agency takes before it spends: the first screen, the
                  site&rsquo;s plumbing, and how local the site reads.
                </p>
                <div className="bg-panel border-line mt-4 rounded-[16px] border px-5 sm:px-6">
                  <Rows className="mt-0">
                    {report.findings
                      .filter((f) => f.group === "more")
                      .map((f) => (
                        <ListRow
                          key={f.key}
                          title={f.title}
                          meta={f.summary}
                          chip={CHIP[f.status].label}
                          chipTone={CHIP[f.status].tone}
                          dot
                        />
                      ))}
                  </Rows>
                </div>
              </section>
            ) : null}
            {report.findings.filter((f) => f.status === "needs_you").length ? (
              <section className="mt-10">
                <h2 className="text-[22px] leading-[27px] font-semibold">What to fix first</h2>
                <ol className="mt-4 flex flex-col gap-4">
                  {report.findings
                    .filter((f) => f.status === "needs_you")
                    .map((f) => (
                      <li
                        key={f.key}
                        className="bg-amber-tint border-amber-line rounded-[16px] border p-5"
                      >
                        <p className="text-[17px] leading-[22px] font-semibold">{f.title}</p>
                        <ul className="text-muted mt-2 flex flex-col gap-1 text-[14px] leading-5">
                          {f.detail.map((d) => (
                            <li key={d}>{d}</li>
                          ))}
                        </ul>
                        {f.fix ? <p className="mt-3 text-[15px] leading-[22px]">{f.fix}</p> : null}
                      </li>
                    ))}
                </ol>
              </section>
            ) : null}
            <section className="mt-10">
              <h2 className="text-[22px] leading-[27px] font-semibold">Everything we saw</h2>
              <div className="divide-line-soft mt-2 divide-y">
                {report.findings.map((f) => (
                  <details key={f.key} className="group py-4">
                    <summary className="flex cursor-pointer list-none items-center justify-between gap-4 text-[16px] leading-5 font-semibold [&::-webkit-details-marker]:hidden">
                      {f.title}
                      <span
                        aria-hidden
                        className="text-faint text-[22px] leading-none transition-transform duration-[120ms] group-open:rotate-45"
                      >
                        +
                      </span>
                    </summary>
                    <ul className="text-muted mt-2 flex flex-col gap-1 text-[14px] leading-5">
                      {f.detail.length ? (
                        f.detail.map((d) => <li key={d}>{d}</li>)
                      ) : (
                        <li>{f.summary}</li>
                      )}
                    </ul>
                  </details>
                ))}
              </div>
            </section>
            {report.notes?.length ? (
              <p className="text-faint mt-6 text-[13px] leading-4">
                {report.notes.map((n) => plainNote(n)).join(" ")}
              </p>
            ) : null}
            <div className="bg-rail mt-12 rounded-[16px] p-6 text-white sm:p-8">
              <p className="text-[22px] leading-[27px] font-semibold text-balance">
                Want us to run the ads and handle the grey ones?
              </p>
              <p className="text-rail-icon mt-2 text-[15px] leading-[22px]">
                About 15 minutes from here to a campaign you approve line by line. Free for 14 days.
              </p>
              <Link
                href="/signup"
                className="bg-panel text-brand-dark hover:bg-brand-pale mt-5 inline-flex h-11 items-center rounded-full px-5 text-[15px] font-semibold"
              >
                Start with this site
              </Link>
            </div>
          </div>
        )}
      </div>
    </AuditPage>
  );
}

function plainNote(note: string): string {
  if (note.startsWith("pagespeed failed"))
    return "Google's speed test did not answer in time, so the speed check is missing; run the audit again in a few minutes.";
  if (note.startsWith("render failed"))
    return "The page could not be opened in a browser, so the checks that need one are missing.";
  if (note.startsWith("crawl failed"))
    return "The site could not be read page by page, so some checks are missing.";
  if (note.startsWith("health check failed")) return "The site health check did not finish.";
  return "";
}

function headline(counts: Record<string, number>, report: Report): string {
  const needs = counts.needs_you ?? 0;
  const who = report.business_name || report.site;
  if (needs === 0) return `${who}: nothing for you to fix.`;
  if (needs === 1) return `${who}: one thing needs you.`;
  return `${who}: ${needs} things need you.`;
}
