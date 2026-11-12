"use client";

import { SparkleIcon, TrashIcon } from "@phosphor-icons/react";
import { useState } from "react";
import {
  LIMITS,
  type AdText,
  type Keyword,
  type Pin,
  type SearchAd,
  type Sitelink,
} from "@/lib/creation";
import { Card, Lines, Note } from "../kit";
import { Confirm, DisplayPath, Quiet, Text } from "./b-form";
import { StrengthMeter } from "./b-meter";
import { SearchPreview } from "./b-preview";
import { searchStrength } from "./b-strength";

/*
  One responsive search ad, laid out as Google's ad editor is: the final URL
  and display path, then headlines and descriptions with their pin menus,
  and beside them Ad Strength and a preview. Up to three per ad group.
*/

const HEADLINE_PINS: Pin[] = ["HEADLINE_1", "HEADLINE_2", "HEADLINE_3"];
const DESCRIPTION_PINS: Pin[] = ["DESCRIPTION_1", "DESCRIPTION_2"];

/*
  The kit's line list deals in strings and removes by position, so the pins
  travel with the lines here: a removed line takes its pin with it, and the
  lines after it keep theirs.
*/
function merge(before: AdText[], next: string[]): AdText[] {
  if (next.length < before.length) {
    const gone = before.findIndex((line, i) => line.text !== next[i]);
    const kept = before.filter((_, i) => i !== gone);
    return next.map((text, i) => ({ text, pin: kept[i]?.pin ?? null }));
  }
  return next.map((text, i) => ({ text, pin: before[i]?.pin ?? null }));
}

const pinAt = (lines: AdText[], at: number, pin: Pin | null) =>
  lines.map((l, i) => (i === at ? { ...l, pin } : l));

export function emptyAd(): SearchAd {
  return {
    final_url: "",
    path1: "",
    path2: "",
    headlines: [0, 1, 2].map(() => ({ text: "", pin: null })),
    descriptions: [0, 1].map(() => ({ text: "", pin: null })),
    ai_written: false,
  };
}

