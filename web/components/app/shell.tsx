import Link from "next/link";
import type { ReactNode } from "react";
import { Brand } from "@/components/ui/brand";
import { cn } from "@/lib/cn";
import { NavIcon, SearchGlyph } from "./icons";
import { navFor, type NavItem, type NavKind } from "./nav";

/*
  The signed-in shell, from the "V2 Dashboard · Desktop 1440" frames and the
  "V2 · Mobile · Home" frames.

  Desktop (lg and up): a 248px navy sidebar with the wordmark, the workspace switcher,
  the main menu, and Settings and Help pinned to the foot. The main column has a
  toolbar (320px search, a period pill, a 42px avatar), then the page, all inside
  40px side padding on a 1112px content width.

  Phone: a 60px top bar with the logo mark and the workspace name, the page, and a
  fixed five-tab bar (Home, Activity, Approvals with its badge, Campaigns, More).
*/

export type Workspace = { name: string; meta: string };

export function AppShell({
  kind = "merchant",
  active,
  workspace,
  initials = "DW",
  period = "Last 30 days",
  badges = { approvals: 2 },
  searchPlaceholder = "Search campaigns, keywords or changes",
  children,
}: {
  kind?: NavKind;
  /** The nav key that is highlighted: overview, activity, approvals, … or merchants, jobs, … */
  active: string;
  workspace: Workspace;
  initials?: string;
  period?: string;
  badges?: Record<string, number | undefined>;
  searchPlaceholder?: string;
  children: ReactNode;
}) {
  const nav = navFor(kind, badges);
  const allItems = [...nav.top.flatMap((g) => g.items), ...nav.bottom];
  const tabs = tabsFor(allItems, kind);
  return (
    <div className="flex min-h-dvh flex-col lg:flex-row">
      <aside className="bg-rail hidden w-[248px] shrink-0 flex-col justify-between px-4 pt-[26px] pb-[22px] lg:flex">
        <div>
          <div className="px-[10px]">
            <Brand tone="dark" size={26} href="/overview" />
          </div>
          <button
            type="button"
            className="bg-rail-soft mt-[21px] flex w-full items-center justify-between rounded-[12px] px-3 py-[11px] text-left"
          >
            <span className="min-w-0">
              <span className="block truncate text-[14px] leading-[17px] font-semibold text-white">
                {workspace.name}
              </span>
              <span className="text-rail-text block truncate text-[12px] leading-[15px]">
                {workspace.meta}
              </span>
            </span>
            <span aria-hidden className="text-rail-text text-[12px]">
              ▾
            </span>
          </button>
          <nav className="mt-[24px]" aria-label="Main">
            {nav.top.map((group, gi) => (
              <div key={gi} className={cn(gi > 0 && "mt-4")}>
                {group.heading ? (
                  <p className="text-rail-text px-3 pt-1 pb-2 text-[11px] leading-[13px] font-semibold tracking-[0.06em] uppercase">
                    {group.heading}
                  </p>
                ) : null}
                <ul className="flex flex-col gap-[3px]">
                  {group.items.map((item) => (
                    <SideItem key={item.key} item={item} active={item.key === active} />
                  ))}
                </ul>
              </div>
            ))}
          </nav>
        </div>
        <ul className="flex flex-col gap-[3px]">
          {nav.bottom.map((item) => (
            <SideItem key={item.key} item={item} active={item.key === active} />
          ))}
        </ul>
      </aside>

      <div className="flex min-w-0 flex-1 flex-col">
        {/* Phone top bar */}
        <header className="flex h-[60px] items-center justify-between px-5 lg:hidden">
          <button type="button" className="flex items-center gap-[10px] text-left">
            <span aria-hidden className="bg-brand block size-7 rounded-[9px]" />
            <span>
              <span className="text-ink block text-[15px] leading-[18px] font-semibold">
                {workspace.name}
              </span>
              <span className="text-muted block text-[12px] leading-[15px] font-medium">
                {workspace.meta.split(",")[0]} ▾
              </span>
            </span>
          </button>
          <span className="bg-rail flex size-9 items-center justify-center rounded-full text-[12px] font-semibold text-white">
            {initials}
          </span>
        </header>

        {/* Desktop toolbar */}
        <div className="hidden items-center justify-between gap-4 px-10 pt-7 lg:flex">
          <label className="bg-panel border-line flex h-10 w-[320px] items-center gap-[10px] rounded-[12px] border px-[15px]">
            <SearchGlyph />
            <input
              type="search"
              placeholder={searchPlaceholder}
              className="text-ink placeholder:text-faint w-full bg-transparent text-[14px] leading-[17px] outline-none"
            />
          </label>
          <div className="flex items-center gap-[10px]">
            <button
              type="button"
              className="bg-panel border-line text-ink flex h-[39px] items-center gap-[10px] rounded-[var(--radius-pill)] border px-[17px] text-[14px] leading-[17px] font-medium"
            >
              {period}
              <span aria-hidden className="text-faint text-[12px]">
                ▾
              </span>
            </button>
            <span className="bg-rail flex size-[42px] items-center justify-center rounded-full text-[13px] font-semibold text-white">
              {initials}
            </span>
          </div>
        </div>

        <main className="flex-1 px-5 pt-2 pb-[110px] sm:px-8 lg:px-10 lg:pt-[26px] lg:pb-10">
          <div className="mx-auto w-full max-w-[1112px]">{children}</div>
        </main>
      </div>

      {/* Phone tab bar */}
      <nav
        aria-label="Main"
        className="bg-panel border-line fixed inset-x-0 bottom-0 z-20 border-t lg:hidden"
        style={{ paddingBottom: "env(safe-area-inset-bottom, 0px)" }}
      >
        <ul className="flex h-[70px] items-start justify-around px-2 pt-[10px]">
          {tabs.map((tab) => {
            const on = tab.key === active || (tab.key === "more" && moreKeys.has(active));
            return (
              <li key={tab.key}>
                <Link
                  href={tab.href}
                  className={cn(
                    "flex w-[62px] flex-col items-center gap-1",
                    on ? "text-brand" : "text-faint",
                  )}
                  aria-current={on ? "page" : undefined}
                >
                  <span className="relative">
                    <NavIcon name={tab.icon} className="scale-[1.09]" />
                    {tab.badge ? (
                      <span className="bg-amber border-panel absolute -top-[3px] -right-[7px] flex size-[15px] items-center justify-center rounded-full border text-[9px] leading-none font-bold text-white">
                        {tab.badge}
                      </span>
                    ) : null}
                  </span>
                  <span
                    className={cn(
                      "text-[11px] leading-[13px]",
                      on ? "font-semibold" : "font-medium",
                    )}
                  >
                    {tab.label}
                  </span>
                </Link>
              </li>
            );
          })}
        </ul>
      </nav>
    </div>
  );
}

