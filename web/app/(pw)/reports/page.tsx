import type { Metadata } from "next";
import { money } from "@/components/pw/campaigns";
import { Chip, Kpi, PwCard } from "@/components/pw/shell";
import { Header, PwPage } from "@/components/pw/shell";
import { NotConnected } from "@/components/pw/states";
import { ask } from "@/lib/pw-fetch";

export const metadata: Metadata = { title: "Reports · PPCway" };

type Summary = {
  read: boolean;
  trouble?: string;
  currency?: string;
  days?: number;
  leads?: number;
  calls?: number;
  forms?: number;
  cost?: number;
  clicks?: number;
  impressions?: number;
  cost_per_lead?: number;
  series?: { date: string; calls: number; forms: number; leads: number }[];
  campaigns?: {
    campaign_id: string;
    name: string;
    leads: number;
    cost: number;
    cost_per_lead: number;
  }[];
};

export default async function ReportsPage() {
  const s = await ask<Summary>("/v1/ads/summary?days=30", { read: false });
  const c = s.currency ?? "";

  if (!s.read) {
    return (
      <>
        <Header eyebrow="Last 30 days" title="Reports" />
        <PwPage>
          <NotConnected what="Your reports are built from what your account actually spent and brought in." />
        </PwPage>
      </>
    );
  }

  const best = [...(s.campaigns ?? [])]
    .filter((row) => row.cost_per_lead > 0)
    .sort((a, b) => a.cost_per_lead - b.cost_per_lead)[0];

  return (
    <>
      <Header eyebrow="Last 30 days, from your Google Ads account" title="Reports" />
      <PwPage>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
          <Kpi
            label="Leads"
            value={String(Math.round(s.leads ?? 0))}
            foot={`${Math.round(s.calls ?? 0)} calls · ${Math.round(s.forms ?? 0)} forms`}
          />
          <Kpi label="Cost per lead" value={s.cost_per_lead ? money(s.cost_per_lead, c) : "—"} />
          <Kpi label="Spend" value={money(s.cost ?? 0, c)} />
          <Kpi
            label="Clicks"
            value={(s.clicks ?? 0).toLocaleString()}
            foot={`${(s.impressions ?? 0).toLocaleString()} times shown`}
          />
        </div>

        <PwCard className="p-5 sm:p-6">
          <h2 className="text-[17px] leading-[22px] font-semibold">In one sentence</h2>
          <p className="mt-2 max-w-[760px] text-[17px] leading-[27px]">
            {(s.leads ?? 0) > 0 ? (
              <>
                You spent {money(s.cost ?? 0, c)} and it brought {Math.round(s.leads ?? 0)}{" "}
                {Math.round(s.leads ?? 0) === 1 ? "enquiry" : "enquiries"}, which is{" "}
                {money(s.cost_per_lead ?? 0, c)} each.
                {best
                  ? ` ${best.name} brought them cheapest, at ${money(best.cost_per_lead, c)}.`
                  : ""}
              </>
            ) : (
              <>
                You spent {money(s.cost ?? 0, c)} and Google counted no enquiries at all. Either
                nobody called, or the tracking that counts calls and forms is not set up — the
                website audit checks that, and it is the first thing to fix.
              </>
            )}
          </p>
        </PwCard>

        <PwCard className="overflow-hidden">
          <h2 className="px-5 py-5 text-[17px] leading-[22px] font-semibold sm:px-6">
            By campaign
          </h2>
          <table className="w-full text-left">
            <thead>
              <tr className="border-pw-divider text-pw-ink-400 border-y text-[12px]">
                <th className="px-5 py-2 font-semibold sm:px-6">Campaign</th>
                <th className="px-3 py-2 text-right font-semibold">Spend</th>
                <th className="px-3 py-2 text-right font-semibold">Leads</th>
                <th className="px-5 py-2 text-right font-semibold sm:px-6">Cost per lead</th>
              </tr>
            </thead>
            <tbody>
              {(s.campaigns ?? []).map((row) => (
                <tr key={row.campaign_id} className="border-pw-divider border-b last:border-0">
                  <td className="max-w-[260px] truncate px-5 py-3 text-[15px] font-semibold sm:px-6">
                    {row.name}
                  </td>
                  <td className="pw-num px-3 py-3 text-right text-[15px]">{money(row.cost, c)}</td>
                  <td className="pw-num px-3 py-3 text-right text-[15px]">
                    {Math.round(row.leads)}
                  </td>
                  <td className="pw-num px-5 py-3 text-right text-[15px] sm:px-6">
                    {row.cost_per_lead ? money(row.cost_per_lead, c) : "—"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </PwCard>

        <PwCard className="p-5 sm:p-6">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <h2 className="text-[17px] leading-[22px] font-semibold">Sent to you</h2>
            <Chip tone="neutral">Not switched on</Chip>
          </div>
          <p className="text-pw-ink-500 mt-2 max-w-[700px] text-[15px] leading-[23px]">
            The weekly email every Monday and the monthly PDF are not sending yet. Until they are,
            this page is the report, and it is always today&rsquo;s numbers rather than last
            week&rsquo;s.
          </p>
        </PwCard>
      </PwPage>
    </>
  );
}
