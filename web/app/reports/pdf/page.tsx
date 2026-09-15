import Link from "next/link";
import { pickView } from "@/lib/view-param";
import { cn } from "@/lib/cn";

/*
  The downloadable report, from the "V2 · Report · PDF" frames: an A4 page at 794 by
  1123 with 60px margins, the wordmark, a rule, a plain paragraph, three stat boxes,
  a weekly bar chart and the sources of calls. Page 2 lists every change. The agency
  version carries the agency's name and footer.
*/
const PAGES = ["1", "agency", "2"] as const;

const chip = (label: string, tone: "brand" | "grey" | "amber") => (
  <span
    className={cn(
      "inline-flex h-[23px] items-center rounded-full px-[10px] text-[12px] font-semibold",
      {
        brand: "bg-brand-pale text-brand-dark",
        grey: "bg-line-soft text-muted",
        amber: "bg-amber-pale text-amber-dark",
      }[tone],
    )}
  >
    {label}
  </span>
);

export default async function ReportPdf({
  searchParams,
}: {
  searchParams: Promise<{ page?: string }>;
}) {
  const page = pickView(PAGES, (await searchParams).page);
  const agency = page === "agency";
  return (
    <div className="bg-canvas min-h-dvh px-4 py-8 print:bg-white print:p-0">
      <nav
        className="mx-auto mb-6 flex max-w-[794px] flex-wrap gap-2 print:hidden"
        aria-label="Pages"
      >
        {[
          ["1", "Page 1"],
          ["agency", "Page 1, agency"],
          ["2", "Page 2"],
        ].map(([p, l]) => (
          <Link
            key={p}
            href={`/reports/pdf?page=${p}`}
            className={
              p === page
                ? "bg-rail h-[33px] rounded-full px-4 text-[14px] leading-[33px] font-semibold text-white"
                : "text-muted h-[33px] px-2 text-[14px] leading-[33px] font-medium"
            }
          >
            {l}
          </Link>
        ))}
      </nav>
      <article
        className="bg-panel mx-auto w-full max-w-[794px] px-6 py-10 shadow-[0_1px_2px_rgba(15,23,32,0.08)] sm:px-[60px] sm:py-[56px] print:shadow-none"
        style={{ minHeight: 1123 }}
      >
        <header className="flex items-center justify-between gap-4">
          <span className="flex items-center gap-2">
            <span className="bg-brand inline-block size-[22px] rounded-[6px]" />
            <span className="text-ink text-[17px] font-bold">
              {agency ? "brightpath" : "ppcway"}
            </span>
          </span>
          <span className="text-faint text-[13px] font-medium">
            {page === "2"
              ? "Alpha Plumbing · 11 Aug to 9 Sep 2026"
              : agency
                ? "Monthly report · 11 Aug to 9 Sep 2026"
                : "Report · 11 Aug to 9 Sep 2026"}
          </span>
        </header>
        <hr className="border-line mt-5" />
        {page === "2" ? (
          <>
            <h1 className="text-ink mt-6 text-[26px] leading-[31px] font-bold">
              Every change we made
            </h1>
            <p className="text-muted mt-1 text-[14px] leading-[17px]">
              14 changes, newest first. Eight are shown here; the rest continue on page 3.
            </p>
            <ul className="divide-line-soft mt-4 divide-y">
              {[
                [
                  "Lowered the top bid on Drains and blocked toilets",
                  "8 Sep · $114 over 14 days for 3 calls",
                  "Applied",
                  "brand",
                ],
                [
                  "Blocked 3 searches that never called",
                  "8 Sep · $38 spent, no calls",
                  "Applied",
                  "brand",
                ],
                [
                  "Added 'emergency plumber near me'",
                  "7 Sep · it had brought 4 calls",
                  "Applied",
                  "brand",
                ],
                ["Held back a 30% bid raise", "6 Sep · over your 20% a day limit", "Held", "grey"],
                [
                  "Kept the daily budget at $40",
                  "6 Sep · a little ahead of pace, watched another day",
                  "Checked",
                  "grey",
                ],
                [
                  "Paused the ad that mentions weekend rates",
                  "5 Sep · you undid it on 6 Sep",
                  "Undone",
                  "amber",
                ],
                [
                  "Raised the bid on burst pipe searches by 10%",
                  "2 Sep · inside your $14 cap",
                  "Applied",
                  "brand",
                ],
                [
                  "Blocked 2 job-seeker searches",
                  "31 Aug · 'plumber salary' and similar",
                  "Applied",
                  "brand",
                ],
              ].map(([t, m, c, tone]) => (
                <li key={t} className="flex items-center justify-between gap-4 py-[14px]">
                  <span>
                    <span className="text-ink block text-[15px] leading-[18px] font-medium">
                      {t}
                    </span>
                    <span className="text-faint mt-[3px] block text-[13px] leading-4">{m}</span>
                  </span>
                  {chip(c, tone as "brand" | "grey" | "amber")}
                </li>
              ))}
            </ul>
            <hr className="border-line mt-4" />
            <p className="text-faint mt-5 text-[11px] leading-[13px]">
              Page 2 of 6 · Each change was written down before it happened and can be undone from
              Activity.
            </p>
          </>
        ) : (
          <>
            <h1 className="text-ink mt-6 text-[30px] leading-[36px] font-bold">
              {agency ? "Northgate HVAC" : "Alpha Plumbing"}
            </h1>
            <p className="text-muted mt-1 text-[14px] leading-[17px]">
              {agency
                ? "Brampton, Ontario · prepared by Priya Shah, Brightpath Media"
                : "Mississauga, Ontario · Google Ads account 742-118-9063"}
            </p>
            <h2 className="text-ink mt-6 text-[15px] leading-[18px] font-semibold">
              In one paragraph
            </h2>
            <p className="text-ink mt-4 text-[16px] leading-[19px]">
              {agency
                ? "Your ads brought 61 calls for $1,159, which is $19.00 a call. Furnace repair searches picked up as the nights got cooler. We made 11 changes, listed on page 2."
                : "Your campaigns brought 58 calls for $1,240, which is $21.40 a call and 12 more calls than the 30 days before. Plumbing repairs did most of the work. We made 14 changes; the list is on page 2."}
            </p>
            <div className="mt-6 grid grid-cols-3 gap-3">
              {(agency
                ? [
                    ["Calls", "61"],
                    ["Spent", "$1,159"],
                    ["Cost per call", "$19.00"],
                  ]
                : [
                    ["Calls", "58"],
                    ["Spent", "$1,240"],
                    ["Cost per call", "$21.40"],
                  ]
              ).map(([l, v], i) => (
                <div
                  key={l}
                  className={cn(
                    "rounded-[10px] px-4 py-[14px]",
                    i === 0 ? (agency ? "bg-[#e8eefc]" : "bg-brand-pale") : "bg-[#f4f6f8]",
                  )}
                >
                  <p className="text-muted text-[12px] font-medium">{l}</p>
                  <p className="text-ink mt-1 text-[24px] leading-[29px] font-bold">{v}</p>
                </div>
              ))}
            </div>
            <h2 className="text-ink mt-6 text-[15px] leading-[18px] font-semibold">
              Calls each week
            </h2>
            <div className="mt-4 flex h-[120px] items-end gap-[31px]">
              {(agency ? [88, 96, 104, 96, 104] : [80, 96, 88, 88, 112]).map((h, i) => (
                <span
                  key={i}
                  className={cn("block flex-1 rounded-[4px]", i === 4 ? "bg-brand" : "bg-bar-soft")}
                  style={{ height: h }}
                />
              ))}
            </div>
            <div className="text-faint mt-2 flex justify-between text-[11px] font-medium">
              {["11 Aug", "18 Aug", "25 Aug", "1 Sep", "8 Sep"].map((d) => (
                <span key={d}>{d}</span>
              ))}
            </div>
            <h2 className="text-ink mt-6 text-[15px] leading-[18px] font-semibold">
              {agency ? "What we are watching" : "Where the calls came from"}
            </h2>
            <ul className="divide-line-soft mt-2 divide-y">
              {(agency
                ? [
                    [
                      "Calls are down 40% so far this week",
                      "After this report ends · tracking checked · two bid changes suggested",
                      "Watching",
                      "amber",
                    ],
                  ]
                : [
                    [
                      "Plumbing repairs in Mississauga",
                      "41 calls · $860 · $20.98 a call",
                      "71%",
                      "brand",
                    ],
                    ["Google Maps (Local)", "17 calls · $336 · $19.77 a call", "29%", "grey"],
                  ]
              ).map(([t, m, c, tone]) => (
                <li key={t} className="flex items-center justify-between gap-4 py-[14px]">
                  <span>
                    <span className="text-ink block text-[15px] leading-[18px] font-medium">
                      {t}
                    </span>
                    <span className="text-faint mt-[3px] block text-[13px] leading-4">{m}</span>
                  </span>
                  {chip(c, tone as "brand" | "grey" | "amber")}
                </li>
              ))}
            </ul>
            <hr className="border-line mt-4" />
            <p className="text-faint mt-5 text-[11px] leading-[13px]">
              {agency
                ? "Brightpath Media · Oakville, Ontario · reports@brightpath.ca · Page 1 of 5"
                : "Page 1 of 6 · Made by PPCWay on 10 September 2026 · Google may revise the last two or three days."}
            </p>
          </>
        )}
      </article>
    </div>
  );
}
