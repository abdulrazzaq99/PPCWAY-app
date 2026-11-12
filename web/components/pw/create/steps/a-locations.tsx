"use client";

import { MapPinIcon, TrashIcon } from "@phosphor-icons/react";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import type { Place, Radius, Setup, Spec } from "@/lib/creation";
import { Choice, Finder, Labelled, NumberBox, Pill } from "../kit";
import { Act, Lookup, Select, count } from "./a-parts";

/*
  Google's Locations setting: "All countries and territories", the
  account's own country, or "Enter another location", where each place found
  is included or excluded and a radius can be drawn around an address
  (Google's "Advanced search", "Radius" tab). Under it, "Location options":
  who counts as being in a place. Exclusions can only be "Presence" now.
*/

type Locations = Spec["locations"];
type Point = { label: string; latitude: number; longitude: number };

export const TARGET_OPTION: Record<Locations["target_option"], { label: string; short: string }> = {
  PRESENCE_OR_INTEREST: {
    label:
      "Presence or interest: People in, regularly in, or who've shown interest in your included locations (recommended)",
    short: "people in, regularly in, or interested in these places",
  },
  PRESENCE: {
    label: "Presence: People in or regularly in your included locations",
    short: "people in or regularly in these places",
  },
};

const UNITS: Record<Radius["units"], string> = { KILOMETERS: "km", MILES: "mi" };

export function radiusWords(r: Radius): string {
  return `${r.radius} ${UNITS[r.units]} around ${r.label || "a point"}`;
}

/** The Locations row's one-line summary. */
export function locationsSummary(loc: Locations, setup: Setup): string {
  const out: string[] = [];
  if (loc.mode === "all") out.push("All countries and territories");
  else if (loc.mode === "home") out.push((loc.home ?? setup.home)?.name ?? "Your country");
  else {
    const named = [...loc.targets.map((p) => p.name), ...loc.radius.map(radiusWords)];
    if (!named.length) out.push("No location entered yet");
    else if (named.length <= 3) out.push(named.join(", "));
    else out.push(`${named.slice(0, 2).join(", ")} and ${named.length - 2} more`);
  }
  if (loc.excluded.length) out.push(`${count(loc.excluded.length, "place")} excluded`);
  return out.join("; ");
}

export function LocationsEditor({
  loc,
  setup,
  onChange,
}: {
  loc: Locations;
  setup: Setup;
  onChange: (next: Locations) => void;
}) {
  const set = (patch: Partial<Locations>) => onChange({ ...loc, ...patch });
  const home = loc.home ?? setup.home ?? null;
  const [options, setOptions] = useState(false);
  const has = (list: Place[], p: Place) => list.some((x) => x.resource === p.resource);

  const include = (p: Place) =>
    set({
      targets: has(loc.targets, p) ? loc.targets : [...loc.targets, p],
      excluded: loc.excluded.filter((x) => x.resource !== p.resource),
    });
  const exclude = (p: Place) =>
    set({
      excluded: has(loc.excluded, p) ? loc.excluded : [...loc.excluded, p],
      targets: loc.targets.filter((x) => x.resource !== p.resource),
    });

  return (
    <div className="flex flex-col gap-4">
      <fieldset className="flex flex-col gap-3">
        <legend className="text-pw-ink mb-2 text-[13px] font-semibold">
          Select locations for this campaign
        </legend>
        <Choice
          name="locations-mode"
          checked={loc.mode === "all"}
          onChange={() => set({ mode: "all" })}
        >
          All countries and territories
        </Choice>
        {home ? (
          <Choice
            name="locations-mode"
            checked={loc.mode === "home"}
            onChange={() => set({ mode: "home", home })}
          >
            {home.name}
          </Choice>
        ) : null}
        <Choice
          name="locations-mode"
          checked={loc.mode === "custom"}
          onChange={() => set({ mode: "custom" })}
        >
          Enter another location
        </Choice>
      </fieldset>

      {loc.mode === "custom" ? (
        <div className="flex flex-col gap-4">
          <Labelled
            label="Enter a location to include or exclude"
            hint="Countries, regions, cities or postcodes, as Google names them."
          >
            <Lookup<Place>
              path={(q) => `places?q=${encodeURIComponent(q)}`}
              pick={(data) =>
                ((data as { places?: Place[] }).places ?? []).filter((p) => p.resource)
              }
              keyOf={(p) => p.resource}
              placeholder="Enter a location to include or exclude"
              ariaLabel="Enter a location to include or exclude"
              empty="Google knows no place by that name."
              row={(p) => (
                <>
                  <span className="min-w-0">
                    <span className="text-pw-ink font-medium">{p.name}</span>
                    {p.kind ? (
                      <span className="text-pw-ink-500 ml-2 text-[12px]">{p.kind}</span>
                    ) : null}
                  </span>
                  <span className="flex shrink-0 gap-2">
                    <Button
                      size="sm"
                      variant={has(loc.targets, p) ? "quiet" : "secondary"}
                      onClick={() => include(p)}
                      disabled={has(loc.targets, p)}
                    >
                      {has(loc.targets, p) ? "Included" : "Include"}
                    </Button>
                    <Button
                      size="sm"
                      variant={has(loc.excluded, p) ? "quiet" : "secondary"}
                      onClick={() => exclude(p)}
                      disabled={has(loc.excluded, p)}
                    >
                      {has(loc.excluded, p) ? "Excluded" : "Exclude"}
                    </Button>
                  </span>
                </>
              )}
            />
          </Labelled>

          <RadiusTool onAdd={(r) => set({ radius: [...loc.radius, r] })} />

          {loc.targets.length || loc.radius.length ? (
            <div className="flex flex-col gap-2">
              <p className="text-pw-ink text-[13px] font-semibold">Targeted locations</p>
              <div className="flex flex-wrap gap-2">
                {loc.targets.map((p) => (
                  <Pill
                    key={p.resource}
                    onRemove={() =>
                      set({ targets: loc.targets.filter((x) => x.resource !== p.resource) })
                    }
                  >
                    {p.name}
                  </Pill>
                ))}
                {loc.radius.map((r, at) => (
                  <Pill
                    key={`${r.latitude},${r.longitude},${at}`}
                    onRemove={() => set({ radius: loc.radius.filter((_, i) => i !== at) })}
                  >
                    {radiusWords(r)}
                  </Pill>
                ))}
              </div>
            </div>
          ) : (
            <p className="text-pw-ink-500 text-[13px]">
              No location is included yet. Add at least one, or choose all countries.
            </p>
          )}
        </div>
      ) : null}

      {loc.excluded.length ? (
        <div className="flex flex-col gap-2">
          <p className="text-pw-ink text-[13px] font-semibold">Excluded locations</p>
          <div className="flex flex-wrap gap-2">
            {loc.excluded.map((p) => (
              <Pill
                key={p.resource}
                tone="red"
                onRemove={() =>
                  set({ excluded: loc.excluded.filter((x) => x.resource !== p.resource) })
                }
              >
                {p.name}
              </Pill>
            ))}
          </div>
        </div>
      ) : null}

      <div className="border-pw-border flex flex-col gap-3 border-t pt-4">
        <Act onClick={() => setOptions((o) => !o)}>
          {options ? "Hide location options" : "Location options"}
        </Act>
        {options ? (
          <div className="flex flex-col gap-4">
            <fieldset className="flex flex-col gap-3">
              <legend className="text-pw-ink mb-2 text-[13px] font-semibold">Include</legend>
              {(Object.keys(TARGET_OPTION) as Locations["target_option"][]).map((o) => (
                <Choice
                  key={o}
                  name="target-option"
                  checked={loc.target_option === o}
                  onChange={() => set({ target_option: o })}
                >
                  {TARGET_OPTION[o].label}
                </Choice>
              ))}
            </fieldset>
            <fieldset className="flex flex-col gap-3">
              <legend className="text-pw-ink mb-2 text-[13px] font-semibold">Exclude</legend>
              <Choice
                name="exclude-option"
                checked
                onChange={() => undefined}
                help="Google no longer offers Presence or interest for exclusions."
              >
                Presence: People in or regularly in your excluded locations
              </Choice>
            </fieldset>
          </div>
        ) : (
          <p className="text-pw-ink-500 text-[13px]">
            Reaching {TARGET_OPTION[loc.target_option].short}.
          </p>
        )}
      </div>
    </div>
  );
}

