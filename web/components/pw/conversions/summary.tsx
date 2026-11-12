"use client";

import { CaretRightIcon } from "@phosphor-icons/react";
import { useRouter } from "next/navigation";
import { useState, type ReactNode } from "react";
import { Card, Note, Tick, Toggle } from "@/components/pw/create/kit";
import { Button, LinkButton } from "@/components/ui/button";
import { Input } from "@/components/ui/field";
import { cn } from "@/lib/cn";
import type { ConversionGoal } from "@/lib/creation";
import { EditAction } from "./edit";
import { TagCheck, TagSetup } from "./tag";
import {
  CATEGORY_ORDER,
  conversions,
  domainOf,
  said,
  talk,
  type Action,
  type Changed,
  type Summary,
} from "./types";

/*
  Google's Goals, Conversions, Summary: the Google tag and whether it is on
  the site, every conversion action grouped by goal (each row opens its
  settings), the conversions Google lists to import, and the account's goals
  with their "Account default" switch. With no actions yet, it says why that
  matters and starts the setup.
*/

const TRACKING: Record<string, string> = {
  NOT_CONVERSION_TRACKED: "This account does not track conversions yet.",
  CONVERSION_TRACKING_MANAGED_BY_SELF: "This account tracks its own conversions.",
  CONVERSION_TRACKING_MANAGED_BY_THIS_MANAGER:
    "This account's manager account tracks its conversions.",
  CONVERSION_TRACKING_MANAGED_BY_ANOTHER_MANAGER: "Another manager account tracks its conversions.",
};

const rank = (category: string) => {
  const at = CATEGORY_ORDER.indexOf(category);
  return at === -1 ? CATEGORY_ORDER.length : at;
};

const plural = (n: number, one: string) => `${n} ${one}${n === 1 ? "" : "s"}`;

const goalKey = (g: { category: string; origin: string }) => `${g.category}~${g.origin}`;

function StateChip({ state }: { state: string }) {
  const tone =
    state === "Recording conversions"
      ? "bg-pw-good-bg text-pw-good-ink"
      : state === "No recent conversions"
        ? "bg-pw-warn-bg text-pw-warn-ink"
        : "bg-pw-muted text-pw-ink-600";
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full px-[9px] py-[3px] text-[12px] font-bold whitespace-nowrap",
        tone,
      )}
    >
      {state || "Unknown"}
    </span>
  );
}

/** A column's name, said before its value where the table stacks on a phone. */
function Mobile({ children }: { children: ReactNode }) {
  return <span className="text-pw-ink-400 sm:hidden">{children} </span>;
}

function TagCard({ summary }: { summary: Summary }) {
  const [how, setHow] = useState(false);
  // When PPCWay has no website for the account, the merchant types it here so
  // the tag can be looked for; it is used for this check, not saved.
  const [entered, setEntered] = useState("");
  const [typed, setTyped] = useState("");
  const site = summary.website || entered;
  const takeTyped = () => {
    const raw = typed.trim();
    if (!raw) return;
    setEntered(raw.startsWith("http://") || raw.startsWith("https://") ? raw : `https://${raw}`);
  };
  const trackingId = summary.tracking_id ?? "";
  const status = TRACKING[summary.tracking_status ?? ""] ?? "";
  return (
    <Card
      title="Google tag"
      help="The tag counts conversions on your website. It goes on every page, once."
      aside={
        trackingId ? (
          <span className="bg-pw-muted text-pw-ink-600 shrink-0 rounded-full px-3 py-1 text-[12px] font-semibold">
            Tag ID {trackingId}
          </span>
        ) : null
      }
    >
      <div className="flex flex-col gap-4 px-4 py-5 sm:px-6">
        <p className="text-pw-ink-600 text-[14px] leading-[20px]">
          {site ? (
            <>
              Your website is <span className="text-pw-ink font-semibold">{domainOf(site)}</span>
              .{" "}
            </>
          ) : (
            "PPCWay does not know your website yet. "
          )}
          {status}
        </p>
        {!summary.website ? (
          <div className="flex max-w-[520px] gap-2">
            <Input
              value={typed}
              aria-label="Your website"
              placeholder="pdfezy.com"
              onChange={(e) => setTyped(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter") {
                  e.preventDefault();
                  takeTyped();
                }
              }}
              className="flex-1"
            />
            <Button variant="secondary" size="sm" onClick={takeTyped} disabled={!typed.trim()}>
              Use this website
            </Button>
          </div>
        ) : null}
        <TagCheck
          key={site}
          site={site}
          trackingId={trackingId}
          initial={summary.website ? summary.tag : undefined}
          label={summary.website || !entered ? "Check again" : "Check the tag"}
        >
          <Button variant="quiet" size="sm" onClick={() => setHow((h) => !h)} aria-expanded={how}>
            {how ? "Hide how to install" : "How to install"}
          </Button>
        </TagCheck>
        {how ? (
          <div className="border-pw-border border-t pt-5">
            <TagSetup
              globalTag={summary.global_site_tag ?? ""}
              trackingId={trackingId}
              actions={summary.actions ?? []}
              site={site}
              account={summary.account_name ?? ""}
            />
          </div>
        ) : null}
      </div>
    </Card>
  );
}

