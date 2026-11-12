"use client";

import { TrashIcon } from "@phosphor-icons/react";
import { useState } from "react";
import {
  LIMITS,
  type AdGroup,
  type Place,
  type SearchAd,
  type Spec,
  type SpecDraft,
} from "@/lib/creation";
import { Card, Finder, Note, NumberBox, Pill, money } from "../kit";
import { Confirm, Quiet, Section, Text } from "./b-form";
import { Dropped, KeywordBox, MatchTypes, PlannerFigures } from "./b-keywords";
import { AdEditor, emptyAd } from "./b-rsa";

/*
  One ad group, as Google's "Keywords and ads" step lays it out: its name,
  the keywords that decide which searches it can show on, its own negative
  keywords, AI Max's locations of interest, a default bid under manual CPC,
  then its responsive search ads.
*/
export function AdGroupEditor({
  group,
  onChange,
  onRemove,
  spec,
  advice,
}: {
  group: AdGroup;
  onChange: (next: AdGroup) => void;
  onRemove: () => void;
  spec: Spec;
  advice: NonNullable<SpecDraft["advice"]>;
}) {
  const [asking, setAsking] = useState(false);
  const set = (patch: Partial<AdGroup>) => onChange({ ...group, ...patch });
  const setAd = (at: number, next: SearchAd) =>
    set({ ads: group.ads.map((a, i) => (i === at ? next : a)) });
  const landing = spec.ways.website_url || spec.generation.url;
  const manual = spec.bidding.strategy === "manual_cpc";
  const ai = spec.ai_max;
  const pinsIgnored = ai.enabled && ai.text_customization && ai.final_url_expansion;
  const mine = advice.filter((a) => a.group === group.name);

  return (
    <div className="flex flex-col gap-4">
      <Card>
        <div className="flex flex-col gap-3 px-5 pt-5 sm:px-6">
          <div className="flex flex-col gap-3 sm:flex-row sm:items-end">
            <Text
              label="Ad group name"
              value={group.name}
              placeholder="Ad group 1"
              onChange={(v) => set({ name: v })}
              className="flex-1"
            />
            <div className="sm:pb-3">
              <Quiet tone="red" onClick={() => setAsking(true)}>
                <TrashIcon className="size-4" /> Remove ad group
              </Quiet>
            </div>
          </div>
          {asking ? (
            <Confirm
              words={`Remove "${group.name || "this ad group"}" with its ${group.keywords.length} keywords and ${group.ads.length} ${group.ads.length === 1 ? "ad" : "ads"}?`}
              yes="Remove ad group"
              onYes={() => {
                setAsking(false);
                onRemove();
              }}
              onNo={() => setAsking(false)}
            />
          ) : null}
          {group.short ? <Note tone="warn">{group.short}</Note> : null}
        </div>

        <Section
          title="Keywords"
          help="Keywords are the searches this ad group can show on. One per line: plain words for broad match, quotes for phrase match, brackets for exact match."
        >
          <KeywordBox
            label="Keywords"
            keywords={group.keywords}
            onChange={(keywords) => set({ keywords })}
            placeholder={'running shoes\n"trail running shoes"\n[womens running shoes]'}
          />
          <PlannerFigures keywords={group.keywords} currency={spec.currency} />
          <Dropped
            dropped={group.dropped}
            have={group.keywords}
            onAdd={(text) => set({ keywords: [...group.keywords, { text, match: "BROAD" }] })}
          />
          <MatchTypes manual={manual} aiMax={ai.enabled && ai.search_term_matching} />
        </Section>

        <Section
          title="Negative keywords"
          help="Searches this ad group should never show on. Same notation: plain words, quotes or brackets. Negatives do not match close variants."
        >
          <KeywordBox
            label="Negative keywords"
            negative
            keywords={group.negatives}
            onChange={(negatives) => set({ negatives })}
            placeholder={'free\n"second hand"'}
          />
        </Section>

        {ai.enabled ? (
          <Section
            title="Locations of interest"
            help="AI Max only. Show this ad group's ads to people searching about these places, wherever they are."
          >
            <Finder<Place>
              path={(q) => `places?q=${encodeURIComponent(q)}`}
              pick={(d) => (d as { places?: Place[] }).places ?? []}
              keyOf={(p) => p.resource}
              render={(p) => (
                <>
                  <span className="text-pw-ink">{p.name}</span>
                  <span className="text-pw-ink-500 text-[12px]">{p.kind}</span>
                </>
              )}
              placeholder="Search for a city, region or country"
              ariaLabel="Add a location of interest"
              onPick={(p) => {
                if (!group.locations_of_interest.some((x) => x.resource === p.resource)) {
                  set({ locations_of_interest: [...group.locations_of_interest, p] });
                }
              }}
            />
            {group.locations_of_interest.length ? (
              <div className="flex flex-wrap gap-2">
                {group.locations_of_interest.map((p) => (
                  <Pill
                    key={p.resource}
                    onRemove={() =>
                      set({
                        locations_of_interest: group.locations_of_interest.filter(
                          (x) => x.resource !== p.resource,
                        ),
                      })
                    }
                  >
                    {p.name}
                  </Pill>
                ))}
              </div>
            ) : null}
          </Section>
        ) : null}

        {manual ? (
          <Section
            title="Default bid"
            help={`The most this ad group pays for a click under manual CPC. ${
              spec.bidding.default_bid
                ? `Empty uses the campaign's ${money(spec.bidding.default_bid, spec.currency)} from the Bidding step.`
                : "Empty uses the default bid from the Bidding step."
            }`}
          >
            <div className="max-w-[220px]">
              <NumberBox
                value={group.default_bid}
                onChange={(v) => set({ default_bid: v })}
                unit={spec.currency}
                min={0}
                step={0.01}
                ariaLabel="Default bid"
              />
            </div>
          </Section>
        ) : null}
      </Card>

      {group.ads.map((ad, at) => (
        <AdEditor
          key={at}
          ad={ad}
          at={at}
          onChange={(next) => setAd(at, next)}
          onRemove={
            group.ads.length > 1
              ? () => set({ ads: group.ads.filter((_, i) => i !== at) })
              : undefined
          }
          landing={landing}
          keywords={group.keywords}
          sitelinks={spec.assets.sitelinks}
          callouts={spec.assets.callouts}
          business={spec.assets.business_name}
          pinsIgnored={pinsIgnored}
          advice={mine.filter((a) =>
            [...ad.headlines, ...ad.descriptions].some((l) => l.text.trim() === a.text.trim()),
          )}
        />
      ))}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <Quiet
          onClick={() => set({ ads: [...group.ads, emptyAd()] })}
          disabled={group.ads.length >= LIMITS.adsPerGroup}
        >
          + Add another ad
        </Quiet>
        <span className="text-pw-ink-400 text-[12px]">
          {group.ads.length} of {LIMITS.adsPerGroup} responsive search ads. Google recommends at
          least 2 rated Good or Excellent.
        </span>
      </div>
    </div>
  );
}
