"use client";

import { useId, type ReactNode } from "react";
import { cn } from "@/lib/cn";

/* A 20px square with a 6px radius. Ticked: brand fill with a white tick. */
export function Checkbox({
  checked,
  onChange,
  children,
  className,
}: {
  checked: boolean;
  onChange: (next: boolean) => void;
  children: ReactNode;
  className?: string;
}) {
  const id = useId();
  return (
    <label htmlFor={id} className={cn("flex cursor-pointer items-start gap-3", className)}>
      <span className="relative mt-[2px] flex size-5 shrink-0">
        <input
          id={id}
          type="checkbox"
          checked={checked}
          onChange={(e) => onChange(e.target.checked)}
          className="peer absolute inset-0 size-5 cursor-pointer opacity-0"
        />
        <span
          aria-hidden
          className={cn(
            "flex size-5 items-center justify-center rounded-[6px] border transition-colors duration-[var(--dur-hover)]",
            "peer-focus-visible:ring-brand-bar peer-focus-visible:ring-4",
            checked ? "bg-brand border-brand" : "border-line-input bg-panel",
          )}
        >
          {checked ? (
            <svg width="12" height="10" viewBox="0 0 12 10" fill="none" aria-hidden>
              <path
                d="M1.5 5.2 4.4 8 10.5 1.8"
                stroke="#fff"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </svg>
          ) : null}
        </span>
      </span>
      <span className="text-muted text-[13px] leading-4">{children}</span>
    </label>
  );
}
