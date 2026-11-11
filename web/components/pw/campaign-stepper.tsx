"use client";

import {
  AppWindowIcon,
  ArrowLeftIcon,
  ArrowRightIcon,
  BriefcaseIcon,
  CheckIcon,
  CircleNotchIcon,
  ShoppingBagIcon,
  SparkleIcon,
  StorefrontIcon,
  VanIcon,
  type Icon,
} from "@phosphor-icons/react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useMemo, useState, type ReactNode } from "react";
import { ENGLISH, PlacePicker, Words, call } from "@/components/pw/campaign-builder";
import { money } from "@/components/pw/campaigns";
import { PwCard } from "@/components/pw/shell";
import { Button } from "@/components/ui/button";
import { Field, Input } from "@/components/ui/field";
import {
  MOST_THEMES,
  type BusinessKind,
  type Draft,
  type Place,
  type Prefill,
  type PromiseOption,
} from "@/lib/builder";
import { cn } from "@/lib/cn";

/*
  Start a new campaign, one question at a time, for any kind of business.

  The client turned the first builder down on 10 November: one long form, and
  every promise and example in it a plumber's. This asks what kind of business
  it is first, and the rest follows from that answer: the examples, the
  promises worth offering, the searches worth skipping, and what counts as a
  win when Google bids.

  The steps are not numbered circles. They are the brief, written as one
  sentence that fills in as the merchant answers:

    Advertise PDFezy, an online tool, selling pdf to word to people in Poland,
    in English. We can promise a free version. Spend up to $20 a day, for
    sign-ups.

  Each filled part is a way back to its question, the part being asked is
  marked, and the parts still to come wait in grey. By the end the merchant
  has read, in their own words, exactly what they are about to approve, which
  a progress bar never tells anybody.
*/

type Step = "business" | "sell" | "who" | "promise" | "budget";
/** After the last of these comes the check: the sentence is whole. */
const STEPS: Step[] = ["business", "sell", "who", "promise", "budget"];

const ICONS: Record<string, Icon> = {
  at_their_place: VanIcon,
  they_visit: StorefrontIcon,
  professional: BriefcaseIcon,
  online_shop: ShoppingBagIcon,
  software: AppWindowIcon,
  other: SparkleIcon,
};

const QUESTION: Record<Step, { title: string; help: string; next: string }> = {
  business: {
    title: "What kind of business is it?",
    help: "This decides the questions that follow, so a shop is asked about shipping and software about free trials.",
    next: "your business",
  },
  sell: {
    title: "What do you sell?",
    help: "One thing at a time, the way a customer would search for it. Each one gets its own ad.",
    next: "what you sell",
  },
  who: {
    title: "Who should see the ads?",
    help: "People in these places, searching in this language.",
    next: "who sees it",
  },
  promise: {
    title: "What can you honestly promise?",
    help: "Tick only what is true. Otto will never write a promise you have not ticked, however good it would sound.",
    next: "your promises",
  },
  budget: {
    title: "How much can it spend a day?",
    help: "You only pay when somebody clicks. Google may spend more on a busy day and evens it out over the month.",
    next: "your budget",
  },
};

/** "a, b and c", or "a, b and 3 more" past `most`. */
function joined(words: string[], most = 3): string {
  const shown = words.slice(0, most);
  const rest = words.length - shown.length;
  if (rest > 0) return `${shown.join(", ")} and ${rest} more`;
  if (shown.length < 2) return shown[0] ?? "";
  return `${shown.slice(0, -1).join(", ")} and ${shown[shown.length - 1]}`;
}

function hostOf(url: string): string {
  try {
    return new URL(url).host.replace(/^www\./, "");
  } catch {
    return "";
  }
}

const isUrl = (value: string) => /^https?:\/\/[^\s.]+\.[^\s]+/.test(value.trim());

type SiteRead = { state: "idle" | "looking" | "found" | "none"; name: string; title: string };