/*
  A circle around an address. Google Maps finds the point; Google Ads
  targets the point, not the address, and wants a radius of at least 1 km.
*/
function RadiusTool({ onAdd }: { onAdd: (r: Radius) => void }) {
  const [point, setPoint] = useState<Point | null>(null);
  const [radius, setRadius] = useState<number | null>(10);
  const [units, setUnits] = useState<Radius["units"]>("KILOMETERS");
  const least = units === "KILOMETERS" ? 1 : 0.62;
  const ok = point !== null && radius !== null && radius >= least;

  return (
    <div className="border-pw-border flex flex-col gap-3 rounded-[12px] border p-4">
      <p className="text-pw-ink flex items-center gap-2 text-[13px] font-semibold">
        <MapPinIcon className="text-pw-blue size-4" /> Radius
      </p>
      <Finder<Point>
        path={(q) => `geocode?q=${encodeURIComponent(q)}`}
        least={3}
        pick={(data) => {
          const found = (data as { found?: Point | null }).found;
          return found ? [found] : [];
        }}
        keyOf={(p) => `${p.latitude},${p.longitude}`}
        render={(p) => <span className="text-pw-ink">{p.label}</span>}
        placeholder="Enter an address, a place name or a postcode"
        ariaLabel="Address to draw a radius around"
        empty="Google Maps could not find that address."
        onPick={setPoint}
      />
      {point ? (
        <div className="flex flex-col gap-3 sm:flex-row sm:items-end">
          <p className="text-pw-ink-700 min-w-0 flex-1 text-[14px] leading-[20px]">
            Around <span className="text-pw-ink font-semibold">{point.label}</span>
            <button
              type="button"
              aria-label="Clear the address"
              onClick={() => setPoint(null)}
              className="text-pw-ink-400 hover:text-pw-bad ml-2 rounded-full p-1 align-[-3px]"
            >
              <TrashIcon className="size-4" />
            </button>
          </p>
          <Labelled label="Radius" className="sm:w-[120px]">
            <NumberBox value={radius} onChange={setRadius} min={least} ariaLabel="Radius" />
          </Labelled>
          <Labelled label="Units" className="sm:w-[90px]">
            <Select
              aria-label="Units"
              value={units}
              onChange={(e) => setUnits(e.target.value as Radius["units"])}
            >
              <option value="KILOMETERS">km</option>
              <option value="MILES">mi</option>
            </Select>
          </Labelled>
          <Button
            variant="secondary"
            disabled={!ok}
            onClick={() => {
              if (!point || radius === null) return;
              onAdd({ ...point, radius, units });
              setPoint(null);
            }}
          >
            Add radius
          </Button>
        </div>
      ) : (
        <p className="text-pw-ink-500 text-[12px]">
          At least 1 km. Google allows up to 500 radius targets in a campaign.
        </p>
      )}
      {point && radius !== null && radius < least ? (
        <p className="text-pw-bad text-[13px]">A radius has to be at least 1 km.</p>
      ) : null}
    </div>
  );
}
