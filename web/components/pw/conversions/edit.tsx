"use client";

import { useRouter } from "next/navigation";
import { useState, type ReactNode } from "react";
import { Labelled, money, Note } from "@/components/pw/create/kit";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/field";
import { ActionSettings, fromAction, settingsProblems } from "./settings";
import {
  DATA_DRIVEN,
  LAST_CLICK,
  SOURCE_OF_TYPE,
  kindOfType,
  said,
  talk,
  type Action,
  type Changed,
  type Settings,
  type SourceKey,
  type SourceOption,
} from "./types";

/*
  One conversion action's settings page, opened from its row in the summary,
  as Google's own: name, goal, action optimization, value, count, the
  windows, attribution, call length, and Remove. Only what changed is sent,
  so Google's update mask names nothing else.

  Imported actions and ones Google keeps to itself are shown, not changed,
  with the reason; so is everything for somebody who may not approve changes.
*/

type Options = Partial<Record<SourceKey, SourceOption>>;

/** The goals Google offers for this kind of action, always including its own. */
function categoriesFor(action: Action, options: Options): { id: string; label: string }[] {
  const all = new Map<string, string>();
  const own = options[SOURCE_OF_TYPE[action.type]]?.categories;
  if (own?.length) {
    for (const c of own) all.set(c.id, c.label);
  } else {
    for (const o of Object.values(options))
      for (const c of o?.categories ?? []) all.set(c.id, c.label);
  }
  if (!all.has(action.category)) all.set(action.category, action.category_label);
  return [...all].map(([id, label]) => ({ id, label }));
}

function attributionWords(model: string): string {
  if (model === DATA_DRIVEN) return "Data-driven";
  if (model === LAST_CLICK) return "Last click";
  if (!model) return "Not set";
  const words = model.replace(/^GOOGLE_(SEARCH_)?(ADS_)?(ATTRIBUTION_)?/, "").replace(/_/g, " ");
  return words.charAt(0) + words.slice(1).toLowerCase();
}

function Row({ term, children }: { term: string; children: ReactNode }) {
  return (
    <div className="flex min-w-0 flex-col gap-[2px]">
      <dt className="text-pw-ink-500 text-[12px] font-semibold">{term}</dt>
      <dd className="text-pw-ink text-[14px] leading-[20px]">{children}</dd>
    </div>
  );
}

