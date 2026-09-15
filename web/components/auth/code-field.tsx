"use client";

import { useId } from "react";

/* A six-digit code box: 50 tall, the digits in Inter Semi Bold 18, spaced "702 518". */
export function CodeField({ label, defaultValue }: { label: string; defaultValue?: string }) {
  const id = useId();
  return (
    <div className="flex flex-col gap-2">
      <label htmlFor={id} className="text-label text-ink">
        {label}
      </label>
      <input
        id={id}
        name="code"
        inputMode="numeric"
        autoComplete="one-time-code"
        pattern="[0-9 ]*"
        maxLength={7}
        defaultValue={defaultValue}
        placeholder="000 000"
        className="text-ink placeholder:text-rail-icon border-line-input focus:border-brand bg-panel h-[50px] w-full rounded-[var(--radius-control)] border px-[17px] text-[18px] leading-[22px] font-semibold tracking-[0.04em] outline-none focus:border-2 focus:px-4"
      />
    </div>
  );
}
