"use client";

import { Input } from "@/components/ui/field";
import type { Spec } from "@/lib/creation";
import type { StepProps } from "../editor";
import {
  Card,
  Choice,
  Counted,
  Labelled,
  Note,
  NumberBox,
  Panel,
  Problems,
  Tick,
  Toggle,
} from "../kit";
import { LanguagesEditor } from "./a-audience";
import { LocationsEditor, locationsSummary } from "./a-locations";
import { NegativesEditor, UrlOptionsEditor, negativesSummary, urlSummary } from "./a-more";
import { Act, Select, count, useShared } from "./a-parts";
import { ScheduleEditor, scheduleSummary } from "./a-schedule";
import { STORES } from "./b-options";
import { DatesEditor, datesSummary } from "./c-dates";
import { UserListsEditor } from "./c-targeting";
import {
  DEVICE_WORDS,
  PRIORITY_LABEL,
  STORE_LABEL,
  SUBTYPE_LABEL,
  devicesWords,
  type Device,
} from "./c-words";

/*
  Campaign settings for Demand Gen, Display, Shopping and App, row for row
  as each of Google's flows has them. Demand Gen: locations and languages
  with Google's campaign-level switch, devices including TV screens, the EU
  question, then schedule, dates and URL options. Display: the same without
  the switch, and devices that can only be turned off. Shopping: the
  Merchant Center account and its options first, then networks, locations,
  the EU question and more settings. App: the app and the subtype first,
  then locations, languages and the EU question.
*/

const ALL_DEVICES: Device[] = ["DESKTOP", "MOBILE", "TABLET", "CONNECTED_TV"];

