"use client";

import { useState } from "react";
import { cn } from "@/lib/cn";
import { keywordText, MATCH_LABEL, parseKeyword, type Keyword, type Match } from "@/lib/creation";
import { money, Note } from "../kit";
import { AREA } from "./b-form";

/*
  Keywords, typed the way Google's keyword box takes them: one per line,
  broad as plain words, "phrase" in quotes, [exact] in brackets. The box
  keeps what is typed, spaces and half-written quotes included, and the
  campaign keeps the keywords it reads from it. What Keyword Planner said
  about a search stays attached to it while the merchant edits around it.
*/

const KEYWORD_CHARS = 80;
const KEYWORD_WORDS = 10;

function read(text: string, negative: boolean): Keyword[] {
  const out: Keyword[] = [];
  const seen = new Set<string>();
  for (const line of text.split("\n")) {
    // Google's box takes a negative with a minus sign; this box is only negatives.
    const k = parseKeyword(negative ? line.replace(/^\s*-/, "") : line);
    if (!k || !k.text) continue;
    const key = `${k.match}:${k.text.toLowerCase()}`;
    if (seen.has(key)) continue;
    seen.add(key);
    out.push(k);
  }
  return out;
}

const written = (keywords: Keyword[]) => keywords.map(keywordText).join("\n");

/** Planner figures belong to the words of a search, whichever match type it is given. */
function keepFigures(next: Keyword[], before: Keyword[]): Keyword[] {
  return next.map((k) => {
    const old = before.find((b) => b.text.toLowerCase() === k.text.toLowerCase());
    if (!old) return k;
    return {
      ...k,
      monthly: old.monthly,
      competition: old.competition,
      top_of_page_low: old.top_of_page_low,
      top_of_page_high: old.top_of_page_high,
    };
  });
}

export function KeywordBox({
  label,
  help,
  keywords,
  onChange,
  negative = false,
  placeholder,
}: {
  label: string;
  help?: string;
  keywords: Keyword[];
  onChange: (next: Keyword[]) => void;
  negative?: boolean;
  placeholder?: string;
}) {
  const fromCampaign = written(keywords);
  const [text, setText] = useState(fromCampaign);
  const [basis, setBasis] = useState(fromCampaign);
  // Keywords changed somewhere else (generated again, a dropped search added):
  // take them, unless the box already says the same thing.
  if (basis !== fromCampaign) {
    setBasis(fromCampaign);
    if (written(read(text, negative)) !== fromCampaign) setText(fromCampaign);
  }

  const counts = keywords.reduce<Record<Match, number>>(
    (n, k) => ({ ...n, [k.match]: n[k.match] + 1 }),
    { BROAD: 0, PHRASE: 0, EXACT: 0 },
  );
  const long = keywords.filter(
    (k) => k.text.length > KEYWORD_CHARS || k.text.split(/\s+/).length > KEYWORD_WORDS,
  );
  return (
    <div className="flex flex-col gap-2">
      <label className="flex flex-col gap-[6px]">
        {/* The section above says the same in large type; the box is still named for screen readers. */}
        <span className="sr-only">{label}</span>
        {help ? <span className="text-pw-ink-500 text-[12px] leading-[16px]">{help}</span> : null}
        <textarea
          value={text}
          rows={negative ? 4 : 8}
          spellCheck={false}
          placeholder={placeholder}
          onChange={(e) => {
            const next = read(e.target.value, negative);
            setText(e.target.value);
            setBasis(written(next));
            onChange(negative ? next : keepFigures(next, keywords));
          }}
          className={cn(AREA, "font-mono text-[14px]")}
        />
      </label>
      <p className="text-pw-ink-500 text-[12px]" aria-live="polite">
        {keywords.length
          ? `${keywords.length} ${negative ? "negative " : ""}keyword${keywords.length === 1 ? "" : "s"}: ${(
              ["BROAD", "PHRASE", "EXACT"] as Match[]
            )
              .filter((m) => counts[m])
              .map((m) => `${counts[m]} ${MATCH_LABEL[m].toLowerCase()}`)
              .join(", ")}.`
          : negative
            ? "No negative keywords in this ad group."
            : "No keywords yet."}
      </p>
      {long.length ? (
        <p className="text-pw-bad text-[13px]">
          Google takes keywords of up to {KEYWORD_CHARS} characters and {KEYWORD_WORDS} words.
          Shorten: {long.map((k) => `"${k.text.slice(0, 40)}"`).join(", ")}.
        </p>
      ) : null}
    </div>
  );
}

const competition = (c: string) => (c ? c.charAt(0) + c.slice(1).toLowerCase() : "Not known");

