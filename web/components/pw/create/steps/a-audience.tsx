"use client";

import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/field";
import { call, said, type Place, type Segment, type Spec } from "@/lib/creation";
import { Choice, Pill, Tick } from "../kit";
import { Lookup, count } from "./a-parts";

/*
  Languages, for Performance Max (Search has had none since late September
  2026), and audience segments with Google's "Targeting setting", for Search.
  Performance Max takes audiences only as signals on its asset group.
*/

type Language = { resource: string; name: string; code: string };

/*
  Google's language picker: the chosen ones as chips, and a box that finds
  the rest by name. The list is Google's own, asked once when opened.
*/
export function LanguagesEditor({
  value,
  onChange,
}: {
  value: Place[];
  onChange: (next: Place[]) => void;
}) {
  const [all, setAll] = useState<Language[] | null>(null);
  const [trouble, setTrouble] = useState("");
  const [typed, setTyped] = useState("");

  useEffect(() => {
    let live = true;
    void call<{ languages?: Language[] }>("languages").then(({ ok, data }) => {
      if (!live) return;
      if (ok) setAll(data.languages ?? []);
      else setTrouble(said(data, "Google could not list its languages just now."));
    });
    return () => {
      live = false;
    };
  }, []);

  const chosen = new Set(value.map((l) => l.resource));
  const q = typed.trim().toLowerCase();
  const matches = (all ?? [])
    .filter((l) => !chosen.has(l.resource) && (!q || l.name.toLowerCase().includes(q)))
    .slice(0, q ? 12 : 8);

  return (
    <div className="flex flex-col gap-3">
      {value.length ? (
        <div className="flex flex-wrap gap-2">
          {value.map((l) => (
            <Pill
              key={l.resource}
              onRemove={() => onChange(value.filter((x) => x.resource !== l.resource))}
            >
              {l.name || l.resource}
            </Pill>
          ))}
        </div>
      ) : (
        <p className="text-pw-bad text-[13px]">Choose at least one language.</p>
      )}
      <Input
        value={typed}
        aria-label="Find a language"
        placeholder={all ? "Start typing a language" : "Loading Google's languages…"}
        disabled={!all}
        onChange={(e) => setTyped(e.target.value)}
      />
      {trouble ? <p className="text-pw-bad text-[13px]">{trouble}</p> : null}
      {all && matches.length ? (
        <div className="flex flex-wrap gap-2">
          {matches.map((l) => (
            <button
              key={l.resource}
              type="button"
              onClick={() => {
                onChange([...value, { resource: l.resource, name: l.name }]);
                setTyped("");
              }}
              className="border-pw-border hover:border-pw-blue text-pw-ink rounded-full border px-3 py-[6px] text-[13px]"
            >
              + {l.name}
            </button>
          ))}
        </div>
      ) : all && q ? (
        <p className="text-pw-ink-500 text-[13px]">Google targets no language by that name.</p>
      ) : null}
    </div>
  );
}

type Audiences = Spec["audiences"];

/** The Audience segments row's one-line summary. */
export function audiencesSummary(a: Audiences): string {
  if (!a.segments.length) return "No audience segments";
  const out = a.segments.filter((s) => s.excluded).length;
  const mode = a.mode === "observation" ? "Observation" : "Targeting";
  return `${count(a.segments.length - out, "segment")}${out ? `, ${out} excluded` : ""}. ${mode}`;
}

// Google lets custom and combined segments be added, not excluded.
const EXCLUDABLE: Segment["kind"][] = ["user_list", "user_interest"];

export function AudiencesEditor({
  value,
  onChange,
}: {
  value: Audiences;
  onChange: (next: Audiences) => void;
}) {
  const set = (patch: Partial<Audiences>) => onChange({ ...value, ...patch });
  const has = (s: Segment) => value.segments.some((x) => x.resource === s.resource);

  return (
    <div className="flex flex-col gap-4">
      <Lookup<Segment>
        path={(q) => `audiences?q=${encodeURIComponent(q)}`}
        pick={(data) =>
          ((data as { segments?: Segment[] }).segments ?? []).filter((s) => s.resource)
        }
        keyOf={(s) => s.resource}
        group={(s) => s.group ?? ""}
        placeholder="Search for segments, such as fitness or website visitors"
        ariaLabel="Search audience segments"
        empty="Google has no segment by that name in this account or its own lists."
        row={(s) => (
          <>
            <span className="min-w-0">
              <span className="text-pw-ink font-medium">{s.name}</span>
              {s.size ? (
                <span className="text-pw-ink-500 ml-2 text-[12px]">
                  About {s.size.toLocaleString()} people
                </span>
              ) : null}
            </span>
            <Button
              size="sm"
              variant={has(s) ? "quiet" : "secondary"}
              disabled={has(s)}
              onClick={() =>
                set({
                  segments: [
                    ...value.segments,
                    {
                      kind: s.kind,
                      resource: s.resource,
                      name: s.name,
                      group: s.group,
                      excluded: false,
                    },
                  ],
                })
              }
            >
              {has(s) ? "Added" : "Add"}
            </Button>
          </>
        )}
      />

      {value.segments.length ? (
        <ul className="flex flex-col gap-2">
          {value.segments.map((s) => (
            <li key={s.resource} className="flex flex-wrap items-center justify-between gap-3">
              <Pill
                tone={s.excluded ? "red" : "blue"}
                onRemove={() =>
                  set({ segments: value.segments.filter((x) => x.resource !== s.resource) })
                }
              >
                {s.excluded ? "Excluded: " : ""}
                {s.name}
              </Pill>
              {EXCLUDABLE.includes(s.kind) ? (
                <Tick
                  checked={Boolean(s.excluded)}
                  onChange={(v) =>
                    set({
                      segments: value.segments.map((x) =>
                        x.resource === s.resource ? { ...x, excluded: v } : x,
                      ),
                    })
                  }
                >
                  Exclude
                </Tick>
              ) : null}
            </li>
          ))}
        </ul>
      ) : (
        <p className="text-pw-ink-500 text-[13px]">
          No segments yet. A Search campaign does not need any.
        </p>
      )}

      <fieldset className="border-pw-border flex flex-col gap-3 border-t pt-4">
        <legend className="text-pw-ink mb-2 text-[13px] font-semibold">
          Targeting setting for this campaign
        </legend>
        <Choice
          name="audience-mode"
          checked={value.mode === "targeting"}
          onChange={() => set({ mode: "targeting" })}
          help="Narrow the reach of your campaign to the selected audience segments, with the option to adjust the bids."
        >
          Targeting
        </Choice>
        <Choice
          name="audience-mode"
          checked={value.mode === "observation"}
          onChange={() => set({ mode: "observation" })}
          help="Don't narrow the reach of your campaign, with the option to adjust the bids on your selected segments. Google recommends this for Search."
        >
          Observation (recommended)
        </Choice>
      </fieldset>
    </div>
  );
}
