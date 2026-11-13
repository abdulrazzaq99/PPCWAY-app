import type { Metadata } from "next";
import { Card } from "@/components/pw/create/kit";
import { Header, PillGroup, PillLink, PwPage, Tile, Tiles } from "@/components/pw/shell";
import { GoogleSide } from "@/components/pw/website/google";
import { Install } from "@/components/pw/website/install";
import { Leads } from "@/components/pw/website/leads";
import type { Choice, Lead, SiteSetup, SiteStats } from "@/components/pw/website/types";
import { ask } from "@/lib/pw-fetch";

export const metadata: Metadata = { title: "Website · PPCway" };

/*
  The merchant's own website, from the PPCWay script on it: how many people
  came, where from, who got in touch, and which of those became jobs. A
  sentence first, then the numbers, then the lists, as everywhere else.

  Until the script is installed, the install card leads the page; after, it
  drops to the bottom and says when it last heard from the site.
*/
const RANGES = [7, 30, 90] as const;

export default async function WebsitePage({
  searchParams,
}: {
  searchParams: Promise<{ days?: string }>;
}) {
  const asked = Number((await searchParams).days);
  const days = (RANGES as readonly number[]).includes(asked) ? asked : 30;
  const [setup, stats, leads] = await Promise.all([
    ask<SiteSetup | null>("/v1/site", null),
    ask<SiteStats | null>(`/v1/site/stats?days=${days}`, null),
    ask<{ leads: Lead[] } | null>("/v1/site/leads", null),
  ]);
  const choices =
    setup?.connected && setup.may_change
      ? await ask<{ actions: Choice[]; reason: string } | null>("/v1/site/choices", null)
      : null;

  if (!setup) {
    return (
      <>
        <Header eyebrow="Your website" title="Website" />
        <PwPage>
          <p className="text-pw-ink-500 text-[15px]">The website could not be read just now.</p>
        </PwPage>
      </>
    );
  }

  const currency = setup.currency || "CAD";
  const money = (n: number) =>
    new Intl.NumberFormat("en-CA", {
      style: "currency",
      currency,
      maximumFractionDigits: 0,
    }).format(n);
  const count = (n: number) => new Intl.NumberFormat("en-CA").format(n);

  return (
    <>
      <Header
        eyebrow="Your website"
        title="Website"
        right={
          <PillGroup>
            {RANGES.map((n) => (
              <PillLink key={n} href={`/website?days=${n}`} active={n === days}>
                {`${n} days`}
              </PillLink>
            ))}
          </PillGroup>
        }
      />

      <PwPage>
        <div className="flex flex-col gap-6">
          {!setup.installed ? <Install setup={setup} open /> : null}

          {stats ? (
            <>
              <p className="text-pw-ink-700 max-w-[70ch] text-[17px] leading-[26px]">
                {sentence(stats, count)}
              </p>
              <Tiles>
                <Tile label="Visits" value={count(stats.visits)} note={`last ${days} days`} />
                <Tile
                  label="Leads"
                  value={count(stats.leads)}
                  note={`${stats.kinds.form} forms · ${stats.kinds.call} calls · ${stats.kinds.email} emails`}
                />
                <Tile
                  label="Got in touch"
                  value={stats.rate != null ? `${stats.rate}%` : "—"}
                  note="of visits"
                />
                <Tile label="Jobs" value={count(stats.jobs)} note="marked by you" />
                <Tile
                  label="Jobs worth"
                  value={stats.jobs_value ? money(stats.jobs_value) : "—"}
                  note="what you entered"
                />
                <Tile
                  label="From Google Ads"
                  value={count(stats.sources.find((s) => s.source === "google_ads")?.visits ?? 0)}
                  note="visits from an ad"
                />
              </Tiles>

              <div className="grid items-start gap-6 xl:grid-cols-[3fr_2fr]">
                <Card
                  title="Visits and leads, day by day"
                  help="The bars are visits; the blue part is how many of them got in touch."
                >
                  <DayBars stats={stats} />
                </Card>
                <Card title="Where visitors come from">
                  <Table
                    head={["", "Visits", "Leads"]}
                    rows={stats.sources.map((s) => [s.label, count(s.visits), count(s.leads)])}
                    empty="No visits yet."
                  />
                </Card>
              </div>
            </>
          ) : null}

          <Leads
            first={leads?.leads ?? []}
            mayChange={setup.may_change}
            sending={setup.send_jobs}
            currency={currency}
          />

          <div className="grid items-start gap-6 xl:grid-cols-2">
            {stats ? (
              <Card title="Pages people arrive on">
                <Table
                  head={["", "Visits", "Leads"]}
                  rows={stats.pages.map((p) => [p.page, count(p.visits), count(p.leads)])}
                  empty="No visits yet."
                />
              </Card>
            ) : null}
            <GoogleSide
              first={setup}
              choices={choices?.actions ?? []}
              reason={choices?.reason ?? ""}
            />
          </div>

          {setup.installed ? <Install setup={setup} open={false} /> : null}

          <Card
            title="For your privacy policy"
            help="Visitors should be told what is recorded. This covers what PPCWay keeps; add it to your privacy policy."
          >
            <p className="text-pw-ink-700 px-6 py-5 text-[14px] leading-[22px]">
              &ldquo;We use PPCWay to understand how visitors find us. It records the pages you
              visit, the website or ad that brought you, and what you send us through our contact
              forms. It does not record passwords or payment details, and it keeps this information
              for 13 months.&rdquo;
            </p>
          </Card>
        </div>
      </PwPage>
    </>
  );
}

