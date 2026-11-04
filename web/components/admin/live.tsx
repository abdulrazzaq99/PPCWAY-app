import Link from "next/link";
import {
  ago,
  count,
  direction,
  moved,
  type Fault,
  type Figure,
  type Grant,
  type JobRun,
  type MerchantRow,
  type Overview,
  type PlatformView,
  type Room,
  type Whoami,
} from "@/lib/admin";
import { GrantAccess, StopWrites } from "./actions";
import { AllWell, Attention, Nothing, Page, Rows, State, Stats } from "./data";
import { Shell } from "./shell";

/*
  The internal screens.

  They used to be seven copies of one layout: a page head, a tab row and a
  table, every time. That is why they read as generated. The job each screen
  does is different, so the shape each one takes is now different too.

  Merchants is a list you search. The overview is a verdict with figures under
  it. Failures is a feed. Settings is prose with a table of record. Access is a
  history. None of them is a dashboard of equal tiles, because none of them is
  answering the question a dashboard answers.

  Same tokens as the merchant app, same palette, same radii. Tighter, because
  somebody here is scanning four hundred businesses and not reading about one.
*/

function Frame({
  who,
  looking_at,
  counts,
  children,
}: {
  who: Whoami;
  looking_at?: string;
  counts?: { failures?: number; waiting?: number };
  children: React.ReactNode;
}) {
  return (
    <Shell who={who} looking_at={looking_at} counts={counts}>
      {children}
    </Shell>
  );
}

function Trouble({ trouble }: { trouble: string }) {
  if (!trouble) return null;
  return <Attention items={[trouble]} />;
}

/* ---------- merchants ---------- */

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
  /*
    Four rows of the same sentence is not four findings. The panel groups
    identical trouble and says how many share it, which is the fact somebody
    can act on: "4 businesses have no Google Ads account connected."
  */
  const grouped = Object.entries(
    needing.reduce<Record<string, string[]>>((all, one) => {
      (all[one.trouble] ||= []).push(one.name);
      return all;
    }, {}),
  ).map(([what, names]) =>
    names.length === 1
      ? `${names[0]}: ${what.charAt(0).toLowerCase()}${what.slice(1)}`
      : `${count(names.length)} businesses: ${what.charAt(0).toLowerCase()}${what.slice(1)}`,
  );
  return (
    <Frame who={who} counts={{ waiting: rows.reduce((n, one) => n + one.waiting, 0) }}>
      <Page
        title={
          rows.length
            ? needing.length
              ? `${count(needing.length)} of ${count(rows.length)} businesses need a person`
              : `${count(rows.length)} businesses, all healthy`
            : "No businesses yet"
        }
        lead={
          rows.length
            ? "Opening one is recorded against your name."
            : "When somebody signs up they appear here."
        }
        side={
          <form action="/admin" className="flex gap-2">
            <label htmlFor="q" className="sr-only">
              Search by name
            </label>
            <input
              id="q"
              name="q"
              defaultValue={lookedFor}
              placeholder="Search by name"
              className="border-pw-border-input text-pw-ink placeholder:text-pw-ink-400 focus:border-pw-blue focus:ring-pw-blue/20 h-9 w-[180px] rounded-[10px] border bg-white px-3 text-[14px] outline-none focus:ring-2"
            />
            <button
              type="submit"
              className="bg-pw-blue hover:bg-pw-blue-hover h-9 rounded-[10px] px-3 text-[14px] font-medium text-white active:scale-[0.98]"
            >
              Search
            </button>
          </form>
        }
      >
        <Trouble trouble={trouble} />
        {grouped.length ? <Attention items={grouped} /> : null}

        <Rows
          titleKey="name"
          cols={[
            { key: "name", label: "Business", width: 240 },
            { key: "state", label: "Google Ads" },
            { key: "waiting", label: "Waiting", num: true },
            { key: "applied", label: "Applied", num: true },
            { key: "people", label: "People", num: true, minor: true },
            { key: "sync", label: "Last sync" },
          ]}
          rows={rows.map((one) => ({
            id: one.organization_id,
            name: (
              <Link
                href={`/admin?view=merchant&id=${one.organization_id}`}
                className="text-pw-blue font-medium underline underline-offset-2"
              >
                {one.name}
              </Link>
            ),
            /*
              A connected account with no status read yet is connected, not
              broken. The first version coloured anything that was not the
              literal string ENABLED as bad, so a healthy account whose status
              had not been synced printed "Connected" in red. That was on
              screen.
            */
            state: !one.connected ? (
              <State tone="faint">Not connected</State>
            ) : !one.account_status || one.account_status === "ENABLED" ? (
              <State tone="good">Connected</State>
            ) : (
              <State tone="bad">{one.account_status.toLowerCase()}</State>
            ),
            waiting: one.waiting ? count(one.waiting) : "0",
            applied: count(one.applied),
            people: count(one.people),
            sync: one.connected ? ago(one.last_sync) : "—",
          }))}
          empty={
            lookedFor ? (
              <Nothing
                title="Nothing matched"
                words={`No business has a name like "${lookedFor}". Try part of the name rather than all of it.`}
              />
            ) : (
              <Nothing
                title="No businesses yet"
                words="When somebody signs up and connects their Google Ads account, they appear here."
              />
            )
          }
        />
      </Page>
    </Frame>
  );
}

