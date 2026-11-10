"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useMemo, useState, type ReactNode } from "react";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Field, Input } from "@/components/ui/field";
import { PwCard } from "@/components/pw/shell";
import {
  DESCRIPTION_CHARS,
  HEADLINE_CHARS,
  type Draft,
  type Place,
  type Plan,
} from "@/lib/builder";
import { cn } from "@/lib/cn";

/*
  The campaign builder: "Start a new campaign" (Figma 87:10926) and "Here's
  the campaign we built for you" (17:2048).

  The form asks for what the campaign is about, where and in which language
  it shows, what it may spend, and what the ads may honestly say. Writing it
  asks Google's Keyword Planner what people actually type and has Otto draft
  the ads, which PPCWay's rules then check. Nothing reaches Google until the
  merchant reads the result and presses Launch, and the launch is checked by
  Google before anything is created.
*/

export const ENGLISH: Place = { resource: "languageConstants/1000", name: "English" };

export async function call<T>(path: string, body?: unknown): Promise<{ ok: boolean; data: T }> {
  const res = await fetch(`/api/campaigns/${path}`, {
    method: body === undefined ? "GET" : "POST",
    headers: body === undefined ? undefined : { "content-type": "application/json" },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  const data = (await res.json().catch(() => ({}))) as T;
  return { ok: res.ok, data };
}

function Tag({ children, onRemove }: { children: ReactNode; onRemove?: () => void }) {
  return (
    <span className="bg-pw-blue-tint text-pw-blue-ink inline-flex items-center gap-2 rounded-full py-[5px] pr-2 pl-3 text-[13px] font-semibold">
      {children}
      {onRemove ? (
        <button
          type="button"
          onClick={onRemove}
          aria-label="Remove"
          className="hover:bg-pw-card rounded-full px-[6px] leading-[18px]"
        >
          ×
        </button>
      ) : null}
    </span>
  );
}

/* Words typed one at a time: services, or searches never to pay for. */
export function Words({
  label,
  hint,
  words,
  onChange,
  most,
  placeholder,
}: {
  label: string;
  hint?: string;
  words: string[];
  onChange: (next: string[]) => void;
  most?: number;
  placeholder: string;
}) {
  const [typed, setTyped] = useState("");
  const full = most !== undefined && words.length >= most;
  const add = () => {
    const word = typed.trim();
    if (!word || full) return;
    if (!words.some((w) => w.toLowerCase() === word.toLowerCase())) onChange([...words, word]);
    setTyped("");
  };
  return (
    <Field label={label} hint={hint}>
      {(id) => (
        <div className="flex flex-col gap-3">
          <div className="flex gap-2">
            <Input
              id={id}
              value={typed}
              disabled={full}
              placeholder={full ? `That is the most a campaign takes` : placeholder}
              onChange={(e) => setTyped(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter") {
                  e.preventDefault();
                  add();
                }
              }}
              className="flex-1"
            />
            <Button
              type="button"
              variant="secondary"
              onClick={add}
              disabled={!typed.trim() || full}
            >
              Add
            </Button>
          </div>
          {words.length ? (
            <div className="flex flex-wrap gap-2">
              {words.map((word) => (
                <Tag key={word} onRemove={() => onChange(words.filter((w) => w !== word))}>
                  {word}
                </Tag>
              ))}
            </div>
          ) : null}
        </div>
      )}
    </Field>
  );
}

/* Places, looked up by name in Google's own list of places it can target. */
export function PlacePicker({
  places,
  onChange,
}: {
  places: Place[];
  onChange: (next: Place[]) => void;
}) {
  const [typed, setTyped] = useState("");
  const [found, setFound] = useState<Place[]>([]);
  const [looking, setLooking] = useState(false);

  useEffect(() => {
    const q = typed.trim();
    if (q.length < 2) return;
    let live = true;
    const timer = setTimeout(async () => {
      setLooking(true);
      const { ok, data } = await call<{ places?: Place[] }>(`places?q=${encodeURIComponent(q)}`);
      if (live) {
        setFound(ok ? (data.places ?? []) : []);
        setLooking(false);
      }
    }, 300);
    return () => {
      live = false;
      clearTimeout(timer);
    };
  }, [typed]);

  // Under two letters is not a search; what was found for an earlier word is
  // hidden rather than cleared, so nothing is reset inside the effect.
  const shown = typed.trim().length >= 2 ? found : [];

  return (
    <Field
      label="Where should the ads show?"
      hint="Countries, regions or cities, as Google knows them."
    >
      {(id) => (
        <div className="flex flex-col gap-3">
          <Input
            id={id}
            value={typed}
            placeholder="Start typing a place: Poland, Ontario, Toronto…"
            onChange={(e) => setTyped(e.target.value)}
            trailing={
              looking ? <span className="text-pw-ink-400 text-[13px]">Looking…</span> : null
            }
          />
          {shown.length ? (
            <ul className="border-pw-border divide-pw-border divide-y rounded-[12px] border">
              {shown.map((one) => (
                <li key={one.resource}>
                  <button
                    type="button"
                    className="hover:bg-pw-muted flex w-full items-center justify-between gap-3 px-4 py-[10px] text-left text-[14px]"
                    onClick={() => {
                      if (!places.some((p) => p.resource === one.resource)) {
                        onChange([...places, one]);
                      }
                      setTyped("");
                      setFound([]);
                    }}
                  >
                    <span>{one.name}</span>
                    <span className="text-pw-ink-400 text-[12px]">{one.kind}</span>
                  </button>
                </li>
              ))}
            </ul>
          ) : null}
          {places.length ? (
            <div className="flex flex-wrap gap-2">
              {places.map((one) => (
                <Tag
                  key={one.resource}
                  onRemove={() => onChange(places.filter((p) => p.resource !== one.resource))}
                >
                  {one.name}
                </Tag>
              ))}
            </div>
          ) : null}
        </div>
      )}
    </Field>
  );
}

function Choice({
  selected,
  title,
  meta,
  onSelect,
}: {
  selected: boolean;
  title: string;
  meta: string;
  onSelect: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onSelect}
      aria-pressed={selected}
      className={cn(
        "rounded-[14px] border p-4 text-left transition-colors",
        selected ? "border-brand bg-pw-blue-tint" : "border-pw-border hover:bg-pw-muted",
      )}
    >
      <p className="text-[15px] leading-[20px] font-semibold">{title}</p>
      <p className="text-pw-ink-500 mt-1 text-[13px] leading-[18px]">{meta}</p>
    </button>
  );
}

