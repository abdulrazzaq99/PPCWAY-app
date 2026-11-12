"use client";

import type { Spec } from "@/lib/creation";
import type { StepProps } from "../editor";
import { Card, Chips, Choice, Labelled, Note, Panel, Problems, Tick, Toggle } from "../kit";
import { AudiencesEditor, LanguagesEditor, audiencesSummary } from "./a-audience";
import { LocationsEditor, locationsSummary } from "./a-locations";
import {
  DevicesEditor,
  NegativesEditor,
  UrlOptionsEditor,
  devicesSummary,
  negativesSummary,
  urlSummary,
} from "./a-more";
import { BrandPicker, LinesArea, TextGuidelinesEditor, count } from "./a-parts";
import {
  BrandGuidelinesEditor,
  DemographicsEditor,
  brandSummary,
  demographicsSummary,
} from "./a-pmax";
import { ScheduleEditor, scheduleSummary } from "./a-schedule";
import { DatesEditor, datesSummary } from "./c-dates";
import { MoreSettings } from "./c-settings";
import { isMore } from "./c-words";

/*
  Google's "Campaign settings" step, row for row in Google's order. Search:
  networks, locations, languages (gone since September 2026, and said so),
  audience segments, the EU political ads question, then "More settings".
  Performance Max: locations and languages, the asset optimization switches
  and brand guidelines, then its own "More settings" (Google's section 3.4
  order). Each row shows its current choice in a line and opens to change it.
*/