export function AdEditor({
  ad,
  at,
  onChange,
  onRemove,
  landing,
  keywords,
  sitelinks,
  callouts,
  business,
  pinsIgnored,
  advice,
}: {
  ad: SearchAd;
  at: number;
  onChange: (next: SearchAd) => void;
  /** Absent for the only ad in the group: an ad group needs one. */
  onRemove?: () => void;
  landing: string;
  keywords: Keyword[];
  sitelinks: Sitelink[];
  callouts: string[];
  business: string;
  /** AI Max text customization and final URL expansion are both on. */
  pinsIgnored: boolean;
  advice: { text: string; because: string }[];
}) {
  const [asking, setAsking] = useState(false);
  const set = (patch: Partial<SearchAd>) => onChange({ ...ad, ...patch });
  const url = ad.final_url.trim() || landing;
  const pinned = [...ad.headlines, ...ad.descriptions].some((l) => l.pin);
  const rating = searchStrength({ ad, keywords, landing, sitelinks });

  return (
    <Card
      title={`Responsive search ad ${at + 1}`}
      help={
        ad.ai_written ? (
          <span className="text-pw-otto-ink inline-flex items-center gap-1">
            <SparkleIcon weight="fill" className="size-[14px]" /> Written by Otto and passed by
            PPCWay&apos;s checks. Every line is yours to change.
          </span>
        ) : (
          "Google mixes your headlines and descriptions into the ad that fits each search best."
        )
      }
      aside={
        onRemove ? (
          <Quiet tone="red" onClick={() => setAsking(true)}>
            <TrashIcon className="size-4" /> Remove
          </Quiet>
        ) : null
      }
    >
      <div className="grid gap-6 p-5 sm:p-6 xl:grid-cols-[minmax(0,1fr)_340px]">
        <div className="flex min-w-0 flex-col gap-5">
          {asking && onRemove ? (
            <Confirm
              words={`Remove ad ${at + 1} and its ${ad.headlines.filter((h) => h.text.trim()).length} headlines?`}
              yes="Remove ad"
              onYes={onRemove}
              onNo={() => setAsking(false)}
            />
          ) : null}
          <Text
            label="Final URL"
            type="url"
            value={ad.final_url}
            placeholder={landing || "https://"}
            hint={
              ad.final_url
                ? "The page people land on when they click this ad."
                : `Empty uses your campaign website${landing ? `, ${landing}` : ""}.`
            }
            onChange={(v) => set({ final_url: v })}
          />
          <DisplayPath
            url={url}
            path1={ad.path1}
            path2={ad.path2}
            onChange={(p) => set({ path1: p.path1, path2: p.path2 })}
          />

          <div className="flex flex-col gap-2">
            <h4 className="text-pw-ink text-[14px] font-semibold">Headlines</h4>
            <p className="text-pw-ink-500 text-[12px] leading-[17px]">
              Write 3 to 15, up to 30 characters each. Google shows up to 3 at a time. A pin keeps a
              headline in one place; positions 1 and 2 always show, position 3 may not. Google says
              pinning &quot;isn&apos;t recommended for most advertisers and can affect ad
              strength&quot;.
            </p>
            <Lines
              values={ad.headlines.map((h) => h.text)}
              onChange={(next) => set({ headlines: merge(ad.headlines, next) })}
              most={LIMITS.headlinesMost}
              least={3}
              longest={LIMITS.headline}
              placeholder="Headline"
              addLabel="Headline"
              pins={HEADLINE_PINS}
              pinned={ad.headlines.map((h) => h.pin)}
              onPin={(i, pin) => set({ headlines: pinAt(ad.headlines, i, pin) })}
            />
          </div>

          <div className="flex flex-col gap-2">
            <h4 className="text-pw-ink text-[14px] font-semibold">Descriptions</h4>
            <p className="text-pw-ink-500 text-[12px] leading-[17px]">
              Write 2 to 4, up to 90 characters each. Google shows up to 2. Description position 1
              always shows when pinned; position 2 may not.
            </p>
            <Lines
              values={ad.descriptions.map((d) => d.text)}
              onChange={(next) => set({ descriptions: merge(ad.descriptions, next) })}
              most={LIMITS.descriptionsMost}
              least={2}
              longest={LIMITS.description}
              placeholder="Description"
              addLabel="Description"
              pins={DESCRIPTION_PINS}
              pinned={ad.descriptions.map((d) => d.pin)}
              onPin={(i, pin) => set({ descriptions: pinAt(ad.descriptions, i, pin) })}
            />
          </div>

          {pinsIgnored && pinned ? (
            <Note tone="warn">
              AI Max text customization and final URL expansion are both on for this campaign, so
              Google won&apos;t respect pins. Turn one of them off on the AI Max step to keep them.
            </Note>
          ) : null}

          {advice.length ? (
            <Note tone="warn">
              <p className="font-semibold">
                PPCWay&apos;s checks flag{" "}
                {advice.length === 1 ? "a line" : `${advice.length} lines`} in this ad
              </p>
              <ul className="mt-1 flex flex-col gap-1">
                {advice.map((a) => (
                  <li key={`${a.text}:${a.because}`}>
                    &quot;{a.text}&quot;: {a.because}
                  </li>
                ))}
              </ul>
              <p className="mt-1">They stay in your ad. Change them if the check is right.</p>
            </Note>
          ) : null}
        </div>

        <div className="flex min-w-0 flex-col gap-4 xl:sticky xl:top-6 xl:self-start">
          <StrengthMeter rating={rating} />
          <SearchPreview
            headlines={ad.headlines}
            descriptions={ad.descriptions}
            url={url}
            path1={ad.path1}
            path2={ad.path2}
            business={business}
            sitelinks={sitelinks}
            callouts={callouts}
          />
        </div>
      </div>
    </Card>
  );
}