/** For a preview screen: where to start and what is already answered. */
export type StepperStart = {
  at?: number;
  kind?: string;
  url?: string;
  site?: { name: string; title: string };
  themes?: string[];
  places?: Place[];
  promises?: string[];
  budget?: string;
};

export function CampaignStepper({
  prefill,
  site,
  trade,
  start,
}: {
  prefill: Prefill;
  site: string;
  trade: string;
  start?: StepperStart;
}) {
  const router = useRouter();
  const kinds = useMemo(() => prefill.kinds ?? [], [prefill.kinds]);
  const catalogue = useMemo(() => prefill.promises ?? [], [prefill.promises]);
  const currency = prefill.currency ?? "";

  const [at, setAt] = useState(start?.at ?? 0);
  const [reached, setReached] = useState(start?.at ?? 0);
  const [kindId, setKindId] = useState(start?.kind ?? "");
  const [url, setUrl] = useState(
    start?.url ?? (site ? (site.startsWith("http") ? site : `https://${site}`) : ""),
  );
  const [read, setRead] = useState<SiteRead>(
    start?.site ? { state: "found", ...start.site } : { state: "idle", name: "", title: "" },
  );
  const [themes, setThemes] = useState<string[]>(start?.themes ?? (trade ? [trade] : []));
  const [name, setName] = useState("");
  const [places, setPlaces] = useState<Place[]>(start?.places ?? []);
  const [language, setLanguage] = useState<Place>(ENGLISH);
  const [languages, setLanguages] = useState<Place[]>([ENGLISH]);
  const [promises, setPromises] = useState<string[]>(start?.promises ?? []);
  const [moreShown, setMoreShown] = useState(false);
  const [years, setYears] = useState("");
  const [negatives, setNegatives] = useState<string[] | null>(null);
  const [budget, setBudget] = useState(start?.budget ?? "20");
  const [bidding, setBidding] = useState<"clicks" | "leads">("clicks");
  const [working, setWorking] = useState(false);
  const [trouble, setTrouble] = useState("");

  const kind: BusinessKind | undefined = kinds.find((k) => k.id === kindId);
  // The searches to skip follow the kind until the merchant edits them.
  const skipped = negatives ?? kind?.negatives ?? ["jobs", "careers", "salary"];

  useEffect(() => {
    let live = true;
    call<{ languages?: Place[] }>("languages").then(({ ok, data }) => {
      if (live && ok && data.languages?.length) setLanguages(data.languages);
    });
    return () => {
      live = false;
    };
  }, []);

  // Read the landing page's own name as the merchant types it, so they can
  // see whose ads these will be before anything is written.
  useEffect(() => {
    if (start?.site) return;
    const address = url.trim();
    if (!isUrl(address)) return;
    let live = true;
    const timer = setTimeout(async () => {
      setRead((was) => ({ ...was, state: "looking" }));
      const { ok, data } = await call<{ name?: string; title?: string }>(
        `site?url=${encodeURIComponent(address)}`,
      );
      if (!live) return;
      setRead(
        ok && data.name
          ? { state: "found", name: data.name, title: data.title ?? "" }
          : { state: "none", name: "", title: "" },
      );
    }, 700);
    return () => {
      live = false;
      clearTimeout(timer);
    };
  }, [url, start?.site]);

  const daily = Number(budget);
  const done: Record<Step, boolean> = {
    business: Boolean(kind) && isUrl(url),
    sell: themes.length > 0,
    who: places.length > 0,
    promise: true,
    budget: daily > 0,
  };
  const step = STEPS[at] as Step | undefined;
  const canGoOn = step ? done[step] : STEPS.every((s) => done[s]);
  const named = read.state === "found" ? read.name : "";
  const shorts = catalogue.filter((p) => promises.includes(p.id)).map((p) => p.short);
  const win = kind?.win ?? "enquiries";

  const go = (to: number) => {
    setAt(to);
    setReached((r) => Math.max(r, to));
    setTrouble("");
  };

  const write = async () => {
    setWorking(true);
    setTrouble("");
    const { ok, data } = await call<Draft & { error?: string }>("drafts", {
      name,
      themes,
      final_url: url.trim(),
      daily_budget: daily,
      places,
      language,
      bidding,
      negatives: skipped,
      kind: kindId,
      promises,
      years_trading: Number(years) > 0 ? Math.round(Number(years)) : undefined,
    });
    if (!ok) {
      setTrouble(data.error ?? "That did not work. Nothing was sent to Google.");
      setWorking(false);
      return;
    }
    router.push(`/campaigns/new/${data.id}`);
  };

  if (!prefill.connected) {
    return (
      <PwCard className="p-6">
        <p className="text-[16px] leading-[22px]">
          Connect your Google Ads account first, and the campaign is built in it.
        </p>
        <Link href="/settings" className="text-brand mt-3 inline-block font-semibold">
          Go to Settings
        </Link>
      </PwCard>
    );
  }

  const blanks: { before: string; value: string; placeholder: string }[] = [
    {
      before: "Advertise ",
      value: kind ? (named ? `${named}, ${kind.noun}` : kind.noun) : "",
      placeholder: "your business",
    },
    { before: ", selling ", value: joined(themes), placeholder: "what you sell" },
    {
      before: " to people in ",
      value: places.length
        ? `${joined(
            places.map((p) => p.name),
            2,
          )}, in ${language.name}`
        : "",
      placeholder: "the places you choose",
    },
    {
      before: ". We can promise ",
      // Live while it is being answered; "nothing extra" only once it has been.
      value: shorts.length ? joined(shorts) : reached > 3 ? "nothing extra" : "",
      placeholder: "what is true",
    },
    {
      before: ". Spend up to ",
      value:
        (reached > 4 || at === 4) && daily > 0
          ? `${money(daily, currency)} a day, for ${bidding === "clicks" ? "clicks" : win}`
          : "",
      placeholder: "a daily budget",
    },
  ];

  return (
    <div className="flex flex-col gap-5">
      <Sentence blanks={blanks} at={at} reached={reached} onGo={go} />

      <div className="grid items-start gap-5 lg:grid-cols-[minmax(0,1fr)_340px]">
        <PwCard className="p-5 sm:p-7">
          <div key={at} className="pw-step-in">
            {step ? (
              <>
                <h2 className="text-[22px] leading-[28px] font-semibold tracking-[-0.01em]">
                  {QUESTION[step].title}
                </h2>
                <p className="text-pw-ink-500 mt-1 max-w-[620px] text-[15px] leading-[22px]">
                  {QUESTION[step].help}
                </p>
                <div className="mt-6">
                  {step === "business" ? (
                    <BusinessStep
                      kinds={kinds}
                      kindId={kindId}
                      onKind={setKindId}
                      url={url}
                      onUrl={(next) => {
                        setUrl(next);
                        if (!isUrl(next)) setRead({ state: "idle", name: "", title: "" });
                      }}
                      read={read}
                      accountName={prefill.account_name ?? ""}
                    />
                  ) : null}
                  {step === "sell" ? (
                    <div className="flex flex-col gap-6">
                      <Words
                        label="What you sell"
                        words={themes}
                        onChange={setThemes}
                        most={MOST_THEMES}
                        placeholder={kind?.services_hint ?? "Type one and press Add"}
                      />
                      <Field
                        label="Campaign name (optional)"
                        hint="Leave it empty and the first thing you sell names it."
                      >
                        {(id) => (
                          <Input id={id} value={name} onChange={(e) => setName(e.target.value)} />
                        )}
                      </Field>
                    </div>
                  ) : null}
                  {step === "who" ? (
                    <div className="flex flex-col gap-6">
                      <PlacePicker places={places} onChange={setPlaces} />
                      <Field label="The language your customers search in">
                        {(id) => (
                          <select
                            id={id}
                            value={language.resource}
                            onChange={(e) =>
                              setLanguage(
                                languages.find((l) => l.resource === e.target.value) ?? ENGLISH,
                              )
                            }
                            className="border-pw-border-strong bg-pw-card h-[48px] rounded-[12px] border px-4 text-[15px]"
                          >
                            {languages.map((one) => (
                              <option key={one.resource} value={one.resource}>
                                {one.name}
                              </option>
                            ))}
                          </select>
                        )}
                      </Field>
                    </div>
                  ) : null}
                  {step === "promise" ? (
                    <PromiseStep
                      kind={kind}
                      catalogue={catalogue}
                      ticked={promises}
                      onTick={(id) =>
                        setPromises((was) =>
                          was.includes(id) ? was.filter((p) => p !== id) : [...was, id],
                        )
                      }
                      moreShown={moreShown}
                      onMore={() => setMoreShown(true)}
                      years={years}
                      onYears={setYears}
                      skipped={skipped}
                      onSkipped={setNegatives}
                    />
                  ) : null}
                  {step === "budget" ? (
                    <BudgetStep
                      budget={budget}
                      onBudget={setBudget}
                      currency={currency}
                      bidding={bidding}
                      onBidding={setBidding}
                      win={win}
                    />
                  ) : null}
                </div>
              </>
            ) : working ? (
              <Writing />
            ) : (
              <CheckStep trouble={trouble} />
            )}
          </div>

          <div className="border-pw-divider mt-8 flex flex-wrap items-center justify-between gap-3 border-t pt-5">
            {at > 0 ? (
              <Button variant="secondary" onClick={() => go(at - 1)} disabled={working}>
                <ArrowLeftIcon size={16} weight="bold" aria-hidden />
                Back
              </Button>
            ) : (
              <span />
            )}
            {step ? (
              <div className="flex flex-wrap items-center justify-end gap-3">
                {!canGoOn ? (
                  <p className="text-pw-ink-500 text-[13px] leading-[18px]">
                    {step === "business"
                      ? "Choose a kind of business and give the page the ads link to."
                      : step === "sell"
                        ? "Add at least one thing you sell."
                        : step === "who"
                          ? "Add at least one place."
                          : "Set a daily budget above zero."}
                  </p>
                ) : null}
                <Button
                  onClick={() => go(at + 1)}
                  disabled={!canGoOn}
                  className="disabled:bg-pw-muted! disabled:text-pw-ink-500!"
                >
                  {at + 1 < STEPS.length ? `Next: ${QUESTION[STEPS[at + 1]].next}` : "Check it"}
                  <ArrowRightIcon size={16} weight="bold" aria-hidden />
                </Button>
              </div>
            ) : (
              <div className="flex flex-wrap items-center justify-end gap-3">
                {working ? null : (
                  <p className="text-pw-ink-500 text-[13px] leading-[18px]">
                    It takes about a minute.
                  </p>
                )}
                <Button
                  onClick={write}
                  disabled={working}
                  aria-busy={working}
                  // Busy, not unavailable: it stays blue while Otto writes.
                  className={working ? "disabled:bg-pw-blue! disabled:text-white!" : ""}
                >
                  {working ? (
                    <CircleNotchIcon
                      size={16}
                      weight="bold"
                      aria-hidden
                      className="animate-spin motion-reduce:animate-none"
                    />
                  ) : null}
                  {working ? "Writing your campaign…" : "Write my campaign"}
                  {working ? null : <ArrowRightIcon size={16} weight="bold" aria-hidden />}
                </Button>
              </div>
            )}
          </div>
        </PwCard>

        <LivePreview
          name={named || prefill.account_name || ""}
          url={url}
          themes={themes}
          places={places}
          shorts={shorts}
        />
      </div>
    </div>
  );
}

