import {
  ArrowUpRightIcon,
  CaretRightIcon,
  LockSimpleIcon,
  LockSimpleOpenIcon,
} from "@phosphor-icons/react/dist/ssr";
import Link from "next/link";
import type { ReactNode } from "react";
import {
  LEVEL_WORDS,
  STATE_WORDS,
  adsId,
  ago,
  clock,
  count,
  dateOf,
  dayHeading,
  direction,
  jobWords,
  fateOf,
  signed,
  staleness,
  stamp,
  words,
  type Chrome,
  type Fault,
  type Fate,
  type Figure,
  type Grant,
  type JobRun,
  type Look,
  type Merchant,
  type MerchantRow,
  type MerchantShow,
  type Overview,
  type PlatformView,
  type Quota,
  type Room,
  type Whoami,
} from "@/lib/admin";
import { GrantAccess, StopWrites, SwitchWrites } from "./actions";
import { FateLegend, ProposalColumns, RunStrip, totalsOf } from "./charts";
import { Shell } from "./shell";
import {
  Empty,
  Figures,
  Head,
  Mark,
  Meter,
  More,
  Pager,
  Panel,
  Pill,
  Problem,
  Table,
  Tabs,
  type FigureCell,
  type Tone,
} from "./ui";

/*
  The internal console's screens.

  Each answers one question first, and its biggest block is the answer:

  - Overview: is the platform working, and can we write to Google?
  - Merchants: who needs a person?
  - One merchant: is this account healthy, and what has Otto done to it?
  - Jobs: did the scheduled reads run?
  - Failures: what failed, and is it one cause or many?
  - Quota: is any account close to Google's daily limit?
  - Settings: is the door open, and who closed it?
  - Access: who can open this console, and who let them in?

  Every figure comes from the backend's own rows and is drawn at its real
  size. Times are UTC and say so.
*/

const WINDOWS = [
  { key: "today", label: "Today", words: "the last 24 hours", before: "the day before" },
  { key: "7d", label: "7 days", words: "the last 7 days", before: "the 7 days before" },
  { key: "30d", label: "30 days", words: "the last 30 days", before: "the 30 days before" },
  { key: "90d", label: "90 days", words: "the last 90 days", before: "the 90 days before" },
];

function windowOf(key: string) {
  return WINDOWS.find((one) => one.key === key) ?? WINDOWS[1];
}

/* "−2 on the 7 days before", in good-or-bad colour for this figure. */
function against(key: string, one: Figure | undefined, window: string) {
  if (!one || one.change === null || !one.known) return {};
  const before = windowOf(window).before;
  const tone = direction(key, one.change);
  return {
    note: one.change === 0 ? `Same as ${before}` : `${signed(one.change)} on ${before}`,
    noteTone: tone,
  } as const;
}

function figure(key: string, one: Figure | undefined, label: string, window: string): FigureCell {
  if (!one) return { label, value: "0", unknown: true };
  return {
    label,
    value: count(one.value),
    unknown: !one.known,
    ...against(key, one, window),
  };
}

const FATE_TONE: Record<Fate, Tone> = {
  applied: "good",
  open: "info",
  refused: "plain",
  expired: "plain",
  undone: "bad",
};

function source(where: string): { what: string; detail: string } {
  const [head, ...rest] = where.split(" ");
  return {
    what: words(head || "Unknown"),
    detail: rest.join(" ").replace(/[()]/g, ""),
  };
}

/* ---------- overview ---------- */

