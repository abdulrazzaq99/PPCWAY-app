import type { ReactNode } from "react";
import { Brand } from "@/components/ui/brand";
import { cn } from "@/lib/cn";

/*
  The onboarding shell, from the "V2 Onboarding" frames.
  Desktop: a 340px navy rail with the wordmark, the six numbered steps and a footnote
  at the foot; the main column holds a headline block, a 620px form card beside a
  348px aside card, and a footer with the progress text and one primary button.
  Narrow screens: the rail becomes a band with the wordmark and a scrolling row of
  step pills; the two cards stack.
*/

export const ONBOARDING_STEPS = [
  { slug: "account", label: "Account and plan" },
  { slug: "connect", label: "Connect Google Ads" },
  { slug: "business", label: "Your business" },
  { slug: "website", label: "Website check" },
  { slug: "calls", label: "Count your calls" },
  { slug: "review", label: "Review and launch" },
] as const;

export type StepSlug = (typeof ONBOARDING_STEPS)[number]["slug"];

export function OnboardingShell({
  step,
  headline,
  subline,
  footnote = "About 15 minutes from here to your first live campaign.",
  progress,
  action,
  aside,
  children,
}: {
  step: StepSlug;
  headline: string;
  subline: string;
  footnote?: string;
  /** Overrides "Step n of 6". */
  progress?: string;
  /** The footer's primary button (and anything beside it). */
  action?: ReactNode;
  aside?: ReactNode;
  children: ReactNode;
}) {
  const index = ONBOARDING_STEPS.findIndex((s) => s.slug === step);
  return (
    <div className="flex min-h-dvh flex-col lg:flex-row">
      <aside className="bg-rail text-white lg:flex lg:w-[340px] lg:shrink-0 lg:flex-col lg:justify-between">
        <div className="px-5 pt-7 pb-5 sm:px-8 lg:px-10 lg:pt-12 lg:pb-0">
          <Brand tone="dark" href="/" />
          <ol className="mt-5 flex gap-2 overflow-x-auto pb-1 lg:mt-[10px] lg:flex-col lg:gap-0 lg:overflow-visible">
            {ONBOARDING_STEPS.map((s, i) => {
              const state = i < index ? "done" : i === index ? "current" : "todo";
              return (
                <li
                  key={s.slug}
                  className={cn(
                    "flex shrink-0 items-center gap-[14px] rounded-[var(--radius-pill)] lg:h-[46px] lg:rounded-none",
                    "px-3 py-[6px] lg:px-0 lg:py-0",
                    state === "current" && "bg-rail-soft lg:bg-transparent",
                  )}
                  aria-current={state === "current" ? "step" : undefined}
                >
                  <span
                    className={cn(
                      "flex size-7 shrink-0 items-center justify-center rounded-full text-[13px] leading-4 font-bold",
                      state === "done" && "bg-brand-dark text-white",
                      state === "current" && "bg-brand text-white",
                      state === "todo" && "bg-rail-soft text-rail-text",
                    )}
                  >
                    {i + 1}
                  </span>
                  <span
                    className={cn(
                      "text-[15px] leading-[18px] whitespace-nowrap",
                      state === "done" && "text-rail-text font-semibold",
                      state === "current" && "font-medium text-white",
                      state === "todo" && "text-rail-text font-medium",
                    )}
                  >
                    {s.label}
                  </span>
                </li>
              );
            })}
          </ol>
        </div>
        <p className="text-rail-text hidden px-10 pb-12 text-[14px] leading-[17px] lg:block">
          {footnote}
        </p>
      </aside>

      <main className="flex flex-1 flex-col px-5 py-8 sm:px-8 lg:px-14 lg:py-12">
        <div className="max-w-[988px]">
          <h1 className="text-ink text-[26px] leading-[32px] font-semibold text-balance sm:text-[32px] sm:leading-[39px]">
            {headline}
          </h1>
          <p className="text-subline mt-[10px] max-w-[900px]">{subline}</p>
        </div>

        <div className="mt-[26px] grid max-w-[988px] gap-5 lg:grid-cols-[620px_348px]">
          <div className="min-w-0">{children}</div>
          {aside ? <div className="min-w-0">{aside}</div> : null}
        </div>

        <footer className="mt-auto flex max-w-[988px] flex-wrap items-center justify-between gap-4 pt-7">
          <p className="text-faint text-[14px] leading-[17px] font-medium">
            {progress ?? `Step ${index + 1} of ${ONBOARDING_STEPS.length}`}
          </p>
          <div className="flex flex-wrap items-center gap-3">{action}</div>
        </footer>
        <p className="text-faint mt-6 text-[13px] leading-4 lg:hidden">{footnote}</p>
      </main>
    </div>
  );
}

/** The 620px white form card: 29px padding, 18px between blocks. */
export function FormCard({ children, className }: { children: ReactNode; className?: string }) {
  return (
    <section
      className={cn(
        "bg-panel border-line flex flex-col gap-[18px] rounded-[16px] border p-5 sm:p-[29px]",
        className,
      )}
    >
      {children}
    </section>
  );
}

/** The 348px aside: a title, a body, and a fine-print line. */
export function AsideCard({
  title,
  children,
  finePrint,
  action,
}: {
  title: string;
  children: ReactNode;
  finePrint?: string;
  action?: ReactNode;
}) {
  return (
    <section className="bg-panel border-line flex flex-col gap-[14px] rounded-[16px] border p-5 sm:p-[27px]">
      <h2 className="text-section text-ink">{title}</h2>
      <div className="text-body text-muted">{children}</div>
      {finePrint ? <p className="text-meta text-faint">{finePrint}</p> : null}
      {action ? <div className="pt-1">{action}</div> : null}
    </section>
  );
}

export function SectionTitle({ children }: { children: ReactNode }) {
  return <h2 className="text-section text-ink">{children}</h2>;
}
