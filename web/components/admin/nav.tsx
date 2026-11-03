"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

/*
  Moving around the panel.

  Seven destinations do not fit across a handset, and the merchant app's
  TabsRow was never asked to carry that many. So this scrolls horizontally on a
  phone and sits on one line from `sm` up, with the current page marked by a
  rule under it rather than a filled pill. A filled pill at this density reads
  as a button somebody should press.

  The list is filtered by what the person may actually do. A tab that leads to
  a 403 is worse than a missing tab: it teaches staff that parts of the panel
  are broken when they are simply not theirs.
*/

const EVERY = [
  { href: "/admin", label: "Merchants", needs: "read_merchant" },
  { href: "/admin/metrics", label: "Overview", needs: "read_platform" },
  { href: "/admin/jobs", label: "Jobs", needs: "run_job" },
  { href: "/admin/errors", label: "Failures", needs: "read_errors" },
  { href: "/admin/quota", label: "Quota", needs: "read_platform" },
  { href: "/admin/platform", label: "Settings", needs: "read_platform" },
  { href: "/admin/staff", label: "Access", needs: "grant_staff" },
];

export function Nav({ may }: { may: string[] }) {
  const here = usePathname();
  const mine = EVERY.filter((one) => may.includes(one.needs));

  return (
    <nav
      aria-label="Internal panel"
      className="border-pw-border -mx-4 mb-5 border-b px-4 sm:mx-0 sm:px-0"
    >
      {/*
        `scrollbar-none` is not relied on: the row scrolls either way, and a
        visible scrollbar on a phone is a hint that there is more to the right.
      */}
      <ul className="flex gap-1 overflow-x-auto">
        {mine.map((one) => {
          const current = here === one.href;
          return (
            <li key={one.href} className="shrink-0">
              <Link
                href={one.href}
                aria-current={current ? "page" : undefined}
                className={[
                  "-mb-px inline-block border-b-2 px-3 py-2.5 text-[14px] leading-[20px] whitespace-nowrap transition-colors",
                  current
                    ? "border-pw-blue text-pw-ink font-semibold"
                    : "text-pw-ink-500 hover:text-pw-ink border-transparent",
                ].join(" ")}
              >
                {one.label}
              </Link>
            </li>
          );
        })}
      </ul>
    </nav>
  );
}
