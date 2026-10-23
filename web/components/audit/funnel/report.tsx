"use client";

import { useEffect, useRef } from "react";
import { Counts, Ring, Tag } from "@/components/audit/funnel/bits";
import { cn } from "@/lib/cn";
import { track, type Unlocked } from "@/lib/funnel";

/*
  The report, which only ever arrives after the address is proved. There is no
  locked version of this component and no findings held back in it: if it is on
  the page at all, the server decided the reader is entitled to it.
*/
const MARK = { fix: "!", improve: "•", good: "✓" } as const;

const ICON = {
  fix: "bg-[#FDECEC] text-[#B91C1C]",
  improve: "bg-[#FFF4E0] text-[#B45309]",
  good: "bg-[#E9FBF0] text-[#15803D]",
} as const;

export function FullReport({ report, who }: { report: Unlocked; who: string }) {
  const seen = useRef<HTMLElement | null>(null);

  useEffect(() => {
    const node = seen.current;
    if (!node) return;
    const watch = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) track("report_view");
      },
      { threshold: 0.2 },
    );
    watch.observe(node);
    return () => watch.disconnect();
  }, []);

  const spending = report.spend && report.spend !== "Not yet" ? report.spend : "Nothing yet";

  return (
    <section
      id="report"
      ref={seen}
      className="mx-auto grid max-w-[1200px] items-start gap-5 px-6 pt-10 pb-14 lg:grid-cols-[minmax(0,1.3fr)_minmax(340px,1fr)]"
    >
      <div className="flex flex-col gap-[14px] rounded-[22px] border border-[#E8E5DF] bg-white p-5 sm:p-6">
        <div className="flex flex-wrap items-center gap-3">
          <h2 className="display flex-1 text-[22px] font-semibold sm:text-[26px]">
            Full report for {report.business}
          </h2>
          <span className="rounded-full bg-[#E9FBF0] px-[10px] py-1 text-[12.5px] font-bold text-[#15803D]">
            Email verified
          </span>
        </div>
        <span className="text-[14.5px] text-[#4A4560]">
          {report.goal} · {spending} a month on ads
        </span>
        <ul className="flex flex-col">
          {report.findings.map((one) => (
            <li key={one.id} className="flex gap-3 border-t border-[#F3F2EE] py-[14px]">
              <span
                className={cn(
                  "flex size-[28px] shrink-0 items-center justify-center rounded-full text-[14px] font-bold",
                  ICON[one.severity],
                )}
                aria-hidden
              >
                {MARK[one.severity]}
              </span>
              <span className="flex min-w-0 flex-1 flex-col gap-1">
                <span className="flex flex-wrap items-center gap-2">
                  <strong className="text-[15.5px] leading-[1.35]">{one.title}</strong>
                  <Tag severity={one.severity} />
                </span>
                {one.detail && (
                  <span className="text-[14px] leading-[1.5] text-[#4A4560]">{one.detail}</span>
                )}
                {one.fix && (
                  <span className="rounded-[10px] bg-[#F6F5F2] px-[10px] py-2 text-[13.5px] leading-[1.5] text-[#15112A]">
                    <strong>How to fix:</strong> {one.fix}
                  </span>
                )}
              </span>
            </li>
          ))}
        </ul>
      </div>

      <div className="flex flex-col gap-5">
        <div className="flex flex-col gap-[18px] rounded-[22px] border border-[#E8E5DF] bg-white p-5 sm:p-6">
          <div className="flex items-center gap-5">
            <Ring score={report.score} size={128} />
            <div className="flex min-w-0 flex-col gap-[6px]">
              <span className="text-[13px] font-bold tracking-[0.06em] text-[#6B6680]">
                AUDIT SCORE
              </span>
              <span className="display text-[22px] leading-[1.25] font-semibold">
                {report.verdict}
              </span>
            </div>
          </div>
          <Counts fix={report.to_fix} improve={report.to_improve} good={report.working} big />
          <div
            className={cn(
              "flex flex-col gap-1 rounded-[16px] px-4 py-[14px]",
              report.waste ? "bg-[#FDECEC] text-[#7F1D1D]" : "bg-[#E9FBF0] text-[#14532D]",
            )}
          >
            <span className="text-[13px] font-bold tracking-[0.04em]">
              ESTIMATED WASTED AD SPEND
            </span>
            <span className="display text-[26px] font-semibold">
              {report.waste ? report.waste.said : "Nothing wasted yet"}
            </span>
            <span className="text-[13px]">
              {report.waste
                ? "Estimate from your site and similar advertisers."
                : "You're not advertising yet. Fix these first so your first dollar works."}
            </span>
          </div>
        </div>

        <div className="flex flex-col gap-3 rounded-[22px] bg-[#15112A] p-5 text-white sm:p-6">
          <strong className="display text-[21px] font-semibold">
            Your audit is unlocked, {who}.
          </strong>
          <p className="text-[15px] leading-[1.55] text-[#C9C4D9]">
            A copy is in your inbox. A specialist may call to walk you through it.
          </p>
          {report.open_again && (
            <a
              href={report.open_again}
              className="text-[14px] font-semibold text-[#A9BCF8] underline"
            >
              Open this report again on another device
            </a>
          )}
        </div>
      </div>
    </section>
  );
}