/* ---------- the overview ---------- */

function stat(key: string, one: Figure | undefined, fallback: string, lead = false) {
  if (!one) return { label: fallback, value: "0", unknown: true };
  return {
    label: one.label,
    value: count(one.value),
    note: moved(one.change, one.window) || one.window || undefined,
    noteTone: direction(key, one.change),
    unknown: !one.known,
    lead,
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
    <Frame who={who}>
      <Page
        title={
          view
            ? view.healthy
              ? "Nothing needs a person"
              : `${view.trouble.length} thing${view.trouble.length > 1 ? "s" : ""} need a person`
            : "The platform"
        }
        lead={view ? view.writes.words : undefined}
      >
        <Trouble trouble={trouble} />
        {view ? (
          <>
            {view.trouble.length ? (
              <Attention items={view.trouble} />
            ) : (
              <AllWell words={`Counted over the last ${view.window}. Nothing is failing.`} />
            )}

            {/*
              Waiting leads, at a size its siblings do not share. It is the
              figure the screen's question turns on: proposals nobody has
              answered are the only number here that somebody has to do
              something about.
            */}
            <Stats
              stats={[
                stat("waiting", view.figures.waiting, "Waiting", true),
                stat("merchants", view.figures.merchants, "Businesses"),
                stat("connected", view.figures.connected, "Connected"),
                stat("proposed", view.figures.proposed, "Proposed"),
                stat("applied", view.figures.applied, "Applied"),
              ]}
            />

            <h2 className="text-pw-ink mt-8 mb-3 text-[15px] leading-[21px] font-semibold">
              Everything counted
            </h2>
            <Rows
              titleKey="what"
              cols={[
                { key: "what", label: "Figure", width: 260 },
                { key: "value", label: "Count", num: true },
                { key: "over", label: "Over" },
                { key: "says", label: "In words", minor: true },
              ]}
              rows={Object.entries(view.figures).map(([key, one]) => ({
                id: key,
                what: one.label,
                value: one.known ? count(one.value) : <State tone="faint">Unknown</State>,
                over: one.window || "now",
                says: one.words,
              }))}
              empty={<Nothing title="Nothing counted" words="There is no data to count yet." />}
            />
          </>
        ) : null}
      </Page>
    </Frame>
  );
}

/* ---------- jobs ---------- */

