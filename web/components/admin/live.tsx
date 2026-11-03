import Link from "next/link";
import { AppShell, type Workspace } from "@/components/app/shell";
import { PageHead, Panel, PanelText, TabsRow, Tile, Tiles } from "@/components/app/blocks";
import { DataTable, StatusWord } from "@/components/app/table";
import {
  ago,
  count,
  moved,
  type Figure,
  type MerchantRow,
  type Overview,
  type PlatformView,
  type Whoami,
} from "@/lib/admin";
import { StaffBar } from "./staff-bar";

/*
  The internal screens, with real figures in them.

  These use the same blocks as every other screen in the app -- AppShell,
  PageHead, Tiles, DataTable -- because the brief is that the admin side
  follows the app, and the fastest way to follow it is to be built from it.
  What differs is rhythm rather than materials: a merchant reading their own
  dashboard needs reassurance, and somebody scanning forty businesses needs
  density. So the tables are tight and the tiles are few.

  Every sentence shown here was written by the backend. The screens do not
  compose their own from the numbers, because the backend is the thing that
  knows whether a figure is a count, a state, or unknown.
*/

const SHELL: { kind: "admin"; workspace: Workspace } = {
  kind: "admin",
  workspace: { name: "PPCWay admin", meta: "Internal" },
};

function shellFor(who: Whoami) {
  return {
    ...SHELL,
    kind: (who.may.includes("stop_writes") ? "admin-super" : "admin") as "admin" | "admin-super",
    workspace: {
      name: "PPCWay admin",
      meta: who.level ? `${who.level} access` : "Internal",
    },
    initials: (who.who ?? "PP").slice(0, 2).toUpperCase(),
    period: "Today",
  };
}

const TABS = [
  { label: "Overview", href: "/admin/metrics" },
  { label: "Merchants", href: "/admin" },
  { label: "Platform", href: "/admin/platform" },
  { label: "Jobs", href: "/admin/jobs" },
];

/*
  What to say when a read failed. An internal screen during an incident is the
  worst possible place for a white page, and "we could not reach the API" is
  itself the most useful thing the panel can say at that moment.
*/
function Trouble({ trouble }: { trouble: string }) {
  return (
    <Panel title="The panel could not read this">
      <PanelText>{trouble}</PanelText>
    </Panel>
  );
}

/* ---------- the overview ---------- */

function tileFor(one: Figure | undefined, fallback: string) {
  if (!one) return { label: fallback, value: "—", chip: "Not available" };
  return {
    label: one.label,
    value: one.known ? count(one.value) : "Unknown",
    chip: one.known ? moved(one.change) || one.window || undefined : "We cannot tell right now",
    valueTone: one.known ? undefined : ("faint" as const),
  };
}

export function AdminOverview({
  who,
  view,
  trouble,
}: {
  who: Whoami;
  view: Overview | null;
  trouble: string;
}) {
  return (
    <>
      <StaffBar who={who} />
      <AppShell {...shellFor(who)} active="metrics">
        <PageHead
          title={
            view
              ? view.healthy
                ? "Nothing needs a person right now."
                : `${view.trouble.length} thing${view.trouble.length > 1 ? "s" : ""} need a person.`
              : "The platform"
          }
          lead={
            view
              ? view.writes.words
              : "Figures for every business on the platform, counted when this page loaded."
          }
        />
        {trouble ? <Trouble trouble={trouble} /> : null}
        {view ? (
          <>
            {/*
              Trouble before figures. A person opening this screen at 2am is
              looking for what is wrong, and making them read four tiles first
              is making them work for it.
            */}
            {view.trouble.length ? (
              <Panel title="What needs a person">
                {view.trouble.map((one) => (
                  <PanelText key={one}>{one}</PanelText>
                ))}
              </Panel>
            ) : null}
            <Tiles>
              <Tile tone="brand" {...tileFor(view.figures.merchants, "Businesses")} />
              <Tile {...tileFor(view.figures.connected, "Connected")} />
              <Tile {...tileFor(view.figures.waiting, "Waiting")} />
              <Tile {...tileFor(view.figures.proposed, "Proposed")} />
            </Tiles>
            <TabsRow tabs={TABS} active="Overview" />
            <DataTable
              columns={[
                { key: "what", label: "Figure", width: 280 },
                { key: "value", label: "Count", align: "right" },
                { key: "over", label: "Measured over" },
                { key: "says", label: "In words" },
              ]}
              rows={Object.values(view.figures).map((one) => ({
                what: one.label,
                value: one.known ? count(one.value) : <StatusWord tone="faint">Unknown</StatusWord>,
                over: one.window || "right now",
                says: one.words,
              }))}
            />
          </>
        ) : null}
      </AppShell>
    </>
  );
}

/* ---------- the merchant list ---------- */