/** What Keyword Planner said about each search, in its own column names. */
export function PlannerFigures({ keywords, currency }: { keywords: Keyword[]; currency: string }) {
  const known = keywords.filter((k) => k.monthly || k.competition || k.top_of_page_high);
  if (!known.length) return null;
  return (
    <details open className="group">
      <summary className="text-pw-ink cursor-pointer text-[13px] font-semibold">
        What Keyword Planner says about{" "}
        {known.length === 1 ? "this search" : `these ${known.length} searches`}
      </summary>
      <p className="text-pw-ink-500 mt-2 text-[12px] leading-[17px]">
        Monthly searches are Google&apos;s average over the last 12 months where your ads will show.
        Top of page bids are what advertisers have paid to appear above the results.
      </p>
      <div className="border-pw-border mt-2 max-h-[320px] overflow-auto rounded-[12px] border">
        <table className="w-full min-w-[560px] text-left text-[13px]">
          <thead className="bg-pw-muted text-pw-ink-600 sticky top-0 text-[12px]">
            <tr>
              <th scope="col" className="px-3 py-2 font-semibold">
                Keyword
              </th>
              <th scope="col" className="px-3 py-2 text-right font-semibold">
                Avg. monthly searches
              </th>
              <th scope="col" className="px-3 py-2 font-semibold">
                Competition
              </th>
              <th scope="col" className="px-3 py-2 text-right font-semibold">
                Top of page bid (low range)
              </th>
              <th scope="col" className="px-3 py-2 text-right font-semibold">
                Top of page bid (high range)
              </th>
            </tr>
          </thead>
          <tbody className="divide-pw-border divide-y">
            {known.map((k) => (
              <tr key={`${k.match}:${k.text}`}>
                <td className="text-pw-ink px-3 py-2">{keywordText(k)}</td>
                <td className="px-3 py-2 text-right tabular-nums">
                  {k.monthly ? k.monthly.toLocaleString() : "Not known"}
                </td>
                <td className="px-3 py-2">{competition(k.competition ?? "")}</td>
                <td className="px-3 py-2 text-right tabular-nums">
                  {k.top_of_page_low ? money(k.top_of_page_low, currency) : "Not known"}
                </td>
                <td className="px-3 py-2 text-right tabular-nums">
                  {k.top_of_page_high ? money(k.top_of_page_high, currency) : "Not known"}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </details>
  );
}

/** Keyword Planner's ideas that were left out, with why, and the choice to add one anyway. */
export function Dropped({
  dropped,
  onAdd,
  have,
}: {
  dropped: { text: string; because: string }[];
  onAdd: (text: string) => void;
  have: Keyword[];
}) {
  if (!dropped.length) return null;
  return (
    <details>
      <summary className="text-pw-ink cursor-pointer text-[13px] font-semibold">
        {dropped.length} {dropped.length === 1 ? "idea" : "ideas"} left out, and why
      </summary>
      <ul className="divide-pw-border border-pw-border mt-2 divide-y rounded-[12px] border">
        {dropped.map((d) => {
          const added = have.some((k) => k.text.toLowerCase() === d.text.toLowerCase());
          return (
            <li
              key={d.text}
              className="flex items-start justify-between gap-3 px-3 py-2 text-[13px]"
            >
              <span className="min-w-0">
                <span className="text-pw-ink font-medium">{d.text}</span>
                <span className="text-pw-ink-500 block">{d.because}</span>
              </span>
              <button
                type="button"
                disabled={added}
                onClick={() => onAdd(d.text)}
                className="text-pw-blue disabled:text-pw-ink-300 shrink-0 text-[13px] font-semibold"
              >
                {added ? "Added" : "Add anyway"}
              </button>
            </li>
          );
        })}
      </ul>
    </details>
  );
}

/** Google's three match types in a sentence each, and its advice on broad match. */
export function MatchTypes({ manual, aiMax }: { manual: boolean; aiMax: boolean }) {
  return (
    <details>
      <summary className="text-pw-ink cursor-pointer text-[13px] font-semibold">
        How match types work
      </summary>
      <ul className="text-pw-ink-700 mt-2 flex flex-col gap-2 text-[13px] leading-[19px]">
        <li>
          <span className="font-mono">running shoes</span>: <strong>Broad match</strong>,
          Google&apos;s default. Ads can show on searches related to the meaning, including ones
          without these words.
        </li>
        <li>
          <span className="font-mono">&quot;running shoes&quot;</span>:{" "}
          <strong>Phrase match</strong>. Ads can show on searches that include the meaning of the
          keyword.
        </li>
        <li>
          <span className="font-mono">[running shoes]</span>: <strong>Exact match</strong>. Ads can
          show on searches with the same meaning or intent.
        </li>
      </ul>
      <Note tone={manual ? "warn" : "info"} className="mt-3">
        Google: &quot;It&apos;s critical to use Smart Bidding with broad match.&quot;
        {manual
          ? " This campaign uses manual CPC, so broad keywords may spend on loosely related searches."
          : ""}
        {aiMax
          ? " With AI Max search term matching on, Google also matches searches beyond your keywords, using your landing page and ads. Negative keywords still apply."
          : ""}
      </Note>
    </details>
  );
}