function sentence(stats: SiteStats, count: (n: number) => string): string {
  if (!stats.visits && !stats.leads) {
    return `No visits recorded in the last ${stats.days} days yet.`;
  }
  const rate = stats.rate != null ? `, ${stats.rate}% of them` : "";
  const top = stats.sources.find((s) => s.leads > 0);
  const best = top ? ` Most leads came from ${top.label}.` : "";
  return `In the last ${stats.days} days, ${count(stats.visits)} ${
    stats.visits === 1 ? "visit" : "visits"
  } to your website brought ${count(stats.leads)} ${stats.leads === 1 ? "lead" : "leads"}${rate}.${best}`;
}

function DayBars({ stats }: { stats: SiteStats }) {
  const peak = Math.max(1, ...stats.by_day.map((d) => d.visits));
  const label = `Visits and leads each day for the last ${stats.days} days`;
  if (!stats.by_day.some((d) => d.visits || d.leads)) {
    return <p className="text-pw-ink-500 px-6 py-8 text-[14px]">Nothing to draw yet.</p>;
  }
  return (
    <div className="px-6 py-5">
      <div role="img" aria-label={label} className="flex h-[180px] items-end gap-[2px]">
        {stats.by_day.map((d) => (
          <div
            key={d.day}
            title={`${d.day}: ${d.visits} visits, ${d.leads} leads`}
            className="bg-pw-muted relative flex min-w-0 flex-1 flex-col justify-end rounded-t-[3px]"
            style={{ height: `${Math.max(2, (d.visits / peak) * 100)}%` }}
          >
            {d.leads ? (
              <div
                className="bg-pw-blue rounded-t-[3px]"
                style={{
                  height: `${Math.min(100, (d.leads / Math.max(1, d.visits)) * 100)}%`,
                  minHeight: 3,
                }}
              />
            ) : null}
          </div>
        ))}
      </div>
      <div className="text-pw-ink-400 mt-2 flex justify-between text-[12px]">
        <span>{stats.by_day[0]?.day}</span>
        <span>{stats.by_day[stats.by_day.length - 1]?.day}</span>
      </div>
    </div>
  );
}

function Table({
  head,
  rows,
  empty,
}: {
  head: string[];
  rows: (string | number)[][];
  empty: string;
}) {
  if (!rows.length) return <p className="text-pw-ink-500 px-6 py-8 text-[14px]">{empty}</p>;
  return (
    <table className="w-full text-[14px]">
      <thead>
        <tr className="text-pw-ink-500 text-left text-[12px]">
          {head.map((h, i) => (
            <th
              key={i}
              className={i ? "px-6 py-2 text-right font-semibold" : "px-6 py-2 font-semibold"}
            >
              {h}
            </th>
          ))}
        </tr>
      </thead>
      <tbody className="divide-pw-border divide-y">
        {rows.map((row, r) => (
          <tr key={r}>
            {row.map((cell, i) => (
              <td
                key={i}
                className={
                  i
                    ? "pw-num px-6 py-[10px] text-right"
                    : "text-pw-ink max-w-[260px] truncate px-6 py-[10px]"
                }
              >
                {cell}
              </td>
            ))}
          </tr>
        ))}
      </tbody>
    </table>
  );
}