export function AdminMerchants({
  who,
  rows,
  trouble,
  lookedFor,
}: {
  who: Whoami;
  rows: MerchantRow[];
  trouble: string;
  lookedFor: string;
}) {
  const needing = rows.filter((one) => one.trouble);
  return (
    <>
      <StaffBar who={who} />
      <AppShell {...shellFor(who)} active="merchants">
        <PageHead
          title={
            rows.length
              ? needing.length
                ? `${count(rows.length)} businesses, ${count(needing.length)} need a person.`
                : `${count(rows.length)} businesses, all healthy.`
              : "No businesses yet."
          }
          lead={
            rows.length
              ? "Opening one is recorded. Every account you look at is written down with your name on it."
              : "When somebody signs up they appear here."
          }
        />
        {trouble ? <Trouble trouble={trouble} /> : null}
        <TabsRow tabs={TABS} active="Merchants" />
        {rows.length ? (
          <DataTable
            columns={[
              { key: "name", label: "Business", width: 260 },
              { key: "state", label: "Google Ads" },
              { key: "people", label: "People", align: "right" },
              { key: "waiting", label: "Waiting", align: "right" },
              { key: "applied", label: "Applied", align: "right" },
              { key: "sync", label: "Last sync" },
              { key: "says", label: "Needs a person" },
            ]}
            rows={rows.map((one) => ({
              name: (
                <Link
                  href={`/admin?view=merchant&id=${one.organization_id}`}
                  className="text-pw-blue font-medium underline underline-offset-2"
                >
                  {one.name}
                </Link>
              ),
              state: one.connected ? (
                <StatusWord tone={one.account_status === "ENABLED" ? undefined : "red"}>
                  {one.account_status || "Connected"}
                </StatusWord>
              ) : (
                <StatusWord tone="faint">Not connected</StatusWord>
              ),
              people: count(one.people),
              waiting: one.waiting ? count(one.waiting) : "0",
              applied: count(one.applied),
              sync: one.connected ? ago(one.last_sync) : "—",
              says: one.trouble ? <StatusWord tone="red">{one.trouble}</StatusWord> : "",
            }))}
            total={{
              name: `${count(rows.length)} businesses`,
              waiting: count(rows.reduce((n, one) => n + one.waiting, 0)),
              applied: count(rows.reduce((n, one) => n + one.applied, 0)),
            }}
          />
        ) : null}
        {lookedFor && !rows.length && !trouble ? (
          <Panel title="Nothing matched">
            <PanelText>
              No business has a name like &ldquo;{lookedFor}&rdquo;. Try part of the name instead of
              all of it.
            </PanelText>
          </Panel>
        ) : null}
      </AppShell>
    </>
  );
}

/* ---------- the platform ---------- */

export function AdminPlatform({
  who,
  view,
  trouble,
}: {
  who: Whoami;
  view: PlatformView | null;
  trouble: string;
}) {
  return (
    <>
      <StaffBar who={who} />
      <AppShell {...shellFor(who)} active="platform">
        <PageHead
          title={
            view
              ? view.anything_can_be_written
                ? "Writes are on."
                : "Nothing is being written."
              : "Platform"
          }
          lead={view ? view.words : "The settings that govern what PPCWay does."}
        />
        {trouble ? <Trouble trouble={trouble} /> : null}
        <TabsRow tabs={TABS} active="Platform" />
        {view ? (
          <>
            {view.stops.length ? (
              <Panel title="Stopped">
                {view.stops.map((one) => (
                  <PanelText key={`${one.scope}-${one.because}`}>
                    {one.scope}: {one.because}
                    {one.ours
                      ? " (set by PPCWay, so the merchant cannot lift it)"
                      : " (set by the merchant)"}
                  </PanelText>
                ))}
              </Panel>
            ) : null}
            <DataTable
              columns={[
                { key: "name", label: "Setting", width: 240 },
                { key: "on", label: "State" },
                { key: "what", label: "What it does" },
                { key: "change", label: "Can the panel change it" },
              ]}
              rows={view.flags.map((one) => ({
                name: one.name,
                on: one.on ? (
                  <StatusWord>On</StatusWord>
                ) : (
                  <StatusWord tone="faint">Off</StatusWord>
                ),
                what: one.what_it_does,
                /*
                  Every row says no, and that is the point. A screen that shows
                  a toggle for something only a deploy can change teaches
                  people the panel is lying to them.
                */
                change: one.changeable ? <StatusWord>Yes</StatusWord> : one.why_not,
              }))}
            />
            {!view.may_stop_writes ? (
              <Panel title="Stopping writes">
                <PanelText>
                  Only principal access can stop writes. Ask somebody who has it rather than going
                  round the panel.
                </PanelText>
              </Panel>
            ) : null}
          </>
        ) : null}
      </AppShell>
    </>
  );
}
