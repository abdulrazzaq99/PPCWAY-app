import Image from "next/image";
import Link from "next/link";
import type { ReactNode } from "react";
import { AccountCard } from "@/components/pw/account-card";
import { cn } from "@/lib/cn";

/*
  The signed-in app's frame, from the client's dashboard handoff: a 252px
  sidebar on the warm ground, the content column capped at 1200, and a header
  that carries the date, the business and the range.

  Everything in here is chrome. No screen's data passes through it, which is why
  it can be a server component and why every page can be read without it.
*/
export type NavItem = {
  href: string;
  label: string;
  icon: ReactNode;
  badge?: number | string;
  external?: boolean;
};

export function Sidebar({
  items,
  tools,
  active,
  business,
  plan,
}: {
  items: NavItem[];
  tools: NavItem[];
  active: string;
  business: string;
  plan?: string;
}) {
  return (
    <aside
      className="border-pw-border bg-pw-card hidden w-[252px] shrink-0 flex-col border-r lg:flex"
      style={{ minHeight: "100dvh" }}
    >
      <div className="px-5 pt-6 pb-4">
        <Link href="/home" className="inline-flex items-center">
          <Image
            src="/brand/ppcway-logo.svg"
            alt="PPCway"
            width={132}
            height={28}
            priority
            className="h-7 w-auto"
          />
        </Link>
      </div>

      <div className="px-4 pb-4">
        <Link
          href="/campaigns/new"
          className="bg-pw-blue hover:bg-pw-blue-hover flex h-11 w-full items-center justify-center gap-2 rounded-[12px] text-[15px] font-semibold text-white"
        >
          <span aria-hidden className="text-[18px] leading-none">
            +
          </span>
          New campaign
        </Link>
      </div>

      <nav className="flex flex-col gap-[2px] px-3" aria-label="Main">
        {items.map((item) => (
          <NavLink key={item.href} item={item} active={active} />
        ))}
      </nav>

      <p className="text-pw-ink-400 px-6 pt-6 pb-2 text-[11px] font-bold tracking-[0.08em] uppercase">
        Free tools
      </p>
      <nav className="flex flex-col gap-[2px] px-3" aria-label="Free tools">
        {tools.map((item) => (
          <NavLink key={item.href} item={item} active={active} />
        ))}
      </nav>

      <div className="mt-auto flex flex-col gap-3 p-4">
        <AccountCard business={business} plan={plan} />
      </div>
    </aside>
  );
}

function NavLink({ item, active }: { item: NavItem; active: string }) {
  const here = active === item.href || active.startsWith(item.href + "/");
  return (
    <Link
      href={item.href}
      aria-current={here ? "page" : undefined}
      className={cn(
        "flex h-10 items-center gap-3 rounded-[10px] px-3 text-[15px] leading-[20px]",
        here
          ? "bg-pw-blue-tint text-pw-blue-ink font-semibold"
          : "text-pw-ink-700 hover:bg-pw-muted",
      )}
    >
      <span aria-hidden className={cn("shrink-0", here ? "text-pw-blue" : "text-pw-ink-400")}>
        {item.icon}
      </span>
      <span className="min-w-0 flex-1 truncate">{item.label}</span>
      {item.badge ? (
        <span
          className={cn(
            "flex h-[20px] min-w-[20px] items-center justify-center rounded-full px-[6px] text-[11px] font-bold",
            here ? "bg-pw-blue text-white" : "bg-pw-muted text-pw-ink-600",
          )}
        >
          {item.badge}
        </span>
      ) : null}
    </Link>
  );
}

export function Header({
  eyebrow,
  title,
  right,
}: {
  eyebrow?: string;
  title: string;
  right?: ReactNode;
}) {
  return (
    <header className="flex flex-wrap items-end justify-between gap-4 px-5 pt-7 pb-5 sm:px-8">
      <div className="min-w-0">
        {eyebrow ? <p className="text-pw-ink-500 text-[13px] leading-[17px]">{eyebrow}</p> : null}
        <h1 className="display mt-1 text-[26px] leading-[32px] font-semibold sm:text-[30px] sm:leading-[36px]">
          {title}
        </h1>
      </div>
      {right ? <div className="flex flex-wrap items-center gap-3">{right}</div> : null}
    </header>
  );
}

export function PwPage({ children }: { children: ReactNode }) {
  return (
    <div className="mx-auto w-full max-w-[1200px] px-5 pb-16 sm:px-8">
      <div className="flex flex-col gap-4">{children}</div>
    </div>
  );
}

export function PwCard({
  children,
  className,
  tone = "card",
}: {
  children: ReactNode;
  className?: string;
  tone?: "card" | "night";
}) {
  return (
    <section
      className={cn(
        "rounded-[18px]",
        tone === "night" ? "bg-pw-night text-pw-night-text" : "bg-pw-card border-pw-border border",
        className,
      )}
    >
      {children}
    </section>
  );
}

/** One figure with its change, as the home and report screens use it. */
export function Kpi({
  label,
  note,
  value,
  chip,
  foot,
}: {
  label: string;
  note?: string;
  value: string;
  chip?: ReactNode;
  foot?: ReactNode;
}) {
  return (
    <PwCard className="flex min-w-0 flex-col justify-between p-5">
      <div className="flex items-start justify-between gap-3">
        <span className="text-[14px] leading-[18px] font-semibold">{label}</span>
        {note ? (
          <span className="text-pw-ink-400 shrink-0 text-[12px] leading-[16px]">{note}</span>
        ) : null}
      </div>
      <p className="pw-num display mt-3 text-[34px] leading-[40px] font-semibold">{value}</p>
      <div className="mt-2 flex min-h-[22px] flex-wrap items-center gap-2">{chip}</div>
      {foot ? <p className="text-pw-ink-500 mt-1 text-[13px] leading-[18px]">{foot}</p> : null}
    </PwCard>
  );
}

export function Chip({
  tone,
  children,
}: {
  tone: "good" | "warn" | "bad" | "info" | "otto" | "neutral";
  children: ReactNode;
}) {
  const tones = {
    good: "bg-pw-good-bg text-pw-good-ink",
    warn: "bg-pw-warn-bg text-pw-warn-ink",
    bad: "bg-pw-bad-bg text-pw-bad-ink",
    info: "bg-pw-blue-tint text-pw-blue-ink",
    otto: "bg-pw-otto-tint text-pw-otto-ink",
    neutral: "bg-pw-muted text-pw-ink-600",
  } as const;
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full px-[9px] py-[3px] text-[12px] font-bold whitespace-nowrap",
        tones[tone],
      )}
    >
      {children}
    </span>
  );
}