const COLS =
  "sm:grid sm:grid-cols-[minmax(0,2.4fr)_minmax(0,1fr)_minmax(0,1.3fr)_minmax(0,1.4fr)_minmax(0,1fr)] sm:items-center sm:gap-4";

function ActionsCard({
  summary,
  goals,
  onSaved,
}: {
  summary: Summary;
  goals: ConversionGoal[] | null;
  onSaved: (message: string) => void;
}) {
  const [open, setOpen] = useState("");
  const actions = summary.actions ?? [];
  const groups = new Map<string, Action[]>();
  for (const a of [...actions].sort(
    (x, y) => rank(x.category) - rank(y.category) || x.name.localeCompare(y.name),
  )) {
    groups.set(a.category, [...(groups.get(a.category) ?? []), a]);
  }
  const defaults = new Set((goals ?? []).filter((g) => g.biddable).map((g) => g.category));
  return (
    <Card
      title="Conversion actions"
      help="Grouped by goal, as Google groups them. Primary actions count in the Conversions column and bidding aims for them; secondary ones are only observed. Open one to see or change its settings."
    >
      <div
        className={cn(
          COLS,
          "bg-pw-muted text-pw-ink-500 hidden px-6 py-2 text-[12px] font-semibold uppercase",
        )}
      >
        <span>Conversion action</span>
        <span>Action optimization</span>
        <span>Conversion source</span>
        <span>Status</span>
        <span className="text-right">All conv., last 30 days</span>
      </div>
      {[...groups].map(([category, list]) => (
        <div key={category}>
          <div className="border-pw-border bg-pw-ground flex flex-wrap items-center gap-x-3 gap-y-1 border-t px-4 py-2 sm:px-6">
            <span className="text-pw-ink text-[14px] font-semibold">{list[0].category_label}</span>
            <span className="text-pw-ink-500 text-[12px]">{plural(list.length, "action")}</span>
            {defaults.has(category) ? (
              <span className="bg-pw-blue-tint text-pw-blue-ink rounded-full px-2 py-[2px] text-[11px] font-bold">
                Account default
              </span>
            ) : null}
          </div>
          <ul>
            {list.map((a) => {
              const here = open === a.resource;
              return (
                <li key={a.resource} className="border-pw-border border-t">
                  <button
                    type="button"
                    aria-expanded={here}
                    onClick={() => setOpen(here ? "" : a.resource)}
                    className={cn(
                      COLS,
                      "hover:bg-pw-row-hover flex w-full flex-col gap-1 px-4 py-3 text-left text-[13px] sm:px-6",
                    )}
                  >
                    <span className="flex min-w-0 items-center gap-2">
                      <CaretRightIcon
                        className={cn(
                          "text-pw-ink-400 size-4 shrink-0 transition-transform",
                          here && "rotate-90",
                        )}
                      />
                      <span className="text-pw-ink truncate text-[14px] font-semibold">
                        {a.name}
                      </span>
                    </span>
                    <span className="text-pw-ink-600 pl-6 sm:pl-0">
                      <Mobile>Action optimization:</Mobile>
                      {a.primary ? "Primary" : "Secondary"}
                    </span>
                    <span className="text-pw-ink-600 pl-6 sm:pl-0">
                      <Mobile>Conversion source:</Mobile>
                      {a.source_label}
                    </span>
                    <span className="pl-6 sm:pl-0">
                      <StateChip state={a.state} />
                    </span>
                    <span className="text-pw-ink pl-6 tabular-nums sm:pl-0 sm:text-right">
                      <Mobile>All conv., last 30 days:</Mobile>
                      {conversions(a.recent)}
                    </span>
                  </button>
                  {here ? (
                    <EditAction
                      action={a}
                      options={summary.source_options ?? {}}
                      currency={summary.currency || "USD"}
                      mayChange={Boolean(summary.may_change)}
                      onClose={() => setOpen("")}
                      onSaved={(message) => {
                        setOpen("");
                        onSaved(message);
                      }}
                    />
                  ) : null}
                </li>
              );
            })}
          </ul>
        </div>
      ))}
    </Card>
  );
}

