"use client";

import type { Spec } from "@/lib/creation";
import type { StepProps } from "../editor";
import { Card, Chips, Labelled, Note, Problems, Toggle } from "../kit";
import { Act, BrandPicker, TextGuidelinesEditor, count } from "./a-parts";

/*
  Google's "AI Max" page for a new Search campaign. AI Max is on by default
  and brings three things: search term matching, text customization and
  final URL expansion, plus brand inclusions and exclusions, which a new
  Search campaign can only use with AI Max on. It also replaced the old
  campaign-level broad match setting, which Google stopped accepting on
  3 August 2026. Turning AI Max off keeps every choice below for when it is
  turned back on, as Google does; nothing under it is sent while it is off.
*/

type AiMax = Spec["ai_max"];

export function StepAiMax({ spec, change, problems, go }: StepProps) {
  const ai = spec.ai_max;
  const set = (patch: Partial<AiMax>) => change("ai_max", { ...ai, ...patch });
  const manual = spec.bidding.strategy === "manual_cpc";
  const expanding = ai.text_customization && ai.final_url_expansion;
  const brands = ai.brand_inclusions.length + ai.brand_exclusions.length;

  if (spec.type !== "SEARCH") {
    return <Note>AI Max is a setting of Search campaigns. This campaign has none.</Note>;
  }

  return (
    <div className="flex flex-col gap-5">
      <Problems items={problems} />

      <Card>
        <div className="flex flex-col gap-4 p-6">
          <Toggle
            on={ai.enabled}
            onChange={(v) => set({ enabled: v })}
            help="AI Max uses your landing pages, ads and keywords to find more of the searches that matter to you, write text that fits each one, and send people to the most relevant page on your site."
          >
            <span className="text-[16px]">AI Max for Search campaigns</span>
          </Toggle>
          <ul className="text-pw-ink-700 grid gap-2 text-[14px] leading-[20px] sm:grid-cols-3 sm:pl-[50px]">
            <li>
              <span className="text-pw-ink font-semibold">Search term matching.</span> Reaches
              searches your keywords miss.
            </li>
            <li>
              <span className="text-pw-ink font-semibold">Text customization.</span> Writes
              headlines and descriptions to fit each search.
            </li>
            <li>
              <span className="text-pw-ink font-semibold">Final URL expansion.</span> Sends people
              to the best page for their search.
            </li>
          </ul>
          <Note>
            The old broad match campaign setting no longer exists. Google stopped accepting it on 3
            August 2026 and moved existing ones into AI Max, whose search term matching does that
            job now. Broad, phrase and exact stay as match types on each keyword.
          </Note>
        </div>
      </Card>

      {ai.enabled ? (
        <>
          <Card title="Search term matching">
            <div className="flex flex-col gap-4 p-6">
              <Toggle
                on={ai.search_term_matching}
                onChange={(v) => set({ search_term_matching: v })}
                help="Uses broad match, plus your landing pages and assets, to show your ads on more relevant searches. Your negative keywords are still respected. With it off, each keyword matches only as its match type says."
              >
                Search term matching
              </Toggle>
              {manual && ai.search_term_matching ? (
                <Note tone="warn">
                  Search term matching doesn&apos;t work with manual CPC bidding. Turn it off, or
                  choose another bid strategy.{" "}
                  <button
                    type="button"
                    onClick={() => go("bidding")}
                    className="font-semibold underline"
                  >
                    Go to bidding
                  </button>
                </Note>
              ) : null}
            </div>
          </Card>

          <Card title="Asset optimization">
            <div className="flex flex-col gap-5 p-6">
              <Toggle
                on={ai.text_customization}
                // Final URL expansion needs text customization, so it goes off with it.
                onChange={(v) =>
                  set({ text_customization: v, final_url_expansion: v && ai.final_url_expansion })
                }
                help="Writes headlines and descriptions from your website, landing pages, ads and keywords. Turning it off also turns off final URL expansion."
              >
                Text customization
              </Toggle>
              <Toggle
                on={expanding}
                disabled={!ai.text_customization}
                onChange={(v) => set({ final_url_expansion: v })}
                help={
                  ai.text_customization
                    ? "Sends people to the page on your site that best fits their search, rather than only the final URL of your ad."
                    : "Needs text customization on."
                }
              >
                Final URL expansion
              </Toggle>
              {expanding ? (
                <>
                  <Note tone="warn">
                    With text customization and final URL expansion both on, Google doesn&apos;t
                    respect pinned headlines and descriptions.
                  </Note>
                  <Labelled
                    label="URL exclusions"
                    hint="Pages Google must not send people to. A full address is matched exactly; a word (URL contains) excludes every address containing it as a whole word."
                  >
                    <Chips
                      values={ai.url_exclusions}
                      onChange={(u) => set({ url_exclusions: u })}
                      placeholder="https://www.example.com/careers or careers"
                      ariaLabel="Add a URL exclusion"
                    />
                  </Labelled>
                </>
              ) : null}
              {ai.text_customization ? (
                <div className="border-pw-border flex flex-col gap-3 border-t pt-5">
                  <div>
                    <p className="text-pw-ink text-[14px] font-semibold">Text guidelines</p>
                    <p className="text-pw-ink-500 text-[13px] leading-[18px]">
                      Keep Google&apos;s written text on brand. Generated text that breaks a
                      guideline stops showing.
                    </p>
                  </div>
                  <TextGuidelinesEditor
                    value={ai.text_guidelines}
                    onChange={(g) => set({ text_guidelines: g })}
                  />
                </div>
              ) : null}
            </div>
          </Card>

          <Card
            title="Brand settings"
            help="Google's brand library. Exclusions win over inclusions."
          >
            <div className="flex flex-col gap-5 p-6">
              <Labelled
                label="Brand inclusions"
                hint="Show ads only on searches that mention these brands."
              >
                <BrandPicker
                  values={ai.brand_inclusions}
                  onChange={(list) => set({ brand_inclusions: list })}
                  ariaLabel="Search brands to include"
                />
              </Labelled>
              <Labelled
                label="Brand exclusions"
                hint="Don't show ads on searches about these brands."
              >
                <BrandPicker
                  values={ai.brand_exclusions}
                  onChange={(list) => set({ brand_exclusions: list })}
                  ariaLabel="Search brands to exclude"
                  tone="red"
                />
              </Labelled>
            </div>
          </Card>
        </>
      ) : (
        <Card title="With AI Max off">
          <div className="flex flex-col gap-4 p-6">
            <ul className="text-pw-ink-700 flex list-disc flex-col gap-1 pl-5 text-[14px] leading-[20px]">
              <li>
                Keywords match only as their match types say. There is no search term matching.
              </li>
              <li>Google writes no headlines or descriptions for you.</li>
              <li>Every click goes to the final URL of your ad.</li>
              <li>No brand inclusions or brand exclusions apply.</li>
            </ul>
            <Note>
              In a new Search campaign, brand lists need AI Max on.
              {brands
                ? ` The ${count(brands, "brand")} you chose ${brands === 1 ? "is" : "are"} kept here and come back if you turn AI Max on. Nothing is sent while it is off.`
                : ""}
            </Note>
            <Act onClick={() => set({ enabled: true })}>Turn AI Max back on</Act>
          </div>
        </Card>
      )}
    </div>
  );
}