/*
  The stepper itself: the brief as one sentence. Answered parts link back to
  their question, the part being asked is marked, and the rest wait in grey.
*/
function Sentence({
  blanks,
  at,
  reached,
  onGo,
}: {
  blanks: { before: string; value: string; placeholder: string }[];
  at: number;
  reached: number;
  onGo: (to: number) => void;
}) {
  return (
    <nav aria-label="Your campaign so far">
      <p className="sr-only">
        {at < blanks.length ? `Question ${at + 1} of ${blanks.length}` : "Every question answered"}
      </p>
      <p className="text-pw-ink-700 max-w-[980px] text-[21px] leading-[36px] font-semibold tracking-[-0.015em] sm:text-[26px] sm:leading-[44px]">
        {blanks.map((blank, n) => {
          const here = n === at;
          const open = n <= reached;
          const text = blank.value || blank.placeholder;
          return (
            <span key={n}>
              {blank.before}
              {open ? (
                // A link, not a button: an answer is words in a sentence and
                // has to wrap like words. A button is a box that cannot break.
                <a
                  href={`#question-${n + 1}`}
                  onClick={(e) => {
                    e.preventDefault();
                    onGo(n);
                  }}
                  aria-current={here ? "step" : undefined}
                  className={cn(
                    "rounded-[8px] box-decoration-clone transition-colors duration-150",
                    here
                      ? "bg-pw-blue-tint text-pw-blue-ink outline-pw-blue mx-[3px] px-[6px] outline-2"
                      : blank.value
                        ? "text-pw-ink hover:bg-pw-blue-tint decoration-pw-blue underline decoration-2 underline-offset-[7px]"
                        : "text-pw-ink-500 hover:bg-pw-muted decoration-pw-border-strong underline decoration-dashed decoration-2 underline-offset-[7px]",
                  )}
                >
                  <span key={text} className={blank.value ? "pw-fill-in" : undefined}>
                    {text}
                  </span>
                </a>
              ) : (
                <span className="text-pw-ink-500 decoration-pw-border-strong font-medium underline decoration-dashed decoration-2 underline-offset-[7px]">
                  {text}
                </span>
              )}
            </span>
          );
        })}
        .
      </p>
    </nav>
  );
}

