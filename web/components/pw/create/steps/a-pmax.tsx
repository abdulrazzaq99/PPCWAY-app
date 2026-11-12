"use client";

import { Input } from "@/components/ui/field";
import type { Spec } from "@/lib/creation";
import { Labelled, Note, Tick, Toggle } from "../kit";
import { Select } from "./a-parts";

/*
  The Performance Max settings Search has no counterpart for: brand
  guidelines and demographic exclusions.
*/

type Pmax = Spec["pmax"];
type Guidelines = Pmax["brand_guidelines"];

/** The fonts Google's brand guidelines accept, spelled as Google wants them. */
export const FONTS = [
  "Open Sans",
  "Roboto",
  "Montserrat",
  "Poppins",
  "Lato",
  "Oswald",
  "Playfair Display",
  "Roboto Slab",
];

const HEX = /^#[0-9a-fA-F]{6}$/;

export function brandSummary(g: Guidelines): string {
  if (!g.enabled) return "Off";
  const out = ["On"];
  if (g.main_color && g.accent_color) out.push(`colors ${g.main_color} and ${g.accent_color}`);
  if (g.font) out.push(g.font);
  return out.join(", ");
}

/*
  Brand guidelines: on by default for a new Performance Max campaign, and
  Google never lets them be turned off once the campaign exists. With them
  on, the business name and logos from the asset group step are linked to
  the campaign. Colours go as a pair or not at all.
*/
export function BrandGuidelinesEditor({
  value,
  onChange,
}: {
  value: Guidelines;
  onChange: (next: Guidelines) => void;
}) {
  const set = (patch: Partial<Guidelines>) => onChange({ ...value, ...patch });
  const half = Boolean(value.main_color) !== Boolean(value.accent_color);
  return (
    <div className="flex flex-col gap-4">
      <Toggle
        on={value.enabled}
        onChange={(v) => set({ enabled: v })}
        help="Your business name, logos, colors and font, kept the same in every ad Google makes for this campaign."
      >
        Brand guidelines
      </Toggle>
      <Note>
        Once the campaign is published with brand guidelines on, Google doesn&apos;t let you turn
        them off. Your business name and logo come from the asset group step.
      </Note>
      {value.enabled ? (
        <>
          <div className="grid gap-4 sm:grid-cols-2">
            <ColorBox
              label="Main color"
              value={value.main_color}
              onChange={(c) => set({ main_color: c })}
            />
            <ColorBox
              label="Accent color"
              value={value.accent_color}
              onChange={(c) => set({ accent_color: c })}
            />
          </div>
          {half ? (
            <p className="text-pw-bad text-[13px]">Google needs both colors, or neither.</p>
          ) : null}
          <Labelled
            label="Font"
            hint="Optional. Google uses it in the ads it builds."
            className="sm:w-[280px]"
          >
            <Select
              aria-label="Font"
              value={value.font}
              onChange={(e) => set({ font: e.target.value })}
            >
              <option value="">No font chosen</option>
              {FONTS.map((f) => (
                <option key={f} value={f}>
                  {f}
                </option>
              ))}
            </Select>
          </Labelled>
        </>
      ) : null}
    </div>
  );
}

function ColorBox({
  label,
  value,
  onChange,
}: {
  label: string;
  value: string;
  onChange: (next: string) => void;
}) {
  const bad = Boolean(value) && !HEX.test(value);
  return (
    <Labelled label={label} hint="A hex code, such as #2F5BD3.">
      <div className="flex items-center gap-2">
        <input
          type="color"
          aria-label={`Pick the ${label.toLowerCase()}`}
          value={HEX.test(value) ? value.toLowerCase() : "#ffffff"}
          onChange={(e) => onChange(e.target.value)}
          className="border-pw-border-input h-[46px] w-[52px] shrink-0 cursor-pointer rounded-[12px] border bg-transparent p-1"
        />
        <Input
          value={value}
          aria-label={label}
          placeholder="#2F5BD3"
          maxLength={7}
          spellCheck={false}
          invalid={bad}
          onChange={(e) => {
            const typed = e.target.value.trim();
            onChange(typed && !typed.startsWith("#") ? `#${typed}` : typed);
          }}
          className="flex-1"
        />
      </div>
    </Labelled>
  );
}

const AGES: { id: string; label: string }[] = [
  { id: "AGE_RANGE_18_24", label: "18-24" },
  { id: "AGE_RANGE_25_34", label: "25-34" },
  { id: "AGE_RANGE_35_44", label: "35-44" },
  { id: "AGE_RANGE_45_54", label: "45-54" },
  { id: "AGE_RANGE_55_64", label: "55-64" },
  { id: "AGE_RANGE_65_UP", label: "65+" },
];

const GENDERS: { id: string; label: string }[] = [
  { id: "MALE", label: "Male" },
  { id: "FEMALE", label: "Female" },
];

export function demographicsSummary(p: Pmax): string {
  const out: string[] = [];
  const ages = AGES.filter((a) => p.excluded_ages.includes(a.id)).map((a) => a.label);
  const genders = GENDERS.filter((g) => p.excluded_genders.includes(g.id)).map((g) =>
    g.label.toLowerCase(),
  );
  if (ages.length) out.push(`Ages ${ages.join(", ")} excluded`);
  if (genders.length) out.push(`${genders.join(" and ")} excluded`);
  return out.length ? out.join("; ") : "No exclusions";
}

/*
  Demographic exclusions: ages and genders ticked here see no ads. Google
  refuses a campaign that excludes every age or every gender, so the last
  one left cannot be ticked. People whose age or gender Google doesn't know
  are always included.
*/
export function DemographicsEditor({
  ages,
  genders,
  onChange,
}: {
  ages: string[];
  genders: string[];
  onChange: (next: { excluded_ages: string[]; excluded_genders: string[] }) => void;
}) {
  const flip = (list: string[], id: string, on: boolean) =>
    on ? [...list, id] : list.filter((x) => x !== id);
  return (
    <div className="flex flex-col gap-4">
      <fieldset className="flex flex-col gap-2">
        <legend className="text-pw-ink mb-2 text-[13px] font-semibold">Exclude ages</legend>
        <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">
          {AGES.map((a) => {
            const on = ages.includes(a.id);
            return (
              <Tick
                key={a.id}
                checked={on}
                disabled={!on && ages.length >= AGES.length - 1}
                onChange={(v) =>
                  onChange({ excluded_ages: flip(ages, a.id, v), excluded_genders: genders })
                }
              >
                {a.label}
              </Tick>
            );
          })}
        </div>
      </fieldset>
      <fieldset className="flex flex-col gap-2">
        <legend className="text-pw-ink mb-2 text-[13px] font-semibold">Exclude genders</legend>
        <div className="flex flex-wrap gap-6">
          {GENDERS.map((g) => {
            const on = genders.includes(g.id);
            return (
              <Tick
                key={g.id}
                checked={on}
                disabled={!on && genders.length >= GENDERS.length - 1}
                onChange={(v) =>
                  onChange({ excluded_ages: ages, excluded_genders: flip(genders, g.id, v) })
                }
              >
                {g.label}
              </Tick>
            );
          })}
        </div>
      </fieldset>
      <p className="text-pw-ink-500 text-[13px] leading-[18px]">
        People whose age or gender Google doesn&apos;t know still see your ads. Gender exclusions
        are a Google beta.
      </p>
    </div>
  );
}