function EmptyCard({ mayChange }: { mayChange: boolean }) {
  return (
    <Card>
      <div className="flex flex-col gap-3 px-4 py-6 sm:px-8 sm:py-8">
        <h2 className="display text-[22px] leading-[28px] font-semibold">
          No conversion actions yet
        </h2>
        <p className="text-pw-ink-500 max-w-[680px] text-[16px] leading-[25px]">
          Google cannot bid for conversions until it can count them. A conversion action is how it
          counts: a purchase on your website, a lead form sent, a phone call. Set up the ones that
          matter to your business, and bidding has something to aim for.
        </p>
        {mayChange ? (
          <div className="pt-2">
            <LinkButton href="/conversions/new">Set up conversions</LinkButton>
          </div>
        ) : (
          <p className="text-pw-ink-500 text-[14px]">
            Ask someone who may approve changes on this account to set them up.
          </p>
        )}
      </div>
    </Card>
  );
}

function GoalsCard({
  goals,
  reason,
  mayChange,
}: {
  goals: ConversionGoal[] | null;
  reason: string;
  mayChange: boolean;
}) {
  const router = useRouter();
  // Only what this screen switched; everything else is the server's latest word.
  const [switched, setSwitched] = useState<Record<string, boolean>>({});
  const [busy, setBusy] = useState("");
  const [trouble, setTrouble] = useState("");
  const [notice, setNotice] = useState("");

  async function flip(g: ConversionGoal, next: boolean) {
    const k = goalKey(g);
    setSwitched((prev) => ({ ...prev, [k]: next }));
    setBusy(k);
    setTrouble("");
    setNotice("");
    const { ok, data } = await talk<Changed>("goal", {
      category: g.category,
      origin: g.origin,
      biddable: next,
    });
    setBusy("");
    const refused = ok ? (data.refused ?? []) : [];
    if (!ok || refused.length) {
      setSwitched((prev) => ({ ...prev, [k]: !next }));
      setTrouble(
        ok
          ? refused.map((r) => r.message).join(" ")
          : said(data, "Google could not be asked just now. Nothing changed."),
      );
      return;
    }
    const which = `${g.label}, ${g.origin_label ?? g.origin}`;
    setNotice(
      next
        ? `${which} is now an account default goal.`
        : `${which} is no longer an account default goal.`,
    );
    router.refresh();
  }

  const sorted = [...(goals ?? [])].sort(
    (x, y) => rank(x.category) - rank(y.category) || x.origin.localeCompare(y.origin),
  );

  return (
    <Card
      title="Goals"
      help="Every campaign bids for the account default goals unless it chooses its own."
    >
      {goals === null ? (
        <div className="px-4 py-5 sm:px-6">
          <Note tone="warn">
            PPCWay could not read this account&apos;s goals{reason ? `: ${reason}` : "."}
          </Note>
        </div>
      ) : !sorted.length ? (
        <p className="text-pw-ink-500 px-4 py-5 text-[14px] sm:px-6">
          No goals yet. Google makes a goal when the first conversion action of its kind exists.
        </p>
      ) : (
        <ul className="divide-pw-border divide-y">
          {sorted.map((g) => {
            const k = goalKey(g);
            const on = k in switched ? switched[k] : g.biddable;
            const counting = g.actions.some((a) => a.primary && a.status === "ENABLED");
            return (
              <li
                key={k}
                className="flex flex-col gap-3 px-4 py-4 sm:flex-row sm:items-start sm:justify-between sm:px-6"
              >
                <div className="min-w-0">
                  <p className="text-pw-ink text-[14px] font-semibold">
                    {g.label}
                    <span className="text-pw-ink-500 font-normal">
                      {" "}
                      · {g.origin_label ?? g.origin}
                    </span>
                  </p>
                  <p className="text-pw-ink-500 text-[12px] leading-[17px]">
                    {plural(g.actions.length, "action")}
                    {g.actions.length ? `: ${g.actions.map((a) => a.name).join(", ")}` : ""}
                  </p>
                  {on && !counting ? (
                    <p className="text-pw-warn-ink mt-1 text-[12px] leading-[17px]">
                      No primary action counts for this goal, so bidding has nothing to aim for
                      here.
                    </p>
                  ) : null}
                </div>
                <Toggle
                  on={on}
                  onChange={(next) => flip(g, next)}
                  disabled={!mayChange || busy === k}
                >
                  Account default
                </Toggle>
              </li>
            );
          })}
        </ul>
      )}
      {trouble || notice ? (
        <div className="px-4 pb-5 sm:px-6">
          {trouble ? <Note tone="bad">{trouble}</Note> : <Note tone="good">{notice}</Note>}
        </div>
      ) : null}
    </Card>
  );
}