export function AdminOverview({
  who,
  chrome,
  view,
  platform,
  faults,
  trouble,
  window,
}: {
  who: Whoami;
  chrome: Chrome;
  view: Overview | null;
  platform: PlatformView | null;
  faults: Fault[] | null;
  trouble: string;
  window: string;
}) {
  const span = windowOf(view?.window ?? window);
  const f = view?.figures ?? {};
  const flag = (name: string) => platform?.flags.find((one) => one.name === name);
  const writing = flag("Writing to Google Ads");
  const asking = flag("Applying without asking");
  const connected = f.connected?.value ?? 0;
  const businesses = f.merchants?.value ?? 0;
  const latest = (faults ?? []).slice(0, 6);
  const door = chrome.door;
  const DoorGlyph = door?.state === "on" ? LockSimpleOpenIcon : LockSimpleIcon;

  return (
    <Shell who={who} here="/admin/metrics" door={chrome.door} failures={chrome.failures}>
      <Head
        title="Overview"
        pill={
          view ? (
            view.healthy ? (
              <Pill tone="good">All clear</Pill>
            ) : (
              <Pill tone="warn">
                {view.trouble.length} need{view.trouble.length === 1 ? "s" : ""} a person
              </Pill>
            )
          ) : null
        }
        lead={
          view
            ? `Counted over ${span.words}. Updated ${clock(view.at)} UTC.`
            : "The platform's figures could not be read."
        }
      />
      <div className="mt-5">
        <Tabs
          label="Window"
          tabs={WINDOWS.map((one) => ({
            label: one.label,
            href: `/admin/metrics?window=${one.key}`,
            here: one.key === span.key,
          }))}
        />
      </div>

      <div className="mt-6 grid gap-6">
        <Problem words={trouble} />

        {view ? (
          <>
            {/*
              The screen's question first: does anything need a person? Full
              width, so its length is the number of problems and never a
              neighbour's height.
            */}
            {view.healthy ? (
              <section className="border-ad-border bg-ad-surface flex flex-wrap items-center gap-x-6 gap-y-2 rounded-[6px] border px-5 py-4">
                <h2 className="text-[15px] leading-[22px] font-semibold">Nothing needs a person</h2>
                <p className="text-ad-muted text-[13px] leading-[20px]">
                  In {span.words} no sync got stuck or failed, no model call failed, and fewer than
                  50 proposals are waiting on a merchant.
                </p>
              </section>
            ) : (
              <Panel title="Needs a person" meta="Worst first" flush>
                <ul>
                  {view.trouble.map((one) => {
                    const where = /sync/i.test(one)
                      ? { href: "/admin/jobs", label: "Open jobs" }
                      : /model/i.test(one)
                        ? { href: `/admin/errors?window=${span.key}`, label: "Open failures" }
                        : /connected/i.test(one)
                          ? { href: "/admin?show=unconnected", label: "Open merchants" }
                          : { href: "/admin", label: "Open merchants" };
                    return (
                      <li
                        key={one}
                        className="border-ad-rule flex flex-wrap items-center justify-between gap-x-6 gap-y-1 border-t px-5 py-3"
                      >
                        <p className="flex min-w-0 items-start gap-3 text-[13px] leading-[20px]">
                          <span
                            aria-hidden
                            className="bg-ad-negative mt-[7px] h-1.5 w-1.5 flex-none rounded-full"
                          />
                          <span>{one}</span>
                        </p>
                        <Link
                          href={where.href}
                          className="text-ad-accent hover:text-ad-text inline-flex flex-none items-center gap-1 pl-[18px] text-[13px] font-medium transition-colors sm:pl-0"
                        >
                          {where.label}
                          <ArrowUpRightIcon size={13} aria-hidden />
                        </Link>
                      </li>
                    );
                  })}
                </ul>
              </Panel>
            )}

            <Figures
              cells={[
                {
                  ...figure("waiting", f.waiting, "Waiting on a merchant", span.key),
                  note: "proposed, not answered yet",
                  noteTone: "plain",
                  lead: true,
                  href: "/admin",
                },
                {
                  ...figure("syncs_failed", f.syncs_failed, "Syncs that failed", span.key),
                  alarm: Boolean(f.syncs_failed?.value),
                  href: "/admin/jobs?failed=1",
                },
                {
                  ...figure("model_trouble", f.model_trouble, "Model calls that failed", span.key),
                  alarm: Boolean(f.model_trouble?.value),
                  href: `/admin/errors?window=${span.key}`,
                },
                (() => {
                  /*
                    Tokens ride in the note rather than beside the figure,
                    where "412 1,284,906" read as one number.
                  */
                  const calls = figure("model_calls", f.model_calls, "Model calls", span.key);
                  const tokens = f.model_tokens?.known
                    ? `${count(f.model_tokens.value)} tokens`
                    : "";
                  return {
                    ...calls,
                    note: [calls.note, tokens].filter(Boolean).join(", ") || undefined,
                  };
                })(),
              ]}
            />

            {/*
              Otto's output beside the door it has to go through. Both have a
              fixed amount to say, so the pair balances whatever the data is,
              and the chart's plot takes whatever height the row has.
            */}
            <div className="grid gap-6 xl:grid-cols-[minmax(0,2fr)_minmax(0,1fr)]">
              {view.series ? (
                <Panel
                  title="What became of Otto’s proposals"
                  meta={`Proposed per ${view.series.step === "hour" ? "hour" : "day"} over ${span.words}, by where each one stands now. UTC.`}
                  grow
                >
                  <div className="mb-5">
                    <FateLegend totals={totalsOf(view.series)} />
                  </div>
                  <ProposalColumns series={view.series} fill />
                </Panel>
              ) : null}

              <section
                className={`border-ad-border bg-ad-surface rounded-[6px] border p-5 ${
                  view.series ? "" : "xl:col-span-3"
                }`}
              >
                <div className="flex items-start gap-3">
                  <DoorGlyph
                    size={20}
                    aria-hidden
                    className={`mt-px flex-none ${
                      door?.state === "on"
                        ? "text-ad-positive"
                        : door?.state === "stopped"
                          ? "text-ad-negative"
                          : "text-ad-warning"
                    }`}
                  />
                  <h2 className="text-[15px] leading-[22px] font-semibold">
                    {view.writes.anything_can_be_written
                      ? "PPCWay can write to Google Ads"
                      : door?.state === "stopped"
                        ? "Writes to Google Ads are stopped"
                        : "Writes to Google Ads are off"}
                  </h2>
                </div>
                <p className="text-ad-muted mt-2 text-[13px] leading-[20px]">{view.writes.words}</p>
                <dl className="mt-5 grid">
                  {[
                    {
                      label: "Writing to Google Ads",
                      value: writing ? (
                        <Pill tone={writing.on ? "good" : "warn"}>{writing.on ? "On" : "Off"}</Pill>
                      ) : (
                        <span className="text-ad-faint">Unknown</span>
                      ),
                    },
                    {
                      label: "Applying without asking",
                      value: asking ? (
                        <Pill tone={asking.on ? "info" : "plain"}>{asking.on ? "On" : "Off"}</Pill>
                      ) : (
                        <span className="text-ad-faint">Unknown</span>
                      ),
                    },
                    {
                      label: "Stops in force",
                      value: <span className="ad-num">{count(view.writes.stops.length)}</span>,
                    },
                    {
                      label: "Connected to Google Ads",
                      value: (
                        <span className="ad-num">
                          {count(connected)}
                          <span className="text-ad-faint"> of {count(businesses)}</span>
                        </span>
                      ),
                    },
                  ].map((one) => (
                    <div
                      key={one.label}
                      className="border-ad-rule flex min-h-11 items-center justify-between gap-4 border-t"
                    >
                      <dt className="text-ad-muted text-[13px]">{one.label}</dt>
                      <dd>{one.value}</dd>
                    </div>
                  ))}
                </dl>
                <Link
                  href="/admin/platform"
                  className="text-ad-accent hover:text-ad-text mt-3 inline-flex items-center gap-1 text-[13px] font-medium transition-colors"
                >
                  Open settings
                  <ArrowUpRightIcon size={13} aria-hidden />
                </Link>
              </section>
            </div>

            <Panel
              title="Latest failures"
              meta={faults ? `${count(faults.length)} in ${span.words}` : undefined}
              action={
                faults && faults.length > latest.length ? (
                  <More href={`/admin/errors?window=${span.key}`}>
                    View all {count(faults.length)}
                  </More>
                ) : null
              }
              flush
            >
              {faults === null ? (
                <div className="px-5 pb-5">
                  <Problem words="The failures could not be read." />
                </div>
              ) : latest.length ? (
                <Table
                  caption="The latest failures"
                  title="what"
                  lead="when"
                  cols={[
                    { key: "what", label: "What happened", width: "54%" },
                    { key: "where", label: "Where" },
                    { key: "account", label: "Account", num: true },
                    { key: "when", label: "When", num: true },
                  ]}
                  lines={latest.map((one, at) => {
                    const from = source(one.where);
                    return {
                      id: `${one.at}-${at}`,
                      cells: {
                        what: <span className="line-clamp-2">{one.what}</span>,
                        where: (
                          <span>
                            {from.what}
                            {from.detail ? (
                              <span className="text-ad-faint"> {from.detail}</span>
                            ) : null}
                          </span>
                        ),
                        account: one.customer_id ? (
                          adsId(one.customer_id)
                        ) : (
                          <span className="text-ad-faint">-</span>
                        ),
                        when: <span className="text-ad-muted">{stamp(one.at)}</span>,
                      },
                    };
                  })}
                />
              ) : (
                <div className="px-5 pb-5">
                  <Empty
                    title={`Nothing failed in ${span.words}`}
                    words="No sync and no model call came back with an error."
                  />
                </div>
              )}
            </Panel>
          </>
        ) : null}
      </div>
    </Shell>
  );
}

/* ---------- merchants ---------- */

function adsState(one: { connected: boolean; account_status: string }): {
  tone: Tone;
  words: string;
} {
  /*
    A connected account whose status has not been read yet is connected, not
    broken. An earlier version printed a healthy "Connected" in red because it
    treated anything other than the literal ENABLED as bad.
  */
  if (!one.connected) return { tone: "plain", words: "Not connected" };
  if (!one.account_status || one.account_status === "ENABLED")
    return { tone: "good", words: "Connected" };
  return { tone: "bad", words: words(one.account_status.toLowerCase()) };
}