function Bidding({
  value,
  onChange,
  narrow = false,
}: {
  value: string;
  onChange: (next: "clicks" | "leads") => void;
  /* In the review's narrow column the two choices stack. */
  narrow?: boolean;
}) {
  return (
    <div className={cn("grid gap-3", narrow ? "" : "sm:grid-cols-2")}>
      <Choice
        selected={value === "clicks"}
        title="Get the most clicks"
        meta="The safe start for a new campaign. Google needs no history to do it."
        onSelect={() => onChange("clicks")}
      />
      <Choice
        selected={value === "leads"}
        title="Get the most leads"
        meta="Better once your calls and forms are counted properly in Google Ads."
        onSelect={() => onChange("leads")}
      />
    </div>
  );
}

/* ---------- 17:2048: the campaign we built for you ---------- */

function Lines({
  label,
  lines,
  most,
  limit,
  onChange,
}: {
  label: string;
  lines: string[];
  most: number;
  limit: number;
  onChange: (next: string[]) => void;
}) {
  return (
    <div>
      <p className="text-[14px] leading-[18px] font-semibold">
        {label}{" "}
        <span className="text-pw-ink-400 font-normal">
          · {lines.length} of {most}
        </span>
      </p>
      <ul className="mt-2 flex flex-col gap-2">
        {lines.map((line, at) => (
          <li key={at} className="flex items-center gap-2">
            <Input
              aria-label={`${label} ${at + 1}`}
              value={line}
              invalid={line.length > limit}
              onChange={(e) => onChange(lines.map((l, n) => (n === at ? e.target.value : l)))}
              trailing={
                <span
                  className={cn(
                    "text-[12px]",
                    line.length > limit ? "text-red-700" : "text-pw-ink-400",
                  )}
                >
                  {line.length}/{limit}
                </span>
              }
              className="flex-1"
            />
            <button
              type="button"
              aria-label={`Remove ${label.toLowerCase()} ${at + 1}`}
              onClick={() => onChange(lines.filter((_, n) => n !== at))}
              className="text-pw-ink-400 hover:text-pw-ink-700 px-2 text-[18px]"
            >
              ×
            </button>
          </li>
        ))}
      </ul>
      {lines.length < most ? (
        <button
          type="button"
          onClick={() => onChange([...lines, ""])}
          className="text-brand mt-2 text-[14px] font-semibold"
        >
          Add one
        </button>
      ) : null}
    </div>
  );
}