export function AdminJobs({
  who,
  runs,
  trouble,
}: {
  who: Whoami;
  runs: JobRun[];
  trouble: string;
}) {
  const stuck = runs.filter((one) => one.stuck);
  const failed = runs.filter((one) => one.status === "failed");
  return (
    <Frame who={who}>
      <Page
        title={
          runs.length
            ? stuck.length
              ? `${count(stuck.length)} job${stuck.length > 1 ? "s" : ""} started and never finished`
              : failed.length
                ? `${count(failed.length)} of the last ${count(runs.length)} runs failed`
                : `The last ${count(runs.length)} runs all finished`
            : "No jobs have run yet"
        }
        lead="The scheduled reads of Google Ads, newest first."
      >
        <Trouble trouble={trouble} />
        {stuck.length ? (
          <Attention
            items={stuck
              .slice(0, 3)
              .map((one) => `${one.kind} on ${one.customer_id || "an account"}: ${one.words}`)}
          />
        ) : null}

        <Rows
          titleKey="kind"
          cols={[
            { key: "kind", label: "Job", width: 130 },
            { key: "state", label: "State" },
            { key: "took", label: "Took", num: true },
            { key: "when", label: "Started" },
            { key: "account", label: "Account", minor: true },
            { key: "says", label: "What happened", minor: true },
          ]}
          rows={runs.map((one) => ({
            id: one.id,
            kind: one.kind,
            state: one.stuck ? (
              <State tone="bad">Stuck</State>
            ) : one.status === "failed" ? (
              <State tone="bad">Failed</State>
            ) : one.took_seconds === null ? (
              <State tone="faint">Running</State>
            ) : (
              <State tone="good">Finished</State>
            ),
            /* An em dash, not 0 s: still running is not instant. */
            took: one.took_seconds === null ? "—" : `${count(one.took_seconds)}s`,
            when: ago(one.started_at),
            account: one.customer_id || "—",
            says: one.words,
          }))}
          empty={
            <Nothing
              title="Nothing has run yet"
              words="A fresh deployment has run no jobs. The syncs start on their own schedule."
            />
          }
        />
      </Page>
    </Frame>
  );
}

/* ---------- failures ---------- */

export function AdminErrors({
  who,
  faults,
  trouble,
  window,
}: {
  who: Whoami;
  faults: Fault[];
  trouble: string;
  window: string;
}) {
  return (
    <Frame who={who} counts={{ failures: faults.length }}>
      <Page
        title={
          faults.length
            ? `${count(faults.length)} thing${faults.length > 1 ? "s" : ""} failed in the last ${window}`
            : `Nothing failed in the last ${window}`
        }
        lead="Jobs and model calls together. They fail for unrelated reasons, but you only want one list."
      >
        <Trouble trouble={trouble} />
        {faults.length ? (
          /*
            A feed rather than a table. A failure is one thing that happened at
            one moment, and the sentence describing it is the row -- putting it
            in a cell four columns wide makes it harder to read, not easier.
          */
          <ul className="border-pw-border divide-pw-divider divide-y overflow-hidden rounded-[12px] border">
            {faults.map((one, at) => (
              <li key={`${one.at}-${at}`} className="px-4 py-3 sm:px-5">
                <p className="text-pw-ink text-[14px] leading-[20px]">{one.what}</p>
                <p className="text-pw-ink-400 pw-num mt-1 flex flex-wrap gap-x-4 text-[12px] leading-[16px]">
                  <span>{one.where}</span>
                  <span>{ago(one.at)}</span>
                  {one.customer_id ? <span>{one.customer_id}</span> : null}
                </p>
              </li>
            ))}
          </ul>
        ) : (
          <Nothing
            title="Nothing to look at"
            words="No job and no model call has failed in this window. If something is wrong and it is not here, it did not get as far as being recorded."
          />
        )}
      </Page>
    </Frame>
  );
}

/* ---------- quota ---------- */

export function AdminQuota({
  who,
  accounts,
  trouble,
}: {
  who: Whoami;
  accounts: Room[];
  trouble: string;
}) {
  const tight = accounts.filter((one) => one.tight);
  return (
    <Frame who={who}>
      <Page
        title={
          accounts.length
            ? tight.length
              ? `${count(tight.length)} account${tight.length > 1 ? "s" : ""} close to the daily limit`
              : `${count(accounts.length)} accounts, none close to the limit`
            : "No connected accounts yet"
        }
        lead="Google allows a fixed number of operations per account per day. Tightest first."
      >
        <Trouble trouble={trouble} />
        <Rows
          titleKey="account"
          cols={[
            { key: "account", label: "Account", width: 200 },
            { key: "share", label: "Used", num: true },
            { key: "used", label: "Operations", num: true },
            { key: "left", label: "Left", num: true },
          ]}
          rows={accounts.map((one) => ({
            id: one.customer_id,
            account: one.customer_id,
            share: (
              <State tone={one.tight ? "bad" : "plain"}>{Math.round(one.share_used * 100)}%</State>
            ),
            used: count(one.used),
            left: count(one.left),
          }))}
          empty={
            <Nothing
              title="No connected accounts"
              words="Quota is counted per Google Ads account, so there is nothing to show until one is connected."
            />
          }
        />
      </Page>
    </Frame>
  );
}

