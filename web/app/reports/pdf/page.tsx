import { ArrowLeft } from "@phosphor-icons/react/dist/ssr";
import type { Metadata } from "next";
import Link from "next/link";
import { DownloadReport } from "@/components/pw/download-report";
import { ReportPaper } from "@/components/pw/report-paper";
import { ask } from "@/lib/pw-fetch";
import type { ReportSaid } from "@/lib/reports";

export const metadata: Metadata = { title: "Report · PPCway", robots: { index: false } };

/*
  The report on paper, with real figures, read when the page is opened.

  Two readers. The backend's Chromium, signed in as whoever pressed "Download
  PDF", prints this page to make the PDF; it prints with the print styles, so
  the grey desk and the buttons below vanish and only the sheets remain. And a
  person can open it to see the PDF before they download it, or print it from
  the browser.
*/
const PERIODS = new Set([7, 30, 90]);

export default async function ReportOnPaper({
  searchParams,
}: {
  searchParams: Promise<{ days?: string }>;
}) {
  const asked = Number((await searchParams).days ?? 30);
  const days = PERIODS.has(asked) ? asked : 30;
  const said = await ask<ReportSaid>(`/v1/reports?days=${days}`, {
    read: false,
    unreachable: true,
  });

  return (
    <div className="bg-pw-ground min-h-dvh px-4 py-8 print:bg-white print:p-0">
      <nav
        className="mx-auto mb-6 flex max-w-[794px] flex-wrap items-start justify-between gap-3 print:hidden"
        aria-label="Report"
      >
        <Link
          href={`/reports?days=${days}`}
          className="text-pw-ink-600 hover:text-pw-ink flex h-[42px] items-center gap-2 text-[15px] font-semibold"
        >
          <ArrowLeft size={16} weight="bold" />
          Back to Reports
        </Link>
        {said.read ? <DownloadReport days={days} /> : null}
      </nav>
      {said.read ? (
        <div className="mx-auto max-w-[794px] shadow-[0_1px_3px_rgba(21,17,42,0.08),0_12px_32px_-12px_rgba(21,17,42,0.12)] print:max-w-none print:shadow-none">
          <ReportPaper said={said} />
        </div>
      ) : (
        <div className="bg-pw-card border-pw-border mx-auto max-w-[560px] rounded-[18px] border p-7">
          <h1 className="text-[20px] leading-[26px] font-semibold">
            There is no report to print yet
          </h1>
          <p className="text-pw-ink-600 mt-2 text-[15px] leading-[23px]">
            {said.unreachable
              ? "PPCWay could not reach its own service. Reload this page in a minute."
              : (said.trouble ?? "Connect a Google Ads account and the report builds itself.")}
          </p>
        </div>
      )}
    </div>
  );
}