function AdPreview({ plan, theme }: { plan: Plan; theme: Plan["themes"][number] }) {
  const host = useMemo(() => {
    try {
      return new URL(plan.final_url).host.replace(/^www\./, "");
    } catch {
      return plan.final_url;
    }
  }, [plan.final_url]);
  return (
    <div className="border-pw-border rounded-[14px] border p-4">
      <p className="text-pw-ink-500 text-[12px] leading-[16px]">
        <span className="font-bold">Sponsored</span> · {host}
      </p>
      <p className="text-brand mt-1 text-[17px] leading-[22px] font-semibold">
        {theme.headlines.slice(0, 3).filter(Boolean).join(" | ") || "No headlines yet"}
      </p>
      <p className="text-pw-ink-700 mt-1 text-[14px] leading-[20px]">
        {theme.descriptions[0] || "No description yet"}
      </p>
    </div>
  );
}

type Tab = "ads" | "searches" | "settings";

/*
  Here's the campaign we built for you.

  It used to be one long column: every search, all fifteen headlines and four
  descriptions as boxes to type in, for each service in turn, and the budget,
  exclusions and Launch at the very bottom. On 10 November the owner had to
  scroll the whole way down to see it, or to launch it.

  So it reads in three tabs, one service at a time, with the ad text shown as
  text until somebody asks to edit it, and a bar along the bottom of the
  screen that always says whether it is ready and holds Save and Launch.
*/
export function DraftReview({ initial, mayLaunch }: { initial: Draft; mayLaunch: boolean }) {
  const router = useRouter();
  const [draft, setDraft] = useState<Draft>(initial);
  const [plan, setPlan] = useState<Plan>(initial.plan);
  const [dirty, setDirty] = useState(false);
  const [working, setWorking] = useState("");
  const [said, setSaid] = useState("");
  const [trouble, setTrouble] = useState("");
  const [tab, setTab] = useState<Tab>("ads");
  const [themeAt, setThemeAt] = useState(0);
  const [editing, setEditing] = useState(false);
  const [allSearches, setAllSearches] = useState(false);
  const launched = draft.status === "launched";

  const change = (next: Partial<Plan>) => {
    setPlan((was) => ({ ...was, ...next }));
    setDirty(true);
  };
  const changeTheme = (at: number, next: Partial<Plan["themes"][number]>) => {
    setPlan((was) => ({
      ...was,
      themes: was.themes.map((t, n) => (n === at ? { ...t, ...next } : t)),
    }));
    setDirty(true);
  };
  const [removed, setRemoved] = useState<Record<string, boolean>>({});

  const save = async () => {
    setWorking("save");
    setTrouble("");
    setSaid("");
    const { ok, data } = await call<Draft & { error?: string }>(`drafts/${draft.id}`, {
      name: plan.name,
      daily_budget: plan.daily_budget,
      final_url: plan.final_url,
      bidding: plan.bidding,
      negatives: plan.negatives,
      not_political: plan.not_political,
      themes: plan.themes.map((t, at) => ({
        keywords: t.keywords.filter((k) => !removed[`${at}:${k.text}`]).map((k) => k.text),
        headlines: t.headlines,
        descriptions: t.descriptions,
      })),
    });
    setWorking("");
    if (!ok) {
      setTrouble(data.error ?? "That did not work.");
      return;
    }
    setDraft(data);
    setPlan(data.plan);
    setRemoved({});
    setDirty(false);
    setEditing(false);
    const refused = data.refused ?? [];
    setSaid(
      refused.length
        ? `Saved. ${refused.length} line${refused.length === 1 ? " was" : "s were"} taken out: ${refused
            .map((r) => `"${r.text}" (${r.because})`)
            .join("; ")}`
        : "Saved.",
    );
  };

  const launch = async () => {
    setWorking("launch");
    setTrouble("");
    setSaid("");
    const { ok, data } = await call<Draft & { live?: boolean; words?: string; error?: string }>(
      `drafts/${draft.id}/launch`,
      {},
    );
    setWorking("");
    if (!ok) {
      setTrouble(data.error ?? "That did not work.");
      return;
    }
    setDraft(data);
    setPlan(data.plan);
    if (data.live) {
      setSaid(data.words ?? "Live.");
      router.refresh();
    } else {
      setTrouble(data.words ?? "Nothing was created.");
    }
  };

  const ads = plan.themes.filter(
    (t) => t.headlines.length >= 3 && t.descriptions.length >= 2,
  ).length;
  const at = Math.min(themeAt, Math.max(0, plan.themes.length - 1));
  const theme = plan.themes[at];
  const searches = theme ? [...theme.keywords].sort((a, b) => b.monthly - a.monthly) : [];
  const shownSearches = allSearches ? searches : searches.slice(0, 12);
  const kept = searches.filter((k) => !removed[`${at}:${k.text}`]).length;

  const tabs: { id: Tab; label: string; meta: string }[] = [
    {
      id: "ads",
      label: "The ads",
      meta: theme
        ? `${theme.headlines.length} headlines, ${theme.descriptions.length} descriptions`
        : "",
    },
    {
      id: "searches",
      label: "The searches",
      meta: theme ? `${kept} of ${searches.length} kept` : "",
    },
    {
      id: "settings",
      label: "Budget and settings",
      meta: `${plan.daily_budget.toLocaleString("en-GB", { maximumFractionDigits: 2 })} ${plan.currency} a day`,
    },
  ];

  return (
    <div className="flex flex-col gap-4">
      <div className="border-pw-border bg-pw-card divide-pw-border grid grid-cols-2 divide-x overflow-hidden rounded-[18px] border sm:grid-cols-4">
        {[
          [
            "Daily budget",
            `${plan.daily_budget.toLocaleString("en-GB", { maximumFractionDigits: 2 })} ${plan.currency}`,
          ],
          ["Services", String(plan.themes.length)],
          ["Ads written", String(ads)],
          [
            "Ready to launch",
            launched ? "Live" : draft.missing.length ? `${draft.missing.length} to fix` : "Yes",
          ],
        ].map(([label, value]) => (
          <div key={label} className="p-4 sm:p-5">
            <p className="text-pw-ink-500 text-[13px] leading-[17px]">{label}</p>
            <p className="pw-num mt-1 text-[22px] leading-[28px] font-semibold">{value}</p>
          </div>
        ))}
      </div>

      <PwCard className="p-5 sm:p-6">
        <p className="text-[16px] leading-[24px]">{draft.sentence}</p>
        {plan.ai_written ? (
          <p className="text-pw-ink-500 mt-2 text-[12px] leading-[17px]">
            The ad text was drafted by Otto and checked by PPCWay&rsquo;s rules. The searches come
            from Google&rsquo;s Keyword Planner.
          </p>
        ) : null}
      </PwCard>

      <PwCard className="overflow-hidden">
        {plan.themes.length > 1 ? (
          <div className="border-pw-divider flex flex-wrap items-center gap-2 border-b px-5 pt-4 pb-3 sm:px-6">
            <span className="text-pw-ink-500 mr-1 text-[13px]">Service</span>
            {plan.themes.map((t, n) => (
              <button
                key={t.name}
                type="button"
                aria-pressed={n === at}
                onClick={() => setThemeAt(n)}
                className={cn(
                  "rounded-full border px-3 py-[6px] text-[14px] font-semibold transition-colors",
                  n === at
                    ? "border-pw-blue bg-pw-blue-tint text-pw-blue-ink"
                    : "border-pw-border text-pw-ink-700 hover:bg-pw-muted",
                )}
              >
                {t.name}
              </button>
            ))}
          </div>
        ) : null}

        <div
          role="tablist"
          aria-label="Parts of the campaign"
          className="border-pw-divider flex gap-6 overflow-x-auto border-b px-5 sm:px-6"
        >
          {tabs.map((one) => (
            <button
              key={one.id}
              type="button"
              role="tab"
              aria-selected={tab === one.id}
              onClick={() => setTab(one.id)}
              className={cn(
                "-mb-px flex flex-col items-start border-b-2 pt-4 pb-3 text-left whitespace-nowrap",
                tab === one.id
                  ? "border-pw-blue text-pw-ink"
                  : "text-pw-ink-500 hover:text-pw-ink border-transparent",
              )}
            >
              <span className="text-[15px] leading-[20px] font-semibold">{one.label}</span>
              <span className="text-pw-ink-500 text-[12px] leading-[16px]">{one.meta}</span>
            </button>
          ))}
        </div>

        <div role="tabpanel" className="p-5 sm:p-6">
          {tab === "ads" && theme ? (
            <div className="flex flex-col gap-6">
              {theme.short ? (
                <p className="text-[14px] leading-[20px] text-amber-900">{theme.short}</p>
              ) : null}
              <AdPreview plan={plan} theme={theme} />
              {editing && !launched ? (
                <div className="grid gap-6 lg:grid-cols-2">
                  <Lines
                    label="Headlines"
                    lines={theme.headlines}
                    most={15}
                    limit={HEADLINE_CHARS}
                    onChange={(headlines) => changeTheme(at, { headlines })}
                  />
                  <Lines
                    label="Descriptions"
                    lines={theme.descriptions}
                    most={4}
                    limit={DESCRIPTION_CHARS}
                    onChange={(descriptions) => changeTheme(at, { descriptions })}
                  />
                </div>
              ) : (
                <div className="flex flex-col gap-5">
                  <ReadLines
                    label="Headlines"
                    lines={theme.headlines}
                    limit={HEADLINE_CHARS}
                    columns
                  />
                  <ReadLines
                    label="Descriptions"
                    lines={theme.descriptions}
                    limit={DESCRIPTION_CHARS}
                  />
                </div>
              )}
              {!launched ? (
                <div>
                  <Button variant="secondary" onClick={() => setEditing((e) => !e)}>
                    {editing ? "Done editing" : "Edit ad text"}
                  </Button>
                </div>
              ) : null}
            </div>
          ) : null}

          {tab === "searches" && theme ? (
            <div>
              <p className="text-pw-ink-700 text-[14px] leading-[20px]">
                What people type into Google, with how often a month. Click one to take it out;
                click again to put it back.
              </p>
              <ul className="mt-4 flex flex-wrap gap-2">
                {shownSearches.map((k) => {
                  const key = `${at}:${k.text}`;
                  const off = removed[key];
                  return (
                    <li key={key}>
                      <button
                        type="button"
                        disabled={launched}
                        onClick={() => {
                          setRemoved((was) => ({ ...was, [key]: !was[key] }));
                          setDirty(true);
                        }}
                        className={cn(
                          "rounded-full border px-3 py-[5px] text-[13px]",
                          off
                            ? "border-pw-border text-pw-ink-500 line-through"
                            : "border-pw-border-strong bg-pw-card",
                        )}
                        title={off ? "Put it back" : "Take it out"}
                      >
                        {k.text}{" "}
                        <span className="text-pw-ink-500">
                          · {k.monthly.toLocaleString("en-GB")}/mo
                        </span>
                      </button>
                    </li>
                  );
                })}
              </ul>
              {searches.length > 12 ? (
                <button
                  type="button"
                  onClick={() => setAllSearches((v) => !v)}
                  className="text-brand mt-3 text-[14px] font-semibold"
                >
                  {allSearches ? "Show the top 12" : `Show all ${searches.length}`}
                </button>
              ) : null}
            </div>
          ) : null}

          {tab === "settings" ? (
            <div className="grid gap-8 lg:grid-cols-2">
              <div className="flex flex-col gap-4">
                <Field label="The most it may spend a day">
                  {(id) => (
                    <Input
                      id={id}
                      inputMode="decimal"
                      disabled={launched}
                      value={String(plan.daily_budget)}
                      onChange={(e) => change({ daily_budget: Number(e.target.value) || 0 })}
                      trailing={
                        <span className="text-pw-ink-500 text-[14px]">{plan.currency}</span>
                      }
                      className="max-w-[240px]"
                    />
                  )}
                </Field>
                <Bidding value={plan.bidding} onChange={(bidding) => change({ bidding })} narrow />
              </div>
              <Words
                label="Searches we'll never pay for"
                hint="Your ads will not show for searches containing these."
                words={plan.negatives}
                onChange={(negatives) => change({ negatives })}
                placeholder="jobs, diy…"
              />
            </div>
          ) : null}
        </div>
      </PwCard>

      <LaunchBar
        launched={launched}
        said={said}
        trouble={trouble}
        missing={draft.missing}
        notPolitical={plan.not_political}
        onNotPolitical={(not_political) => change({ not_political })}
        dirty={dirty}
        working={working}
        mayLaunch={mayLaunch}
        onSave={save}
        onLaunch={launch}
      />
    </div>
  );
}