function BusinessStep({
  kinds,
  kindId,
  onKind,
  url,
  onUrl,
  read,
  accountName,
}: {
  kinds: BusinessKind[];
  kindId: string;
  onKind: (id: string) => void;
  url: string;
  onUrl: (url: string) => void;
  read: SiteRead;
  accountName: string;
}) {
  return (
    <div className="flex flex-col gap-7">
      <div role="radiogroup" aria-label="Kind of business" className="grid gap-3 sm:grid-cols-2">
        {kinds.map((k) => {
          const Glyph = ICONS[k.id] ?? SparkleIcon;
          const on = k.id === kindId;
          return (
            <button
              key={k.id}
              type="button"
              role="radio"
              aria-checked={on}
              onClick={() => onKind(k.id)}
              className={cn(
                "group flex items-start gap-3 rounded-[14px] border p-4 text-left transition-[background-color,border-color,transform] duration-150 active:scale-[0.99]",
                on
                  ? "border-pw-blue bg-pw-blue-tint"
                  : "border-pw-border hover:border-pw-border-strong hover:bg-pw-muted",
              )}
            >
              <Glyph
                size={24}
                weight={on ? "fill" : "regular"}
                aria-hidden
                className={cn("mt-[1px] shrink-0", on ? "text-pw-blue" : "text-pw-ink-500")}
              />
              <span className="min-w-0">
                <span className="block text-[15px] leading-[20px] font-semibold">{k.label}</span>
                <span className="text-pw-ink-500 mt-[2px] block text-[13px] leading-[18px]">
                  {k.examples}
                </span>
              </span>
            </button>
          );
        })}
      </div>

      <Field label="The page the ads send people to">
        {(id) => (
          <div className="flex flex-col gap-2">
            <Input
              id={id}
              value={url}
              placeholder="https://"
              inputMode="url"
              onChange={(e) => onUrl(e.target.value)}
            />
            <p
              className="text-pw-ink-700 min-h-[20px] text-[14px] leading-[20px]"
              aria-live="polite"
            >
              {read.state === "looking" ? "Reading that page…" : null}
              {read.state === "found" ? (
                <>
                  The ads will be written for <strong className="font-semibold">{read.name}</strong>
                  {read.title ? (
                    <span className="text-pw-ink-500">, from “{read.title}”</span>
                  ) : null}
                  .
                </>
              ) : null}
              {read.state === "none"
                ? `We could not read that page, so the ads will use your Google Ads account's name${
                    accountName ? `, ${accountName}` : ""
                  }.`
                : null}
            </p>
          </div>
        )}
      </Field>
    </div>
  );
}

