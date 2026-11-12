"use client";

import {
  CheckCircleIcon,
  CheckIcon,
  DatabaseIcon,
  DeviceMobileIcon,
  GlobeIcon,
  PhoneIcon,
  WarningCircleIcon,
  XIcon,
  type Icon,
} from "@phosphor-icons/react";
import { useRouter } from "next/navigation";
import { useState, type ReactNode } from "react";
import { Card, Labelled, Note, Panel, Problems, Tick } from "@/components/pw/create/kit";
import { Button, LinkButton } from "@/components/ui/button";
import { Input } from "@/components/ui/field";
import { cn } from "@/lib/cn";
import type { Problem } from "@/lib/creation";
import { ActionSettings, defaultsFor, settingsLine, settingsProblems } from "./settings";
import { TagCheck, TagSetup } from "./tag";
import {
  asAddress,
  domainOf,
  kindOfSource,
  said,
  talk,
  type Action,
  type Changed,
  type Created,
  type NewAction,
  type Settings,
  type SourceKey,
  type SourceOption,
  type Summary,
  type Tag,
} from "./types";

/*
  Google's Conversions setup (ads.google.com/aw/conversions/setup), on its own
  three steps:

  1. Get started: choose the data sources where customers act. A website (with
     its domain and whether the Google tag is there), an app, phone calls (from
     ads, from website visits, via uploads) and offline.
  2. Create conversion actions: for each source, Google's goal categories as
     ticks. Each tick becomes an action with a name and Google's settings, and
     everything is sent to Google in one request.
  3. Summary: what Google created and refused, then the Google tag to install
     and a check that it is there.

  The API keeps no "data source": a source is the kind of action measuring it.
  So step 1 only decides what step 2 offers; nothing is sent until step 2.
*/

type Data = "website" | "app" | "calls" | "offline";
type CallKey = "calls_from_ads" | "calls_from_website" | "call_uploads";

type Draft = {
  key: string;
  source: SourceKey;
  category: string;
  name: string;
  settings: Settings;
};

type Outcome = { made: Created | null; imported: Changed | null; importTrouble: string };

const DATA: { id: Data; title: string; help: string; icon: Icon }[] = [
  {
    id: "website",
    title: "Conversions on a website",
    help: "For any web conversions that'll be measured with a Google tag or imported from Google Analytics",
    icon: GlobeIcon,
  },
  {
    id: "app",
    title: "Conversions on an app",
    help: "Measure app engagement, Google Play downloads, and in-app purchases. Import events from Google Analytics or third-party analytics.",
    icon: DeviceMobileIcon,
  },
  {
    id: "calls",
    title: "Conversions from phone calls",
    help: "For phone call conversions from ads, website visits, or uploads",
    icon: PhoneIcon,
  },
  {
    id: "offline",
    title: "Conversions offline",
    help: "Conversions outside of the internet, measured by connecting data in a CRM, importing a file, or with the Google Ads API",
    icon: DatabaseIcon,
  },
];

const CALL_WAYS: { id: CallKey; label: string; help: string }[] = [
  {
    id: "calls_from_ads",
    label: "Calls from ads",
    help: "Calls to the number in your ads, through a Google forwarding number.",
  },
  {
    id: "calls_from_website",
    label: "Calls from website visits",
    help: "Calls to the number on your site from people who clicked your ad. Needs the Google tag and a short snippet.",
  },
  {
    id: "call_uploads",
    label: "Calls via uploads",
    help: "Calls you track yourself and upload afterwards, with the click ID.",
  },
];

const STEPS = ["Get started", "Create conversion actions", "Summary"] as const;

/** Imports belong under the website or the app, by where Google says they come from. */
const importGroup = (a: Action): Data => (a.source === "app" ? "app" : "website");

/** The name Google's screen would suggest for a new action. */
function baseName(source: SourceKey, category: string, label: string, option?: SourceOption) {
  if (source === "website") return category === "DEFAULT" ? "Website conversion" : label;
  if (source === "offline") {
    return category === "DEFAULT" ? "Offline conversion" : `Offline ${label.toLowerCase()}`;
  }
  if (source === "app_download") return "Google Play installs";
  if (source === "app_purchase") return "In-app purchases";
  return option?.label ?? label;
}

/** Google needs every name to be different, so a taken one gets a number. */
function freeName(base: string, used: Set<string>): string {
  if (!used.has(base.toLowerCase())) return base;
  for (let n = 2; ; n += 1) {
    const next = `${base} (${n})`;
    if (!used.has(next.toLowerCase())) return next;
  }
}

