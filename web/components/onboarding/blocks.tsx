"use client";

import { useId, type ReactNode } from "react";
import { GoogleMark } from "@/components/ui/brand";
import { cn } from "@/lib/cn";

/*
  Blocks that recur across the onboarding form cards.
*/

type Tone = "brand" | "amber" | "red" | "grey" | "ink";

const toneText: Record<Tone, string> = {
  brand: "text-brand",
  amber: "text-amber",
  red: "text-[#c0392b]",
  grey: "text-faint",
  ink: "text-ink",
};

const rowFill = {
  none: "bg-panel",
  brand: "bg-brand-pale",
  amber: "bg-amber-tint",
} as const;

export type ChoiceRow = {
  id: string;
  name: string;
  detail: string;
  /** The word at the right edge, such as "Selected", "Choose", "Needs you". */
  status: string;
  statusTone?: Tone;
  fill?: keyof typeof rowFill;
  /** Greyed name, for an option that cannot be chosen right now. */
  muted?: boolean;
};

/*
  The hairline list of 69px rows: a name in Inter Semi Bold 15, a detail in 13 muted,
  and a status word at the right. When `onChange` is given the rows are radio buttons
  and the chosen one is filled pale blue.
*/
export function ChoiceList({
  rows,
  value,
  onChange,
  ariaLabel,
}: {
  rows: ChoiceRow[];
  value?: string;
  onChange?: (id: string) => void;
  ariaLabel?: string;
}) {
  const name = useId();
  const interactive = Boolean(onChange);
  return (
    <div
      role={interactive ? "radiogroup" : "list"}
      aria-label={ariaLabel}
      className="border-line overflow-hidden rounded-[12px] border"
    >
      {rows.map((row, i) => {
        const selected = interactive ? value === row.id : false;
        const fill = selected ? "brand" : (row.fill ?? "none");
        const inner = (
          <>
            <span className="min-w-0 flex-1">
              <span
                className={cn(
                  "block text-[15px] leading-[18px] font-semibold",
                  row.muted ? "text-faint" : "text-ink",
                )}
              >
                {row.name}
              </span>
              <span className="text-muted mt-[3px] block text-[13px] leading-4">{row.detail}</span>
            </span>
            <span
              className={cn(
                "shrink-0 text-[15px] leading-[18px] font-semibold",
                toneText[selected ? "brand" : (row.statusTone ?? "grey")],
              )}
            >
              {selected && interactive ? "Selected" : row.status}
            </span>
          </>
        );
        const rowClass = cn(
          "flex min-h-[69px] w-full items-center gap-4 px-[18px] py-4 text-left",
          rowFill[fill],
          i > 0 && "border-line border-t",
          interactive &&
            "cursor-pointer transition-colors duration-[var(--dur-hover)] hover:bg-line-soft",
          interactive && selected && "hover:bg-brand-pale",
        );
        if (!interactive) {
          return (
            <div key={row.id} role="listitem" className={rowClass}>
              {inner}
            </div>
          );
        }
        return (
          <label key={row.id} className={cn(rowClass, "relative")}>
            <input
              type="radio"
              name={name}
              value={row.id}
              checked={selected}
              onChange={() => onChange?.(row.id)}
              className="peer absolute inset-0 cursor-pointer opacity-0"
            />
            <span className="peer-focus-visible:ring-brand-bar pointer-events-none absolute inset-0 rounded-none peer-focus-visible:ring-4 peer-focus-visible:ring-inset" />
            {inner}
          </label>
        );
      })}
    </div>
  );
}

/*
  The 50px status strip drawn where the Google button sits on later screens:
  an icon and one line of text, tinted by tone.
*/
export function StatusStrip({
  tone = "neutral",
  icon = "google",
  children,
}: {
  tone?: "neutral" | "brand" | "amber";
  icon?: "google" | "none";
  children: ReactNode;
}) {
  return (
    <div
      className={cn(
        "flex h-[50px] items-center justify-center gap-[10px] rounded-[12px] border px-4 text-[15px] leading-[18px] font-semibold",
        tone === "neutral" && "bg-panel border-line-input text-ink",
        tone === "brand" && "bg-brand-pale border-brand-line text-brand-dark",
        tone === "amber" && "bg-amber-tint border-amber-line text-[#9e681a]",
      )}
    >
      {icon === "google" ? (
        <GoogleMark className={tone !== "neutral" ? "opacity-90" : undefined} />
      ) : null}
      <span className="truncate">{children}</span>
    </div>
  );
}

/* A read-only fact drawn in the shape of a field, such as "Google Ads customer ID". */
export function FactField({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex flex-col gap-2">
      <p className="text-label text-ink">{label}</p>
      <div className="border-line-input text-body text-ink bg-panel flex h-[46px] items-center rounded-[var(--radius-control)] border px-[17px]">
        <span className="truncate">{value}</span>
      </div>
    </div>
  );
}

/* A bordered option with a round radio, a title and a line of meta. Selected: pale tint and brand border. */
export function OptionCard({
  title,
  meta,
  selected,
  onSelect,
  name,
}: {
  title: string;
  meta: string;
  selected: boolean;
  onSelect: () => void;
  name: string;
}) {
  return (
    <label
      className={cn(
        "relative flex cursor-pointer items-start gap-[14px] rounded-[12px] border px-[17px] py-4 transition-colors duration-[var(--dur-hover)]",
        selected ? "bg-brand-tint border-brand" : "bg-panel border-line hover:bg-line-soft",
      )}
    >
      <input
        type="radio"
        name={name}
        checked={selected}
        onChange={onSelect}
        className="peer absolute inset-0 cursor-pointer opacity-0"
      />
      <span
        aria-hidden
        className={cn(
          "bg-panel mt-[1px] flex size-5 shrink-0 items-center justify-center rounded-full border",
          selected ? "border-brand" : "border-[#b8c3cc]",
        )}
      >
        {selected ? <span className="bg-brand block size-[10px] rounded-full" /> : null}
      </span>
      <span className="min-w-0">
        <span className="text-ink block text-[15px] leading-[18px] font-semibold">{title}</span>
        <span className="text-muted mt-1 block text-[14px] leading-[17px]">{meta}</span>
      </span>
      <span className="peer-focus-visible:ring-brand-bar pointer-events-none absolute inset-0 rounded-[12px] peer-focus-visible:ring-4" />
    </label>
  );
}