function PromiseStep({
  kind,
  catalogue,
  ticked,
  onTick,
  moreShown,
  onMore,
  years,
  onYears,
  skipped,
  onSkipped,
}: {
  kind?: BusinessKind;
  catalogue: PromiseOption[];
  ticked: string[];
  onTick: (id: string) => void;
  moreShown: boolean;
  onMore: () => void;
  years: string;
  onYears: (value: string) => void;
  skipped: string[];
  onSkipped: (next: string[]) => void;
}) {
  const first = kind?.promises ?? [];
  const usual = catalogue.filter((p) => first.includes(p.id));
  const rest = catalogue.filter((p) => !first.includes(p.id));
  // A promise ticked from the longer list stays in sight even if it is closed.
  const shownRest = moreShown ? rest : rest.filter((p) => ticked.includes(p.id));
  return (
    <div className="flex flex-col gap-7">
      <div className="flex flex-col gap-3">
        <div className="flex flex-wrap gap-2">
          {[...usual, ...shownRest].map((p) => (
            <Toggle key={p.id} on={ticked.includes(p.id)} onClick={() => onTick(p.id)}>
              {p.label}
            </Toggle>
          ))}
        </div>
        {!moreShown && rest.length ? (
          <button
            type="button"
            onClick={onMore}
            className="text-pw-blue-ink self-start text-[14px] font-semibold hover:underline"
          >
            Show {rest.length} more promises
          </button>
        ) : null}
      </div>

      <Field label="Years in business (optional)" hint="Only used in the ads if you fill it in.">
        {(id) => (
          <Input
            id={id}
            inputMode="numeric"
            value={years}
            onChange={(e) => onYears(e.target.value.replace(/[^0-9]/g, "").slice(0, 3))}
            className="max-w-[160px]"
          />
        )}
      </Field>

      <Words
        label="Searches to skip"
        hint="Your ads will not show for searches containing these. Remove any that are part of what you sell."
        words={skipped}
        onChange={onSkipped}
        placeholder="free, second hand, course…"
      />
    </div>
  );
}

