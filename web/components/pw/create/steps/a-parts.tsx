"use client";

import { useEffect, useState, type ReactNode, type SelectHTMLAttributes } from "react";
import { cn } from "@/lib/cn";
import { call, said, type Brand, type Spec } from "@/lib/creation";
import { Chips, Finder, Labelled, Lines, Pill, money } from "../kit";

/*
  Small parts the bidding, settings, AI Max, budget and review steps share:
  a select in the kit's input shape, a link-shaped button, a search box whose
  rows carry their own buttons (Google's "Include" and "Exclude" per place),
  the account's shared library loaded once, the brand picker and the text
  guidelines editor that AI Max and Performance Max both have, and the
  sentences the review page and the bidding step both say.
*/

/** A native select drawn like the kit's inputs. Label it with `aria-label`. */
export function Select({ className, ...rest }: SelectHTMLAttributes<HTMLSelectElement>) {
  return (
    <select
      className={cn(
        "border-pw-border-input bg-pw-card text-pw-ink h-[46px] max-w-full rounded-[12px] border px-3 text-[14px] outline-none",
        "focus:border-pw-blue focus:border-2 focus:px-[11px] disabled:opacity-60",
        className,
      )}
      {...rest}
    />
  );
}

/** A button that reads as a link: "Edit", "Fix it", "Or, select a bid strategy directly". */
export function Act({
  onClick,
  children,
  className,
  disabled,
}: {
  onClick: () => void;
  children: ReactNode;
  className?: string;
  disabled?: boolean;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      className={cn(
        "text-pw-blue hover:text-pw-blue-hover disabled:text-pw-ink-300 self-start text-left text-[14px] font-semibold hover:underline",
        className,
      )}
    >
      {children}
    </button>
  );
}

/*
  A box multi-line text is typed into, one entry a line: IP addresses,
  negative keywords. The text is kept as typed, so a new line can be started;
  what is saved is the lines that have something on them.
*/
export function LinesArea({
  lines,
  onChange,
  ariaLabel,
  placeholder,
  rows = 5,
}: {
  lines: string[];
  onChange: (next: string[]) => void;
  ariaLabel: string;
  placeholder?: string;
  rows?: number;
}) {
  const [text, setText] = useState(() => lines.join("\n"));
  return (
    <textarea
      value={text}
      rows={rows}
      aria-label={ariaLabel}
      placeholder={placeholder}
      spellCheck={false}
      onChange={(e) => {
        setText(e.target.value);
        onChange(
          e.target.value
            .split("\n")
            .map((line) => line.trim())
            .filter(Boolean),
        );
      }}
      className={cn(
        "border-pw-border-input bg-pw-card text-pw-ink placeholder:text-pw-ink-300 w-full rounded-[12px] border px-4 py-3",
        "focus:border-pw-blue font-mono text-[13px] leading-[20px] outline-none focus:border-2 focus:px-[15px] focus:py-[11px]",
      )}
    />
  );
}

