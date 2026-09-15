/*
  The sidebar and the phone tab bar, from the "V2 Dashboard · Desktop 1440" and
  "V2 · Mobile · Home" frames. Merchants and agencies share one menu; PPCWay staff
  see a different one, and super admins get a second group.
*/
export type IconName =
  "overview" | "activity" | "approvals" | "campaigns" | "searches" | "settings" | "help" | "more";

export type NavItem = { key: string; label: string; href: string; icon: IconName; badge?: number };
export type NavGroup = { heading?: string; items: NavItem[] };

export type NavKind = "merchant" | "agency" | "admin" | "admin-super";

export function navFor(
  kind: NavKind,
  badges: Record<string, number | undefined>,
): {
  top: NavGroup[];
  bottom: NavItem[];
} {
  if (kind === "admin" || kind === "admin-super") {
    const top: NavGroup[] = [
      {
        items: [
          { key: "merchants", label: "Merchants", href: "/admin", icon: "overview" },
          { key: "jobs", label: "Jobs", href: "/admin/jobs", icon: "activity" },
          {
            key: "errors",
            label: "Errors",
            href: "/admin/errors",
            icon: "approvals",
            badge: badges.errors,
          },
          { key: "quota", label: "Quota", href: "/admin/quota", icon: "campaigns" },
          { key: "audit", label: "Audit log", href: "/admin/audit", icon: "searches" },
        ],
      },
    ];
    if (kind === "admin-super") {
      top.push({
        heading: "Super admin",
        items: [
          {
            key: "reviews",
            label: "Reviews",
            href: "/admin/reviews",
            icon: "approvals",
            badge: badges.reviews,
          },
          { key: "staff", label: "Staff", href: "/admin/staff", icon: "campaigns" },
          { key: "platform", label: "Platform", href: "/admin/platform", icon: "campaigns" },
          { key: "metrics", label: "Metrics", href: "/admin/metrics", icon: "campaigns" },
        ],
      });
    }
    return {
      top,
      bottom: [
        { key: "runbook", label: "Runbook", href: "/admin/runbook", icon: "settings" },
        { key: "help", label: "Help", href: "/help", icon: "help" },
      ],
    };
  }
  const agency = kind === "agency";
  return {
    top: [
      {
        items: [
          {
            key: "overview",
            label: "Overview",
            href: agency ? "/agency/overview" : "/overview",
            icon: "overview",
          },
          { key: "activity", label: "Activity", href: "/activity", icon: "activity" },
          {
            key: "approvals",
            label: "Approvals",
            href: "/approvals",
            icon: "approvals",
            badge: badges.approvals,
          },
          { key: "campaigns", label: "Campaigns", href: "/campaigns", icon: "campaigns" },
          { key: "searches", label: "Searches", href: "/searches", icon: "searches" },
        ],
      },
    ],
    bottom: [
      {
        key: "settings",
        label: "Settings",
        href: agency ? "/agency/settings" : "/settings",
        icon: "settings",
      },
      { key: "help", label: "Help", href: "/help", icon: "help" },
    ],
  };
}
