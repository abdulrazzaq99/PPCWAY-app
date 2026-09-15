import type { ReactNode } from "react";
import { cn } from "@/lib/cn";

/* Waiting: grey bars, no spinner, a 1.6 second pulse between opacity 1 and 0.6. */
export function Skeleton({
  widths = [150, 340, 250],
  className,
}: {
  widths?: number[];
  className?: string;
}) {
  return (
    <div className={cn("flex flex-col gap-3", className)} aria-busy aria-live="polite">
      {widths.map((w, i) => (
        <div key={i} className="skeleton-bar" style={{ width: `min(100%, ${w}px)` }} />
      ))}
    </div>
  );
}

/* Nothing to show: say what will appear and when. */
export function EmptyState({
  title,
  body,
  action,
  className,
}: {
  title: string;
  body: string;
  action?: ReactNode;
  className?: string;
}) {
  return (
    <div className={cn("flex flex-col gap-[10px]", className)}>
      <span className="bg-brand-pale flex size-7 items-center justify-center rounded-[9px]">
        <span className="bg-brand block size-3 rounded-[3px]" aria-hidden />
      </span>
      <p className="text-section text-ink">{title}</p>
      <p className="text-muted text-[14px] leading-[17px]">{body}</p>
      {action ? <div className="pt-1">{action}</div> : null}
    </div>
  );
}

/* The white card with a hairline border and the shell radius. */
export function Card({
  children,
  className,
  as: Tag = "div",
}: {
  children: ReactNode;
  className?: string;
  as?: "div" | "section" | "article" | "form";
}) {
  return (
    <Tag className={cn("bg-panel border-line rounded-[var(--radius-shell)] border", className)}>
      {children}
    </Tag>
  );
}