export function EditAction({
  action,
  options,
  currency,
  mayChange,
  onClose,
  onSaved,
}: {
  action: Action;
  options: Options;
  currency: string;
  mayChange: boolean;
  onClose: () => void;
  onSaved: (message: string) => void;
}) {
  const router = useRouter();
  const kind = kindOfType(action.type);
  const start = fromAction(action);
  const actionCurrency = action.value.currency || currency;
  const [name, setName] = useState(action.name);
  const [category, setCategory] = useState(action.category);
  const [s, setS] = useState<Settings>(start);
  const [confirm, setConfirm] = useState(false);
  const [busy, setBusy] = useState<"" | "save" | "remove">("");
  const [trouble, setTrouble] = useState<string[]>([]);
  const canEdit = action.editable && mayChange;

  /** What changed, in the names the update endpoint takes. */
  function change(): { body: Record<string, unknown>; touched: Set<keyof Settings> } {
    const body: Record<string, unknown> = {};
    const touched = new Set<keyof Settings>();
    const trimmed = name.trim();
    if (trimmed !== action.name) body.name = trimmed;
    if (category !== action.category) body.category = category;
    if (s.primary !== start.primary) body.primary = s.primary;
    if (s.count !== start.count) body.count = s.count;
    if (s.click_days !== start.click_days) {
      body.click_days = s.click_days;
      touched.add("click_days");
    }
    if (kind.view && s.view_days !== start.view_days) {
      body.view_days = s.view_days;
      touched.add("view_days");
    }
    if (s.attribution && s.attribution !== start.attribution) body.attribution = s.attribution;
    if (kind.call && s.call_seconds !== start.call_seconds) {
      body.call_seconds = s.call_seconds;
      touched.add("call_seconds");
    }
    if (s.value !== start.value || s.amount !== start.amount) {
      body.value = { mode: s.value, amount: s.amount ?? 0 };
      touched.add("value");
    }
    return { body, touched };
  }

  async function send(body: Record<string, unknown>, done: string, which: "save" | "remove") {
    setBusy(which);
    setTrouble([]);
    const { ok, data } = await talk<Changed>("update", { resource: action.resource, change: body });
    setBusy("");
    if (!ok) {
      setTrouble([said(data, "Google could not be asked just now. Nothing changed.")]);
      return;
    }
    if (data.refused?.length) {
      setTrouble(data.refused.map((r) => r.message));
      return;
    }
    onSaved(done);
    router.refresh();
  }

  async function save() {
    const { body, touched } = change();
    const problems = [
      ...(name.trim() ? [] : ["Give the conversion action a name."]),
      ...settingsProblems(name.trim() || action.name, s, kind, touched),
    ];
    if (problems.length) {
      setTrouble(problems);
      return;
    }
    if (!Object.keys(body).length) {
      onClose();
      return;
    }
    await send(body, `Saved "${name.trim()}". Google has the change.`, "save");
  }

  if (!canEdit) {
    const why = !mayChange
      ? "Only someone who may approve changes on this account can change conversion actions."
      : action.imported
        ? `PPCWay does not change imported conversions. This one comes from ${action.source_label}: change it in Google Ads, or where it is measured in Google Analytics or Firebase.`
        : "Google does not let PPCWay change this conversion action. Open it in Google Ads to see all its settings.";
    const value =
      action.value.default === null
        ? "No value set"
        : action.value.always
          ? `${money(action.value.default, actionCurrency)} for each conversion`
          : `Different values, ${money(action.value.default, actionCurrency)} when none is sent`;
    return (
      <div className="border-pw-border bg-pw-ground flex flex-col gap-4 border-t px-4 py-5 sm:px-6">
        <Note tone="info">{why}</Note>
        <dl className="grid gap-x-6 gap-y-4 sm:grid-cols-2 lg:grid-cols-3">
          <Row term="Goal">{action.category_label}</Row>
          <Row term="Action optimization">
            {action.primary
              ? "Primary action used for bidding optimization"
              : "Secondary action used for observation only"}
          </Row>
          <Row term="Conversion source">{action.source_label}</Row>
          <Row term="Value">{value}</Row>
          <Row term="Count">
            {action.counting === "ONE_PER_CLICK"
              ? "One"
              : action.counting === "MANY_PER_CLICK"
                ? "Every"
                : "Not set"}
          </Row>
          <Row term="Click-through conversion window">
            {action.click_days ? `${action.click_days} days` : "Not set"}
          </Row>
          {kind.view ? (
            <Row term="View-through conversion window">
              {action.view_days ? `${action.view_days} days` : "Not set"}
            </Row>
          ) : null}
          <Row term="Attribution">{attributionWords(action.attribution)}</Row>
          {kind.call ? (
            <Row term="Call length">
              {action.call_seconds !== null ? `${action.call_seconds} seconds` : "Not set"}
            </Row>
          ) : null}
        </dl>
        <div>
          <Button variant="secondary" size="sm" onClick={onClose}>
            Close
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div className="border-pw-border bg-pw-ground flex flex-col gap-5 border-t px-4 py-5 sm:px-6">
      <div className="grid gap-4 sm:grid-cols-2">
        <Labelled label="Conversion action name">
          <Input
            value={name}
            maxLength={100}
            onChange={(e) => setName(e.target.value)}
            aria-label="Conversion action name"
          />
        </Labelled>
        <Labelled label="Goal" hint="The goal this action counts towards.">
          <select
            value={category}
            onChange={(e) => setCategory(e.target.value)}
            aria-label="Goal"
            className="border-pw-border-input text-pw-ink bg-pw-card focus:border-pw-blue h-[46px] w-full rounded-[12px] border px-4 text-[15px] outline-none"
          >
            {categoriesFor(action, options).map((c) => (
              <option key={c.id} value={c.id}>
                {c.label}
              </option>
            ))}
          </select>
        </Labelled>
      </div>

      <ActionSettings value={s} onChange={setS} kind={kind} currency={actionCurrency} />

      {!start.attribution && action.attribution ? (
        <p className="text-pw-ink-500 text-[13px]">
          Google says this action uses {attributionWords(action.attribution)} attribution, which
          PPCWay does not offer. It stays as it is unless you choose one above.
        </p>
      ) : null}

      {trouble.length ? (
        <Note tone="bad">
          <ul className="flex flex-col gap-1">
            {trouble.map((t, i) => (
              <li key={i}>{t}</li>
            ))}
          </ul>
        </Note>
      ) : null}

      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex flex-wrap gap-3">
          <Button size="sm" onClick={save} working={busy === "save" ? "Saving…" : false}>
            Save
          </Button>
          <Button variant="secondary" size="sm" onClick={onClose} disabled={Boolean(busy)}>
            Cancel
          </Button>
        </div>
        {!confirm ? (
          <button
            type="button"
            onClick={() => setConfirm(true)}
            className="text-pw-bad hover:bg-pw-bad-bg focus-visible:ring-brand-bar h-11 rounded-full px-5 text-[14px] font-semibold focus-visible:ring-4 focus-visible:outline-none sm:h-[38px]"
          >
            Remove
          </button>
        ) : null}
      </div>

      {confirm ? (
        <Note tone="warn">
          <p>
            Remove &quot;{action.name}&quot;? Google stops counting it, and a removed action cannot
            be switched back on. Its past conversions stay in your reports.
          </p>
          <div className="mt-3 flex flex-wrap gap-3">
            <Button
              variant="danger"
              size="sm"
              onClick={() =>
                send(
                  { status: "REMOVED" },
                  `Removed "${action.name}". Google no longer counts it.`,
                  "remove",
                )
              }
              working={busy === "remove" ? "Removing…" : false}
            >
              Remove
            </Button>
            <Button
              variant="secondary"
              size="sm"
              onClick={() => setConfirm(false)}
              disabled={Boolean(busy)}
            >
              Keep it
            </Button>
          </div>
        </Note>
      ) : null}
    </div>
  );
}
