import type { Metadata } from "next";
import { DownloadReport } from "@/components/pw/download-report";
import { Report } from "@/components/pw/report";
import { ShareReport } from "@/components/pw/share-report";
import { Header, PillGroup, PillLink, PwCard, PwPage } from "@/components/pw/shell";
import { NotConnected } from "@/components/pw/states";
import { ask } from "@/lib/pw-fetch";
import { periodWords } from "@/lib/report-view";
import type { ReportSaid } from "@/lib/reports";

export const metadata: Metadata = { title: "Reports · PPCway" };

/*
  The report, over whichever period is asked for, built when the page is
  opened: everything comes out of our own mirror, which the syncs keep current,
  including the same period a year ago. The PDF is printed from the same
  figures at the moment it is downloaded, so neither is ever a stale copy.
*/
const PERIODS = [7, 30, 90] as const;

export default async function ReportsPage({
  searchParams,
}: {
  searchParams: Promise<{ days?: string }>;
}) {
  const asked = Number((await searchParams).days ?? 30);
  const days = (PERIODS as readonly number[]).includes(asked) ? asked : 30;
  const said = await ask<ReportSaid>(`/v1/reports?days=${days}`, {
    read: false,
    unreachable: true,
  });

  if (!said.read) {
    return (
      <>
        <Header eyebrow={`Last ${days} days`} title="Reports" />
        <PwPage>
          {said.unreachable ? (
            <PwCard className="p-6 sm:p-8">
              <h2 className="text-[17px] leading-[22px] font-semibold">
                The report could not be read just now
              </h2>
              <p className="text-pw-ink-600 mt-1.5 max-w-[62ch] text-[15px] leading-[23px]">
                PPCWay could not reach its own service. Nothing is wrong with your Google Ads
                account, and your ads keep running. Reload this page in a minute.
              </p>
            </PwCard>
          ) : said.choose ? (
            <PwCard className="p-6 sm:p-8">
              <h2 className="text-[17px] leading-[22px] font-semibold">
                Choose which account to report on
              </h2>
              <p className="text-pw-ink-600 mt-1.5 max-w-[62ch] text-[15px] leading-[23px]">
                {said.trouble} You can pick it in Settings.
              </p>
            </PwCard>
          ) : (
            <NotConnected what="Your reports are built from what your account actually spent and brought in." />
          )}
        </PwPage>
      </>
    );
  }

  const period = periodWords(said.starts_on ?? "", said.ends_on ?? "");
  return (
    <>
      <Header
        eyebrow={said.business ? `${said.business}, ${period}` : period}
        title="Reports"
        right={<DownloadReport days={days} />}
      />
      <PwPage>
        <PillGroup>
          {PERIODS.map((n) => (
            <PillLink key={n} active={days === n} href={`/reports?days=${n}`}>
              {n} days
            </PillLink>
          ))}
        </PillGroup>
        <Report said={said} share={<ShareReport shares={said.shares ?? []} />} />
      </PwPage>
    </>
  );
}