/*
  A search box whose results each carry their own buttons, for where Google
  offers more than one thing to do with a result (a place is included or
  excluded) or groups the results under headings (audience segments). The
  kit's `Finder` is one click per result; this keeps the list open so
  several can be picked in a row, as Google's advanced search does.
*/
export function Lookup<T>({
  path,
  pick,
  keyOf,
  row,
  group,
  placeholder,
  ariaLabel,
  least = 2,
  empty = "Nothing found.",
}: {
  path: (q: string) => string;
  pick: (data: unknown) => T[];
  keyOf: (item: T) => string;
  row: (item: T) => ReactNode;
  group?: (item: T) => string;
  placeholder: string;
  ariaLabel: string;
  least?: number;
  empty?: string;
}) {
  const [typed, setTyped] = useState("");
  const [found, setFound] = useState<T[] | null>(null);
  const [looking, setLooking] = useState(false);
  const [trouble, setTrouble] = useState("");

  useEffect(() => {
    const q = typed.trim();
    if (q.length < least) return;
    let live = true;
    const timer = setTimeout(async () => {
      setLooking(true);
      const { ok, data } = await call<unknown>(path(q));
      if (!live) return;
      setLooking(false);
      setTrouble(ok ? "" : said(data, "Google could not be asked just now."));
      setFound(ok ? pick(data) : []);
    }, 300);
    return () => {
      live = false;
      clearTimeout(timer);
    };
    // `path` and `pick` are written inline by callers; the text is what matters.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [typed, least]);

  const long = typed.trim().length >= least;
  const shown = long ? found : null;
  // Headings in the order the server sent them: the account's own data first.
  const groups: { name: string; items: T[] }[] = [];
  for (const item of shown ?? []) {
    const name = group ? group(item) : "";
    const at = groups.find((g) => g.name === name);
    if (at) at.items.push(item);
    else groups.push({ name, items: [item] });
  }

  return (
    <div className="flex flex-col gap-2">
      <input
        value={typed}
        aria-label={ariaLabel}
        placeholder={placeholder}
        onChange={(e) => setTyped(e.target.value)}
        className={cn(
          "text-pw-ink placeholder:text-pw-ink-300 bg-pw-card border-pw-border-input h-[46px] w-full rounded-[12px] border px-[17px] text-[15px] outline-none",
          "focus:border-pw-blue focus:border-2 focus:px-4",
        )}
      />
      {looking && long ? <p className="text-pw-ink-500 text-[13px]">Looking…</p> : null}
      {trouble ? <p className="text-pw-bad text-[13px]">{trouble}</p> : null}
      {shown && !looking ? (
        shown.length ? (
          <div className="border-pw-border max-h-[340px] overflow-y-auto rounded-[12px] border">
            {groups.map((g) => (
              <div key={g.name || "all"}>
                {g.name ? (
                  <p className="bg-pw-muted text-pw-ink-500 sticky top-0 px-4 py-[6px] text-[12px] font-semibold">
                    {g.name}
                  </p>
                ) : null}
                <ul className="divide-pw-border divide-y">
                  {g.items.map((item) => (
                    <li
                      key={keyOf(item)}
                      className="flex flex-col gap-2 px-4 py-[10px] text-[14px] sm:flex-row sm:items-center sm:justify-between"
                    >
                      {row(item)}
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        ) : (
          <p className="text-pw-ink-500 text-[13px]">{empty}</p>
        )
      ) : null}
    </div>
  );
}

/* ---- The account's shared library, asked once per visit ----------------- */

export type SharedLibrary = {
  budgets: { resource: string; name: string; amount: number | null; period?: string }[];
  negative_lists: { resource: string; name: string; count: number }[];
  merchants: { id: string; name: string }[];
};

// Kept for the page's life: the budget and settings steps both read it, and
// each read is three questions to Google.
let library: SharedLibrary | null = null;

export function useShared(): { shared: SharedLibrary | null; trouble: string } {
  const [shared, setShared] = useState<SharedLibrary | null>(library);
  const [trouble, setTrouble] = useState("");
  useEffect(() => {
    if (library) return;
    let live = true;
    void call<Partial<SharedLibrary>>("shared").then(({ ok, data }) => {
      if (!live) return;
      if (!ok) {
        setTrouble(said(data, "Google could not list the shared library just now."));
        return;
      }
      library = {
        budgets: data.budgets ?? [],
        negative_lists: data.negative_lists ?? [],
        merchants: data.merchants ?? [],
      };
      setShared(library);
    });
    return () => {
      live = false;
    };
  }, []);
  return { shared, trouble };
}

/* ---- Brands and text guidelines ----------------------------------------- */

type FoundBrand = Brand & { urls?: string[]; state?: string };

function host(url: string | undefined): string {
  if (!url) return "";
  try {
    return new URL(url.startsWith("http") ? url : `https://${url}`).hostname.replace(/^www\./, "");
  } catch {
    return url;
  }
}

/** Brands from Google's brand library, picked into a list, as Google's brand list editor does. */
export function BrandPicker({
  values,
  onChange,
  ariaLabel,
  tone = "blue",
}: {
  values: Brand[];
  onChange: (next: Brand[]) => void;
  ariaLabel: string;
  tone?: "blue" | "red";
}) {
  return (
    <div className="flex flex-col gap-2">
      <Finder<FoundBrand>
        path={(q) => `brands?q=${encodeURIComponent(q)}`}
        pick={(data) => ((data as { brands?: FoundBrand[] }).brands ?? []).filter((b) => b.id)}
        keyOf={(b) => b.id}
        render={(b) => (
          <>
            <span className="text-pw-ink font-medium">{b.name}</span>
            <span className="text-pw-ink-500 truncate text-[12px]">
              {values.some((v) => v.id === b.id) ? "Already in the list" : host(b.urls?.[0])}
            </span>
          </>
        )}
        placeholder="Search Google's brand library"
        ariaLabel={ariaLabel}
        empty="Google's brand library has no brand by that name."
        onPick={(b) => {
          if (!values.some((v) => v.id === b.id)) onChange([...values, { id: b.id, name: b.name }]);
        }}
      />
      {values.length ? (
        <div className="flex flex-wrap gap-2">
          {values.map((b) => (
            <Pill
              key={b.id}
              tone={tone}
              onRemove={() => onChange(values.filter((v) => v.id !== b.id))}
            >
              {b.name || b.id}
            </Pill>
          ))}
        </div>
      ) : null}
    </div>
  );
}

type Guidelines = Spec["ai_max"]["text_guidelines"];

/*
  Google's "Add text guidelines": words its generated text must never use,
  and rules in plain language. A restriction can hold commas, so each one is
  its own line rather than a chip.
*/
export function TextGuidelinesEditor({
  value,
  onChange,
}: {
  value: Guidelines;
  onChange: (next: Guidelines) => void;
}) {
  return (
    <div className="flex flex-col gap-4">
      <Labelled
        label="Term exclusions"
        hint="Words or phrases Google's generated text must never use. Up to 25, each up to 30 characters."
      >
        <Chips
          values={value.term_exclusions}
          onChange={(next) => onChange({ ...value, term_exclusions: next })}
          placeholder="For example: cheapest"
          ariaLabel="Add a term exclusion"
          most={25}
          longest={30}
        />
      </Labelled>
      <Labelled
        label="Messaging restrictions"
        hint="Rules in your own words, such as: Don't mention discounts or free trials. Up to 40, each up to 300 characters."
      >
        <Lines
          values={value.messaging_restrictions}
          onChange={(next) => onChange({ ...value, messaging_restrictions: next })}
          most={40}
          longest={300}
          placeholder="Restriction"
          addLabel="Add a restriction"
        />
      </Labelled>
    </div>
  );
}

/* ---- Words the bidding step and the review page both say ---------------- */

export type Direct =
  | "target_cpa"
  | "target_roas"
  | "max_conversions"
  | "max_value"
  | "max_clicks"
  | "impression_share"
  | "manual_cpc";

/** Which of Google's bid strategies the answers add up to. */
export function directOf(b: Spec["bidding"]): Direct {
  if (b.strategy === "manual_cpc") return "manual_cpc";
  if (b.focus === "conversions") return b.set_target ? "target_cpa" : "max_conversions";
  if (b.focus === "conversion_value") return b.set_target ? "target_roas" : "max_value";
  if (b.focus === "clicks") return "max_clicks";
  return "impression_share";
}

export const DIRECT_LABEL: Record<Direct, string> = {
  target_cpa: "Target CPA",
  target_roas: "Target ROAS",
  max_conversions: "Maximize conversions",
  max_value: "Maximize conversion value",
  max_clicks: "Maximize clicks",
  impression_share: "Target impression share",
  manual_cpc: "Manual CPC",
};

export const WHERE_LABEL: Record<Spec["bidding"]["impression_location"], string> = {
  ANYWHERE_ON_PAGE: "Anywhere on results page",
  TOP_OF_PAGE: "Top of results page",
  ABSOLUTE_TOP_OF_PAGE: "Absolute top of results page",
};

/** The bid strategy in one plain sentence. */
export function strategySentence(spec: Spec): string {
  const b = spec.bidding;
  const cur = spec.currency;
  switch (directOf(b)) {
    case "manual_cpc":
      return b.default_bid
        ? `Manual CPC: you set the bids, starting at ${money(b.default_bid, cur)} a click for each ad group.`
        : "Manual CPC: you set the bids. The default bid for each ad group is not set yet.";
    case "target_cpa":
      return b.target_cpa
        ? `Target CPA: as many conversions as Google can get at about ${money(b.target_cpa, cur)} each.`
        : "Target CPA: the target cost per action is not set yet.";
    case "max_conversions":
      return "Maximize conversions: as many conversions as the budget allows.";
    case "target_roas": {
      if (!b.target_roas) return "Target ROAS: the target return on ad spend is not set yet.";
      const explore =
        b.explore && spec.type === "SEARCH"
          ? ` Smart Bidding may go up to ${b.explore_tolerance}% below it to find new traffic.`
          : "";
      return `Target ROAS: as much conversion value as Google can get at a ${b.target_roas}% return on ad spend.${explore}`;
    }
    case "max_value":
      return "Maximize conversion value: as much conversion value as the budget allows.";
    case "max_clicks":
      return b.max_cpc
        ? `Maximize clicks: as many clicks as the budget allows, never more than ${money(b.max_cpc, cur)} a click.`
        : "Maximize clicks: as many clicks as the budget allows.";
    case "impression_share": {
      const share = b.impression_percent
        ? `${b.impression_percent}% of searches`
        : "a share of searches not set yet";
      const most = b.impression_max_cpc
        ? `, paying at most ${money(b.impression_max_cpc, cur)} a click`
        : ", with no maximum CPC bid limit set yet";
      return `Target impression share: shown on ${share} ${WHERE_WORDS[b.impression_location]}${most}.`;
    }
  }
}

// `money()` writes a missing amount as a dash, so every sentence here checks first.
const WHERE_WORDS: Record<Spec["bidding"]["impression_location"], string> = {
  ANYWHERE_ON_PAGE: "anywhere on the results page",
  TOP_OF_PAGE: "at the top of the results page",
  ABSOLUTE_TOP_OF_PAGE: "at the absolute top of the results page",
};

export function customerSentence(b: Spec["bidding"], currency: string): string {
  if (b.new_customers === "only") return "Bids only for new customers.";
  if (b.new_customers === "bid_higher") {
    return b.new_customer_value
      ? `Bids higher for new customers, counting each one as worth ${money(b.new_customer_value, currency)} more.`
      : "Bids higher for new customers.";
  }
  return "Bids equally for new and existing customers.";
}

/** "3 keywords", "1 keyword". */
export function count(n: number, one: string, many = `${one}s`): string {
  return `${n.toLocaleString()} ${n === 1 ? one : many}`;
}

/** An ISO date as people read it: 1 Dec 2026. */
export function dateWords(iso: string | null): string {
  if (!iso) return "";
  const d = new Date(`${iso}T00:00:00`);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleDateString(undefined, { day: "numeric", month: "short", year: "numeric" });
}
