"use client";

import type { ReactNode } from "react";
import { Input } from "@/components/ui/field";
import { cn } from "@/lib/cn";
import { Counted } from "../kit";

/*
  Labelled controls for the ad and asset screens. The kit's `Labelled` names a
  control with a span; these use a real <label>, so every box on Google's long
  ad forms says what it is to a screen reader as well as to the eye.
*/

export const BOX =
  "border-pw-border-input bg-pw-card text-pw-ink focus:border-pw-blue h-[46px] w-full rounded-[12px] border px-3 text-[14px] outline-none";

export const AREA =
  "border-pw-border-input bg-pw-card text-pw-ink placeholder:text-pw-ink-300 focus:border-pw-blue w-full rounded-[12px] border p-3 text-[15px] leading-[22px] outline-none";

function Name({ label, hint, children }: { label: string; hint?: ReactNode; children: ReactNode }) {
  return (
    <>
      <span className="text-pw-ink text-[13px] leading-[18px] font-semibold">{label}</span>
      {children}
      {hint ? <span className="text-pw-ink-500 text-[12px] leading-[16px]">{hint}</span> : null}
    </>
  );
}

/** A text box with its label, counted against Google's limit when it has one. */
export function Text({
  label,
  hint,
  value,
  onChange,
  most,
  placeholder,
  type,
  className,
  disabled,
}: {
  label: string;
  hint?: ReactNode;
  value: string;
  onChange: (next: string) => void;
  most?: number;
  placeholder?: string;
  type?: "text" | "url" | "tel" | "date";
  className?: string;
  disabled?: boolean;
}) {
  return (
    <label className={cn("flex min-w-0 flex-col gap-[6px]", className)}>
      <Name label={label} hint={hint}>
        {most && !disabled ? (
          <Counted value={value} onChange={onChange} most={most} placeholder={placeholder} />
        ) : (
          <Input
            type={type ?? "text"}
            inputMode={type === "url" ? "url" : undefined}
            value={value}
            disabled={disabled}
            placeholder={placeholder}
            onChange={(e) => onChange(e.target.value)}
            trailing={
              most ? (
                <span className="text-pw-ink-300 text-[12px] tabular-nums">
                  {value.length}/{most}
                </span>
              ) : null
            }
          />
        )}
      </Name>
    </label>
  );
}

/** A dropdown with its label. Values are Google's enum names, labels are its words. */
export function Pick<T extends string>({
  label,
  hint,
  value,
  onChange,
  options,
  className,
}: {
  label: string;
  hint?: ReactNode;
  value: T;
  onChange: (next: T) => void;
  options: readonly { value: T; label: string }[];
  className?: string;
}) {
  return (
    <label className={cn("flex min-w-0 flex-col gap-[6px]", className)}>
      <Name label={label} hint={hint}>
        <select value={value} onChange={(e) => onChange(e.target.value as T)} className={BOX}>
          {options.map((o) => (
            <option key={o.value} value={o.value}>
              {o.label}
            </option>
          ))}
        </select>
      </Name>
    </label>
  );
}

/** A box for several lines, counted when Google limits it. */
export function Area({
  label,
  hint,
  value,
  onChange,
  rows = 4,
  most,
  placeholder,
}: {
  label: string;
  hint?: ReactNode;
  value: string;
  onChange: (next: string) => void;
  rows?: number;
  most?: number;
  placeholder?: string;
}) {
  const over = most !== undefined && value.length > most;
  return (
    <label className="flex min-w-0 flex-col gap-[6px]">
      <span className="flex items-baseline justify-between gap-3">
        <span className="text-pw-ink text-[13px] leading-[18px] font-semibold">{label}</span>
        {most ? (
          <span
            className={cn("text-[12px] tabular-nums", over ? "text-pw-bad" : "text-pw-ink-400")}
          >
            {value.length}/{most}
          </span>
        ) : null}
      </span>
      <textarea
        value={value}
        rows={rows}
        placeholder={placeholder}
        aria-invalid={over || undefined}
        onChange={(e) => onChange(e.target.value)}
        className={cn(AREA, over && "border-pw-bad")}
      />
      {hint ? <span className="text-pw-ink-500 text-[12px] leading-[16px]">{hint}</span> : null}
    </label>
  );
}

/** A part of a card with its own small heading, ruled off from the part above. */
export function Section({
  title,
  help,
  aside,
  children,
  className,
}: {
  title: string;
  help?: ReactNode;
  aside?: ReactNode;
  children: ReactNode;
  className?: string;
}) {
  return (
    <div
      className={cn(
        "border-pw-border flex flex-col gap-4 border-t px-5 py-5 first:border-t-0 sm:px-6",
        className,
      )}
    >
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <h3 className="text-pw-ink text-[15px] leading-[20px] font-semibold">{title}</h3>
          {help ? (
            <p className="text-pw-ink-500 mt-1 max-w-[680px] text-[13px] leading-[18px]">{help}</p>
          ) : null}
        </div>
        {aside}
      </div>
      {children}
    </div>
  );
}

