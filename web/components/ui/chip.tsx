import type { ReactNode } from "react";
import { cn } from "@/lib/cn";

type Tone = "brand" | "amber" | "red" | "grey" | "inverse";

/*
  The small pill used for status words: Live, Learning, Waiting for you, Your role.
  Brand for done or healthy, amber for waiting on the merchant, red for money or account
  trouble, grey for information.
*/
const tones: Record<Tone, string> = {
  brand: "bg-brand-pale text-brand-dark",
  amber: "bg-amber-pale text-amber-dark",
  red: "bg-red-pale text-red",
  grey: "bg-line-soft text-muted",
  inverse: "bg-brand-dark text-white",
};

export function Chip({
  tone = "grey",
  dot,
  children,
  className,
}: {
  tone?: Tone;
  /** A 6px dot before the label, as on the campaign status pills. */
  dot?: boolean;
  children: ReactNode;
  className?: string;
}) {
  return (
    <span
      className={cn(
        "inline-flex h-[23px] items-center gap-[6px] rounded-[var(--radius-pill)] px-[10px] text-[12px] leading-[15px] font-semibold whitespace-nowrap",
        tones[tone],
        className,
      )}
    >
      {dot ? <span aria-hidden className="size-[6px] rounded-full bg-current" /> : null}
      {children}
    </span>
  );
}
