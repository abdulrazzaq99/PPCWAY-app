"use client";

import type { ReactNode } from "react";
import { cn } from "@/lib/cn";

/*
  The pieces the free audit card is made of, at the sizes the handoff draws
  them. Kept here rather than reaching for the signed-in app's controls: this
  page is the client's own design and should not drift when that one changes.
*/
export const BOX =
  "h-[50px] w-full rounded-[12px] border-2 px-[14px] text-[16px] text-[#15112A] " +
  "placeholder:text-[#9A94AD] outline-none transition-colors";

export function fieldBorder(bad?: boolean): string {
  return bad ? "border-[#DC2626] bg-[#FEF2F2]" : "border-[#D9DEF0] focus:border-[#2F5BEA]";
}

export function Label({
  htmlFor,
  children,
  className,
}: {
  htmlFor?: string;
  children: ReactNode;
  className?: string;
}) {
  return (
    <label
      htmlFor={htmlFor}
      className={cn(
        "flex flex-col gap-[6px] text-[14.5px] font-semibold text-[#3A3550]",
        className,
      )}
    >
      {children}
    </label>
  );
}

/** Errors are spoken, not only coloured. */
export function Trouble({ children }: { children: ReactNode }) {
  if (!children) return null;
  return (
    <span role="alert" className="text-[14px] text-[#B91C1C]">
      {children}
    </span>
  );
}

export function Primary({
  children,
  onClick,
  busy,
  tall = 56,
  type = "button",
}: {
  children: ReactNode;
  onClick?: () => void;
  busy?: boolean;
  tall?: 54 | 56;
  type?: "button" | "submit";
}) {
  return (
    <button
      type={type}
      onClick={onClick}
      disabled={busy}
      style={{ height: tall }}
      className="w-full rounded-[14px] bg-[#2F5BEA] text-[17px] font-semibold text-white transition-[filter] hover:brightness-95 disabled:opacity-70"
    >
      {children}
    </button>
  );
}

export function Ghost({ children, onClick }: { children: ReactNode; onClick: () => void }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="h-[56px] rounded-[14px] border-[1.5px] border-[#D5D0DF] bg-white px-[18px] text-[16px] font-semibold text-[#3A3550] hover:bg-[#F3F2EE]"
    >
      {children}
    </button>
  );
}

/** A choice among a few, where the whole thing is the target. */
export function Choice({
  on,
  onClick,
  children,
  className,
  tall = "h-[46px]",
}: {
  on: boolean;
  onClick: () => void;
  children: ReactNode;
  className?: string;
  tall?: string;
}) {
  return (
    <button
      type="button"
      aria-pressed={on}
      onClick={onClick}
      className={cn(
        "rounded-[12px] px-3 text-[14.5px] font-semibold transition-colors",
        tall,
        on
          ? "border-2 border-[#2F5BEA] bg-[#EEF2FE] text-[#2F5BEA]"
          : "border-[1.5px] border-[#E0DCE8] bg-white text-[#3A3550] hover:bg-[#FAF9F7]",
        className,
      )}
    >
      {children}
    </button>
  );
}

/** The score, as a ring. The number is also written, so colour is never the only signal. */
export function Ring({ score, size = 104 }: { score: number; size?: number }) {
  const colour = score >= 60 ? "#15803D" : "#D97706";
  const inner = size - 20;
  return (
    <div
      role="img"
      aria-label={`Audit score ${score} out of 100`}
      className="flex shrink-0 items-center justify-center rounded-full"
      style={{
        width: size,
        height: size,
        background: `conic-gradient(${colour} ${score * 3.6}deg, #E8E5DF 0deg)`,
      }}
    >
      <span
        className="flex flex-col items-center justify-center rounded-full bg-white"
        style={{ width: inner, height: inner }}
      >
        <span
          className="display font-semibold"
          style={{ fontSize: size > 110 ? 40 : 32, lineHeight: 1 }}
        >
          {score}
        </span>
        <span className="text-[11.5px] text-[#6B6680]">of 100</span>
      </span>
    </div>
  );
}

const TONES = {
  fix: "bg-[#FDECEC] text-[#B91C1C]",
  improve: "bg-[#FFF4E0] text-[#B45309]",
  good: "bg-[#E9FBF0] text-[#15803D]",
} as const;

const UNDER = {
  fix: "text-[#7F1D1D]",
  improve: "text-[#713F12]",
  good: "text-[#14532D]",
} as const;

export function Counts({
  fix,
  improve,
  good,
  big,
}: {
  fix: number;
  improve: number;
  good: number;
  big?: boolean;
}) {
  const rows: [keyof typeof TONES, number, string][] = [
    ["fix", fix, "to fix"],
    ["improve", improve, "to improve"],
    ["good", good, "working well"],
  ];
  return (
    <div className="grid grid-cols-3 gap-2">
      {rows.map(([tone, n, label]) => (
        <div
          key={label}
          className={cn("rounded-[12px] px-3 py-[10px]", TONES[tone], big && "rounded-[14px] p-3")}
        >
          <div className={cn("display font-semibold", big ? "text-[26px]" : "text-[24px]")}>
            {n}
          </div>
          <div className={cn("text-[12.5px]", UNDER[tone], big && "text-[13px]")}>{label}</div>
        </div>
      ))}
    </div>
  );
}

export function Tag({ severity }: { severity: "fix" | "improve" | "good" }) {
  const said = { fix: "Fix", improve: "Improve", good: "Working well" }[severity];
  return (
    <span className={cn("rounded-full px-2 py-[2px] text-[11.5px] font-bold", TONES[severity])}>
      {said}
    </span>
  );
}
