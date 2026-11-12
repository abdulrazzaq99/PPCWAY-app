"use client";

import { WarningCircleIcon } from "@phosphor-icons/react";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import {
  call,
  said,
  type Problem,
  type Setup,
  type Spec,
  type SpecDraft,
  type StepId,
} from "@/lib/creation";
import type { StepProps } from "../editor";
import { Card, Note, money } from "../kit";
import { devicesSummary, negativesSummary, urlSummary } from "./a-more";
import { Act, count, customerSentence, dateWords, strategySentence } from "./a-parts";
import { TARGET_OPTION, locationsSummary } from "./a-locations";
import { brandSummary, demographicsSummary } from "./a-pmax";
import { scheduleSummary } from "./a-schedule";
import { isMore, moreLines } from "./c-words";

/*
  Google's review page: the whole campaign in plain sentences, each part
  with a way back to its step; every issue still to fix, each with "Fix it";
  then Google's own check, which creates nothing, and "Publish campaign",
  which creates everything in one request or nothing at all.
*/

type Checked = { ok: boolean; words: string; problems: Problem[] };
type Launched = SpecDraft & { ok: boolean; words: string };

export function StepReview({ draft, spec, setup, allProblems, replace, go, flush }: StepProps) {
  const ids = draft.steps.map((s) => s.id);
  const label = (step: string) =>
    draft.steps.find((s) => s.id === step)?.label ??
    setup.step_labels[step] ??
    (step === "review" ? "Review" : step);
  const fixable = (step: string) => ids.includes(step as StepId) && step !== "review";
  const blocking = allProblems.filter((p) => p.blocks);
  const advice = allProblems.filter((p) => !p.blocks);
  const textAdvice = draft.advice ?? [];
  const adsStep: StepId = spec.type === "PERFORMANCE_MAX" ? "asset_group" : "ads";

  const [busy, setBusy] = useState<"" | "check" | "launch">("");
  const [checked, setChecked] = useState<Checked | null>(null);
  const [failed, setFailed] = useState<{
    words: string;
    problems: Problem[];
    google: string[];
  } | null>(null);

  async function check() {
    setBusy("check");
    setFailed(null);
    // Google checks what is saved, so anything typed goes first.
    if (!(await flush())) {
      setBusy("");
      setChecked({
        ok: false,
        words: "The draft could not be saved, so Google was not asked.",
        problems: [],
      });
      return;
    }
    const { ok, data } = await call<Checked>(`v2/${draft.id}/check`, {});
    setBusy("");
    setChecked(
      ok
        ? { ok: Boolean(data.ok), words: data.words, problems: data.problems ?? [] }
        : { ok: false, words: said(data, "Google could not be asked just now."), problems: [] },
    );
  }

  async function publish() {
    setBusy("launch");
    setChecked(null);
    if (!(await flush())) {
      setBusy("");
      setFailed({
        words: "The draft could not be saved, so nothing was published.",
        problems: [],
        google: [],
      });
      return;
    }
    const { ok, data } = await call<Launched>(`v2/${draft.id}/launch`, {});
    setBusy("");
    if (ok && data.ok) {
      // The editor shows its published page for a launched draft.
      replace(data);
      return;
    }
    if (!ok) {
      setFailed({
        words: said(data, "Publishing did not work. Nothing was created."),
        problems: [],
        google: [],
      });
      return;
    }
    // The reply's `problems` are what stopped it: PPCWay's checks, or Google's
    // reasons when Google refused, each filed against its step.
    setFailed({
      words: data.words,
      problems: (data.problems ?? []).filter((p) => p.blocks),
      google: [],
    });
  }

  const sections: StepId[] = ids.filter((id) => id !== "review");
  // Problems filed against no step of this campaign (Google's general ones) go under Review.
  const groupOf = (p: Problem): StepId =>
    sections.includes(p.step as StepId) ? (p.step as StepId) : "review";
  const groups = [...sections, "review" as StepId].filter((step) =>
    blocking.some((p) => groupOf(p) === step),
  );
  const mayLaunch = Boolean(setup.may_launch);

  return (
    <div className="flex flex-col gap-5">
      <Card
        title="Your campaign"
        help="Everything it will be. Nothing is created in Google Ads until you publish."
      >
        {sections.map((step) => (
          <Section
            key={step}
            title={label(step)}
            flagged={blocking.some((p) => p.step === step)}
            onEdit={() => go(step)}
            lines={linesFor(step, spec, setup)}
          />
        ))}
      </Card>

      {blocking.length ? (
        <Card title="Issues to fix" help="Google won't take the campaign until these are fixed.">
          <div className="flex flex-col gap-5 p-6">
            {groups.map((step) => (
              <div key={step} className="flex flex-col gap-2">
                <p className="text-pw-ink text-[13px] font-semibold">{label(step)}</p>
                <ul className="flex flex-col gap-2">
                  {blocking
                    .filter((p) => groupOf(p) === step)
                    .map((p, at) => (
                      <ProblemRow
                        key={at}
                        problem={p}
                        fix={fixable(p.step) ? () => go(p.step as StepId) : undefined}
                      />
                    ))}
                </ul>
              </div>
            ))}
          </div>
        </Card>
      ) : (
        <Note tone="good">
          Nothing PPCWay can see is stopping this campaign. Check it with Google, then publish.
        </Note>
      )}

      {advice.length || textAdvice.length ? (
        <Card title="Google's advice" help="Worth doing, but none of it stops publishing.">
          <ul className="flex flex-col gap-2 p-6">
            {advice.map((p, at) => (
              <ProblemRow
                key={`a${at}`}
                problem={p}
                fix={fixable(p.step) ? () => go(p.step as StepId) : undefined}
                soft
              />
            ))}
            {textAdvice.map((a, at) => (
              <ProblemRow
                key={`t${at}`}
                problem={{
                  step: adsStep,
                  words: `"${a.text}" in ${a.group}: ${a.because}`,
                  blocks: false,
                }}
                fix={fixable(adsStep) ? () => go(adsStep) : undefined}
                soft
              />
            ))}
          </ul>
        </Card>
      ) : null}

      <Card title="Publish">
        <div className="flex flex-col gap-4 p-6">
          <p className="text-pw-ink-700 text-[14px] leading-[20px]">
            Nothing is created in Google Ads until you press Publish campaign. Then the whole
            campaign is created at once, or nothing is. Google reviews new ads, usually within one
            business day.
          </p>
          <p className="text-pw-ink-500 text-[13px] leading-[18px]">
            Check with Google first if you like: Google reads the whole campaign and says what it
            would refuse, without creating anything.
          </p>
          <div className="flex flex-col gap-3 sm:flex-row">
            <Button
              variant="secondary"
              onClick={check}
              disabled={busy !== ""}
              working={busy === "check" ? "Checking with Google…" : false}
            >
              Check with Google
            </Button>
            <Button
              onClick={publish}
              disabled={busy !== "" || !mayLaunch || blocking.length > 0}
              working={busy === "launch" ? "Publishing…" : false}
            >
              Publish campaign
            </Button>
          </div>
          {!mayLaunch ? (
            <p className="text-pw-ink-600 text-[13px] leading-[18px]">
              Only someone who may approve changes on this account can publish. You can still check
              the campaign with Google and leave it as a draft for them.
            </p>
          ) : blocking.length ? (
            <p className="text-pw-ink-600 text-[13px] leading-[18px]">
              Fix the {count(blocking.length, "issue")} above first, then publish.
            </p>
          ) : null}

          {checked ? (
            <div className="flex flex-col gap-2" aria-live="polite">
              <Note tone={checked.ok ? "good" : "bad"}>{checked.words}</Note>
              {checked.problems.length ? (
                <ul className="flex flex-col gap-2">
                  {checked.problems.map((p, at) => (
                    <ProblemRow
                      key={at}
                      problem={p}
                      fix={fixable(p.step) ? () => go(p.step as StepId) : undefined}
                      soft={!p.blocks}
                    />
                  ))}
                </ul>
              ) : null}
            </div>
          ) : null}

          {failed ? (
            <div className="flex flex-col gap-2" aria-live="polite">
              <Note tone="bad">{failed.words}</Note>
              {failed.google.length || failed.problems.length ? (
                <ul className="flex flex-col gap-2">
                  {failed.google.map((m, at) => (
                    <ProblemRow
                      key={`g${at}`}
                      problem={{ step: "review", words: `Google: ${m}`, blocks: true }}
                    />
                  ))}
                  {failed.problems.map((p, at) => (
                    <ProblemRow
                      key={`p${at}`}
                      problem={p}
                      fix={fixable(p.step) ? () => go(p.step as StepId) : undefined}
                    />
                  ))}
                </ul>
              ) : null}
            </div>
          ) : null}
        </div>
      </Card>
    </div>
  );
}