function Toggle({
  on,
  onClick,
  children,
}: {
  on: boolean;
  onClick: () => void;
  children: ReactNode;
}) {
  return (
    <button
      type="button"
      aria-pressed={on}
      onClick={onClick}
      className={cn(
        "inline-flex items-center gap-2 rounded-full border py-[9px] pr-4 pl-3 text-[14px] leading-[18px] font-medium transition-colors duration-150 active:scale-[0.98]",
        on
          ? "border-pw-blue bg-pw-blue text-white"
          : "border-pw-border-strong text-pw-ink-700 hover:bg-pw-muted bg-pw-card",
      )}
    >
      <span
        aria-hidden
        className={cn(
          "flex size-[18px] items-center justify-center rounded-full border",
          on ? "border-white/70 bg-white/15" : "border-pw-border-strong",
        )}
      >
        {on ? <CheckIcon size={11} weight="bold" /> : null}
      </span>
      {children}
    </button>
  );
}

function BudgetStep({
  budget,
  onBudget,
  currency,
  bidding,
  onBidding,
  win,
}: {
  budget: string;
  onBudget: (value: string) => void;
  currency: string;
  bidding: "clicks" | "leads";
  onBidding: (value: "clicks" | "leads") => void;
  win: string;
}) {
  const daily = Number(budget);
  return (
    <div className="flex flex-col gap-7">
      <Field label="The most it may spend a day">
        {(id) => (
          <div className="flex flex-col gap-2">
            <Input
              id={id}
              inputMode="decimal"
              value={budget}
              onChange={(e) => onBudget(e.target.value)}
              trailing={<span className="text-pw-ink-500 text-[14px]">{currency}</span>}
              className="max-w-[220px]"
            />
            <p className="text-pw-ink-700 text-[14px] leading-[20px]">
              {daily > 0
                ? `That is at most about ${money(daily * 30.4, currency)} a month.`
                : "Set an amount above zero."}
            </p>
          </div>
        )}
      </Field>

      <div
        role="radiogroup"
        aria-label="What Google should aim for"
        className="grid gap-3 sm:grid-cols-2"
      >
        {(
          [
            [
              "clicks",
              "Get as many clicks as possible",
              "Best while the campaign is new. Google needs no history to do it.",
            ],
            [
              "leads",
              `Get as many ${win} as possible`,
              `Best once Google Ads is counting your ${win}.`,
            ],
          ] as const
        ).map(([value, title, meta]) => {
          const on = bidding === value;
          return (
            <button
              key={value}
              type="button"
              role="radio"
              aria-checked={on}
              onClick={() => onBidding(value)}
              className={cn(
                "flex flex-col justify-start rounded-[14px] border p-4 text-left transition-colors duration-150",
                on ? "border-pw-blue bg-pw-blue-tint" : "border-pw-border hover:bg-pw-muted",
              )}
            >
              <span className="block text-[15px] leading-[20px] font-semibold">{title}</span>
              <span className="text-pw-ink-500 mt-1 block text-[13px] leading-[18px]">{meta}</span>
            </button>
          );
        })}
      </div>
    </div>
  );
}