export function StepSettings(props: StepProps) {
  const { spec, setup, change, problems } = props;
  // Demand Gen, Display, Shopping and App have their own settings, in Google's order for each.
  if (isMore(spec.type)) return <MoreSettings {...props} />;
  const search = spec.type === "SEARCH";
  const pmax = spec.type === "PERFORMANCE_MAX";
  const b = spec.bidding;
  // Bid adjustments and "Do not optimize" rotation reach Google only without Smart Bidding.
  const adjustable = b.strategy === "manual_cpc" || b.focus === "clicks";
  const says = (pattern: RegExp) => problems.some((p) => p.blocks && pattern.test(p.words));
  const loc = spec.locations;
  const locationsWrong =
    (loc.mode === "custom" && !loc.targets.length && !loc.radius.length) ||
    (loc.mode === "home" && !loc.home && !setup.home);
  const expanding = search
    ? spec.ai_max.enabled && spec.ai_max.text_customization && spec.ai_max.final_url_expansion
    : spec.pmax.text_customization && spec.pmax.final_url_expansion;
  const setPmax = (patch: Partial<Spec["pmax"]>) => change("pmax", { ...spec.pmax, ...patch });

  const schedule = (
    <Panel
      title="Ad schedule"
      summary={scheduleSummary(spec.schedule)}
      flagged={says(/ad schedule/i)}
    >
      <ScheduleEditor
        entries={spec.schedule}
        onChange={(s) => change("schedule", s)}
        adjust={search}
        adjustApplies={adjustable}
        timeZone={spec.time_zone}
      />
    </Panel>
  );
  const dates = (
    <Panel
      title="Start and end dates"
      summary={datesSummary(spec.dates)}
      flagged={says(/end date/i)}
    >
      <DatesEditor
        dates={spec.dates}
        onChange={(d) => change("dates", d)}
        totalBudget={spec.budget.type === "total"}
      />
    </Panel>
  );
  const devices = (
    <Panel
      title="Devices"
      summary={devicesSummary(spec.devices, pmax)}
      flagged={says(/bid adjustment/i)}
    >
      <DevicesEditor
        devices={spec.devices}
        onChange={(d) => change("devices", d)}
        pmax={pmax}
        smart={!adjustable}
      />
    </Panel>
  );
  const urls = (
    <Panel
      title="Campaign URL options"
      summary={urlSummary(spec.url_options)}
      flagged={says(/custom parameter|tracking template|letters or numbers/i)}
    >
      <UrlOptionsEditor
        value={spec.url_options}
        onChange={(o) => change("url_options", o)}
        expanding={expanding}
      />
    </Panel>
  );
  const negatives = (
    <Panel
      title="Negative keywords"
      summary={negativesSummary(spec.negatives, search ? spec.negative_lists.length : 0)}
    >
      <NegativesEditor
        negatives={spec.negatives}
        lists={spec.negative_lists}
        onNegatives={(n) => change("negatives", n)}
        onLists={(l) => change("negative_lists", l)}
        shareable={search}
      />
      {pmax ? (
        <p className="text-pw-ink-500 text-[13px] leading-[18px]">
          In Performance Max, negative keywords apply to Search and Shopping ads only.
        </p>
      ) : null}
    </Panel>
  );

  return (
    <div className="flex flex-col gap-5">
      <Problems items={problems} />

      <Card>
        {search ? (
          <Panel title="Networks" summary={networksSummary(spec.networks)}>
            <Tick
              checked={spec.networks.search_partners}
              onChange={(v) => change("networks", { ...spec.networks, search_partners: v })}
              help="Ads can appear near search results on other Google sites and on partner sites, when people search for what your keywords cover."
            >
              Include Google search partners
            </Tick>
            <Tick
              checked={spec.networks.display}
              onChange={(v) => change("networks", { ...spec.networks, display: v })}
              help="Ads can also show on relevant websites, videos and apps across the internet when they're likely to get results."
            >
              Include Google Display Network
            </Tick>
            {spec.networks.display ? (
              <p className="text-pw-ink-500 text-[13px] leading-[18px]">
                From February 2027 Google changes how a Search campaign splits its budget with the
                Display Network. To keep today&apos;s split, set the Display Network to low priority
                in Google Ads.
              </p>
            ) : null}
          </Panel>
        ) : null}

        <Panel
          title="Locations"
          summary={locationsSummary(loc, setup)}
          flagged={locationsWrong || says(/radius/i)}
          open={locationsWrong}
        >
          <LocationsEditor loc={loc} setup={setup} onChange={(l) => change("locations", l)} />
        </Panel>

        <Panel
          title="Languages"
          summary={
            search
              ? "Matched to the language of your ads"
              : spec.languages.map((l) => l.name).join(", ") || "None chosen"
          }
          flagged={!search && !spec.languages.length}
          open={!search && !spec.languages.length}
        >
          {search ? (
            <Note>
              Google removed language targeting from Search campaigns in late September 2026. Search
              ads now show to people based on the language of your ads, so there is nothing to
              choose here.
            </Note>
          ) : (
            <>
              <LanguagesEditor value={spec.languages} onChange={(l) => change("languages", l)} />
              <p className="text-pw-ink-500 text-[13px] leading-[18px]">
                Languages no longer apply to Google Search for Performance Max. They still decide
                who sees your ads on YouTube, Display, Discover and Gmail.
              </p>
            </>
          )}
        </Panel>

        {search ? (
          <Panel title="Audience segments" summary={audiencesSummary(spec.audiences)}>
            <AudiencesEditor value={spec.audiences} onChange={(a) => change("audiences", a)} />
          </Panel>
        ) : null}

        <Panel
          title="EU political ads"
          summary={
            spec.eu_political === null
              ? "Not answered yet. Google requires an answer."
              : spec.eu_political
                ? "Yes, this campaign has EU political ads"
                : "No EU political ads"
          }
          flagged={spec.eu_political === null}
          open={spec.eu_political === null}
        >
          <fieldset className="flex flex-col gap-3">
            <legend className="text-pw-ink-600 mb-2 text-[13px] leading-[18px]">
              Does your campaign have European Union political ads? Google asks every campaign.
            </legend>
            <Choice
              name="eu-political"
              checked={spec.eu_political === false}
              onChange={() => change("eu_political", false)}
            >
              No, this campaign doesn&apos;t have EU political ads
            </Choice>
            <Choice
              name="eu-political"
              checked={spec.eu_political === true}
              onChange={() => change("eu_political", true)}
              help="Ads in a campaign declared this way don't show anywhere in the European Union."
            >
              Yes, this campaign has EU political ads
            </Choice>
          </fieldset>
        </Panel>
      </Card>

      {pmax ? (
        <Card
          title="Asset optimization"
          help="What Google AI may write and change for this campaign."
        >
          <Panel title="Text customization" summary={spec.pmax.text_customization ? "On" : "Off"}>
            <Toggle
              on={spec.pmax.text_customization}
              // Final URL expansion needs text customization, so it goes off with it.
              onChange={(v) =>
                setPmax({
                  text_customization: v,
                  final_url_expansion: v && spec.pmax.final_url_expansion,
                })
              }
              help="Google AI may write text assets from your landing page, ads and keywords, and use them in your ads. Not used for Shopping ads."
            >
              Text customization
            </Toggle>
            {spec.pmax.text_customization ? (
              <div className="flex flex-col gap-2">
                <p className="text-pw-ink text-[13px] font-semibold">Text guidelines</p>
                <TextGuidelinesEditor
                  value={spec.pmax.text_guidelines}
                  onChange={(g) => setPmax({ text_guidelines: g })}
                />
              </div>
            ) : null}
          </Panel>
          <Panel
            title="Final URL expansion"
            summary={
              expanding
                ? spec.pmax.url_exclusions.length
                  ? `On, ${count(spec.pmax.url_exclusions.length, "URL")} excluded`
                  : "On"
                : "Off"
            }
          >
            <Toggle
              on={expanding}
              disabled={!spec.pmax.text_customization}
              onChange={(v) => setPmax({ final_url_expansion: v })}
              help={
                spec.pmax.text_customization
                  ? "Google may send people to a more relevant page on your site than your final URL, and write a headline to match it."
                  : "Needs text customization on."
              }
            >
              Final URL expansion
            </Toggle>
            {expanding ? (
              <Labelled
                label="URL exclusions"
                hint="Pages Google must not send people to. A full address is matched exactly; a word excludes every address containing it."
              >
                <Chips
                  values={spec.pmax.url_exclusions}
                  onChange={(u) => setPmax({ url_exclusions: u })}
                  placeholder="https://www.example.com/careers or careers"
                  ariaLabel="Add a URL exclusion"
                />
              </Labelled>
            ) : null}
            <p className="text-pw-ink-500 text-[13px] leading-[18px]">
              Google doesn&apos;t expand final URLs for a campaign whose only goals are store
              visits.
            </p>
          </Panel>
          <Panel title="Brand guidelines" summary={brandSummary(spec.pmax.brand_guidelines)}>
            <BrandGuidelinesEditor
              value={spec.pmax.brand_guidelines}
              onChange={(g) => setPmax({ brand_guidelines: g })}
            />
          </Panel>
        </Card>
      ) : null}

      <Card title="More settings" help="Optional. Google's defaults suit most campaigns.">
        {search ? (
          <>
            {dates}
            {schedule}
            {devices}
            {urls}
            <Panel
              title="IP exclusions"
              summary={
                spec.ip_exclusions.length
                  ? count(spec.ip_exclusions.length, "IP address", "IP addresses")
                  : "None"
              }
              flagged={says(/IP exclusion/i)}
            >
              <Labelled
                label="IP addresses to exclude"
                hint={`One a line: a single address, or a range such as 203.0.113.0/24. ${spec.ip_exclusions.length} of 500.`}
              >
                <LinesArea
                  lines={spec.ip_exclusions}
                  onChange={(ips) => change("ip_exclusions", ips)}
                  ariaLabel="IP addresses to exclude, one a line"
                  placeholder={"203.0.113.10\n198.51.100.0/24"}
                />
              </Labelled>
              <p className="text-pw-ink-500 text-[13px] leading-[18px]">
                People browsing from these addresses, such as your own office, won&apos;t see your
                ads.
              </p>
            </Panel>
            <Panel
              title="Ad rotation"
              summary={spec.ad_rotation === "OPTIMIZE" ? "Optimize" : "Do not optimize"}
            >
              <fieldset className="flex flex-col gap-3">
                <legend className="sr-only">Ad rotation</legend>
                <Choice
                  name="ad-rotation"
                  checked={spec.ad_rotation === "OPTIMIZE"}
                  onChange={() => change("ad_rotation", "OPTIMIZE")}
                  help="Google shows the ads it expects to do best more often."
                >
                  Optimize: Prefer best performing ads
                </Choice>
                <Choice
                  name="ad-rotation"
                  checked={spec.ad_rotation === "ROTATE_FOREVER"}
                  onChange={() => change("ad_rotation", "ROTATE_FOREVER")}
                  help="Ads take turns evenly for as long as they run."
                >
                  Do not optimize: Rotate ads indefinitely
                </Choice>
              </fieldset>
              {!adjustable ? (
                <p className="text-pw-ink-500 text-[13px] leading-[18px]">
                  Smart Bidding always optimizes rotation, so this choice applies only under manual
                  CPC or Maximize clicks.
                </p>
              ) : null}
            </Panel>
            {negatives}
          </>
        ) : (
          <>
            {schedule}
            {dates}
            <Panel
              title="Brand exclusions"
              summary={
                spec.pmax.brand_exclusions.length
                  ? `${count(spec.pmax.brand_exclusions.length, "brand")} excluded`
                  : "None"
              }
            >
              <BrandPicker
                values={spec.pmax.brand_exclusions}
                onChange={(list) => setPmax({ brand_exclusions: list })}
                ariaLabel="Search brands to exclude"
                tone="red"
              />
              <p className="text-pw-ink-500 text-[13px] leading-[18px]">
                Your ads won&apos;t show on searches about these brands, on Search and Shopping.
              </p>
            </Panel>
            <Panel title="Demographic exclusions" summary={demographicsSummary(spec.pmax)}>
              <DemographicsEditor
                ages={spec.pmax.excluded_ages}
                genders={spec.pmax.excluded_genders}
                onChange={(d) => setPmax(d)}
              />
            </Panel>
            {urls}
            {devices}
            {negatives}
          </>
        )}
      </Card>
    </div>
  );
}

function networksSummary(n: Spec["networks"]): string {
  const out = ["Google Search"];
  if (n.search_partners) out.push("search partners");
  if (n.display) out.push("Display Network");
  return out.length === 3
    ? "Google Search, search partners and Display Network"
    : out.join(" and ");
}
