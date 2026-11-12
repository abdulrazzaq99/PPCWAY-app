"use client";

import {
  ArrowLeftIcon,
  ArrowRightIcon,
  CheckCircleIcon,
  CircleIcon,
  CloudCheckIcon,
  WarningCircleIcon,
} from "@phosphor-icons/react";
import Link from "next/link";
import { useCallback, useEffect, useRef, useState, type ComponentType } from "react";
import { Button, LinkButton } from "@/components/ui/button";
import { cn } from "@/lib/cn";
import {
  call,
  said,
  type Problem,
  type Setup,
  type Spec,
  type SpecDraft,
  type StepId,
} from "@/lib/creation";
import { StepAds } from "./steps/ads";
import { StepAiMax } from "./steps/ai-max";
import { StepAssetGroup } from "./steps/asset-group";
import { StepBidding } from "./steps/bidding";
import { StepBudget } from "./steps/budget";
import { StepGeneration } from "./steps/generation";
import { StepGoal } from "./steps/goal";
import { StepMoreAdGroup } from "./steps/more-ad-group";
import { StepMoreAds } from "./steps/more-ads";
import { StepReview } from "./steps/review";
import { StepSettings } from "./steps/settings";

/*
  A campaign being created, on Google's own steps.

  Google's creation screen keeps the steps in a menu on the left, each one
  marked done, current, or needing attention, and saves as the advertiser
  goes so a draft can be left and picked up. This is that: every change is
  saved a moment after it is made, the menu shows what each step still needs,
  and Next goes on in Google's order. Nothing reaches Google until the review
  step's "Publish campaign".
*/

export type StepProps = {
  draft: SpecDraft;
  spec: Spec;
  setup: Setup;
  /** Change one section of the campaign; it is saved a moment later. */
  change: <K extends keyof Spec>(key: K, value: Spec[K]) => void;
  /** What PPCWay's checks say about this step. */
  problems: Problem[];
  /** What they say about every step, for the review page. */
  allProblems: Problem[];
  /** Take a whole new draft from the server, after generation or a check. */
  replace: (next: SpecDraft) => void;
  go: (step: StepId) => void;
  /** Save anything not yet saved, and wait for it. */
  flush: () => Promise<boolean>;
};

const SCREENS: Record<StepId, ComponentType<StepProps>> = {
  goal: StepGoal,
  bidding: StepBidding,
  settings: StepSettings,
  ai_max: StepAiMax,
  generation: StepGeneration,
  ads: StepAds,
  asset_group: StepAssetGroup,
  ad_group: StepAds,
  budget: StepBudget,
  review: StepReview,
};

type Saving = { state: "idle" | "saving" | "saved" | "failed"; words?: string };

