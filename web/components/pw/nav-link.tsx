"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import type { NavItem } from "@/components/pw/shell";
import { cn } from "@/lib/cn";

/*
  One sidebar link, marked when it is the screen being shown.

  Marked here, in the browser, rather than in the layout. A layout is not
  rendered again when somebody moves between the screens inside it -- the
  Next.js docs: "On navigation, layouts preserve state, remain interactive, and
  do not rerender" -- so a mark worked out there stayed on whichever screen was
  opened first. On 9 November that was Settings, still marked while the
  merchant read Campaigns.

  `active` is what the server saw on the first load, so the first paint is the
  same either way; after that the address in the browser decides.
*/
export function NavLink({ item, active }: { item: NavItem; active: string }) {
  const path = usePathname() || active;
  const here = path === item.href || path.startsWith(item.href + "/");
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
            "flex h-[20px] min-w-[22px] items-center justify-center rounded-full px-[7px] text-[11px] font-bold",
            item.badgeTone === "otto" ? "bg-pw-otto text-white" : "bg-pw-muted text-pw-ink-600",
          )}
        >
          {item.badge}
        </span>
      ) : null}
    </Link>
  );
}
