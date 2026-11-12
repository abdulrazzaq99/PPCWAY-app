"use client";

import { TrashIcon } from "@phosphor-icons/react";
import { LIMITS, type Sitelink } from "@/lib/creation";
import { Note } from "../kit";
import { Quiet, Text } from "./b-form";

/*
  Sitelinks, as Google's sitelink form has them: link text up to 25
  characters, two description lines up to 35 that go together or not at
  all, and the page it opens. Google shows them only from two, shows up to 6
  on a computer and 8 on a phone, and recommends at least 4 (6 for the best
  Ad Strength).
*/
const EMPTY: Sitelink = { text: "", description1: "", description2: "", final_url: "" };

export function Sitelinks({
  links,
  onChange,
  landing,
  most = 20,
}: {
  links: Sitelink[];
  onChange: (next: Sitelink[]) => void;
  landing: string;
  most?: number;
}) {
  const set = (at: number, patch: Partial<Sitelink>) =>
    onChange(links.map((l, i) => (i === at ? { ...l, ...patch } : l)));
  const live = links.filter((l) => l.text.trim()).length;
  return (
    <div className="flex flex-col gap-3">
      {live === 1 ? (
        <Note tone="warn">Sitelinks show only when there are at least 2. Add one more.</Note>
      ) : null}
      {links.map((link, at) => {
        const half = Boolean(link.description1.trim()) !== Boolean(link.description2.trim());
        return (
          <fieldset
            key={at}
            className="border-pw-border flex flex-col gap-3 rounded-[14px] border p-4"
          >
            <legend className="text-pw-ink-500 px-1 text-[12px] font-semibold">
              Sitelink {at + 1}
            </legend>
            <div className="grid gap-3 sm:grid-cols-2">
              <Text
                label="Sitelink text"
                value={link.text}
                most={LIMITS.sitelinkText}
                placeholder="Book a visit"
                onChange={(v) => set(at, { text: v })}
              />
              <Text
                label="Final URL"
                type="url"
                value={link.final_url}
                placeholder={landing || "https://"}
                hint={link.final_url ? undefined : "Empty opens your campaign website."}
                onChange={(v) => set(at, { final_url: v })}
              />
              <Text
                label="Description line 1 (optional)"
                value={link.description1}
                most={LIMITS.sitelinkLine}
                onChange={(v) => set(at, { description1: v })}
              />
              <Text
                label="Description line 2 (optional)"
                value={link.description2}
                most={LIMITS.sitelinkLine}
                onChange={(v) => set(at, { description2: v })}
              />
            </div>
            {half ? (
              <p className="text-pw-bad text-[13px]">
                Fill both description lines, or leave both empty. Google takes them as a pair.
              </p>
            ) : null}
            <Quiet tone="red" onClick={() => onChange(links.filter((_, i) => i !== at))}>
              <TrashIcon className="size-4" /> Remove sitelink {at + 1}
            </Quiet>
          </fieldset>
        );
      })}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <Quiet onClick={() => onChange([...links, { ...EMPTY }])} disabled={links.length >= most}>
          + Sitelink
        </Quiet>
        <span className="text-pw-ink-400 text-[12px]">
          {live} of {most}. Google recommends at least 4, and 6 for the best Ad Strength.
        </span>
      </div>
    </div>
  );
}