/* ---------- settings ---------- */

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
    <Frame who={who}>
      <Page
        title={
          view
            ? view.anything_can_be_written
              ? "Writes are on"
              : "Nothing is being written"
            : "Settings"
        }
        lead={view?.words}
        side={
          /*
            The job this screen exists for, one click from the answer it sits
            under. Shown only to somebody who may do it: a button that returns
            403 teaches staff the panel is broken when it is simply not theirs.
          */
          view?.may_stop_writes ? (
            <StopWrites stopped={Boolean(view.stops.find((one) => !one.customer_id))} />
          ) : undefined
        }
      >
        <Trouble trouble={trouble} />
        {view ? (
          <>
            {view.stops.length ? (
              <Attention
                items={view.stops.map(
                  (one) =>
                    `${one.scope}: ${one.because}${
                      one.ours
                        ? " (set by PPCWay, so the merchant cannot lift it)"
                        : " (set by the merchant)"
                    }`,
                )}
              />
            ) : null}

            <Rows
              titleKey="name"
              cols={[
                { key: "name", label: "Setting", width: 220 },
                { key: "on", label: "State" },
                { key: "what", label: "What it does" },
                { key: "change", label: "Changeable here", minor: true },
              ]}
              rows={view.flags.map((one) => ({
                id: one.name,
                name: one.name,
                on: one.on ? <State tone="good">On</State> : <State tone="faint">Off</State>,
                what: one.what_it_does,
                /*
                  Every row says no, and that is the point rather than an
                  omission: a toggle for something only a deploy can change
                  teaches people the panel is lying to them.
                */
                change: one.changeable ? <State tone="good">Yes</State> : one.why_not,
              }))}
              empty={<Nothing title="No settings" words="Nothing is configured." />}
            />

            {!view.may_stop_writes ? (
              <p className="text-pw-ink-500 mt-4 text-[13px] leading-[18px]">
                Only principal access can stop writes. Ask somebody who has it rather than going
                round the panel.
              </p>
            ) : null}
          </>
        ) : null}
      </Page>
    </Frame>
  );
}

/* ---------- access ---------- */

export function AdminStaff({
  who,
  grants,
  trouble,
}: {
  who: Whoami;
  grants: Grant[];
  trouble: string;
}) {
  const live = grants.filter((one) => one.granted);
  return (
    <Frame who={who}>
      <Page
        title={
          grants.length
            ? `${count(live.length)} grant${live.length === 1 ? "" : "s"} of access`
            : "Nobody has been given access yet"
        }
        lead="Every grant and every withdrawal, newest first. Nothing here is ever deleted."
        side={<GrantAccess />}
      >
        <Trouble trouble={trouble} />
        <Rows
          titleKey="level"
          cols={[
            { key: "level", label: "Level", width: 130 },
            { key: "what", label: "Given or taken" },
            { key: "when", label: "When" },
            { key: "why", label: "Why", minor: true },
          ]}
          rows={grants.map((one, at) => ({
            id: `${one.at}-${at}`,
            level: one.level,
            what: one.granted ? (
              <State tone="good">Given</State>
            ) : (
              <State tone="faint">Taken away</State>
            ),
            when: ago(one.at),
            why: one.because || "—",
          }))}
          empty={
            <Nothing
              title="Nobody has access yet"
              words="Access is given by email, and the person has to have signed in once first. Every grant needs a reason, because this list exists to be read back."
            />
          }
        />
      </Page>
    </Frame>
  );
}