/* Ad text as text: what a merchant reads before deciding to edit any of it. */
function ReadLines({
  label,
  lines,
  limit,
  columns = false,
}: {
  label: string;
  lines: string[];
  limit: number;
  columns?: boolean;
}) {
  return (
    <div>
      <p className="text-[14px] leading-[18px] font-semibold">
        {label} <span className="text-pw-ink-500 font-normal">({lines.length})</span>
      </p>
      <ul
        className={cn("mt-2 grid gap-x-6 gap-y-[6px]", columns && "sm:grid-cols-2 lg:grid-cols-3")}
      >
        {lines.map((line, n) => (
          <li
            key={`${n}-${line}`}
            className="border-pw-divider flex items-baseline justify-between gap-3 border-b py-[6px] text-[14px] leading-[20px]"
          >
            <span className="min-w-0">{line}</span>
            <span
              className={cn(
                "pw-num shrink-0 text-[12px]",
                line.length > limit ? "text-red-700" : "text-pw-ink-500",
              )}
            >
              {line.length}/{limit}
            </span>
          </li>
        ))}
      </ul>
    </div>
  );
}

/*
  Always on screen, along the bottom: whether it is ready, the one thing
  Google asks every advertiser to confirm, and Save and Launch. Nobody has to
  scroll to find out what is stopping a launch, or to press it.
*/
function LaunchBar({
  launched,
  said,
  trouble,
  missing,
  notPolitical,
  onNotPolitical,
  dirty,
  working,
  mayLaunch,
  onSave,
  onLaunch,
}: {
  launched: boolean;
  said: string;
  trouble: string;
  missing: string[];
  notPolitical: boolean;
  onNotPolitical: (value: boolean) => void;
  dirty: boolean;
  working: string;
  mayLaunch: boolean;
  onSave: () => void;
  onLaunch: () => void;
}) {
  const others = missing.filter((one) => !/political/i.test(one));
  const status = launched
    ? said || "This campaign is live in Google Ads."
    : trouble
      ? trouble
      : said
        ? said
        : dirty
          ? "You have changes. Save them and they are checked before anything is launched."
          : !mayLaunch
            ? "Only an owner or admin of the business can launch it."
            : missing.length
              ? (others[0] ?? "Confirm the box on the left to launch.")
              : "Ready. Google checks the whole campaign first; if it refuses anything, nothing is created.";
  return (
    <div className="border-pw-border bg-pw-card sticky bottom-0 z-10 -mx-5 border-t px-5 py-3 sm:-mx-8 sm:px-8">
      <div className="flex flex-wrap items-center justify-between gap-x-6 gap-y-3">
        <div className="flex min-w-0 flex-1 flex-wrap items-center gap-x-6 gap-y-2">
          {!launched ? (
            <Checkbox checked={notPolitical} onChange={onNotPolitical}>
              Not political advertising in the EU
            </Checkbox>
          ) : null}
          <p
            role={trouble ? "alert" : undefined}
            aria-live="polite"
            className={cn(
              "min-w-0 text-[14px] leading-[20px]",
              trouble ? "font-semibold text-red-700" : "text-pw-ink-700",
            )}
          >
            {status}
          </p>
        </div>
        {launched ? (
          <Link href="/campaigns" className="text-brand font-semibold">
            See it on Campaigns
          </Link>
        ) : (
          <div className="flex shrink-0 flex-wrap gap-2">
            <Button
              variant="secondary"
              onClick={onSave}
              disabled={!dirty || Boolean(working)}
              className="disabled:bg-pw-muted! disabled:text-pw-ink-500!"
            >
              {working === "save" ? "Checking and saving…" : "Save changes"}
            </Button>
            <Button
              onClick={onLaunch}
              disabled={dirty || missing.length > 0 || !mayLaunch || Boolean(working)}
              className="disabled:bg-pw-muted! disabled:text-pw-ink-500!"
            >
              {working === "launch" ? "Google is checking it…" : "Launch campaign"}
            </Button>
          </div>
        )}
      </div>
    </div>
  );
}