/*
  While Otto writes. It takes up to a minute, and a button that only changes
  its words for a minute looks broken. This says what is happening, counts the
  seconds, and says so plainly when it runs long, without pretending to know
  how far along it is: the backend sends no progress, so there is no bar
  filling up to a made-up percentage.
*/
const WRITING = [
  ["Reading your website", "Its name and title, so the ads carry your business's own name."],
  [
    "Asking Google what people search for",
    "Real searches from Keyword Planner, never invented ones.",
  ],
  ["Writing the ads", "Headlines and descriptions for each group of searches, in your words."],
  ["Checking every line", "Length, honesty against what you ticked, and no other company's name."],
] as const;

function Writing() {
  const [seconds, setSeconds] = useState(0);
  useEffect(() => {
    const tick = window.setInterval(() => setSeconds((s) => s + 1), 1000);
    return () => window.clearInterval(tick);
  }, []);
  const clock = `${Math.floor(seconds / 60)}:${String(seconds % 60).padStart(2, "0")}`;
  const note =
    seconds >= 120
      ? "This is taking much longer than usual. You can keep waiting, or go back and try again: nothing has been sent to Google."
      : seconds >= 60
        ? "Still writing. A long website or many services takes a little longer. Nothing has been sent to Google."
        : "This takes up to a minute. You can leave this page open and look at the preview meanwhile.";
  return (
    <div role="status" aria-live="polite">
      <div className="flex items-start justify-between gap-4">
        <div className="flex items-center gap-3">
          <CircleNotchIcon
            size={22}
            weight="bold"
            aria-hidden
            className="text-pw-blue shrink-0 animate-spin motion-reduce:animate-none"
          />
          <h2 className="text-[22px] leading-[28px] font-semibold tracking-[-0.01em]">
            Otto is writing your campaign
          </h2>
        </div>
        <span
          className="pw-num text-pw-ink-500 pt-1 text-[14px] leading-[20px]"
          aria-label={`${seconds} seconds so far`}
        >
          {clock}
        </span>
      </div>
      <div className="bg-pw-blue-tint relative mt-5 h-[5px] overflow-hidden rounded-full">
        <span className="pw-indeterminate bg-pw-blue absolute inset-y-0 left-0 w-1/3 rounded-full" />
      </div>
      <p className="text-pw-ink-600 mt-4 max-w-[620px] text-[14px] leading-[21px]">{note}</p>
      <ol className="mt-6 flex flex-col gap-4">
        {WRITING.map(([title, meta]) => (
          <li key={title} className="flex gap-3">
            <span
              aria-hidden
              className="bg-pw-blue-tint text-pw-blue mt-[2px] flex size-[18px] shrink-0 items-center justify-center rounded-full"
            >
              <span className="bg-pw-blue size-[6px] rounded-full" />
            </span>
            <span>
              <span className="block text-[15px] leading-[20px] font-semibold">{title}</span>
              <span className="text-pw-ink-500 mt-[2px] block text-[14px] leading-[20px]">
                {meta}
              </span>
            </span>
          </li>
        ))}
      </ol>
    </div>
  );
}