function scrollTop() {
  window.scrollTo({ top: 0, behavior: "smooth" });
}

function Stepper({ at, onGo }: { at: 1 | 2 | 3; onGo: (n: 1 | 2) => void }) {
  return (
    <nav aria-label="Setup steps">
      <ol className="flex items-center gap-2 sm:gap-3">
        {STEPS.map((label, i) => {
          const n = (i + 1) as 1 | 2 | 3;
          const done = n < at;
          const current = n === at;
          // Once Google has created the actions there is no going back to change them here.
          const can = done && at !== 3;
          const inner = (
            <>
              <span
                className={cn(
                  "flex size-7 shrink-0 items-center justify-center rounded-full text-[13px] font-bold",
                  done || current
                    ? "bg-pw-blue text-white"
                    : "border-pw-border-strong text-pw-ink-400 border",
                )}
              >
                {done ? <CheckIcon weight="bold" className="size-4" /> : n}
              </span>
              <span
                className={cn(
                  "text-[14px] leading-[20px] whitespace-nowrap",
                  current ? "text-pw-ink font-semibold" : "text-pw-ink-500 hidden sm:inline",
                )}
              >
                {label}
              </span>
            </>
          );
          return (
            <li key={label} className={cn("flex items-center gap-2 sm:gap-3", i < 2 && "flex-1")}>
              {can ? (
                <button
                  type="button"
                  onClick={() => onGo(n as 1 | 2)}
                  className="hover:bg-pw-muted flex items-center gap-2 rounded-full pr-2"
                >
                  {inner}
                </button>
              ) : (
                <span
                  aria-current={current ? "step" : undefined}
                  className="flex items-center gap-2"
                >
                  {inner}
                </span>
              )}
              {i < 2 ? (
                <span
                  aria-hidden
                  className={cn("h-px min-w-4 flex-1", done ? "bg-pw-blue" : "bg-pw-border-strong")}
                />
              ) : null}
            </li>
          );
        })}
      </ol>
    </nav>
  );
}

/** One new conversion action: its name, its goal, and Google's settings. */
function ActionBlock({
  draft,
  option,
  currency,
  onChange,
  heading,
  help,
}: {
  draft: Draft;
  option?: SourceOption;
  currency: string;
  onChange: (patch: Partial<Draft>) => void;
  heading?: string;
  help?: string;
}) {
  const kind = kindOfSource(draft.source, option);
  const label = option?.categories.find((c) => c.id === draft.category)?.label ?? draft.category;
  const flagged = settingsProblems(draft.name || label, draft.settings, kind).length > 0;
  return (
    <div className="border-pw-border overflow-hidden rounded-[14px] border">
      <div className="border-pw-border flex flex-col gap-3 border-b px-4 py-4 sm:px-6">
        {heading ? (
          <div>
            <p className="text-pw-ink text-[15px] font-semibold">{heading}</p>
            {help ? <p className="text-pw-ink-500 text-[13px] leading-[18px]">{help}</p> : null}
          </div>
        ) : (
          <p className="text-pw-ink-500 text-[13px]">
            Goal: <span className="text-pw-ink font-semibold">{label}</span>
          </p>
        )}
        <Labelled label="Conversion action name" className="max-w-[520px]">
          <Input
            value={draft.name}
            maxLength={100}
            onChange={(e) => onChange({ name: e.target.value })}
            aria-label={`Name of the ${label} conversion action`}
          />
        </Labelled>
      </div>
      <Panel
        title="Settings"
        summary={settingsLine(draft.settings, kind, currency)}
        flagged={flagged}
      >
        <ActionSettings
          value={draft.settings}
          onChange={(settings) => onChange({ settings })}
          kind={kind}
          currency={currency}
          sourceKey={draft.source}
        />
      </Panel>
    </div>
  );
}