export function MoreSettings({ spec, setup, change, problems }: StepProps) {
  const type = spec.type;
  const dg = type === "DEMAND_GEN";
  const display = type === "DISPLAY";
  const shopping = type === "SHOPPING";
  const app = type === "APP";
  const manual = spec.bidding.strategy === "manual_cpc" && (display || shopping);
  const says = (pattern: RegExp) => problems.some((p) => p.blocks && pattern.test(p.words));
  const loc = spec.locations;
  const locationsWrong =
    (loc.mode === "custom" && !loc.targets.length && !loc.radius.length) ||
    (loc.mode === "home" && !loc.home && !setup.home);
  // Google takes a radius on these types, but PPCWay's request for them sends places only.
  const radiusDropped = !shopping && loc.mode === "custom" && loc.radius.length > 0;

  const locations = (
    <Panel
      title="Locations"
      summary={locationsSummary(loc, setup)}
      flagged={locationsWrong || radiusDropped || says(/radius/i)}
      open={locationsWrong || radiusDropped}
    >
      <LocationsEditor loc={loc} setup={setup} onChange={(l) => change("locations", l)} />
      {radiusDropped ? (
        <Note tone="warn">
          {`PPCWay can't send a radius for this campaign type yet, so it would be left out${loc.targets.length ? "" : " and the ads would show everywhere"}. Enter a city, region or postcode instead.`}
        </Note>
      ) : null}
    </Panel>
  );

  const languages = (
    <Panel
      title="Languages"
      summary={spec.languages.map((l) => l.name).join(", ") || "None chosen"}
      flagged={!spec.languages.length}
      open={!spec.languages.length}
    >
      <LanguagesEditor value={spec.languages} onChange={(l) => change("languages", l)} />
      <p className="text-pw-ink-500 text-[13px] leading-[18px]">
        {app
          ? "Google shows your ads to people who use Google, Google Play and YouTube in these languages."
          : "Google shows your ads to people who use Google products in these languages."}
      </p>
    </Panel>
  );

  const eu = (
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
  );

  const schedule = (
    <Panel
      title="Ad schedule"
      summary={scheduleSummary(spec.schedule)}
      flagged={says(/ad schedule/i)}
    >
      <ScheduleEditor
        entries={spec.schedule}
        onChange={(s) => change("schedule", s)}
        // Display and Shopping send schedule bid adjustments only under manual CPC.
        adjust={manual}
        adjustApplies
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
        totalBudget={!app && spec.budget.type === "total"}
      />
    </Panel>
  );

  const devices = (
    <Panel
      title="Devices"
      summary={devicesWords(spec.devices, ALL_DEVICES)}
      flagged={says(/bid adjustment/i)}
    >
      <DeviceTicks devices={spec.devices} onChange={(d) => change("devices", d)} />
      <p className="text-pw-ink-500 text-[13px] leading-[18px]">
        {dg
          ? "Google recommends all eligible devices. TV screens show your video ads on YouTube on TVs."
          : "Display takes no device bid adjustments here. Untick a device to stop ads showing on it."}
      </p>
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
        expanding={false}
      />
    </Panel>
  );

  return (
    <div className="flex flex-col gap-5">
      <Problems items={problems} />

      {display ? (
        <Note>
          Google is moving Display campaigns into Demand Gen through 2026 and 2027. A Display
          campaign made now keeps running, and Google will offer to move it.
        </Note>
      ) : null}

      {shopping ? <MerchantCard spec={spec} change={change} says={says} /> : null}
      {app ? <AppCard spec={spec} change={change} says={says} /> : null}

      <Card>
        {shopping ? (
          <Panel
            title="Networks"
            summary={
              spec.networks.search_partners
                ? "Google Search and search partners"
                : "Google Search only"
            }
          >
            <Tick
              checked={spec.networks.search_partners}
              onChange={(v) => change("networks", { ...spec.networks, search_partners: v })}
              help="Products can also show on other Google sites and partner sites, when people search for them."
            >
              Include Google search partners
            </Tick>
            <p className="text-pw-ink-500 text-[13px] leading-[18px]">
              Shopping ads can&apos;t run on the Display Network. Google refuses it for Shopping
              campaigns, so it isn&apos;t offered.
            </p>
          </Panel>
        ) : null}
        {locations}
        {shopping ? null : languages}
        {dg ? (
          <Panel
            title="Targeting level"
            summary={
              spec.demand_gen.campaign_level_targeting
                ? "Campaign level"
                : "Ad group level, Google's default"
            }
          >
            <Toggle
              on={spec.demand_gen.campaign_level_targeting}
              onChange={(v) =>
                change("demand_gen", { ...spec.demand_gen, campaign_level_targeting: v })
              }
              help="Off keeps Google's default for Demand Gen: locations and languages belong to each ad group, so ad groups added later can reach different places. On sets them once for the whole campaign."
            >
              Enable campaign level location and language targeting
            </Toggle>
            <p className="text-pw-ink-600 text-[13px] leading-[18px]">
              Either way, PPCWay gives the new ad group the locations and languages above, so your
              ads reach the same people. This can&apos;t be changed after the campaign is published.
            </p>
          </Panel>
        ) : null}
        {dg ? devices : null}
        {app && spec.app.subtype === "APP_CAMPAIGN_FOR_ENGAGEMENT" ? (
          <Panel
            title="Your app's users"
            summary={
              spec.audiences.segments.some((s) => s.kind === "user_list")
                ? count(
                    spec.audiences.segments.filter((s) => s.kind === "user_list").length,
                    "list",
                  )
                : "No list chosen yet"
            }
            flagged={says(/list of your app's users/i)}
            open={!spec.audiences.segments.some((s) => s.kind === "user_list")}
          >
            <Note>
              An engagement campaign shows ads only to people who already have your app, so Google
              needs a list of your app&apos;s users to know who they are.
            </Note>
            <UserListsEditor
              value={spec.audiences.segments}
              onChange={(segments) => change("audiences", { ...spec.audiences, segments })}
            />
          </Panel>
        ) : null}
        {eu}
      </Card>

      {app ? (
        <Card title="More settings" help="Optional.">
          {dates}
        </Card>
      ) : (
        <Card title="More settings" help="Optional. Google's defaults suit most campaigns.">
          {dg ? (
            <>
              {schedule}
              {dates}
              {urls}
            </>
          ) : display ? (
            <>
              {schedule}
              {devices}
              {dates}
              {urls}
            </>
          ) : (
            <>
              {dates}
              {schedule}
              {urls}
              <Panel title="Negative keywords" summary={negativesSummary(spec.negatives, 0)}>
                <NegativesEditor
                  negatives={spec.negatives}
                  lists={spec.negative_lists}
                  onNegatives={(n) => change("negatives", n)}
                  onLists={(l) => change("negative_lists", l)}
                  shareable={false}
                />
                <p className="text-pw-ink-500 text-[13px] leading-[18px]">
                  Your products won&apos;t show on searches that contain these words.
                </p>
              </Panel>
            </>
          )}
        </Card>
      )}
    </div>
  );
}

/** Devices turned on or off, with no bid adjustments; at least one stays on. */
function DeviceTicks({
  devices,
  onChange,
}: {
  devices: Spec["devices"];
  onChange: (next: Spec["devices"]) => void;
}) {
  const on = (d: Device) => (devices[d] ?? 0) > -100;
  const onCount = ALL_DEVICES.filter(on).length;
  return (
    <ul className="flex flex-col gap-3">
      {ALL_DEVICES.map((d) => (
        <li key={d}>
          <Tick
            checked={on(d)}
            disabled={on(d) && onCount === 1}
            onChange={(v) => {
              const next = { ...devices };
              if (v) delete next[d];
              else next[d] = -100;
              onChange(next);
            }}
          >
            {DEVICE_WORDS[d].charAt(0).toUpperCase() + DEVICE_WORDS[d].slice(1)}
          </Tick>
        </li>
      ))}
    </ul>
  );
}

type Says = (pattern: RegExp) => boolean;

/*
  Shopping's Merchant Center account, the feed label, campaign priority and
  local inventory ads. The account list is Google Ads' own links; a linked
  account's name lives in Merchant Center, so it is shown by number.
*/
function MerchantCard({
  spec,
  change,
  says,
}: {
  spec: Spec;
  change: StepProps["change"];
  says: Says;
}) {
  const sh = spec.shopping;
  const set = (patch: Partial<Spec["shopping"]>) => change("shopping", { ...sh, ...patch });
  const { shared, trouble } = useShared();
  const merchants = shared?.merchants ?? [];
  const known = merchants.some((m) => Number(m.id) === sh.merchant_id);
  const typeIt = (
    <Labelled
      label="Merchant Center ID"
      hint="The number at the top of Merchant Center, such as 123456789."
      className="sm:w-[260px]"
    >
      <NumberBox
        value={sh.merchant_id}
        onChange={(v) => set({ merchant_id: v === null ? null : Math.trunc(v) })}
        min={1}
        step={1}
        placeholder="123456789"
        ariaLabel="Merchant Center ID"
      />
    </Labelled>
  );

  return (
    <Card title="Products" help="Shopping ads are built from the products in Merchant Center.">
      <Panel
        title="Merchant Center account"
        summary={sh.merchant_id ? `Merchant Center ${sh.merchant_id}` : "Not chosen yet"}
        flagged={says(/merchant center/i)}
        open={!sh.merchant_id}
      >
        {trouble ? (
          <>
            <p className="text-pw-bad text-[13px]">{trouble}</p>
            {typeIt}
          </>
        ) : !shared ? (
          <p className="text-pw-ink-500 text-[13px]">
            Looking for linked Merchant Center accounts…
          </p>
        ) : merchants.length ? (
          <Labelled label="Select a Merchant Center account" className="sm:w-[420px]">
            <Select
              aria-label="Select a Merchant Center account"
              value={sh.merchant_id ? String(sh.merchant_id) : ""}
              onChange={(e) => set({ merchant_id: e.target.value ? Number(e.target.value) : null })}
            >
              <option value="">Choose an account</option>
              {merchants.map((m) => (
                <option key={m.id} value={m.id}>
                  {m.name ? `${m.name} (${m.id})` : `Merchant Center ${m.id}`}
                </option>
              ))}
              {sh.merchant_id && !known ? (
                <option value={String(sh.merchant_id)}>Merchant Center {sh.merchant_id}</option>
              ) : null}
            </Select>
          </Labelled>
        ) : (
          <>
            <Note tone="warn">
              This Google Ads account has no linked Merchant Center account. Link one in Google Ads,
              under Tools, Data manager, then come back to this step. If you have just linked it,
              type its number below.
            </Note>
            {typeIt}
          </>
        )}
        <p className="text-pw-ink-500 text-[13px] leading-[18px]">
          The campaign sells the products in this account. It can&apos;t be changed after the
          campaign is created.
        </p>
      </Panel>

      <Panel title="Feed label" summary={sh.feed_label.trim() || "All products in the account"}>
        <Labelled
          label="Feed label (optional)"
          hint="Only products with this feed label are advertised. Leave it empty to use them all."
          className="sm:w-[320px]"
        >
          <Counted
            value={sh.feed_label}
            onChange={(feed_label) => set({ feed_label })}
            most={20}
            placeholder="For example: US"
            ariaLabel="Feed label"
          />
        </Labelled>
      </Panel>

      <Panel title="Campaign priority" summary={PRIORITY_LABEL[sh.priority]}>
        <fieldset className="flex flex-col gap-3">
          <legend className="text-pw-ink-600 mb-2 text-[13px] leading-[18px]">
            Priority matters only when the same product is in more than one of your Shopping
            campaigns. Google then uses the campaign with the higher priority for it.
          </legend>
          {([0, 1, 2] as const).map((p) => (
            <Choice
              key={p}
              name="campaign-priority"
              checked={sh.priority === p}
              onChange={() => set({ priority: p })}
              help={p === 0 ? "Google's default." : undefined}
            >
              {PRIORITY_LABEL[p]}
            </Choice>
          ))}
        </fieldset>
      </Panel>

      <Panel title="Local inventory ads" summary={sh.enable_local ? "On" : "Off"}>
        <Toggle
          on={sh.enable_local}
          onChange={(enable_local) => set({ enable_local })}
          help="Show products that are in stock in your stores, from the local inventory in your Merchant Center account. Google says these will soon run by default."
        >
          Local inventory ads
        </Toggle>
      </Panel>
    </Card>
  );
}

/*
  App's first questions: which app, from which store, and Google's campaign
  subtype. Both are fixed once the campaign exists. Pre-registration is for
  Android apps not yet released, so it goes when the store is Apple's.
*/
function AppCard({ spec, change, says }: { spec: Spec; change: StepProps["change"]; says: Says }) {
  const a = spec.app;
  const set = (patch: Partial<Spec["app"]>) => change("app", { ...a, ...patch });
  const fromStep1 = spec.ways.app_id.trim();
  const apple = a.store === "APPLE_APP_STORE";

  return (
    <Card title="App" help="The app this campaign promotes.">
      <Panel
        title="Your app"
        summary={
          a.app_id.trim() ? `${a.app_id.trim()}, ${STORE_LABEL[a.store]}` : "No app chosen yet"
        }
        flagged={says(/app to promote/i)}
        open={!a.app_id.trim()}
      >
        <div className="grid gap-4 sm:grid-cols-[220px_minmax(0,1fr)]">
          <Labelled label="App store">
            <Select
              aria-label="App store"
              value={a.store}
              onChange={(e) => {
                const store = e.target.value as Spec["app"]["store"];
                set(
                  store === "APPLE_APP_STORE" && a.subtype === "APP_CAMPAIGN_FOR_PRE_REGISTRATION"
                    ? { store, subtype: "APP_CAMPAIGN" }
                    : { store },
                );
              }}
            >
              {STORES.map((s) => (
                <option key={s.value} value={s.value}>
                  {s.label}
                </option>
              ))}
            </Select>
          </Labelled>
          <Labelled
            label="App ID"
            hint={
              apple
                ? "The number in the app's App Store address, such as 123456789."
                : "The package name in the app's Google Play address, such as com.example.app."
            }
          >
            <Input
              value={a.app_id}
              aria-label="App ID"
              spellCheck={false}
              placeholder={apple ? "123456789" : "com.example.app"}
              onChange={(e) => set({ app_id: e.target.value.trim() })}
            />
          </Labelled>
        </div>
        {!a.app_id.trim() && fromStep1 ? (
          <Act onClick={() => set({ app_id: fromStep1, store: spec.ways.app_store })}>
            Use {fromStep1} from step 1
          </Act>
        ) : null}
        <p className="text-pw-ink-500 text-[13px] leading-[18px]">
          Google reads the app&apos;s name, icon and store listing from the store. The app
          can&apos;t be changed after the campaign is created.
        </p>
      </Panel>

      <Panel title="Campaign subtype" summary={SUBTYPE_LABEL[a.subtype]}>
        <fieldset className="flex flex-col gap-3">
          <legend className="sr-only">Campaign subtype</legend>
          <Choice
            name="app-subtype"
            checked={a.subtype === "APP_CAMPAIGN"}
            onChange={() => set({ subtype: "APP_CAMPAIGN" })}
            help="Get new people to install your app."
          >
            {SUBTYPE_LABEL.APP_CAMPAIGN}
          </Choice>
          <Choice
            name="app-subtype"
            checked={a.subtype === "APP_CAMPAIGN_FOR_ENGAGEMENT"}
            // Engagement bids for actions in the app, never installs.
            onChange={() =>
              set({
                subtype: "APP_CAMPAIGN_FOR_ENGAGEMENT",
                focus: a.focus === "installs" ? "in_app_actions" : a.focus,
                target_cpa: a.focus === "installs" ? null : a.target_cpa,
              })
            }
            help="Get people who already have your app to come back and act in it. Needs a list of your app's users."
          >
            {SUBTYPE_LABEL.APP_CAMPAIGN_FOR_ENGAGEMENT}
          </Choice>
          <Choice
            name="app-subtype"
            checked={a.subtype === "APP_CAMPAIGN_FOR_PRE_REGISTRATION"}
            onChange={() => set({ subtype: "APP_CAMPAIGN_FOR_PRE_REGISTRATION" })}
            disabled={apple}
            help={
              apple
                ? "For Google Play apps only."
                : "Get people to pre-register before the app is released on Google Play."
            }
          >
            {SUBTYPE_LABEL.APP_CAMPAIGN_FOR_PRE_REGISTRATION}
          </Choice>
        </fieldset>
        <p className="text-pw-ink-500 text-[13px] leading-[18px]">
          The subtype can&apos;t be changed after the campaign is created.
        </p>
      </Panel>
    </Card>
  );
}