function CheckStep({ trouble }: { trouble: string }) {
  return (
    <div>
      <h2 className="text-[22px] leading-[28px] font-semibold tracking-[-0.01em]">
        That is the whole campaign.
      </h2>
      <p className="text-pw-ink-500 mt-1 max-w-[620px] text-[15px] leading-[22px]">
        Read the sentence above once more. Anything underlined takes you back to change it.
      </p>
      <ol className="mt-6 flex flex-col gap-4">
        {[
          [
            "Google says what people really search for",
            "Only real searches, from Keyword Planner. Otto cannot make any up.",
          ],
          [
            "Otto writes the ads",
            "Every line is checked for length, for honesty against what you ticked, and for other companies' names.",
          ],
          [
            "You read it before anything goes live",
            "Change anything you like. Nothing reaches Google, and nothing costs money, until you approve it.",
          ],
        ].map(([title, meta]) => (
          <li key={title} className="flex gap-3">
            <CheckIcon
              size={18}
              weight="bold"
              aria-hidden
              className="text-pw-blue mt-[1px] shrink-0"
            />
            <span>
              <span className="block text-[15px] leading-[20px] font-semibold">{title}</span>
              <span className="text-pw-ink-500 mt-[2px] block text-[14px] leading-[20px]">
                {meta}
              </span>
            </span>
          </li>
        ))}
      </ol>
      {trouble ? (
        <p role="alert" className="mt-5 text-[14px] leading-[20px] font-semibold text-red-700">
          {trouble}
        </p>
      ) : null}
    </div>
  );
}

/*
  How the ad could look, from what has been answered so far. Otto writes the
  real wording later from real searches; this is so the merchant can see the
  answers turning into an ad, not a promise of the words.
*/
function LivePreview({
  name,
  url,
  themes,
  places,
  shorts,
}: {
  name: string;
  url: string;
  themes: string[];
  places: Place[];
  shorts: string[];
}) {
  const host = hostOf(url);
  const cap = (s: string) => (s ? s[0].toUpperCase() + s.slice(1) : s);
  const headline = [name || "Your business", cap(themes[0] ?? ""), cap(shorts[0] ?? "")]
    .filter(Boolean)
    .join(" | ");
  const about = themes.length
    ? `${cap(joined(themes))}${
        places.length
          ? ` for people in ${joined(
              places.map((p) => p.name),
              2,
            )}`
          : ""
      }.`
    : "What you sell goes here.";
  const promise = shorts.length ? ` ${cap(joined(shorts))}.` : "";
  return (
    <aside className="flex flex-col gap-3 lg:sticky lg:top-6" aria-label="How your ad could look">
      <p className="text-pw-ink-700 text-[14px] leading-[20px] font-semibold">
        How your ad could look
      </p>
      <div className="border-pw-border bg-pw-card rounded-[16px] border p-5">
        <p className="text-pw-ink-500 text-[12px] leading-[16px]">
          <span className="text-pw-ink font-bold">Sponsored</span>
          {host ? ` · ${host}` : ""}
        </p>
        <p className="text-brand mt-2 text-[18px] leading-[24px] font-semibold">{headline}</p>
        <p className="text-pw-ink-700 mt-1 text-[14px] leading-[20px]">
          {about}
          {promise}
        </p>
      </div>
      <p className="text-pw-ink-500 text-[13px] leading-[18px]">
        A sketch from your answers. Otto writes the real wording from what people actually search
        for.
      </p>
    </aside>
  );
}