/** "Are you sure", asked in place rather than in a browser dialog. */
export function Confirm({
  words,
  yes,
  onYes,
  onNo,
}: {
  words: ReactNode;
  yes: string;
  onYes: () => void;
  onNo: () => void;
}) {
  return (
    <div
      role="alert"
      className="bg-pw-warn-bg text-pw-warn-ink flex flex-col gap-3 rounded-[12px] px-4 py-3 text-[13px] leading-[19px] sm:flex-row sm:items-center sm:justify-between"
    >
      <span>{words}</span>
      <span className="flex shrink-0 gap-2">
        <button
          type="button"
          onClick={onYes}
          className="bg-pw-bad-solid rounded-full px-4 py-[7px] text-[13px] font-semibold text-white"
        >
          {yes}
        </button>
        <button
          type="button"
          onClick={onNo}
          className="border-pw-border-input bg-pw-card text-pw-ink rounded-full border px-4 py-[7px] text-[13px] font-semibold"
        >
          Cancel
        </button>
      </span>
    </div>
  );
}

/** Two or three choices side by side, as Google's preview switches them. */
export function Segmented<T extends string>({
  label,
  value,
  options,
  onChange,
}: {
  label: string;
  value: T;
  options: readonly { value: T; label: string; icon?: ReactNode }[];
  onChange: (next: T) => void;
}) {
  return (
    <div
      role="radiogroup"
      aria-label={label}
      className="bg-pw-muted inline-flex rounded-full p-[3px]"
    >
      {options.map((o) => (
        <button
          key={o.value}
          type="button"
          role="radio"
          aria-checked={o.value === value}
          onClick={() => onChange(o.value)}
          className={cn(
            "inline-flex items-center gap-1 rounded-full px-3 py-[5px] text-[12px] font-semibold transition-colors",
            o.value === value
              ? "bg-pw-card text-pw-ink shadow-sm"
              : "text-pw-ink-500 hover:text-pw-ink",
          )}
        >
          {o.icon}
          {o.label}
        </button>
      ))}
    </div>
  );
}

/** A small text button for adding or removing, in the brand blue or red. */
export function Quiet({
  children,
  onClick,
  tone = "blue",
  disabled,
  label,
}: {
  children: ReactNode;
  onClick: () => void;
  tone?: "blue" | "red";
  disabled?: boolean;
  label?: string;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      aria-label={label}
      className={cn(
        "disabled:text-pw-ink-300 inline-flex items-center gap-1 self-start text-[14px] font-semibold",
        tone === "red" ? "text-pw-bad hover:underline" : "text-pw-blue hover:underline",
      )}
    >
      {children}
    </button>
  );
}

/*
  Google's "Display path": two short words after the domain in the ad's
  address. They need not be real pages. The second waits for the first,
  because Google refuses a second path on its own.
*/
export function DisplayPath({
  url,
  path1,
  path2,
  onChange,
}: {
  url: string;
  path1: string;
  path2: string;
  onChange: (next: { path1: string; path2: string }) => void;
}) {
  const domain = domainOf(url) || "example.com";
  const box = (value: string, label: string, set: (v: string) => void, disabled = false) => (
    <Input
      aria-label={label}
      value={value}
      disabled={disabled}
      placeholder={disabled ? "Fill path 1 first" : label}
      invalid={value.length > 15}
      onChange={(e) => set(e.target.value.replace(/\s+/g, "-"))}
      className="min-w-0 flex-1"
      trailing={
        <span
          className={cn(
            "text-[12px] tabular-nums",
            value.length > 15 ? "text-pw-bad" : "text-pw-ink-400",
          )}
        >
          {value.length}/15
        </span>
      }
    />
  );
  const shown = [domain, path1.trim(), path1.trim() ? path2.trim() : ""].filter(Boolean).join("/");
  return (
    <div className="flex min-w-0 flex-col gap-[6px]">
      <span className="text-pw-ink text-[13px] leading-[18px] font-semibold">Display path</span>
      <div className="flex flex-col gap-2 sm:flex-row sm:items-center">
        <span className="text-pw-ink-500 shrink-0 truncate text-[14px]">{domain}/</span>
        {box(path1, "Path 1", (v) => onChange({ path1: v, path2 }))}
        <span className="text-pw-ink-400 hidden text-[14px] sm:inline">/</span>
        {box(path2, "Path 2", (v) => onChange({ path1, path2: v }), !path1.trim())}
      </div>
      <span className="text-pw-ink-500 text-[12px] leading-[16px]">
        People see <span className="text-pw-ink font-medium">{shown}</span>. Up to 15 characters
        each; they need not be real pages on your site.
      </span>
    </div>
  );
}

/** The site's own address without the scheme or www, as Google shows it in an ad. */
export function domainOf(url: string): string {
  try {
    return new URL(url.trim()).hostname.replace(/^www\./, "");
  } catch {
    return "";
  }
}

export function isUrl(url: string): boolean {
  return /^https?:\/\/[^\s.]+\.[^\s]+/.test(url.trim());
}
