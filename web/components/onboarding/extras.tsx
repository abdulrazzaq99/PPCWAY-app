"use client";

import { useId, type ReactNode } from "react";
import { cn } from "@/lib/cn";
import { Chip } from "@/components/ui/chip";

/* An amber note inside a form card, such as the low-budget warning. */
export function Note({
  tone = "amber",
  children,
}: {
  tone?: "amber" | "brand";
  children: ReactNode;
}) {
  return (
    <div
      className={cn(
        "rounded-[12px] border px-4 py-3 text-[14px] leading-[17px]",
        tone === "amber" && "bg-amber-tint border-amber-line text-amber-dark",
        tone === "brand" && "bg-brand-tint border-brand-line text-brand-dark",
      )}
    >
      {children}
    </div>
  );
}

/* The lighter optional field: a 13px muted label and a 44px box with a hairline border. */
export function OptionalField({
  label,
  placeholder,
  defaultValue,
  name,
}: {
  label: string;
  placeholder?: string;
  defaultValue?: string;
  name?: string;
}) {
  const id = useId();
  return (
    <div className="flex flex-col gap-[7px]">
      <label htmlFor={id} className="text-muted text-[13px] leading-4 font-semibold">
        {label}
      </label>
      <input
        id={id}
        name={name}
        placeholder={placeholder}
        defaultValue={defaultValue}
        className="text-ink placeholder:text-faint border-line focus:border-brand bg-panel h-11 w-full rounded-[12px] border px-[15px] text-[15px] leading-[18px] outline-none focus:border-2 focus:px-[14px]"
      />
    </div>
  );
}

/* A small pill choice: navy when chosen, white with a hairline otherwise. */
export function PillChoice({
  options,
  value,
  onChange,
  name,
}: {
  options: string[];
  value: string;
  onChange: (next: string) => void;
  name: string;
}) {
  return (
    <div role="radiogroup" aria-label={name} className="flex flex-wrap gap-[6px]">
      {options.map((option) => {
        const on = option === value;
        return (
          <label
            key={option}
            className={cn(
              "relative inline-flex h-8 cursor-pointer items-center rounded-[var(--radius-pill)] border px-[13px] text-[13px] leading-4 font-semibold transition-colors duration-[var(--dur-hover)]",
              on
                ? "bg-rail border-rail text-white"
                : "bg-panel border-line text-ink hover:bg-line-soft",
            )}
          >
            <input
              type="radio"
              name={name}
              value={option}
              checked={on}
              onChange={() => onChange(option)}
              className="peer absolute inset-0 cursor-pointer opacity-0"
            />
            <span className="peer-focus-visible:ring-brand-bar pointer-events-none absolute inset-0 rounded-[var(--radius-pill)] peer-focus-visible:ring-4" />
            {option}
          </label>
        );
      })}
    </div>
  );
}

/* Rows of title, meta and a status chip, split by soft hairlines. Used for "What we found". */
export type ChipRowItem = {
  title: string;
  meta: string;
  chip: string;
  tone?: "brand" | "amber" | "red" | "grey";
  /** Draws a text link instead of a chip. */
  link?: string;
};

export function ChipRows({ rows }: { rows: ChipRowItem[] }) {
  return (
    <div className="flex flex-col">
      {rows.map((row, i) => (
        <div
          key={row.title}
          className={cn(
            "flex items-center justify-between gap-4 py-3",
            i > 0 && "border-line-soft border-t",
          )}
        >
          <div className="min-w-0">
            <p className="text-ink text-[15px] leading-[18px] font-medium">{row.title}</p>
            <p className="text-faint mt-[3px] text-[13px] leading-4">{row.meta}</p>
          </div>
          {row.link ? (
            <span className="text-brand shrink-0 text-[14px] leading-[17px] font-semibold">
              {row.link}
            </span>
          ) : (
            <Chip tone={row.tone ?? "grey"} className="shrink-0">
              {row.chip}
            </Chip>
          )}
        </div>
      ))}
    </div>
  );
}

/* A campaign the merchant already runs, with a three-way choice underneath. */
export function CampaignCard({
  title,
  meta,
  suggestion,
  suggestionTone,
  note,
  value,
  onChange,
}: {
  title: string;
  meta: string;
  suggestion: string;
  suggestionTone: "brand" | "amber" | "grey";
  note: string;
  value: string;
  onChange: (next: string) => void;
}) {
  return (
    <div className="border-line flex flex-col gap-[10px] rounded-[12px] border px-4 py-[15px]">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="text-ink text-[15px] leading-[18px] font-medium">{title}</p>
          <p className="text-faint mt-[3px] text-[13px] leading-4">{meta}</p>
        </div>
        <Chip tone={suggestionTone} className="shrink-0">
          {suggestion}
        </Chip>
      </div>
      <PillChoice
        name={title}
        options={["Let PPCWay manage it", "Leave it to me", "Pause it"]}
        value={value}
        onChange={onChange}
      />
      <p className="text-faint text-[13px] leading-4">{note}</p>
    </div>
  );
}