function Section({
  title,
  flagged,
  onEdit,
  lines,
}: {
  title: string;
  flagged: boolean;
  onEdit: () => void;
  lines: string[];
}) {
  return (
    <div className="border-pw-border flex flex-col gap-2 border-b px-6 py-4 last:border-b-0 sm:flex-row sm:gap-4">
      <div className="flex shrink-0 items-start justify-between gap-3 sm:w-[200px] sm:flex-col sm:justify-start sm:gap-1">
        <h3 className="text-pw-ink flex items-center gap-1 text-[14px] leading-[20px] font-semibold">
          {flagged ? (
            <WarningCircleIcon
              weight="fill"
              className="text-pw-bad size-4 shrink-0"
              aria-label="Needs attention"
            />
          ) : null}
          {title}
        </h3>
        <button
          type="button"
          onClick={onEdit}
          aria-label={`Edit ${title}`}
          className="text-pw-blue hover:text-pw-blue-hover text-[13px] font-semibold hover:underline"
        >
          Edit
        </button>
      </div>
      <div className="text-pw-ink-700 flex min-w-0 flex-1 flex-col gap-1 text-[14px] leading-[20px]">
        {lines.map((line, at) => (
          <p key={at} className="break-words">
            {line}
          </p>
        ))}
      </div>
    </div>
  );
}

