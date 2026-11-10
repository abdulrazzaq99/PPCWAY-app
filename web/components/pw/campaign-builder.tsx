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

function Section({ title, hint, children }: { title: string; hint?: string; children: ReactNode }) {
  return (
    <PwCard className="p-5 sm:p-6">
      <h2 className="text-[17px] leading-[22px] font-semibold">{title}</h2>
      {hint ? <p className="text-pw-ink-500 mt-1 text-[14px] leading-[20px]">{hint}</p> : null}
      <div className="mt-4">{children}</div>
    </PwCard>
  );
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

export function DraftReview({ initial, mayLaunch }: { initial: Draft; mayLaunch: boolean }) {
  const router = useRouter();
  const [draft, setDraft] = useState<Draft>(initial);
  const [plan, setPlan] = useState<Plan>(initial.plan);
  const [dirty, setDirty] = useState(false);
  const [working, setWorking] = useState("");
  const [said, setSaid] = useState("");
  const [trouble, setTrouble] = useState("");
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

  return (
    <div className="flex flex-col gap-4">
      <div className="border-pw-border bg-pw-card divide-pw-border grid grid-cols-2 divide-x overflow-hidden rounded-[18px] border sm:grid-cols-4">
        {[
          [
            "Daily budget",
            `${plan.daily_budget.toLocaleString("en-GB", { maximumFractionDigits: 2 })} ${plan.currency}`,
          ],
          ["Search themes", String(plan.themes.length)],
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

      <div className="grid items-start gap-4 lg:grid-cols-[minmax(0,1fr)_340px]">
        <div className="flex flex-col gap-4">
          <Section title="In one sentence">
            <p className="text-[16px] leading-[24px]">{draft.sentence}</p>
            {plan.ai_written ? (
              <p className="text-pw-ink-400 mt-2 text-[12px] leading-[17px]">
                The ad text was drafted by Otto and checked by PPCWay&rsquo;s rules. The keywords
                come from Google&rsquo;s Keyword Planner.
              </p>
            ) : null}
          </Section>

          {plan.themes.map((theme, at) => (
            <Section
              key={theme.name}
              title={theme.name}
              hint={theme.short || `${theme.keywords.length} searches people really make`}
            >
              <div className="flex flex-col gap-5">
                <div>
                  <p className="text-[14px] leading-[18px] font-semibold">
                    What people search to find you
                  </p>
                  <ul className="mt-2 flex flex-wrap gap-2">
                    {theme.keywords.map((k) => {
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
                                ? "border-pw-border text-pw-ink-400 line-through"
                                : "border-pw-border-strong bg-pw-card",
                            )}
                            title={off ? "Put it back" : "Take it out"}
                          >
                            {k.text}{" "}
                            <span className="text-pw-ink-400">
                              · {k.monthly.toLocaleString("en-GB")}/mo
                            </span>
                          </button>
                        </li>
                      );
                    })}
                  </ul>
                </div>
                <AdPreview plan={plan} theme={theme} />
                {!launched ? (
                  <>
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
                  </>
                ) : null}
              </div>
            </Section>
          ))}
        </div>

        <div className="flex flex-col gap-4 lg:sticky lg:top-6">
          {!launched ? (
            <>
              <Section title="Budget and bidding">
                <div className="flex flex-col gap-4">
                  <Field label="The most it may spend a day">
                    {(id) => (
                      <Input
                        id={id}
                        inputMode="decimal"
                        value={String(plan.daily_budget)}
                        onChange={(e) => change({ daily_budget: Number(e.target.value) || 0 })}
                        trailing={
                          <span className="text-pw-ink-500 text-[14px]">{plan.currency}</span>
                        }
                      />
                    )}
                  </Field>
                  <Bidding
                    narrow
                    value={plan.bidding}
                    onChange={(bidding) => change({ bidding })}
                  />
                </div>
              </Section>
              <Section title="Searches we'll never pay for">
                <Words
                  label="Excluded words"
                  words={plan.negatives}
                  onChange={(negatives) => change({ negatives })}
                  placeholder="jobs, diy…"
                />
              </Section>
            </>
          ) : null}

          <PwCard className="p-5 sm:p-6">
            <h2 className="text-[17px] leading-[22px] font-semibold">
              {launched ? "It's live" : "Launch it"}
            </h2>
            {launched ? (
              <>
                <p className="text-pw-ink-700 mt-2 text-[14px] leading-[20px]">
                  {said || "This campaign is live in Google Ads."}
                </p>
                <Link href="/campaigns" className="text-brand mt-3 inline-block font-semibold">
                  See it on Campaigns
                </Link>
              </>
            ) : (
              <>
                <Checkbox
                  className="mt-3"
                  checked={plan.not_political}
                  onChange={(not_political) => change({ not_political })}
                >
                  This campaign is not political advertising in the European Union. Google asks
                  every advertiser to say so.
                </Checkbox>
                {draft.missing.length ? (
                  <ul className="mt-3 flex list-disc flex-col gap-1 pl-5 text-[13px] leading-[18px] text-amber-900">
                    {draft.missing.map((one) => (
                      <li key={one}>{one}</li>
                    ))}
                  </ul>
                ) : null}
                {said ? (
                  <p className="text-pw-ink-700 mt-3 text-[14px] leading-[19px]">{said}</p>
                ) : null}
                {trouble ? (
                  <p
                    role="alert"
                    className="mt-3 text-[14px] leading-[19px] font-semibold text-red-700"
                  >
                    {trouble}
                  </p>
                ) : null}
                <div className="mt-4 flex flex-col gap-2">
                  <Button variant="secondary" onClick={save} disabled={!dirty || Boolean(working)}>
                    {working === "save" ? "Checking and saving…" : "Save changes"}
                  </Button>
                  <Button
                    onClick={launch}
                    disabled={dirty || draft.missing.length > 0 || !mayLaunch || Boolean(working)}
                  >
                    {working === "launch" ? "Google is checking it…" : "Launch campaign"}
                  </Button>
                </div>
                <p className="text-pw-ink-400 mt-2 text-[12px] leading-[17px]">
                  {!mayLaunch
                    ? "Only an owner or admin of the business can launch it."
                    : dirty
                      ? "Save your changes first; they are checked before anything is launched."
                      : "Google checks the whole campaign first. If it refuses anything, nothing is created."}
                </p>
              </>
            )}
          </PwCard>
        </div>
      </div>
    </div>
  );
}
