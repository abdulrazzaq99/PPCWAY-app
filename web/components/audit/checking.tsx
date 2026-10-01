"use client";

import { useEffect, useState } from "react";
import { Card } from "./shell";

/*
  The wait, which runs one to four minutes depending on the site. A spinner for
  that long reads as a broken page, so this says what is happening now, how far
  along it is, and how long it has been.

  The stage comes from the run itself, reported as each one begins, and the page
  count climbs as the crawl reads. Between stages the bar creeps towards the end
  of the stage it is in and never past it, so it cannot claim to be further on
  than it is.
*/
export type Stage = "crawling" | "rendering" | "speed" | "checks" | "done" | "";

const STEPS: { key: Stage; title: string; meta: string; seconds: number }[] = [
  {
    key: "crawling",
    title: "Reading your website",
    meta: "Up to 25 pages: services, towns served, phone numbers and tracking tags",
    seconds: 45,
  },
  {
    key: "rendering",
    title: "Opening it on a phone",
    meta: "A phone screen and a laptop screen, photographed as a visitor sees them",
    seconds: 45,
  },
  {
    key: "speed",
    title: "Asking Google how fast it is",
    meta: "Google measures your home page on a mid-range phone. This is the slow part",
    seconds: 60,
  },
  {
    key: "checks",
    title: "Writing your report",
    meta: "Your Google listing, your competitors, and what to fix first",
    seconds: 15,
  },
];

const TOTAL = STEPS.reduce((a, s) => a + s.seconds, 0);

/** Where the bar sits: the stages behind us, plus some of the one running. */
function progress(stage: Stage, inStage: number): number {
  if (stage === "done") return 100;
  const at = STEPS.findIndex((s) => s.key === stage);
  if (at < 0) return 4;
  const before = STEPS.slice(0, at).reduce((a, s) => a + s.seconds, 0);
  const mine = STEPS[at].seconds;
  // Approaches the end of this stage without ever reaching it.
  const part = mine * (1 - Math.exp(-inStage / mine));
  return Math.min(99, Math.round(((before + part * 0.9) / TOTAL) * 100));
}

function clock(seconds: number): string {
  const whole = Math.max(0, Math.floor(seconds));
  const m = Math.floor(whole / 60);
  const s = whole % 60;
  return m > 0 ? `${m}m ${String(s).padStart(2, "0")}s` : `${s}s`;
}

export function Checking({
  site,
  stage,
  pagesRead,
}: {
  site: string;
  stage: Stage;
  pagesRead: number;
}) {
  // One clock. How long the current stage has run is worked out from the total
  // elapsed and the stages already behind it, so there is no second timer.
  const [now, setNow] = useState(() => Date.now());
  const [opened] = useState(() => Date.now());

  useEffect(() => {
    const tick = window.setInterval(() => setNow(Date.now()), 1000);
    return () => window.clearInterval(tick);
  }, []);

  const elapsed = (now - opened) / 1000;
  const at = STEPS.findIndex((s) => s.key === stage);
  const done = at < 0 ? 0 : at;
  const behind = STEPS.slice(0, done).reduce((a, s) => a + s.seconds, 0);
  const bar = progress(stage, Math.max(0, elapsed - behind));

  return (
    <>
      <h1 className="text-[32px] leading-[38px] font-bold text-balance sm:text-[42px] sm:leading-[51px]">
        Checking {site}.
      </h1>
      <p className="text-muted mt-6 max-w-[700px] text-[18px] leading-[22px]">
        One to four minutes, depending on how big your site is. Stay and watch, or give us an email
        address below and we will send the report when it is ready. We change nothing on your site.
      </p>

      <Card className="mt-6 p-5 sm:p-7">
        <div className="flex flex-wrap items-end justify-between gap-x-4 gap-y-1">
          <p className="text-[17px] leading-[21px] font-bold sm:text-[20px] sm:leading-6">
            {at < 0 ? "Starting" : STEPS[at].title}
          </p>
          <p className="text-muted text-[14px] leading-[17px] font-semibold tabular-nums">
            {bar}% · {clock(elapsed)}
          </p>
        </div>
        <div
          className="bg-track mt-3 h-2 overflow-hidden rounded-full"
          role="progressbar"
          aria-valuenow={bar}
          aria-valuemin={0}
          aria-valuemax={100}
          aria-label="How far the check has got"
        >
          <div
            className="bg-brand h-full rounded-full transition-[width] duration-700 ease-out motion-reduce:transition-none"
            style={{ width: `${bar}%` }}
          />
        </div>
        {pagesRead > 0 ? (
          <p className="text-faint mt-2 text-[13px] leading-4 tabular-nums">
            {pagesRead} {pagesRead === 1 ? "page" : "pages"} read so far
          </p>
        ) : null}

        <div className="divide-line-soft mt-4 divide-y">
          {STEPS.map((step, i) => {
            const state = stage === "done" || i < done ? "done" : i === done ? "running" : "todo";
            return (
              <div key={step.key} className="flex items-start gap-[14px] py-4">
                <span
                  className={`mt-[2px] flex size-7 shrink-0 items-center justify-center rounded-full text-[14px] font-bold ${
                    state === "done"
                      ? "bg-brand-pale text-brand"
                      : state === "running"
                        ? "bg-brand text-white"
                        : "bg-line-soft text-faint"
                  }`}
                >
                  {state === "done" ? "✓" : null}
                  {state === "running" ? (
                    <span className="size-2 animate-ping rounded-full bg-white motion-reduce:animate-none" />
                  ) : null}
                  {state === "todo" ? i + 1 : null}
                </span>
                <span className="min-w-0">
                  <span
                    className={`block text-[16px] leading-[19px] font-semibold ${
                      state === "todo" ? "text-faint" : "text-ink"
                    }`}
                  >
                    {step.title}
                  </span>
                  <span className="text-faint mt-[2px] block text-[13px] leading-4">
                    {step.meta}
                  </span>
                </span>
              </div>
            );
          })}
        </div>
      </Card>
    </>
  );
}