function Synced({ when, connected }: { when: string | null; connected: boolean }) {
  if (!connected) return <span className="text-ad-faint">-</span>;
  const how = staleness(when);
  return (
    <span
      className={
        how === "stale" ? "text-ad-warning" : how === "never" ? "text-ad-faint" : "text-ad-muted"
      }
    >
      {ago(when)}
    </span>
  );
}

export function AdminMerchants({
  who,
  chrome,
  rows,
  total,
  counts,
  page,
  per,
  trouble,
  lookedFor,
  show,
}: {
  who: Whoami;
  chrome: Chrome;
  /* This page of the open tab. */
  rows: MerchantRow[];
  /* How many the open tab holds. */
  total: number;
  /* Every tab's count, under the same search. */
  counts: Record<MerchantShow, number>;
  page: number;
  per: number;
  trouble: string;
  lookedFor: string;
  show: "" | "attention" | "unconnected";
}) {
  const pages = Math.max(1, Math.ceil(total / per));
  const link = (tab: string, n = 1) => {
    const q = new URLSearchParams();
    if (tab) q.set("show", tab);
    if (lookedFor) q.set("q", lookedFor);
    if (n > 1) q.set("page", String(n));
    const tail = q.toString();
    return tail ? `/admin?${tail}` : "/admin";
  };
  const tabName =
    show === "attention"
      ? "Need a person"
      : show === "unconnected"
        ? "Not connected"
        : "Every business";

  return (
    <Shell
      who={who}
      here="/admin"
      door={chrome.door}
      failures={chrome.failures}
      lookedFor={lookedFor}
    >
      <Head
        title="Merchants"
        pill={
          counts.all ? (
            counts.attention ? (
              <Pill tone="warn">{count(counts.attention)} need a person</Pill>
            ) : (
              <Pill tone="good">All healthy</Pill>
            )
          ) : null
        }
        lead={
          lookedFor ? (
            <>
              Businesses with a name like &ldquo;{lookedFor}&rdquo;.{" "}
              <Link href="/admin" className="text-ad-accent hover:text-ad-text font-medium">
                Show every business
              </Link>
            </>
          ) : (
            "Every business on PPCWay, newest first. Opening one is recorded against your name."
          )
        }
      />
      <div className="mt-5">
        <Tabs
          label="Which businesses"
          tabs={[
            { label: "All", href: link(""), count: counts.all, here: !show },
            {
              label: "Need a person",
              href: link("attention"),
              count: counts.attention,
              here: show === "attention",
            },
            {
              label: "Not connected",
              href: link("unconnected"),
              count: counts.unconnected,
              here: show === "unconnected",
            },
          ]}
        />
      </div>

      <div className="mt-6 grid gap-6">
        <Problem words={trouble} />
        {rows.length ? (
          <Panel
            title={tabName}
            meta={`${count(total)} ${total === 1 ? "business" : "businesses"}${
              pages > 1 ? `, page ${count(page)} of ${count(pages)}` : ""
            }.`}
            flush
            className="overflow-clip"
          >
            <Table
              caption="Businesses"
              title="name"
              lead="ads"
              stickyHead
              cols={[
                { key: "name", label: "Business", width: "34%" },
                { key: "ads", label: "Google Ads" },
                { key: "waiting", label: "Waiting", num: true },
                { key: "applied", label: "Applied", num: true },
                { key: "people", label: "People", num: true, minor: true },
                { key: "sync", label: "Last sync", num: true },
                { key: "go", label: "", minor: true },
              ]}
              lines={rows.map((one) => {
                const state = adsState(one);
                const href = `/admin?view=merchant&id=${one.organization_id}`;
                return {
                  id: one.organization_id,
                  cells: {
                    name: (
                      <div className="flex min-w-0 items-center gap-3">
                        <Mark seed={one.organization_id} name={one.name} />
                        <div className="min-w-0">
                          <Link
                            href={href}
                            className="hover:text-ad-accent block truncate font-medium transition-colors"
                          >
                            {one.name}
                          </Link>
                          {one.trouble ? (
                            <p
                              className={`truncate text-[13px] leading-[18px] ${
                                state.tone === "bad" ? "text-ad-negative" : "text-ad-warning"
                              }`}
                            >
                              {one.trouble}
                            </p>
                          ) : null}
                        </div>
                      </div>
                    ),
                    ads: (
                      <div className="flex flex-col items-start gap-1">
                        <Pill tone={state.tone}>{state.words}</Pill>
                        {one.customer_id ? (
                          <span className="ad-num text-ad-faint text-[13px] leading-[18px] max-md:hidden">
                            {adsId(one.customer_id)}
                          </span>
                        ) : null}
                      </div>
                    ),
                    waiting: (
                      <span className={one.waiting ? "text-ad-text" : "text-ad-faint"}>
                        {count(one.waiting)}
                      </span>
                    ),
                    applied: count(one.applied),
                    people: count(one.people),
                    sync: <Synced when={one.last_sync} connected={one.connected} />,
                    go: (
                      <Link
                        href={href}
                        aria-label={`Open ${one.name}`}
                        className="text-ad-faint hover:text-ad-text flex justify-end transition-colors"
                      >
                        <CaretRightIcon size={14} aria-hidden />
                      </Link>
                    ),
                  },
                };
              })}
            />
            <div className="border-ad-rule border-t px-5 py-4">
              <Pager
                page={page}
                per={per}
                total={total}
                noun={total === 1 ? "business" : "businesses"}
                href={(n) => link(show, n)}
              />
            </div>
          </Panel>
        ) : total > 0 ? (
          /* A page past the end, from an edited or an old link. */
          <Empty
            title={`There is no page ${count(page)}`}
            words={`${count(total)} ${total === 1 ? "business fills" : "businesses fill"} ${count(pages)} page${pages === 1 ? "" : "s"}.`}
            action={
              <Link
                href={link(show, pages)}
                className="text-ad-accent hover:text-ad-text text-[13px] font-medium transition-colors"
              >
                Go to the last page
              </Link>
            }
          />
        ) : (
          <Empty
            title={
              lookedFor
                ? "Nothing matched"
                : show === "attention"
                  ? "Nobody needs a person"
                  : show === "unconnected"
                    ? "Every business is connected"
                    : "No businesses yet"
            }
            words={
              lookedFor
                ? `No business has a name like "${lookedFor}". Try part of the name rather than all of it.`
                : show
                  ? undefined
                  : "When somebody signs up and connects their Google Ads account, they appear here."
            }
          />
        )}
      </div>
    </Shell>
  );
}

/* ---------- one merchant ---------- */

