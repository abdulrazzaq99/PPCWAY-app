"use client";

import { useId, useState, type InputHTMLAttributes, type ReactNode } from "react";
import { cn } from "@/lib/cn";

/*
  Inputs, from the "States and motion" frame.
  Rest: white, 1px line-input border, radius 12, 46 tall, placeholder shows the shape of the answer.
  Focus: 2px brand border, no glow. Filled: value in ink, border unchanged.
  Error: pale red fill, red border, and the message under the field says what to do.
*/

type InputProps = Omit<InputHTMLAttributes<HTMLInputElement>, "className"> & {
  invalid?: boolean;
  /** Something drawn inside the box at the right edge, such as a Show link or a unit. */
  trailing?: ReactNode;
  className?: string;
};

export function Input({ invalid, trailing, className, ...rest }: InputProps) {
  return (
    <div className={cn("relative", className)}>
      <input
        aria-invalid={invalid || undefined}
        className={cn(
          "text-body text-ink placeholder:text-rail-icon bg-panel h-[46px] w-full rounded-[var(--radius-control)] border px-[17px] outline-none",
          "transition-[border-color,background-color] duration-[var(--dur-hover)] ease-out",
          "border-line-input focus:border-brand focus:border-2 focus:px-4",
          invalid && "bg-red-pale border-[#c0392b] focus:border-[#c0392b]",
          Boolean(trailing) && "pr-16",
        )}
        {...rest}
      />
      {trailing ? (
        <div className="absolute inset-y-0 right-[17px] flex items-center">{trailing}</div>
      ) : null}
    </div>
  );
}

type FieldProps = {
  label: string;
  /** Drawn at the right end of the label row, such as "Forgot it?". */
  labelAside?: ReactNode;
  hint?: string;
  error?: string;
  children: (id: string) => ReactNode;
  className?: string;
};

export function Field({ label, labelAside, hint, error, children, className }: FieldProps) {
  const id = useId();
  return (
    <div className={cn("flex flex-col gap-2", className)}>
      <div className="flex items-center justify-between gap-3">
        <label htmlFor={id} className="text-label text-ink">
          {label}
        </label>
        {labelAside}
      </div>
      {children(id)}
      {error ? (
        <p className="text-meta font-medium text-[#c0392b]" role="alert">
          {error}
        </p>
      ) : hint ? (
        <p className="text-meta text-faint">{hint}</p>
      ) : null}
    </div>
  );
}

type PasswordProps = Omit<InputProps, "type" | "trailing">;

export function PasswordInput(props: PasswordProps) {
  const [shown, setShown] = useState(false);
  return (
    <Input
      {...props}
      type={shown ? "text" : "password"}
      trailing={
        <button
          type="button"
          onClick={() => setShown((s) => !s)}
          className="text-brand hover:text-brand-dark focus-visible:ring-brand-bar rounded-sm text-[14px] leading-[17px] font-semibold focus-visible:ring-4 focus-visible:outline-none"
          aria-pressed={shown}
        >
          {shown ? "Hide" : "Show"}
        </button>
      }
    />
  );
}
