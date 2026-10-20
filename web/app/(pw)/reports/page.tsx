import type { Metadata } from "next";
import { Report } from "@/components/pw/report";
import { ShareReport } from "@/components/pw/share-report";
import { AskOttoButton, Header, PillGroup, PillLink, PwPage } from "@/components/pw/shell";
import { NotConnected } from "@/components/pw/states";
import { ask } from "@/lib/pw-fetch";
import type { ReportSaid } from "@/lib/reports";

export const metadata: Metadata = { title: "Reports · PPCway" };

/*
  The report, over whichever period is asked for. Everything comes out of our
  own mirror, including the same period a year ago, so a year-on-year column
  costs a database query rather than a round trip to California.
*/
const PERIODS = [7, 30, 90] as const;

export default async function ReportsPage({
  searchParams,
}: {
  searchParams: Promise<{ days?: string }>;
}) {
  const asked = Number((await searchParams).days ?? 30);
  const days = (PERIODS as readonly number[]).includes(asked) ? asked : 30;
  const said = await ask<ReportSaid>(`/v1/reports?days=${days}`, { read: false });

  if (!said.read) {
    return (
      <>
        <Header eyebrow={`Last ${days} days`} title="Reports" right={<AskOttoButton />} />
        <PwPage>
          <NotConnected what="Your reports are built from what your account actually spent and brought in." />
        </PwPage>
      </>
    );
  }

  return (
    <>
      <Header
        eyebrow={`${said.starts_on} to ${said.ends_on} · ${said.business ?? "your account"}`}
        title="Reports"
        right={<AskOttoButton />}
      />
      <PwPage>
        <PillGroup>
          {PERIODS.map((n) => (
            <PillLink key={n} active={days === n} href={`/reports?days=${n}`}>
              {n} days
            </PillLink>
          ))}
        </PillGroup>
        <Report said={said} action={<ShareReport shares={said.shares ?? []} />} />
      </PwPage>
    </>
  );
}