export function ConversionSetup({ summary }: { summary: Summary }) {
  const router = useRouter();
  const options = summary.source_options ?? {};
  const currency = summary.currency || "USD";
  const trackingId = summary.tracking_id ?? "";
  const importable = summary.importable ?? [];
  const taken = new Set(
    [...(summary.actions ?? []), ...importable].map((a) => a.name.trim().toLowerCase()),
  );

  const [step, setStep] = useState<1 | 2 | 3>(1);

  // Step 1: the data sources.
  const [intro, setIntro] = useState(true);
  const [chosen, setChosen] = useState<Record<Data, boolean>>({
    website: false,
    app: false,
    calls: false,
    offline: false,
  });
  const [callWays, setCallWays] = useState<Record<CallKey, boolean>>({
    calls_from_ads: true,
    calls_from_website: false,
    call_uploads: false,
  });
  const [site, setSite] = useState(summary.website ?? "");
  const [tag, setTag] = useState<Tag | undefined>(summary.website ? summary.tag : undefined);
  const [editingSite, setEditingSite] = useState(!summary.website);
  const [typedSite, setTypedSite] = useState(summary.website ?? "");
  const [checking, setChecking] = useState(false);
  const [siteTrouble, setSiteTrouble] = useState("");
  const [startTrouble, setStartTrouble] = useState("");

  // Step 2: the actions.
  const [drafts, setDrafts] = useState<Draft[]>([]);
  const [appId, setAppId] = useState("");
  const [imports, setImports] = useState<string[]>([]);
  const [tried, setTried] = useState(false);
  const [busy, setBusy] = useState(false);
  const [trouble, setTrouble] = useState("");

  // Step 3: what Google said.
  const [outcome, setOutcome] = useState<Outcome | null>(null);

  function makeDraft(source: SourceKey, category: string, others: Draft[]): Draft {
    const option = options[source];
    const label = option?.categories.find((c) => c.id === category)?.label ?? category;
    const used = new Set([...taken, ...others.map((d) => d.name.trim().toLowerCase())]);
    return {
      key: `${source}:${category}`,
      source,
      category,
      name: freeName(baseName(source, category, label, option), used),
      settings: defaultsFor(category, option),
    };
  }

  function toggleDraft(source: SourceKey, category: string, on: boolean) {
    const key = `${source}:${category}`;
    setDrafts((prev) =>
      on
        ? prev.some((d) => d.key === key)
          ? prev
          : [...prev, makeDraft(source, category, prev)]
        : prev.filter((d) => d.key !== key),
    );
  }

  function updateDraft(key: string, patch: Partial<Draft>) {
    setDrafts((prev) => prev.map((d) => (d.key === key ? { ...d, ...patch } : d)));
  }

  async function checkSite() {
    const address = asAddress(typedSite);
    if (!address) {
      setSiteTrouble("Give the website's address, like pdfezy.com.");
      return;
    }
    setSiteTrouble("");
    setChecking(true);
    const { ok, data } = await talk<Tag>(
      `tag?url=${encodeURIComponent(address)}&tracking=${encodeURIComponent(trackingId)}`,
    );
    setChecking(false);
    setSite(address);
    setTypedSite(address);
    setEditingSite(false);
    setTag(
      ok
        ? data
        : {
            read: false,
            google_tag: false,
            this_account: false,
            tag_manager: false,
            found_ids: [],
          },
    );
  }

  function next() {
    if (!Object.values(chosen).some(Boolean)) {
      setStartTrouble("Choose at least one data source.");
      return;
    }
    if (chosen.website && !site) {
      setStartTrouble(
        "Give your website's address and check it, or untick Conversions on a website.",
      );
      return;
    }
    if (chosen.calls && !Object.values(callWays).some(Boolean)) {
      setStartTrouble("Choose at least one kind of call to measure.");
      return;
    }
    setStartTrouble("");
    const active = new Set<SourceKey>();
    if (chosen.website) active.add("website");
    if (chosen.offline) active.add("offline");
    if (chosen.app) {
      active.add("app_download");
      active.add("app_purchase");
    }
    if (chosen.calls) for (const w of CALL_WAYS) if (callWays[w.id]) active.add(w.id);
    // Each kind of call has one goal, so choosing it in step 1 is choosing its action.
    setDrafts((prev) => {
      let kept = prev.filter((d) => active.has(d.source));
      for (const w of CALL_WAYS) {
        if (active.has(w.id) && !kept.some((d) => d.source === w.id)) {
          const category = options[w.id]?.categories[0]?.id ?? "PHONE_CALL_LEAD";
          kept = [...kept, makeDraft(w.id, category, kept)];
        }
      }
      return kept;
    });
    setImports((prev) =>
      prev.filter((r) => {
        const a = importable.find((i) => i.resource === r);
        return a ? chosen[importGroup(a)] : false;
      }),
    );
    setTried(false);
    setTrouble("");
    setStep(2);
    scrollTop();
  }

  function problems(): Problem[] {
    const out: string[] = [];
    if (!drafts.length && !imports.length) {
      out.push("Tick at least one goal to measure, or a conversion to import.");
    }
    const seen = new Map<string, string>();
    const twice = new Set<string>();
    for (const d of drafts) {
      const option = options[d.source];
      const name = d.name.trim();
      if (!name) {
        out.push(`${option?.label ?? "A conversion action"}: give the conversion action a name.`);
      } else if (taken.has(name.toLowerCase())) {
        out.push(
          `"${name}" is already the name of a conversion action in this account. Google needs each name to be different.`,
        );
      }
      if (name) {
        if (seen.has(name.toLowerCase())) twice.add(name);
        seen.set(name.toLowerCase(), name);
      }
      out.push(
        ...settingsProblems(
          name || option?.label || d.source,
          d.settings,
          kindOfSource(d.source, option),
        ),
      );
    }
    for (const name of twice) {
      out.push(
        `Two conversion actions are called "${name}". Google needs each name to be different.`,
      );
    }
    if (drafts.some((d) => options[d.source]?.app) && !appId.trim()) {
      out.push("Give the app's package name, like com.example.app, for the Google Play actions.");
    }
    return out.map((words) => ({ step: "conversions", words, blocks: true }));
  }

  async function create() {
    setTried(true);
    if (problems().length) return;
    setBusy(true);
    setTrouble("");
    let made: Created | null = null;
    if (drafts.length) {
      const actions: NewAction[] = drafts.map((d) => ({
        source: d.source,
        name: d.name.trim(),
        category: d.category,
        value: d.settings.value,
        amount: d.settings.amount ?? 0,
        count: d.settings.count,
        click_days: d.settings.click_days ?? 30,
        view_days: d.settings.view_days ?? 1,
        attribution: d.settings.attribution || "data_driven",
        primary: d.settings.primary,
        call_seconds: d.settings.call_seconds ?? 60,
        app_id: options[d.source]?.app ? appId.trim() : "",
      }));
      const { ok, data } = await talk<Created>("", { actions });
      if (!ok) {
        setBusy(false);
        setTrouble(said(data, "Google could not be asked just now. Nothing was created."));
        return;
      }
      made = data;
    }
    let imported: Changed | null = null;
    let importTrouble = "";
    if (imports.length) {
      const { ok, data } = await talk<Changed>("import", { resources: imports });
      if (ok) imported = data;
      else importTrouble = said(data, "Google could not be asked just now.");
    }
    setBusy(false);
    setOutcome({ made, imported, importTrouble });
    setStep(3);
    scrollTop();
  }

  // --- step 1 --------------------------------------------------------------

  function siteStatus(): ReactNode {
    if (checking) return "Looking for the Google tag…";
    if (!tag) return "Not checked yet";
    if (tag.this_account) {
      return (
        <span className="text-pw-good-ink inline-flex items-center gap-1">
          <CheckCircleIcon weight="fill" className="size-4" /> via Google Tag
        </span>
      );
    }
    if (tag.google_tag) {
      return (
        <span className="text-pw-warn-ink inline-flex items-center gap-1">
          <WarningCircleIcon weight="fill" className="size-4" /> A Google tag, but not this
          account&apos;s
        </span>
      );
    }
    if (tag.tag_manager) return "via Google Tag Manager, which PPCWay cannot see into";
    if (!tag.read) return "PPCWay could not read this site";
    return "No Google tag yet. You get it at the end of setup.";
  }

  function websiteExtra() {
    return (
      <div className="border-pw-blue-light mx-4 mb-4 flex flex-col gap-3 border-t pt-3">
        {site && !editingSite ? (
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div className="min-w-0">
              <p className="text-pw-ink truncate text-[14px] font-semibold">{domainOf(site)}</p>
              <p className="text-pw-ink-600 text-[13px] leading-[18px]">{siteStatus()}</p>
            </div>
            <button
              type="button"
              onClick={() => {
                setTypedSite(site);
                setEditingSite(true);
              }}
              className="text-pw-blue hover:text-pw-blue-hover text-[14px] font-semibold"
            >
              Edit data sources
            </button>
          </div>
        ) : (
          <div className="flex flex-col gap-2">
            <Labelled
              label="Your website"
              hint="The site where people buy, sign up or get in touch."
            >
              <div className="flex flex-col gap-2 sm:flex-row">
                <Input
                  value={typedSite}
                  onChange={(e) => setTypedSite(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter") {
                      e.preventDefault();
                      void checkSite();
                    }
                  }}
                  placeholder="pdfezy.com"
                  aria-label="Your website's address"
                  className="min-w-0 flex-1"
                />
                <Button
                  variant="secondary"
                  onClick={checkSite}
                  working={checking ? "Checking…" : false}
                >
                  Check
                </Button>
                {site ? (
                  <Button
                    variant="quiet"
                    onClick={() => {
                      setEditingSite(false);
                      setSiteTrouble("");
                    }}
                  >
                    Cancel
                  </Button>
                ) : null}
              </div>
            </Labelled>
            {siteTrouble ? <p className="text-pw-bad text-[13px]">{siteTrouble}</p> : null}
          </div>
        )}
      </div>
    );
  }

  function callsExtra() {
    return (
      <div className="border-pw-blue-light mx-4 mb-4 flex flex-col gap-3 border-t pt-3">
        {CALL_WAYS.map((w) => (
          <Tick
            key={w.id}
            checked={callWays[w.id]}
            onChange={(on) => setCallWays((prev) => ({ ...prev, [w.id]: on }))}
            help={w.help}
          >
            {w.label}
          </Tick>
        ))}
      </div>
    );
  }

  function sourceCard(d: (typeof DATA)[number]) {
    const on = chosen[d.id];
    const SourceIcon = d.icon;
    const measured = summary.sources?.[d.id];
    return (
      <div
        key={d.id}
        className={cn(
          "flex min-w-0 flex-col rounded-[16px] border transition-[border-color,background-color]",
          on
            ? "border-pw-blue bg-pw-blue-tint ring-pw-blue ring-1"
            : "border-pw-border bg-pw-card hover:border-pw-border-strong",
        )}
      >
        <label className="flex cursor-pointer items-start gap-3 p-4">
          <SourceIcon
            className={cn("mt-[2px] size-6 shrink-0", on ? "text-pw-blue" : "text-pw-ink-500")}
          />
          <span className="flex min-w-0 flex-1 flex-col gap-1">
            <span className="text-pw-ink text-[15px] leading-[20px] font-semibold">{d.title}</span>
            <span className="text-pw-ink-500 text-[13px] leading-[18px]">{d.help}</span>
            {measured ? (
              <span className="text-pw-good-ink mt-1 inline-flex items-center gap-1 text-[12px] font-semibold">
                <CheckCircleIcon weight="fill" className="size-[14px]" /> Already measuring
              </span>
            ) : null}
          </span>
          <input
            type="checkbox"
            checked={on}
            onChange={(e) => setChosen((prev) => ({ ...prev, [d.id]: e.target.checked }))}
            aria-label={d.title}
            className="accent-pw-blue mt-[3px] size-[18px] shrink-0"
          />
        </label>
        {on && d.id === "website" ? websiteExtra() : null}
        {on && d.id === "calls" ? callsExtra() : null}
      </div>
    );
  }

  // --- step 2 --------------------------------------------------------------

  function goalTicks(source: SourceKey) {
    const option = options[source];
    if (!option?.categories.length) {
      return <Note tone="warn">PPCWay could not load Google&apos;s goals for this source.</Note>;
    }
    return (
      <fieldset className="flex flex-col gap-3">
        <legend className="text-pw-ink mb-2 text-[14px] font-semibold">
          Choose the goals you want to measure
        </legend>
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {option.categories.map((c) => (
            <Tick
              key={c.id}
              checked={drafts.some((d) => d.key === `${source}:${c.id}`)}
              onChange={(on) => toggleDraft(source, c.id, on)}
            >
              {c.label}
            </Tick>
          ))}
        </div>
      </fieldset>
    );
  }

  function blocks(source: SourceKey) {
    return drafts
      .filter((d) => d.source === source)
      .map((d) => (
        <ActionBlock
          key={d.key}
          draft={d}
          option={options[d.source]}
          currency={currency}
          onChange={(patch) => updateDraft(d.key, patch)}
        />
      ));
  }

  function importList(group: Data) {
    const list = importable.filter((a) => importGroup(a) === group);
    if (!list.length) return null;
    return (
      <div className="flex flex-col gap-3">
        <div>
          <p className="text-pw-ink text-[14px] font-semibold">
            {group === "app"
              ? "Import from Google Analytics, Firebase or an app analytics partner"
              : "Import from Google Analytics"}
          </p>
          <p className="text-pw-ink-500 text-[13px] leading-[18px]">
            These are measured already. Importing lets Google Ads count them; nothing needs
            installing.
          </p>
        </div>
        <ul className="border-pw-border divide-pw-border divide-y rounded-[12px] border">
          {list.map((a) => (
            <li
              key={a.resource}
              className="flex flex-col gap-2 px-4 py-3 sm:flex-row sm:items-center sm:justify-between"
            >
              <span className="min-w-0">
                <span className="text-pw-ink block text-[14px] font-medium">{a.name}</span>
                <span className="text-pw-ink-500 block text-[12px]">
                  {a.source_label} · {a.category_label}
                </span>
              </span>
              <Tick
                checked={imports.includes(a.resource)}
                onChange={(on) =>
                  setImports((prev) =>
                    on ? [...prev, a.resource] : prev.filter((r) => r !== a.resource),
                  )
                }
              >
                <span className="sr-only">Import {a.name}</span>
                <span aria-hidden>Import</span>
              </Tick>
            </li>
          ))}
        </ul>
      </div>
    );
  }

  const body = "flex flex-col gap-5 px-4 py-5 sm:px-6";

  function websiteCard() {
    return (
      <Card
        title="Conversions on a website"
        help={
          <>
            Measured with the Google tag on {domainOf(site) || "your website"}, or imported from
            Google Analytics.
          </>
        }
      >
        <div className={body}>
          {goalTicks("website")}
          {blocks("website")}
          {importList("website")}
        </div>
      </Card>
    );
  }

  function appCard() {
    const appDrafts = drafts.some(
      (d) => d.source === "app_download" || d.source === "app_purchase",
    );
    return (
      <Card
        title="Conversions on an app"
        help="Installs and in-app purchases from Google Play, or events imported from Google Analytics for Firebase or an app analytics partner."
      >
        <div className={body}>
          <fieldset className="flex flex-col gap-3">
            <legend className="text-pw-ink mb-2 text-[14px] font-semibold">
              Choose what to measure from Google Play
            </legend>
            {(["app_download", "app_purchase"] as const).map((source) => {
              const option = options[source];
              const category = option?.categories[0]?.id;
              if (!option || !category) return null;
              return (
                <Tick
                  key={source}
                  checked={drafts.some((d) => d.key === `${source}:${category}`)}
                  onChange={(on) => toggleDraft(source, category, on)}
                >
                  {option.label}
                </Tick>
              );
            })}
          </fieldset>
          {appDrafts ? (
            <Labelled
              label="App package name"
              hint="As in the app's Google Play address after id=, for example play.google.com/store/apps/details?id=com.example.app"
              className="max-w-[520px]"
            >
              <Input
                value={appId}
                onChange={(e) => setAppId(e.target.value)}
                placeholder="com.example.app"
                aria-label="App package name"
              />
            </Labelled>
          ) : null}
          {blocks("app_download")}
          {blocks("app_purchase")}
          {appDrafts ? (
            <Note tone="info">
              Google counts Google Play installs and in-app purchases once your Google Play
              developer account is linked to Google Ads, under Tools, Data manager. Without the
              link, Google refuses these actions.
            </Note>
          ) : null}
          {importList("app")}
          <p className="text-pw-ink-500 text-[13px] leading-[18px]">
            Apps on the App Store, and events from other analytics tools, are measured through
            Firebase or the analytics partner. Once that is linked in Google Ads, their events show
            here to import.
          </p>
        </div>
      </Card>
    );
  }

  function callsCard() {
    return (
      <Card
        title="Conversions from phone calls"
        help="Each kind of call you chose becomes its own conversion action."
      >
        <div className={body}>
          {CALL_WAYS.filter((w) => callWays[w.id]).map((w) => {
            const d = drafts.find((x) => x.source === w.id);
            return d ? (
              <ActionBlock
                key={d.key}
                draft={d}
                option={options[d.source]}
                currency={currency}
                onChange={(patch) => updateDraft(d.key, patch)}
                heading={w.label}
                help={w.help}
              />
            ) : null;
          })}
          {callWays.calls_from_website ? (
            <Note tone="info">
              Calls from website visits need the Google tag on your site and a phone snippet. The
              summary gives you both.
            </Note>
          ) : null}
          {callWays.call_uploads ? (
            <Note tone="info">
              Uploads come after the action exists: once it is created, upload your calls in Google
              Ads under Goals, Conversions, Uploads, or with the Google Ads API.
            </Note>
          ) : null}
        </div>
      </Card>
    );
  }

  function offlineCard() {
    return (
      <Card
        title="Conversions offline"
        help="Sales and leads that finish away from your website, like on the phone or in person, matched back to the ad click."
      >
        <div className={body}>
          {goalTicks("offline")}
          {blocks("offline")}
          <Note tone="info">
            Uploads come after the action exists. Once it is created, send conversions from your CRM
            (Google Ads connects Salesforce, HubSpot and others in its Data manager), upload a file
            in Google Ads under Goals, Conversions, Uploads, or send them with the Google Ads API.
            Each conversion needs the click ID (GCLID), or the customer&apos;s email or phone
            number.
          </Note>
        </div>
      </Card>
    );
  }

  // --- step 3 --------------------------------------------------------------

  function summaryStep() {
    const made = outcome?.made ?? null;
    const created = made?.created ?? [];
    const unread = (made?.created_names.length ?? 0) - created.length;
    const imported = (outcome?.imported?.changed ?? []).map(
      (r) => importable.find((a) => a.resource === r)?.name ?? r,
    );
    const refused = [...(made?.refused ?? []), ...(outcome?.imported?.refused ?? [])];
    const nothing = !created.length && unread <= 0 && !imported.length;
    const needsTag = created.some((a) => a.type === "WEBPAGE" || a.type === "WEBSITE_CALL");
    const globalTag = made?.global_site_tag || summary.global_site_tag || "";
    const tagId = made?.tracking_id || trackingId;
    const has = (...types: string[]) => created.some((a) => types.includes(a.type));
    const plural = (n: number, one: string) => `${n} ${one}${n === 1 ? "" : "s"}`;

    return (
      <div className="flex flex-col gap-4">
        <Card
          title="Summary"
          help={
            nothing
              ? "Nothing was created."
              : "What Google has now. Each action starts counting once its tag or upload is in place."
          }
        >
          <div className={body}>
            {created.length ? (
              <div className="flex flex-col gap-2">
                <p className="text-pw-ink text-[14px] font-semibold">
                  Google created {plural(created.length, "conversion action")}.
                </p>
                <ul className="border-pw-border divide-pw-border divide-y rounded-[12px] border">
                  {created.map((a) => (
                    <li
                      key={a.resource}
                      className="flex flex-col gap-1 px-4 py-3 sm:flex-row sm:items-center sm:justify-between"
                    >
                      <span className="min-w-0">
                        <span className="text-pw-ink block text-[14px] font-semibold">
                          {a.name}
                        </span>
                        <span className="text-pw-ink-500 block text-[12px]">
                          {a.category_label} · {a.source_label}
                        </span>
                      </span>
                      <span className="text-pw-ink-600 text-[13px]">
                        {a.primary ? "Primary" : "Secondary"}
                      </span>
                    </li>
                  ))}
                </ul>
              </div>
            ) : null}
            {unread > 0 ? (
              <Note tone="info">
                Google created {plural(unread, "more conversion action")} that PPCWay could not read
                back yet. They show on the Conversions summary in a minute.
              </Note>
            ) : null}
            {imported.length ? (
              <div className="flex flex-col gap-2">
                <p className="text-pw-ink text-[14px] font-semibold">
                  Imported {plural(imported.length, "conversion")}.
                </p>
                <p className="text-pw-ink-600 text-[14px]">{imported.join(", ")}</p>
              </div>
            ) : null}
            {refused.length ? (
              <Note tone="bad">
                <p className="font-semibold">Google refused {refused.length}:</p>
                <ul className="mt-1 flex flex-col gap-1">
                  {refused.map((r, i) => (
                    <li key={i}>
                      {r.name ? `"${r.name}": ` : ""}
                      {r.message}
                    </li>
                  ))}
                </ul>
              </Note>
            ) : null}
            {outcome?.importTrouble ? (
              <Note tone="bad">The imports did not go through. {outcome.importTrouble}</Note>
            ) : null}
            {nothing ? (
              <div>
                <Button variant="secondary" onClick={() => setStep(2)}>
                  Back to fix them
                </Button>
              </div>
            ) : refused.length ? (
              <p className="text-pw-ink-500 text-[13px]">
                To try the refused ones again, start a new conversion action from the Conversions
                summary.
              </p>
            ) : null}
          </div>
        </Card>

        {needsTag ? (
          <Card
            title="Set up the Google tag"
            help="Google counts conversions on your website only once its tag is there. Install it one of these ways, then check it."
          >
            <div className="flex flex-col gap-6 px-4 py-5 sm:px-6">
              <TagSetup
                globalTag={globalTag}
                trackingId={tagId}
                actions={created}
                site={site}
                account={summary.account_name ?? ""}
              />
              <div className="border-pw-border flex flex-col gap-3 border-t pt-5">
                <div>
                  <p className="text-pw-ink text-[15px] font-semibold">Check the tag</p>
                  <p className="text-pw-ink-500 text-[13px] leading-[18px]">
                    Once the tag is on your site, check that PPCWay can see it on{" "}
                    {domainOf(site) || "your website"}.
                  </p>
                </div>
                <TagCheck site={site} trackingId={tagId} initial={tag} />
              </div>
            </div>
          </Card>
        ) : null}

        {has("AD_CALL") ? (
          <Note tone="info">
            Calls from ads count on their own once your ads show a phone number through a call
            asset, where Google offers forwarding numbers. Nothing to install.
          </Note>
        ) : null}
        {has("UPLOAD_CLICKS", "UPLOAD_CALLS") ? (
          <Note tone="info">
            Your offline actions are ready for uploads: from your CRM through Google Ads&apos; Data
            manager, as a file under Goals, Conversions, Uploads, or with the Google Ads API.
            {summary.data_terms
              ? ""
              : " To upload customer details such as emails, accept Google's customer data terms in Google Ads first, under Goals, Settings."}
          </Note>
        ) : null}
        {has("GOOGLE_PLAY_DOWNLOAD", "GOOGLE_PLAY_IN_APP_PURCHASE") ? (
          <Note tone="info">
            Google counts installs and in-app purchases once the app&apos;s Google Play account is
            linked to Google Ads.
          </Note>
        ) : null}

        <div className="flex flex-wrap gap-3">
          <Button
            onClick={() => {
              router.push("/conversions");
              router.refresh();
            }}
          >
            Done
          </Button>
        </div>
      </div>
    );
  }

  const found = problems();

  return (
    <div className="flex flex-col gap-5">
      <div className="bg-pw-card border-pw-border rounded-[18px] border px-4 py-4 sm:px-6">
        <Stepper at={step} onGo={(n) => setStep(n)} />
      </div>

      {step === 1 ? (
        <div className="flex flex-col gap-4">
          {intro ? (
            <section className="bg-pw-blue-tint border-pw-blue-light relative rounded-[18px] border p-5 sm:p-6">
              <button
                type="button"
                aria-label="Dismiss"
                onClick={() => setIntro(false)}
                className="text-pw-ink-500 hover:text-pw-ink hover:bg-pw-card absolute top-3 right-3 rounded-full p-2"
              >
                <XIcon className="size-4" />
              </button>
              <h2 className="text-pw-ink pr-10 text-[17px] leading-[22px] font-semibold">
                Welcome to a simpler conversion measurement setup
              </h2>
              <ol className="mt-4 grid gap-4 sm:grid-cols-3">
                {[
                  "Choose where customers interact with your business and connect those data sources upfront",
                  "Set up measurement across all your data sources at one time",
                  "Then, measure all the interactions that matter to your business",
                ].map((words, i) => (
                  <li key={i} className="flex gap-3">
                    <span className="bg-pw-card text-pw-blue-ink flex size-6 shrink-0 items-center justify-center rounded-full text-[12px] font-bold">
                      {i + 1}
                    </span>
                    <span className="text-pw-ink-700 text-[14px] leading-[20px]">{words}</span>
                  </li>
                ))}
              </ol>
            </section>
          ) : null}

          <Card
            title="Choose data sources to measure conversions"
            help="Conversions are important customer interactions you want to measure, like purchases, signups, and phone calls. Choose from available data sources to set up conversions faster and get a complete picture of your ad performance."
          >
            <div className="grid gap-3 p-4 sm:p-6 md:grid-cols-2">{DATA.map(sourceCard)}</div>
          </Card>

          {startTrouble ? <Note tone="bad">{startTrouble}</Note> : null}
          <div className="flex flex-wrap gap-3">
            <Button onClick={next}>Save and continue</Button>
            <LinkButton href="/conversions" variant="secondary">
              Cancel
            </LinkButton>
          </div>
        </div>
      ) : null}

      {step === 2 ? (
        <div className="flex flex-col gap-4">
          <div>
            <h2 className="display text-[22px] leading-[28px] font-semibold">
              Create conversion actions
            </h2>
            <p className="text-pw-ink-500 mt-1 max-w-[760px] text-[14px] leading-[20px]">
              For each data source, tick the goals you want to measure. Each one becomes a
              conversion action in Google Ads, with Google&apos;s recommended settings until you
              change them.
            </p>
          </div>
          {chosen.website ? websiteCard() : null}
          {chosen.app ? appCard() : null}
          {chosen.calls ? callsCard() : null}
          {chosen.offline ? offlineCard() : null}
          {tried ? <Problems items={found} /> : null}
          {trouble ? <Note tone="bad">{trouble}</Note> : null}
          <div className="flex flex-wrap items-center gap-3">
            <Button onClick={create} working={busy ? "Creating…" : false}>
              Create conversion actions
            </Button>
            <Button variant="secondary" onClick={() => setStep(1)} disabled={busy}>
              Back
            </Button>
          </div>
          <p className="text-pw-ink-500 text-[13px]">
            Nothing reaches Google until you click Create conversion actions. Then everything here
            goes in one request.
          </p>
        </div>
      ) : null}

      {step === 3 ? summaryStep() : null}
    </div>
  );
}