function ProblemRow({
  problem,
  fix,
  soft,
}: {
  problem: Problem;
  fix?: () => void;
  soft?: boolean;
}) {
  return (
    <li className="flex items-start gap-3 text-[14px] leading-[20px]">
      <WarningCircleIcon
        weight="fill"
        className={
          soft ? "text-pw-warn mt-[2px] size-4 shrink-0" : "text-pw-bad mt-[2px] size-4 shrink-0"
        }
      />
      <span className="text-pw-ink-700 min-w-0 flex-1">{problem.words}</span>
      {fix ? (
        <Act onClick={fix} className="shrink-0 text-[13px]">
          Fix it
        </Act>
      ) : null}
    </li>
  );
}

/* ---- The summary's sentences, step by step ------------------------------- */

const onOff = (v: boolean) => (v ? "on" : "off");
const filled = (values: string[]) => values.filter((v) => v.trim()).length;

function linesFor(step: StepId, spec: Spec, setup: Setup): string[] {
  const cur = spec.currency;
  const b = spec.bidding;
  const pm = spec.pmax;
  const lines: string[] = [];

  if (step === "goal") {
    const o = setup.objectives[spec.objective];
    const t = setup.types[spec.type];
    lines.push(
      `${/^[AEIOU]/i.test(t?.label ?? spec.type) ? "An" : "A"} ${t?.label ?? spec.type} campaign called "${spec.name || "Untitled campaign"}", for ${o?.label ?? "no set objective"}.`,
    );
    if (o?.goals) {
      const names = spec.goals.chosen.map((g) => g.name || g.category).join(", ");
      lines.push(
        spec.goals.account_default
          ? "Bids for the account's default conversion goals."
          : spec.goals.chosen.length
            ? `Bids for ${count(spec.goals.chosen.length, "conversion goal")} set for this campaign: ${names}.`
            : "No conversion goal is chosen yet.",
      );
    }
    if (spec.ways.website_url) lines.push(`Sends people to ${spec.ways.website_url}.`);
    if (spec.ways.calls)
      lines.push(`Asks for calls${spec.ways.phone_number ? ` to ${spec.ways.phone_number}` : ""}.`);
    if (spec.ways.lead_forms) lines.push("Collects leads with a form in the ad.");
    if (spec.ways.app) lines.push(`Promotes the app ${spec.ways.app_id || "not named yet"}.`);
    if (spec.ways.store_visits) lines.push("Shows your store locations.");
  }

  // Demand Gen, Display, Shopping and App have their own sections; step 1 reads the same.
  if (step !== "goal" && isMore(spec.type)) return moreLines(step, spec, setup);

  if (step === "bidding") {
    lines.push(strategySentence(spec));
    if (b.new_customers !== "off" || b.focus === "conversions" || b.focus === "conversion_value") {
      lines.push(customerSentence(b, cur));
    }
  }

  if (step === "settings") {
    if (spec.type === "SEARCH") {
      const extra = [
        spec.networks.search_partners && "Google search partners",
        spec.networks.display && "the Display Network",
      ].filter(Boolean);
      lines.push(
        extra.length === 2
          ? `Shows on Google Search, ${extra[0]} and ${extra[1]}.`
          : `Shows on Google Search${extra.length ? ` and ${extra[0]}` : " only"}.`,
      );
    }
    lines.push(
      `Locations: ${locationsSummary(spec.locations, setup)}. Reaches ${TARGET_OPTION[spec.locations.target_option].short}.`,
    );
    lines.push(
      spec.type === "SEARCH"
        ? "Language: matched to the language of your ads, as Google now does for Search."
        : `Languages: ${spec.languages.map((l) => l.name).join(", ") || "none chosen yet"}.`,
    );
    if (spec.type === "SEARCH") {
      const segs = spec.audiences.segments;
      lines.push(
        segs.length
          ? `${count(segs.length, "audience segment")}, ${spec.audiences.mode === "observation" ? "observed only, so reach isn't narrowed" : "targeted, so only those people see the ads"}.`
          : "No audience segments.",
      );
    }
    lines.push(
      spec.eu_political === null
        ? "EU political ads: not answered yet."
        : spec.eu_political
          ? "Has EU political ads, so its ads don't show in the European Union."
          : "Has no EU political ads.",
    );
    lines.push(
      `${spec.dates.start ? `Starts ${dateWords(spec.dates.start)}` : "Starts when published"}, ${spec.dates.end ? `ends ${dateWords(spec.dates.end)}` : "with no end date"}.`,
    );
    lines.push(
      spec.schedule.length
        ? `Ad schedule: ${scheduleSummary(spec.schedule)}.`
        : "Runs all day, every day.",
    );
    lines.push(`Devices: ${devicesSummary(spec.devices, spec.type === "PERFORMANCE_MAX")}.`);
    if (spec.type === "PERFORMANCE_MAX") {
      lines.push(
        `Text customization ${onOff(pm.text_customization)}, final URL expansion ${onOff(pm.text_customization && pm.final_url_expansion)}.`,
      );
      lines.push(`Brand guidelines: ${brandSummary(pm.brand_guidelines).toLowerCase()}.`);
      if (pm.brand_exclusions.length)
        lines.push(`${count(pm.brand_exclusions.length, "brand")} excluded.`);
      lines.push(`Demographics: ${demographicsSummary(pm).toLowerCase()}.`);
    }
    const urls = urlSummary(spec.url_options);
    if (urls !== "No options set") lines.push(`Campaign URL options: ${urls}.`);
    if (spec.type === "SEARCH" && spec.ip_exclusions.length) {
      lines.push(`${count(spec.ip_exclusions.length, "IP address", "IP addresses")} excluded.`);
    }
    if (spec.type === "SEARCH" && spec.ad_rotation === "ROTATE_FOREVER")
      lines.push("Ads take turns evenly.");
    lines.push(
      `${negativesSummary(spec.negatives, spec.type === "SEARCH" ? spec.negative_lists.length : 0)}.`,
    );
  }

  if (step === "ai_max") {
    const ai = spec.ai_max;
    if (!ai.enabled) {
      lines.push("AI Max is off. Keywords match only as their match types say.");
    } else {
      lines.push(
        `AI Max is on, with search term matching ${onOff(ai.search_term_matching)}, text customization ${onOff(ai.text_customization)} and final URL expansion ${onOff(ai.text_customization && ai.final_url_expansion)}.`,
      );
      if (ai.brand_inclusions.length)
        lines.push(`Shows only on searches about ${count(ai.brand_inclusions.length, "brand")}.`);
      if (ai.brand_exclusions.length)
        lines.push(`${count(ai.brand_exclusions.length, "brand")} excluded.`);
      const g = ai.text_guidelines;
      if (ai.text_customization && (g.term_exclusions.length || filled(g.messaging_restrictions))) {
        lines.push(
          `Text guidelines: ${count(g.term_exclusions.length, "term exclusion")} and ${count(filled(g.messaging_restrictions), "messaging restriction")}.`,
        );
      }
    }
  }

  if (step === "generation") {
    lines.push(
      spec.generation.done
        ? `Otto read ${spec.generation.url || "your website"} and suggested the ad groups, keywords and ads.`
        : "Not run. The ad groups are written by hand.",
    );
  }

  if (step === "ads" || step === "ad_group") {
    const groups = spec.ad_groups;
    const keywords = groups.reduce((n, g) => n + g.keywords.length, 0);
    const ads = groups.reduce((n, g) => n + g.ads.length, 0);
    lines.push(
      groups.length
        ? `${count(groups.length, "ad group")} with ${count(keywords, "keyword")} and ${count(ads, "responsive search ad")}.`
        : "No ad groups yet.",
    );
    for (const g of groups.slice(0, 6)) {
      lines.push(
        `${g.name || "Ad group"}: ${count(g.keywords.length, "keyword")}, ${count(g.ads.length, "ad")}.`,
      );
    }
    if (groups.length > 6) lines.push(`And ${count(groups.length - 6, "more ad group")}.`);
    const a = spec.assets;
    const assets = [
      a.sitelinks.length && count(a.sitelinks.length, "sitelink"),
      a.callouts.length && count(a.callouts.length, "callout"),
      a.snippets.length && count(a.snippets.length, "structured snippet"),
      a.images.length && count(a.images.length, "image"),
      a.logo && "a logo",
      a.business_name && "a business name",
      (a.call || spec.ways.calls) && "a call asset",
      a.price && "a price asset",
      a.promotion && "a promotion",
      a.lead_form && "a lead form",
      a.app && "an app link",
    ].filter((x): x is string => Boolean(x));
    lines.push(
      assets.length
        ? `Assets: ${assets.join(", ")}.`
        : "No assets yet. Google recommends at least 4 sitelinks.",
    );
  }

  if (step === "asset_group") {
    const g = pm.asset_group;
    lines.push(
      `${g.name || "Asset group 1"}, sending people to ${g.final_url || spec.ways.website_url || "a final URL not set yet"}.`,
    );
    lines.push(
      `${count(filled(g.headlines), "headline")}, ${count(filled(g.long_headlines), "long headline")} and ${count(filled(g.descriptions), "description")}.`,
    );
    const images = g.marketing_images.length + g.square_images.length + g.portrait_images.length;
    lines.push(
      `${count(images, "image")}, ${count(g.logos.length + g.landscape_logos.length, "logo")} and ${count(g.videos.length, "video")}.`,
    );
    if (g.search_themes.length || g.signal.length) {
      lines.push(
        `Signals: ${count(g.search_themes.length, "search theme")} and ${count(g.signal.length, "audience segment")}.`,
      );
    }
  }

  if (step === "budget") {
    const bud = spec.budget;
    if (bud.shared) lines.push(`Uses the shared budget "${bud.shared_name || "chosen earlier"}".`);
    else if (!(bud.amount > 0)) lines.push("No budget set yet.");
    else if (bud.type === "daily") {
      lines.push(
        `${money(bud.amount, cur)} a day on average. Google may spend up to twice that on a busy day, and never more than 30.4 times it in a month.`,
      );
    } else {
      lines.push(
        `${money(bud.amount, cur)} in total, from ${spec.dates.start ? dateWords(spec.dates.start) : "the day it is published"} to ${spec.dates.end ? dateWords(spec.dates.end) : "an end date not set yet"}.`,
      );
    }
  }

  return lines.length ? lines : ["Nothing to show for this step."];
}