export function CampaignEditor({
  initial,
  setup,
  startAt,
}: {
  initial: SpecDraft;
  setup: Setup;
  startAt?: string;
}) {
  const [draft, setDraft] = useState(initial);
  const [spec, setSpec] = useState(initial.spec);
  const [problems, setProblems] = useState(initial.problems);
  const [saving, setSaving] = useState<Saving>({ state: "idle" });
  const ids = draft.steps.map((s) => s.id);
  const [step, setStep] = useState<StepId>(
    ids.includes(startAt as StepId) ? (startAt as StepId) : (ids[1] ?? "goal"),
  );
  const [visited, setVisited] = useState<Set<StepId>>(() => new Set(["goal", step]));

  const pending = useRef<Partial<Spec>>({});
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const chain = useRef<Promise<boolean>>(Promise.resolve(true));

  const flush = useCallback(async (): Promise<boolean> => {
    if (timer.current) {
      clearTimeout(timer.current);
      timer.current = null;
    }
    chain.current = chain.current.then(async () => {
      const body = pending.current;
      if (!Object.keys(body).length) return true;
      pending.current = {};
      setSaving({ state: "saving" });
      const { ok, data } = await call<SpecDraft>(`v2/${initial.id}`, body);
      if (!ok) {
        // Put the unsaved sections back, behind anything newer.
        pending.current = { ...body, ...pending.current };
        setSaving({
          state: "failed",
          words: said(data, "Could not save. Your changes are kept here."),
        });
        return false;
      }
      setProblems(data.problems);
      setDraft((d) => ({
        ...d,
        problems: data.problems,
        advice: data.advice,
        status: data.status,
      }));
      setSaving({ state: "saved" });
      return true;
    });
    return chain.current;
  }, [initial.id]);

  const change = useCallback(
    <K extends keyof Spec>(key: K, value: Spec[K]) => {
      setSpec((s) => ({ ...s, [key]: value }));
      pending.current = { ...pending.current, [key]: value };
      setSaving({ state: "idle" });
      if (timer.current) clearTimeout(timer.current);
      timer.current = setTimeout(() => void flush(), 700);
    },
    [flush],
  );

  const replace = useCallback((next: SpecDraft) => {
    pending.current = {};
    setDraft(next);
    setSpec(next.spec);
    setProblems(next.problems);
  }, []);

  const go = useCallback(
    (next: StepId) => {
      void flush();
      setStep(next);
      setVisited((v) => new Set(v).add(next));
      window.history.replaceState(null, "", `?step=${next}`);
      window.scrollTo({ top: 0, behavior: "smooth" });
    },
    [flush],
  );

  // Leaving with something unsaved: save it on the way out.
  useEffect(() => {
    const save = () => {
      if (Object.keys(pending.current).length) {
        navigator.sendBeacon?.(
          `/api/campaigns/v2/${initial.id}`,
          new Blob([JSON.stringify(pending.current)], { type: "application/json" }),
        );
      }
    };
    window.addEventListener("pagehide", save);
    return () => window.removeEventListener("pagehide", save);
  }, [initial.id]);

  if (draft.status === "launched") {
    return <Published draft={draft} />;
  }

  const at = ids.indexOf(step);
  // Demand Gen, Display, Shopping and App have their own ad group and ads
  // screens; the Search ones are for keywords and responsive search ads.
  const other = spec.type !== "SEARCH" && spec.type !== "PERFORMANCE_MAX";
  const Screen =
    other && step === "ad_group"
      ? StepMoreAdGroup
      : other && step === "ads"
        ? StepMoreAds
        : SCREENS[step];
  const mine = problems.filter((p) => p.step === step);
  const typeLabel = setup.types[spec.type]?.label ?? spec.type;

  return (
    <div className="grid gap-6 lg:grid-cols-[248px_minmax(0,1fr)]">
      <nav aria-label="Campaign steps" className="lg:sticky lg:top-6 lg:self-start">
        <div className="bg-pw-card border-pw-border rounded-[18px] border p-3">
          <p className="text-pw-ink-500 px-3 pt-2 pb-1 text-[12px] font-semibold tracking-[0.04em] uppercase">
            {typeLabel} campaign
          </p>
          <p className="text-pw-ink truncate px-3 pb-3 text-[15px] font-semibold">
            {spec.name || "Untitled campaign"}
          </p>
          <ol className="flex flex-col gap-[2px]">
            {draft.steps.map((s, n) => {
              const flagged = problems.some((p) => p.step === s.id && p.blocks);
              const done = visited.has(s.id) && !flagged && s.id !== "review";
              const current = s.id === step;
              return (
                <li key={s.id}>
                  <button
                    type="button"
                    onClick={() => go(s.id)}
                    aria-current={current ? "step" : undefined}
                    className={cn(
                      "flex w-full items-center gap-3 rounded-[12px] px-3 py-[10px] text-left text-[14px] transition-colors",
                      current
                        ? "bg-pw-blue-tint text-pw-blue-ink font-semibold"
                        : "text-pw-ink-700 hover:bg-pw-muted",
                    )}
                  >
                    {flagged && visited.has(s.id) ? (
                      <WarningCircleIcon
                        weight="fill"
                        className="text-pw-bad size-[18px] shrink-0"
                        aria-label="Needs attention"
                      />
                    ) : done ? (
                      <CheckCircleIcon
                        weight="fill"
                        className="text-pw-good size-[18px] shrink-0"
                        aria-label="Done"
                      />
                    ) : (
                      <CircleIcon
                        weight={current ? "fill" : "regular"}
                        className={cn(
                          "size-[18px] shrink-0",
                          current ? "text-pw-blue" : "text-pw-ink-300",
                        )}
                      />
                    )}
                    <span className="min-w-0 flex-1 truncate">{s.label}</span>
                    <span className="text-pw-ink-400 text-[11px] tabular-nums">{n + 1}</span>
                  </button>
                </li>
              );
            })}
          </ol>
          <SaveState saving={saving} onRetry={() => void flush()} />
        </div>
      </nav>

      <div className="flex min-w-0 flex-col gap-4">
        <div className="flex items-end justify-between gap-4">
          <div>
            <p className="text-pw-ink-500 text-[13px]">
              Step {at + 1} of {ids.length}
            </p>
            <h1 className="text-pw-ink text-[26px] leading-[32px] font-semibold tracking-[-0.01em]">
              {draft.steps[at]?.label}
            </h1>
          </div>
        </div>

        <Screen
          draft={draft}
          spec={spec}
          setup={setup}
          change={change}
          problems={mine}
          allProblems={problems}
          replace={replace}
          go={go}
          flush={flush}
        />

        {step !== "review" ? (
          <div className="flex items-center justify-between gap-3 pt-2">
            {at > 0 ? (
              <Button variant="secondary" onClick={() => go(ids[at - 1])}>
                <ArrowLeftIcon className="size-4" /> Back
              </Button>
            ) : (
              <span />
            )}
            <Button onClick={() => go(ids[at + 1])}>
              Next <ArrowRightIcon className="size-4" />
            </Button>
          </div>
        ) : null}
      </div>
    </div>
  );
}

function SaveState({ saving, onRetry }: { saving: Saving; onRetry: () => void }) {
  return (
    <div className="border-pw-border mt-3 border-t px-3 pt-3 pb-1 text-[12px]" aria-live="polite">
      {saving.state === "saving" ? (
        <span className="text-pw-ink-500">Saving the draft…</span>
      ) : saving.state === "failed" ? (
        <span className="text-pw-bad">
          {saving.words}{" "}
          <button type="button" onClick={onRetry} className="font-semibold underline">
            Try again
          </button>
        </span>
      ) : (
        <span className="text-pw-ink-500 inline-flex items-center gap-1">
          <CloudCheckIcon className="size-4" /> Saved as a draft. Nothing is live until you publish.
        </span>
      )}
    </div>
  );
}

function Published({ draft }: { draft: SpecDraft }) {
  return (
    <div className="bg-pw-card border-pw-border flex flex-col items-start gap-4 rounded-[18px] border p-8">
      <CheckCircleIcon weight="fill" className="text-pw-good size-10" />
      <h1 className="text-pw-ink text-[26px] leading-[32px] font-semibold">
        {draft.spec.name} is published.
      </h1>
      <p className="text-pw-ink-700 max-w-[620px] text-[15px] leading-[22px]">
        Google reviews new ads, usually within one business day, and its bidding needs a week or two
        of its own data to settle. The campaign shows on your Campaigns page within a few minutes.
      </p>
      <div className="flex gap-3">
        <LinkButton href="/campaigns">Go to campaigns</LinkButton>
        <Link href="/campaigns/new" className="text-pw-blue self-center text-[14px] font-semibold">
          Create another campaign
        </Link>
      </div>
    </div>
  );
}