function ImportCard({
  importable,
  mayChange,
  onDone,
}: {
  importable: Action[];
  mayChange: boolean;
  onDone: (message: string) => void;
}) {
  const router = useRouter();
  const [picked, setPicked] = useState<string[]>([]);
  const [busy, setBusy] = useState(false);
  const [trouble, setTrouble] = useState("");

  async function run() {
    setBusy(true);
    setTrouble("");
    const { ok, data } = await talk<Changed>("import", { resources: picked });
    setBusy(false);
    if (!ok) {
      setTrouble(said(data, "Google could not be asked just now. Nothing was imported."));
      return;
    }
    if (data.refused?.length) setTrouble(data.refused.map((r) => r.message).join(" "));
    if (data.changed?.length) {
      onDone(
        `Imported ${plural(data.changed.length, "conversion")}. Google counts them from now on.`,
      );
      setPicked([]);
      router.refresh();
    }
  }

  return (
    <Card
      title="Import conversions"
      help="Conversions Google lists from a linked Google Analytics property, Firebase or an app analytics partner. Importing lets Google Ads count them."
    >
      {importable.length ? (
        <div className="flex flex-col gap-4 px-4 py-5 sm:px-6">
          <ul className="border-pw-border divide-pw-border divide-y rounded-[12px] border">
            {importable.map((a) => (
              <li key={a.resource} className="px-4 py-3">
                <Tick
                  checked={picked.includes(a.resource)}
                  disabled={!mayChange}
                  onChange={(on) =>
                    setPicked((prev) =>
                      on ? [...prev, a.resource] : prev.filter((r) => r !== a.resource),
                    )
                  }
                  help={`${a.source_label} · ${a.category_label}`}
                >
                  {a.name}
                </Tick>
              </li>
            ))}
          </ul>
          {trouble ? <Note tone="bad">{trouble}</Note> : null}
          {mayChange ? (
            <div>
              <Button
                size="sm"
                onClick={run}
                disabled={!picked.length}
                working={busy ? "Importing…" : false}
              >
                Import
              </Button>
            </div>
          ) : (
            <p className="text-pw-ink-500 text-[13px]">
              Importing needs someone who may approve changes on this account.
            </p>
          )}
        </div>
      ) : (
        <p className="text-pw-ink-500 px-4 py-5 text-[14px] leading-[20px] sm:px-6">
          Nothing to import right now. When a Google Analytics property or a Firebase project is
          linked to this account, its key events show here.
        </p>
      )}
    </Card>
  );
}

export function ConversionsSummary({
  summary,
  goals,
  goalsReason,
}: {
  summary: Summary;
  goals: ConversionGoal[] | null;
  goalsReason: string;
}) {
  const [notice, setNotice] = useState("");
  const actions = summary.actions ?? [];
  const mayChange = Boolean(summary.may_change);
  const uploads = actions.some((a) => a.type === "UPLOAD_CLICKS" || a.type === "UPLOAD_CALLS");

  return (
    <div className="flex flex-col gap-4">
      {!mayChange ? (
        <Note tone="info">
          You can see conversions here. Changing them needs someone who may approve changes on this
          account.
        </Note>
      ) : null}
      {summary.read === false ? (
        <Note tone="warn">
          Google would not say how this account measures conversions
          {summary.reason ? `: ${summary.reason}` : "."}
        </Note>
      ) : summary.reason ? (
        <Note tone="warn">Google did not list every conversion action: {summary.reason}</Note>
      ) : null}
      {notice ? (
        <Note tone="good">
          <span aria-live="polite">{notice}</span>
        </Note>
      ) : null}

      <TagCard summary={summary} />

      {summary.read === false ? null : actions.length ? (
        <ActionsCard summary={summary} goals={goals} onSaved={setNotice} />
      ) : (
        <EmptyCard mayChange={mayChange} />
      )}

      {uploads && !summary.data_terms ? (
        <Note tone="info">
          To upload offline conversions with customer details such as emails, accept Google&apos;s
          customer data terms in Google Ads, under Goals, Settings.
        </Note>
      ) : null}

      <div className="grid items-start gap-4 lg:grid-cols-2">
        <GoalsCard goals={goals} reason={goalsReason} mayChange={mayChange} />
        <ImportCard
          importable={summary.importable ?? []}
          mayChange={mayChange}
          onDone={setNotice}
        />
      </div>
    </div>
  );
}
