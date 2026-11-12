"use client";

import { MagicWandIcon, PlusIcon } from "@phosphor-icons/react";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/cn";
import type { AdGroup } from "@/lib/creation";
import type { StepProps } from "../editor";
import { Card, Problems } from "../kit";
import { AssetsCard } from "./b-assets";
import { AdGroupEditor } from "./b-group";
import { emptyAd } from "./b-rsa";

/*
  Google's "Keywords and ads" step: the ad groups, each with its keywords and
  up to three responsive search ads, then the campaign's assets. Generated
  ad groups arrive here to be read and changed; a merchant who skipped
  generation starts one here. Every change is the whole list of ad groups,
  saved a moment later; empty lines stay while typing and the server
  ignores them.
*/

function newGroup(groups: AdGroup[]): AdGroup {
  const taken = new Set(groups.map((g) => g.name.trim().toLowerCase()));
  let n = groups.length + 1;
  while (taken.has(`ad group ${n}`)) n += 1;
  return {
    name: `Ad group ${n}`,
    keywords: [],
    negatives: [],
    ads: [emptyAd()],
    default_bid: null,
    locations_of_interest: [],
    dropped: [],
    short: "",
  };
}

export function StepAds({ draft, spec, change, problems, go }: StepProps) {
  const groups = spec.ad_groups;
  const [picked, setPicked] = useState(0);
  const at = Math.min(picked, Math.max(groups.length - 1, 0));
  const setGroups = (next: AdGroup[]) => change("ad_groups", next);
  const add = () => {
    setGroups([...groups, newGroup(groups)]);
    setPicked(groups.length);
  };
  const keywords = groups.reduce((n, g) => n + g.keywords.length, 0);
  const ads = groups.reduce((n, g) => n + g.ads.length, 0);

  return (
    <div className="flex flex-col gap-5">
      <Problems items={problems} />
      <Card
        title="Ad groups"
        help={
          groups.length
            ? `This campaign has ${groups.length} ad ${groups.length === 1 ? "group" : "groups"}, with ${keywords} keywords and ${ads} ${ads === 1 ? "ad" : "ads"} in all. Keep each group to one product or service, so the ad matches the search.`
            : "An ad group holds keywords and the ads that show for them. Keep each one to a single product or service."
        }
        aside={
          <Button variant="secondary" size="sm" onClick={add}>
            <PlusIcon className="size-4" /> New ad group
          </Button>
        }
      >
        {groups.length ? (
          <div
            role="tablist"
            aria-label="Ad groups"
            className="flex flex-wrap gap-2 px-5 py-4 sm:px-6"
          >
            {groups.map((g, i) => (
              <button
                key={i}
                type="button"
                role="tab"
                aria-selected={i === at}
                onClick={() => setPicked(i)}
                className={cn(
                  "flex min-w-0 flex-col items-start rounded-[12px] border px-4 py-2 text-left transition-colors",
                  i === at
                    ? "border-pw-blue bg-pw-blue-tint"
                    : "border-pw-border hover:border-pw-border-strong hover:bg-pw-muted",
                )}
              >
                <span
                  className={cn(
                    "max-w-[220px] truncate text-[14px] font-semibold",
                    i === at ? "text-pw-blue-ink" : "text-pw-ink",
                  )}
                >
                  {g.name || "Untitled ad group"}
                </span>
                <span className="text-pw-ink-500 text-[12px]">
                  {g.keywords.length} keywords, {g.ads.length} {g.ads.length === 1 ? "ad" : "ads"}
                </span>
              </button>
            ))}
          </div>
        ) : (
          <div className="flex flex-col items-start gap-3 px-6 py-6">
            <p className="text-pw-ink-700 max-w-[620px] text-[14px] leading-[20px]">
              No ad groups yet. Generate them from your site, with keywords from real searches and
              ads written by Otto, or start one yourself.
            </p>
            <div className="flex flex-wrap gap-3">
              <Button size="sm" onClick={() => go("generation")}>
                <MagicWandIcon className="size-4" /> Generate from your site
              </Button>
              <Button size="sm" variant="secondary" onClick={add}>
                <PlusIcon className="size-4" /> New ad group
              </Button>
            </div>
          </div>
        )}
      </Card>

      {groups[at] ? (
        <AdGroupEditor
          key={at}
          group={groups[at]}
          spec={spec}
          advice={draft.advice ?? []}
          onChange={(next) => setGroups(groups.map((g, i) => (i === at ? next : g)))}
          onRemove={() => {
            setGroups(groups.filter((_, i) => i !== at));
            setPicked(Math.max(0, at - 1));
          }}
        />
      ) : null}

      <AssetsCard spec={spec} change={(next) => change("assets", next)} draftId={draft.id} />
    </div>
  );
}