const moreKeys = new Set([
  "settings",
  "help",
  "searches",
  "runbook",
  "audit",
  "quota",
  "reviews",
  "staff",
  "platform",
  "metrics",
]);

function tabsFor(items: NavItem[], kind: NavKind): NavItem[] {
  const pick = (keys: string[]) =>
    keys.map((k) => items.find((i) => i.key === k)).filter(Boolean) as NavItem[];
  const main =
    kind === "admin" || kind === "admin-super"
      ? pick(["merchants", "jobs", "errors", "quota"])
      : pick(["overview", "activity", "approvals", "campaigns"]);
  const home = main[0]
    ? { ...main[0], label: kind.startsWith("admin") ? "Merchants" : "Home" }
    : null;
  const more: NavItem = {
    key: "more",
    label: "More",
    href: kind.startsWith("admin")
      ? "/admin/runbook"
      : kind === "agency"
        ? "/agency/settings"
        : "/settings",
    icon: "more",
  };
  return [...(home ? [home] : []), ...main.slice(1), more];
}

function SideItem({ item, active }: { item: NavItem; active: boolean }) {
  return (
    <li>
      <Link
        href={item.href}
        aria-current={active ? "page" : undefined}
        className={cn(
          "flex h-[42px] items-center gap-3 rounded-[11px] px-3 transition-colors duration-[var(--dur-hover)]",
          active ? "bg-brand text-white" : "text-rail-icon hover:bg-rail-soft hover:text-white",
        )}
      >
        <NavIcon name={item.icon} />
        <span
          className={cn("text-[15px] leading-[18px]", active ? "font-semibold" : "font-medium")}
        >
          {item.label}
        </span>
        {item.badge ? (
          <span className="bg-amber ml-auto flex h-[21px] min-w-6 items-center justify-center rounded-full px-[7px] text-[12px] leading-none font-bold text-white">
            {item.badge}
          </span>
        ) : null}
      </Link>
    </li>
  );
}