export function AdminMerchant({
  who,
  chrome,
  merchant,
  row,
  looks,
  quota,
  stopped,
  all,
  trouble,
}: {
  who: Whoami;
  chrome: Chrome;
  merchant: Merchant | null;
  /* The list's row for this business: people, last sync. Absent if unread. */
  row?: MerchantRow;
  looks: Look[];
  quota: Quota | null;
  /* Whether writes are stopped for this account alone. */
  stopped: boolean;
  all: boolean;
  trouble: string;
}) {
  if (!merchant) {
    return (
      <Shell
        who={who}
        here="/admin"
        door={chrome.door}
        failures={chrome.failures}
        crumbs={[{ label: "Merchants", href: "/admin" }]}
      >
        <Head title="This business could not be opened" />
        <div className="mt-6">
          <Problem words={trouble || "We have no record of that business."} />
        </div>
      </Shell>
    );
  }

  const ads = merchant.connection;
  const state = adsState({
    connected: Boolean(ads?.customer_id),
    account_status: ads?.account_status ?? "",
  });
  const fates = merchant.changes.reduce<Record<Fate, number>>(
    (n, one) => {
      n[fateOf(one.status)] += 1;
      return n;
    },
    { applied: 0, open: 0, refused: 0, expired: 0, undone: 0 },
  );
  const capped = merchant.changes.length >= 100;
  const changes = all ? merchant.changes : merchant.changes.slice(0, 10);
  const mayStop = who.may.includes("stop_writes") && Boolean(ads?.customer_id);

  return (
    <Shell
      who={who}
      here="/admin"
      door={chrome.door}
      failures={chrome.failures}
      crumbs={[{ label: "Merchants", href: "/admin" }, { label: merchant.name }]}
      lookingAt={merchant.name}
    >
      <div className="flex flex-wrap items-start gap-4">
        <Mark seed={merchant.organization_id} name={merchant.name} size={44} />
        <div className="min-w-0 flex-1">
          <Head
            title={merchant.name}
            pill={<Pill tone={state.tone}>{state.words}</Pill>}
            lead={
              ads?.customer_id
                ? `On PPCWay since ${dateOf(merchant.created_at)}. Opening this screen is recorded against your name.`
                : `On PPCWay since ${dateOf(merchant.created_at)}. No Google Ads account is connected, so Otto can read and propose nothing.`
            }
            side={
              mayStop ? (
                <StopWrites
                  stopped={stopped}
                  customerId={ads!.customer_id}
                  label="Stop writes to this account"
                />
              ) : undefined
            }
          />
        </div>
      </div>

      <div className="mt-6 grid gap-6">
        <Problem words={trouble} />
        <Figures
          cells={[
            {
              label: capped ? "Proposed, latest 100" : "Changes proposed",
              value: count(merchant.changes.length),
            },
            {
              label: "Still open",
              value: count(fates.open),
              note: "with a guardrail or the merchant",
              lead: true,
            },
            { label: "Applied", value: count(fates.applied) },
            {
              label: "Put back or failed",
              value: count(fates.undone),
              alarm: fates.undone > 0,
            },
          ]}
        />

        <div className="grid items-start gap-6 xl:grid-cols-[minmax(0,2fr)_minmax(0,1fr)]">
          <Panel
            title="Changes Otto proposed"
            meta="Newest first. Times in UTC."
            action={
              merchant.changes.length > 10 ? (
                <More
                  href={`/admin?view=merchant&id=${merchant.organization_id}${all ? "" : "&all=1"}`}
                >
                  {all ? "Show the latest 10" : `Show all ${count(merchant.changes.length)}`}
                </More>
              ) : null
            }
            flush
          >
            {changes.length ? (
              <Table
                caption="Changes Otto proposed for this business"
                title="change"
                lead="state"
                cols={[
                  { key: "change", label: "Change", width: "52%" },
                  { key: "risk", label: "Risk" },
                  { key: "state", label: "Where it stands" },
                  { key: "when", label: "Proposed", num: true },
                ]}
                lines={changes.map((one) => ({
                  id: one.id,
                  cells: {
                    change: (
                      <div className="min-w-0">
                        <p className="font-medium">{words(one.kind)}</p>
                        {one.reason ? (
                          <p className="text-ad-muted line-clamp-1 text-[13px] leading-[18px]">
                            {one.reason}
                          </p>
                        ) : null}
                      </div>
                    ),
                    risk: one.risk ? words(one.risk) : <span className="text-ad-faint">-</span>,
                    state: (
                      <Pill tone={FATE_TONE[fateOf(one.status)]}>
                        {STATE_WORDS[one.status] ?? words(one.status)}
                      </Pill>
                    ),
                    when: <span className="text-ad-muted">{stamp(one.created_at)}</span>,
                  },
                }))}
              />
            ) : (
              <div className="px-5 pb-5">
                <Empty
                  title="Otto has proposed nothing here yet"
                  words={
                    ads
                      ? "Proposals appear after the nightly pass has read this account."
                      : "Nothing can be proposed until a Google Ads account is connected."
                  }
                />
              </div>
            )}
          </Panel>

          <div className="grid gap-6">
            <Panel title="Google Ads account">
              {ads?.customer_id ? (
                <dl className="-mt-1 grid">
                  {[
                    { label: "Name at Google", value: ads.customer_name || merchant.name },
                    {
                      label: "Customer id",
                      value: <span className="ad-num">{adsId(ads.customer_id)}</span>,
                    },
                    {
                      label: "Billed in",
                      value: <span className="ad-num">{ads.currency || "-"}</span>,
                    },
                    { label: "Status", value: <Pill tone={state.tone}>{state.words}</Pill> },
                  ].map((one) => (
                    <div
                      key={one.label}
                      className="border-ad-rule flex min-h-11 items-center justify-between gap-4 border-t first:border-t-0"
                    >
                      <dt className="text-ad-muted text-[13px]">{one.label}</dt>
                      <dd className="min-w-0 truncate text-right">{one.value}</dd>
                    </div>
                  ))}
                </dl>
              ) : (
                <p className="text-ad-muted text-[13px] leading-[20px]">
                  Not connected yet. Only the merchant can connect it, from their own dashboard.
                </p>
              )}
            </Panel>

            <Panel title="Google’s allowance today" meta={quota ? undefined : "Not read"}>
              {quota ? (
                <div>
                  <div className="flex items-baseline justify-between gap-3">
                    <span className="ad-num text-[20px] leading-[28px]">
                      {Math.round(quota.share_used * 100)}%
                    </span>
                    <span className="ad-num text-ad-faint text-[12px]">
                      {count(quota.used)} of {count(quota.allowance)}
                    </span>
                  </div>
                  <div className="mt-2.5">
                    <Meter share={quota.share_used} tone={quota.tight ? "warn" : "plain"} />
                  </div>
                  <p className="text-ad-muted mt-3 text-[13px] leading-[20px]">
                    <span className="ad-num">{count(quota.left)}</span> operations left today.
                    {quota.tight ? " Close to the limit: syncs may start to fail." : ""}
                  </p>
                </div>
              ) : (
                <p className="text-ad-muted text-[13px]">
                  {ads
                    ? "The allowance could not be read."
                    : "Counted only for a connected account."}
                </p>
              )}
            </Panel>

            <Panel
              title="Who opened this account"
              meta={looks.length ? `${count(looks.length)} times, newest first` : undefined}
            >
              {looks.length ? (
                <ul className="grid gap-3">
                  {looks.slice(0, 6).map((one, at) => (
                    <li key={`${one.at}-${at}`} className="flex items-center gap-3">
                      <Mark seed={one.who || one.account_id} name={one.who || "?"} size={24} />
                      <div className="min-w-0 flex-1">
                        <p className="truncate text-[13px] leading-[18px]">
                          {one.who || `Account ${one.account_id.slice(0, 8)}`}
                        </p>
                        <p className="text-ad-faint text-[12px] leading-[16px]">
                          {LEVEL_WORDS[one.level] ?? one.level}
                        </p>
                      </div>
                      <span className="ad-num text-ad-faint text-[12px]">{ago(one.at)}</span>
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="text-ad-muted text-[13px]">Nobody, until now.</p>
              )}
              {row ? (
                <p className="border-ad-rule text-ad-faint mt-4 border-t pt-3 text-[12px] leading-[18px]">
                  {count(row.people)} {row.people === 1 ? "person works" : "people work"} in this
                  account. Last synced {ago(row.last_sync).toLowerCase()}.
                </p>
              ) : null}
            </Panel>
          </div>
        </div>
      </div>
    </Shell>
  );
}

/* ---------- jobs ---------- */

function runState(one: JobRun): { tone: Tone; words: string } {
  if (one.stuck) return { tone: "bad", words: "Never finished" };
  if (one.status === "failed") return { tone: "bad", words: "Failed" };
  if (one.took_seconds === null) return { tone: "info", words: "Running" };
  return { tone: "plain", words: "Finished" };
}

export function AdminJobs({
  who,
  chrome,
  runs,
  strip,
  total,
  totals,
  page,
  per,
  trouble,
  failedOnly,
}: {
  who: Whoami;
  chrome: Chrome;
  /* This page of the table. */
  runs: JobRun[];
  /* The latest hundred runs, whichever page is open: the heartbeat. */
  strip: JobRun[] | null;
  /* Every run the current tab matches. */
  total: number;
  /* Both tabs' totals, where they could be read. */
  totals: { all?: number; failed?: number };
  page: number;
  per: number;
  trouble: string;
  failedOnly: boolean;
}) {
  /*
    The pill reads the heartbeat, not the page: "2 never finished" is about the
    platform now, and page 7 of last week's runs has nothing to say about that.
  */
  const recent = strip ?? (page === 1 ? runs : []);
  const stuck = recent.filter((one) => one.stuck);
  const failed = recent.filter((one) => one.status === "failed");
  const pages = Math.max(1, Math.ceil(total / per));
  const href = (n: number) => {
    const q = new URLSearchParams();
    if (failedOnly) q.set("failed", "1");
    if (n > 1) q.set("page", String(n));
    const tail = q.toString();
    return tail ? `/admin/jobs?${tail}` : "/admin/jobs";
  };

  return (
    <Shell who={who} here="/admin/jobs" door={chrome.door} failures={chrome.failures}>
      <Head
        title="Jobs"
        pill={
          recent.length ? (
            stuck.length ? (
              <Pill tone="bad">{count(stuck.length)} never finished</Pill>
            ) : failed.length ? (
              <Pill tone="warn">{count(failed.length)} of the latest failed</Pill>
            ) : (
              <Pill tone="good">All finished</Pill>
            )
          ) : null
        }
        lead={
          failedOnly
            ? "Every scheduled read of Google Ads that failed, newest first. Times in UTC."
            : "The scheduled reads of Google Ads, newest first. Times in UTC."
        }
      />
      <div className="mt-5">
        <Tabs
          label="Which runs"
          tabs={[
            { label: "Every run", href: "/admin/jobs", count: totals.all, here: !failedOnly },
            {
              label: "Failed only",
              href: "/admin/jobs?failed=1",
              count: totals.failed,
              here: failedOnly,
            },
          ]}
        />
      </div>

      <div className="mt-6 grid gap-6">
        <Problem words={trouble} />
        {!failedOnly && strip?.length ? (
          <Panel
            title="Run by run"
            meta={`The latest ${count(strip.length)}, one mark each. A gap or a red run reads at a glance.`}
          >
            <RunStrip runs={strip} />
          </Panel>
        ) : null}

        {runs.length ? (
          <Panel
            title={failedOnly ? "Failed runs" : "Every run"}
            meta={`${count(total)} in all, newest first. Page ${count(page)} of ${count(pages)}.`}
            flush
            className="overflow-clip"
          >
            <Table
              caption={failedOnly ? "Failed job runs" : "Job runs"}
              title="job"
              lead="state"
              stickyHead
              cols={[
                { key: "job", label: "Job", width: "26%" },
                { key: "state", label: "What happened" },
                { key: "took", label: "Took", num: true },
                { key: "when", label: "Started", num: true },
              ]}
              lines={runs.map((one) => {
                const state = runState(one);
                return {
                  id: one.id,
                  cells: {
                    job: (
                      <div className="min-w-0">
                        <p className="font-medium">{jobWords(one.kind)}</p>
                        <p className="ad-num text-ad-faint text-[13px] leading-[18px]">
                          {one.customer_id ? adsId(one.customer_id) : "Every account"}
                        </p>
                      </div>
                    ),
                    /*
                      The state, and under it what happened when there is
                      something to say. A clean run's sentence only repeated
                      the Took column, and on a quiet day it left a column of
                      dashes across the whole table.
                    */
                    state: (
                      <div className="flex min-w-0 flex-col items-start gap-1">
                        <Pill tone={state.tone}>{state.words}</Pill>
                        {state.words !== "Finished" ? (
                          <p
                            className={`text-[13px] leading-[18px] ${
                              state.tone === "bad" ? "text-ad-text" : "text-ad-muted"
                            }`}
                          >
                            {one.words}
                          </p>
                        ) : null}
                      </div>
                    ),
                    took:
                      one.took_seconds === null ? (
                        <span className="text-ad-faint">-</span>
                      ) : (
                        `${count(one.took_seconds)} s`
                      ),
                    when: (
                      <div>
                        <p>{stamp(one.started_at)}</p>
                        <p className="text-ad-faint text-[13px] leading-[18px]">
                          {ago(one.started_at)}
                        </p>
                      </div>
                    ),
                  },
                };
              })}
            />
            <div className="border-ad-rule border-t px-5 py-4">
              <Pager page={page} per={per} total={total} noun="runs" href={href} />
            </div>
          </Panel>
        ) : total > 0 ? (
          /* A page past the end, from an edited or an old link. */
          <Empty
            title={`There is no page ${count(page)}`}
            words={`${count(total)} runs fill ${count(pages)} page${pages === 1 ? "" : "s"}.`}
            action={
              <Link
                href={href(pages)}
                className="text-ad-accent hover:text-ad-text text-[13px] font-medium transition-colors"
              >
                Go to the last page
              </Link>
            }
          />
        ) : (
          <Empty
            title={failedOnly ? "No run has failed" : "Nothing has run yet"}
            words={
              failedOnly
                ? "Every recorded run finished or is still running."
                : "A fresh deployment has run no jobs. The syncs start on their own schedule."
            }
          />
        )}
      </div>
    </Shell>
  );
}

/* ---------- failures ---------- */

export function AdminErrors({
  who,
  chrome,
  faults,
  trouble,
  window,
  ran,
}: {
  who: Whoami;
  chrome: Chrome;
  faults: Fault[];
  trouble: string;
  window: string;
  /*
    What ran in the same window, from the overview's counts. "Nothing failed"
    only reassures when something ran; without it the empty screen cannot
    tell a quiet platform from a stopped one.
  */
  ran?: { modelCalls?: Figure; syncsStuck?: Figure };
}) {
  const span = windowOf(window);
  /*
    Grouped by day, because "is this one incident or a slow leak" is the first
    question and a day heading answers it before a single row is read.
  */
  const days = faults.reduce<{ day: string; items: Fault[] }[]>((all, one) => {
    const day = dayHeading(one.at);
    const last = all[all.length - 1];
    if (last && last.day === day) last.items.push(one);
    else all.push({ day, items: [one] });
    return all;
  }, []);
  const bySource = Object.entries(
    faults.reduce<Record<string, number>>((all, one) => {
      const from = source(one.where);
      const key = from.detail ? `${from.what}, ${from.detail}` : from.what;
      all[key] = (all[key] ?? 0) + 1;
      return all;
    }, {}),
  ).sort((a, b) => b[1] - a[1]);
  const byAccount = Object.entries(
    faults.reduce<Record<string, number>>((all, one) => {
      if (one.customer_id) all[one.customer_id] = (all[one.customer_id] ?? 0) + 1;
      return all;
    }, {}),
  )
    .sort((a, b) => b[1] - a[1])
    .slice(0, 4);
  const top = bySource[0]?.[1] ?? 1;

  return (
    <Shell who={who} here="/admin/errors" door={chrome.door} failures={chrome.failures}>
      <Head
        title="Failures"
        pill={
          faults.length ? (
            <Pill tone="bad">
              {count(faults.length)} in {span.words}
            </Pill>
          ) : (
            <Pill tone="good">Nothing failed</Pill>
          )
        }
        lead="Jobs and model calls together, newest first. They fail for unrelated reasons, but you only want one list. Times in UTC."
      />
      <div className="mt-5">
        <Tabs
          label="Window"
          tabs={WINDOWS.map((one) => ({
            label: one.label,
            href: `/admin/errors?window=${one.key}`,
            here: one.key === span.key,
          }))}
        />
      </div>

      <div className="mt-6 grid gap-6">
        <Problem words={trouble} />
        {faults.length ? (
          <div className="grid items-start gap-6 xl:grid-cols-[minmax(0,2fr)_minmax(0,1fr)]">
            <div className="grid gap-6">
              {days.map((group) => (
                <Panel
                  key={group.day}
                  title={group.day}
                  meta={`${count(group.items.length)} failure${group.items.length === 1 ? "" : "s"}`}
                  flush
                >
                  <ul>
                    {group.items.map((one, at) => {
                      const from = source(one.where);
                      return (
                        <li
                          key={`${one.at}-${at}`}
                          className="border-ad-rule grid grid-cols-[52px_minmax(0,1fr)] gap-x-4 border-t px-5 py-3"
                        >
                          <span className="ad-num text-ad-faint pt-px text-[12px] leading-[20px]">
                            {clock(one.at)}
                          </span>
                          <div className="min-w-0">
                            <p className="text-[13px] leading-[20px]">{one.what}</p>
                            <p className="text-ad-faint mt-1 flex flex-wrap gap-x-3 text-[12px] leading-[18px]">
                              <span className="text-ad-muted">{from.what}</span>
                              {from.detail ? <span>{from.detail}</span> : null}
                              {one.customer_id ? (
                                <span className="ad-num">{adsId(one.customer_id)}</span>
                              ) : null}
                            </p>
                          </div>
                        </li>
                      );
                    })}
                  </ul>
                </Panel>
              ))}
            </div>

            <div className="grid gap-6">
              <Panel title="Where it failed" meta={`Over ${span.words}`}>
                <ul className="grid gap-3.5">
                  {bySource.map(([what, n]) => (
                    <li key={what}>
                      <div className="flex items-baseline justify-between gap-3 text-[13px]">
                        <span className={n === top ? "text-ad-text" : "text-ad-muted"}>{what}</span>
                        <span className="ad-num">{count(n)}</span>
                      </div>
                      {/*
                        A bar at its true share of the largest. The largest in
                        ink, ties included, so equal counts look equal.
                      */}
                      <span
                        aria-hidden
                        className={`mt-2 block h-1 rounded-full ${n === top ? "bg-ad-text" : "bg-ad-control"}`}
                        style={{ width: `${(n / top) * 100}%` }}
                      />
                    </li>
                  ))}
                </ul>
              </Panel>
              {byAccount.length ? (
                <Panel title="Accounts most affected">
                  <ul className="grid gap-2.5">
                    {byAccount.map(([id, n]) => (
                      <li key={id} className="flex items-baseline justify-between gap-3">
                        <span className="ad-num text-ad-muted">{adsId(id)}</span>
                        <span className="ad-num">{count(n)}</span>
                      </li>
                    ))}
                  </ul>
                </Panel>
              ) : null}
            </div>
          </div>
        ) : (
          <Empty
            title={`Nothing failed in ${span.words}`}
            words={
              ran?.modelCalls?.known ? (
                <>
                  <span className="ad-num text-ad-text">{count(ran.modelCalls.value)}</span> model
                  call{ran.modelCalls.value === 1 ? " was" : "s were"} made in {span.words} and none
                  failed.{" "}
                  {ran.syncsStuck?.value
                    ? `${count(ran.syncsStuck.value)} sync${ran.syncsStuck.value === 1 ? " is" : "s are"} still running long after it should have finished, which this list does not count: see Jobs.`
                    : "No sync failed, and none is stuck."}
                </>
              ) : (
                "No job and no model call has failed in this window. If something is wrong and it is not here, it did not get as far as being recorded."
              )
            }
            action={WINDOWS.filter(
              (one) => one.key !== span.key && WINDOWS.indexOf(one) > WINDOWS.indexOf(span),
            ).map((one) => (
              <Link
                key={one.key}
                href={`/admin/errors?window=${one.key}`}
                className="text-ad-accent hover:text-ad-text text-[13px] font-medium transition-colors"
              >
                Look over {one.words.replace("the last ", "")}
              </Link>
            ))}
          />
        )}
      </div>
    </Shell>
  );
}

/* ---------- quota ---------- */

export function AdminQuota({
  who,
  chrome,
  accounts,
  names,
  trouble,
}: {
  who: Whoami;
  chrome: Chrome;
  accounts: Room[];
  /* Google Ads customer id to the business it belongs to. */
  names: Record<string, { name: string; id: string }>;
  trouble: string;
}) {
  const tight = accounts.filter((one) => one.tight);
  const used = accounts.reduce((n, one) => n + one.used, 0);
  return (
    <Shell who={who} here="/admin/quota" door={chrome.door} failures={chrome.failures}>
      <Head
        title="Quota"
        pill={
          accounts.length ? (
            tight.length ? (
              <Pill tone="warn">{count(tight.length)} close to the limit</Pill>
            ) : (
              <Pill tone="good">Plenty left</Pill>
            )
          ) : null
        }
        lead="Google allows each account a fixed number of operations a day. Counted today, tightest first."
      />

      <div className="mt-6 grid gap-6">
        <Problem words={trouble} />
        {accounts.length ? (
          <>
            <Figures
              cells={[
                { label: "Connected accounts", value: count(accounts.length) },
                {
                  label: "Close to the limit",
                  value: count(tight.length),
                  warn: tight.length > 0,
                  lead: true,
                  note: "80% or more of the day's allowance used",
                },
                { label: "Operations used today", value: count(used) },
              ]}
            />
            <section className="border-ad-border bg-ad-surface overflow-hidden rounded-[6px] border">
              <Table
                caption="Google Ads quota by account"
                title="account"
                lead="share"
                cols={[
                  { key: "account", label: "Account", width: "32%" },
                  { key: "meter", label: "Used of the allowance", width: "34%" },
                  { key: "share", label: "Used", num: true },
                  { key: "left", label: "Left", num: true },
                ]}
                lines={accounts.map((one) => {
                  const who = names[one.customer_id];
                  return {
                    id: one.customer_id,
                    cells: {
                      account: (
                        <div className="flex min-w-0 items-center gap-3">
                          <Mark seed={who?.id ?? one.customer_id} name={who?.name ?? "?"} />
                          <div className="min-w-0">
                            {who ? (
                              <Link
                                href={`/admin?view=merchant&id=${who.id}`}
                                className="hover:text-ad-accent block truncate font-medium transition-colors"
                              >
                                {who.name}
                              </Link>
                            ) : (
                              <p className="text-ad-muted">Google Ads account</p>
                            )}
                            <p className="ad-num text-ad-faint text-[13px] leading-[18px]">
                              {adsId(one.customer_id)}
                            </p>
                          </div>
                        </div>
                      ),
                      meter: (
                        <div className="max-w-[320px]">
                          <Meter share={one.share_used} tone={one.tight ? "warn" : "plain"} />
                          <p className="ad-num text-ad-faint mt-1.5 text-[12px] leading-[16px]">
                            {count(one.used)} of {count(one.allowance)}
                          </p>
                        </div>
                      ),
                      share: (
                        <span className={one.tight ? "text-ad-warning" : "text-ad-text"}>
                          {(one.share_used * 100).toFixed(1)}%
                        </span>
                      ),
                      left: count(one.left),
                    },
                  };
                })}
              />
            </section>
          </>
        ) : (
          <Empty
            title="No connected accounts"
            words="Quota is counted per Google Ads account, so there is nothing to show until one is connected."
          />
        )}
      </div>
    </Shell>
  );
}

/* ---------- settings ---------- */

function Setting({
  title,
  words: about,
  children,
}: {
  title: string;
  words: string;
  children: ReactNode;
}) {
  return (
    <section className="border-ad-border grid gap-4 border-t py-8 first:border-t-0 first:pt-0 lg:grid-cols-[minmax(0,360px)_minmax(0,1fr)] lg:gap-10">
      <div>
        <h2 className="text-[15px] leading-[22px] font-semibold">{title}</h2>
        <p className="text-ad-muted mt-1 text-[13px] leading-[20px]">{about}</p>
      </div>
      <div className="min-w-0">{children}</div>
    </section>
  );
}

export function AdminPlatform({
  who,
  chrome,
  view,
  trouble,
}: {
  who: Whoami;
  chrome: Chrome;
  view: PlatformView | null;
  trouble: string;
}) {
  const door = chrome.door;
  const platformStop = view?.stops.find((one) => !one.customer_id);
  const accountStops = view?.stops.filter((one) => one.customer_id) ?? [];
  return (
    <Shell who={who} here="/admin/platform" door={chrome.door} failures={chrome.failures}>
      <Head
        title="Settings"
        pill={
          door ? (
            <Pill tone={door.state === "on" ? "good" : door.state === "stopped" ? "bad" : "warn"}>
              {door.state === "on"
                ? "Writes on"
                : door.state === "stopped"
                  ? "Writes stopped"
                  : "Writes off"}
            </Pill>
          ) : null
        }
        lead="What governs the platform. Writes to Google Ads switch on and off here, with your reason kept; everything else is read from the deployment."
      />

      <div className="mt-8 grid gap-6">
        <Problem words={trouble} />
        {view ? (
          <div>
            <Setting
              title="Writes to Google Ads"
              words="The one door. Every change Otto sends to a merchant's account goes through it. Switch it on and off here; a stop still wins over the switch."
            >
              <div className="border-ad-border bg-ad-surface rounded-[6px] border p-5">
                <p className="text-[15px] leading-[22px] font-semibold">
                  {view.anything_can_be_written
                    ? "PPCWay can write to Google Ads"
                    : platformStop && door?.state === "stopped"
                      ? "Stopped across the whole platform"
                      : view.writes?.source === "panel"
                        ? "Off, switched off here"
                        : "Off"}
                </p>
                <p className="text-ad-muted mt-1 text-[13px] leading-[20px]">{view.words}</p>
                {view.writes ? (
                  <div className="border-ad-rule mt-4 border-t pt-4">
                    <SwitchWrites on={view.writes.on} may={Boolean(view.may_switch_writes)} />
                    {view.writes.source === "panel" && view.writes.set_at ? (
                      <p className="text-ad-faint mt-2 text-[12px] leading-[18px]">
                        Last switched {view.writes.on ? "on" : "off"}
                        {view.writes.set_by ? ` by ${view.writes.set_by}` : ""},{" "}
                        <span className="ad-num">{stamp(view.writes.set_at)}</span>
                        {/* Off, the sentence above already says why. */}
                        {view.writes.on && view.writes.because ? `: ${view.writes.because}` : ""}
                      </p>
                    ) : (
                      <p className="text-ad-faint mt-2 text-[12px] leading-[18px]">
                        Nobody has switched it here yet, so the deployment’s setting stands.
                      </p>
                    )}
                  </div>
                ) : null}
                <div className="border-ad-rule mt-4 border-t pt-4">
                  {view.may_stop_writes ? (
                    <StopWrites stopped={Boolean(platformStop)} label="Stop writes everywhere" />
                  ) : (
                    <p className="text-ad-faint text-[12px] leading-[18px]">
                      Only principal access can stop writes. Ask somebody who has it rather than
                      going round the panel.
                    </p>
                  )}
                </div>
              </div>
            </Setting>

            <Setting
              title="Stops in force"
              words="Writes stopped for one account or for everybody, and who did it. A stop PPCWay set cannot be lifted by the merchant."
            >
              {view.stops.length ? (
                <ul className="border-ad-border bg-ad-surface rounded-[6px] border">
                  {[...(platformStop ? [platformStop] : []), ...accountStops].map((one, at) => (
                    <li
                      key={`${one.scope}-${at}`}
                      className="border-ad-rule flex flex-wrap items-start justify-between gap-3 border-t px-5 py-4 first:border-t-0"
                    >
                      <div className="min-w-0">
                        <p className="font-medium">
                          {one.customer_id ? (
                            <span className="ad-num">{adsId(one.customer_id)}</span>
                          ) : (
                            "The whole platform"
                          )}
                        </p>
                        <p className="text-ad-muted mt-0.5 text-[13px] leading-[20px]">
                          {one.because}
                        </p>
                      </div>
                      <div className="flex flex-none items-center gap-3">
                        <Pill tone={one.ours ? "warn" : "plain"}>
                          {one.ours ? "Set by PPCWay" : "Set by the merchant"}
                        </Pill>
                        {one.pulled_at ? (
                          <span className="ad-num text-ad-faint text-[12px]">
                            {stamp(one.pulled_at)}
                          </span>
                        ) : null}
                      </div>
                    </li>
                  ))}
                </ul>
              ) : (
                <Empty
                  title="Nothing is stopped"
                  words="No account and no person has pulled a switch."
                />
              )}
            </Setting>

            <Setting
              title="How this deployment is set"
              words="Writing to Google Ads is the switch above. The rest are read from the environment and take a deploy to change, on purpose: applying without asking is the client's decision, not something to flip while testing."
            >
              <ul className="border-ad-border bg-ad-surface rounded-[6px] border">
                {view.flags.map((one) => (
                  <li
                    key={one.name}
                    className="border-ad-rule grid gap-x-6 gap-y-1 border-t px-5 py-4 first:border-t-0 sm:grid-cols-[minmax(0,1fr)_auto]"
                  >
                    <div className="min-w-0">
                      <p className="font-medium">{one.name}</p>
                      <p className="text-ad-muted mt-0.5 text-[13px] leading-[20px]">
                        {one.what_it_does}
                      </p>
                      {!one.changeable ? (
                        <p className="text-ad-faint mt-1 text-[12px] leading-[18px]">
                          {one.why_not}
                        </p>
                      ) : null}
                    </div>
                    <div className="sm:pt-0.5">
                      <Pill tone={one.on ? "good" : "plain"}>{one.on ? "On" : "Off"}</Pill>
                    </div>
                  </li>
                ))}
              </ul>
            </Setting>
          </div>
        ) : null}
      </div>
    </Shell>
  );
}

/* ---------- access ---------- */

export function AdminStaff({
  who,
  chrome,
  grants,
  trouble,
}: {
  who: Whoami;
  chrome: Chrome;
  grants: Grant[];
  trouble: string;
}) {
  /*
    Who holds access now, read from the history rather than stored apart from
    it: the newest row for each person decides, and a withdrawal removes them.
  */
  const seen = new Set<string>();
  const holding: Grant[] = [];
  for (const one of grants) {
    if (seen.has(one.account_id)) continue;
    seen.add(one.account_id);
    if (one.granted) holding.push(one);
  }
  const person = (one: Grant) => one.who || `Account ${one.account_id.slice(0, 8)}`;

  return (
    <Shell who={who} here="/admin/staff" door={chrome.door} failures={chrome.failures}>
      <Head
        title="Access"
        pill={<Pill tone="plain">{count(holding.length)} with access</Pill>}
        lead="Who can open this console, and every grant and withdrawal there has been. Nothing here is ever deleted."
        side={<GrantAccess />}
      />

      <div className="mt-6 grid gap-6">
        <Problem words={trouble} />
        <div className="grid items-start gap-6 xl:grid-cols-[minmax(0,2fr)_minmax(0,1fr)]">
          <Panel title="Every change of access" meta="Newest first. Times in UTC." flush>
            {grants.length ? (
              <Table
                caption="Grants and withdrawals of internal access"
                title="person"
                lead="what"
                cols={[
                  { key: "person", label: "Person", width: "46%" },
                  { key: "what", label: "Change" },
                  { key: "when", label: "When", num: true },
                ]}
                lines={grants.map((one, at) => ({
                  id: `${one.at}-${at}`,
                  cells: {
                    person: (
                      <div className="flex min-w-0 items-center gap-3">
                        <Mark seed={one.who || one.account_id} name={person(one)} />
                        <div className="min-w-0">
                          <p className="truncate font-medium">{person(one)}</p>
                          {one.because ? (
                            <p className="text-ad-muted truncate text-[13px] leading-[18px]">
                              {one.because}
                            </p>
                          ) : null}
                        </div>
                      </div>
                    ),
                    /* Who did it sits under what they did: one fact, read together. */
                    what: (
                      <div className="flex min-w-0 flex-col items-start gap-1">
                        {one.granted ? (
                          <Pill tone="info">Given {LEVEL_WORDS[one.level] ?? one.level}</Pill>
                        ) : (
                          <Pill tone="plain">Taken away</Pill>
                        )}
                        <span className="text-ad-faint max-w-full truncate text-[12px] leading-[16px]">
                          by{" "}
                          {one.by || (one.by_account_id ? "another principal" : "the command line")}
                        </span>
                      </div>
                    ),
                    when: <span className="text-ad-muted">{stamp(one.at)}</span>,
                  },
                }))}
              />
            ) : (
              <div className="px-5 pb-5">
                <Empty
                  title="Nobody has been given access yet"
                  words="Access is given by email, and the person has to have signed in once first. Every grant needs a reason, because this list exists to be read back."
                />
              </div>
            )}
          </Panel>

          <div className="grid gap-6">
            <Panel title="Holding access now" meta={`${count(holding.length)} people`}>
              {holding.length ? (
                <ul className="grid gap-3">
                  {holding.map((one) => (
                    <li key={one.account_id} className="flex items-center gap-3">
                      <Mark seed={one.who || one.account_id} name={person(one)} size={24} />
                      <span className="min-w-0 flex-1 truncate">{person(one)}</span>
                      <Pill tone={one.level === "principal" ? "info" : "plain"}>
                        {LEVEL_WORDS[one.level] ?? one.level}
                      </Pill>
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="text-ad-muted">Nobody.</p>
              )}
            </Panel>
            {who.levels.length ? (
              <Panel title="What each level may do">
                <dl className="grid gap-3">
                  {who.levels.map((one) => (
                    <div key={one.level}>
                      <dt className="font-medium">{LEVEL_WORDS[one.level] ?? words(one.level)}</dt>
                      <dd className="text-ad-muted mt-0.5 text-[13px] leading-[20px]">
                        {one.what}
                      </dd>
                    </div>
                  ))}
                </dl>
              </Panel>
            ) : null}
          </div>
        </div>
      </div>
    </Shell>
  );
}
