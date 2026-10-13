import {
  ChartBar,
  ChatCircleDots,
  Gauge,
  Gear,
  House,
  MagnifyingGlass,
  Megaphone,
  PencilSimple,
  Sparkle,
  TrendUp,
} from "@phosphor-icons/react/dist/ssr";
import { cookies, headers } from "next/headers";
import { redirect } from "next/navigation";
import type { ReactNode } from "react";
import { Sidebar } from "@/components/pw/shell";
import { SESSION_COOKIE } from "@/lib/session";

/*
  The signed-in app, in the design the client handed over. Everything inside
  this group wears the dashboard tokens and the 252px sidebar; the public site
  and the audit keep their own skin.
*/
const BACKEND = process.env.BACKEND_URL ?? "http://localhost:8300";
const size = 18;

const MAIN = [
  { href: "/home", label: "Home", icon: <House size={size} weight="bold" /> },
  { href: "/campaigns", label: "Campaigns", icon: <Megaphone size={size} weight="bold" /> },
  { href: "/otto", label: "Otto inbox", icon: <Sparkle size={size} weight="bold" /> },
  { href: "/reports", label: "Reports", icon: <ChartBar size={size} weight="bold" /> },
  { href: "/chat", label: "Chat with Otto", icon: <ChatCircleDots size={size} weight="bold" /> },
  { href: "/settings", label: "Settings", icon: <Gear size={size} weight="bold" /> },
];

const TOOLS = [
  {
    href: "/tools/audit",
    label: "Website audit",
    icon: <MagnifyingGlass size={size} weight="bold" />,
  },
  { href: "/tools/budget", label: "Budget calculator", icon: <Gauge size={size} weight="bold" /> },
  {
    href: "/tools/cost-per-lead",
    label: "Cost per lead & ROAS",
    icon: <TrendUp size={size} weight="bold" />,
  },
  {
    href: "/tools/ad-copy",
    label: "Ad copy checker",
    icon: <PencilSimple size={size} weight="bold" />,
  },
];

/** Where the visitor was going, so signing in returns them to it with its query. */
async function here(): Promise<string> {
  const head = await headers();
  return head.get("x-pathname") ?? head.get("x-invoke-path") ?? "/home";
}

type Run = { status: string; score?: number | null };

/** The latest audit's score, which the sidebar shows beside Website audit. */
async function latestScore(token: string): Promise<number | null> {
  try {
    const res = await fetch(`${BACKEND}/v1/audits/mine`, {
      headers: { "x-session-token": token },
      cache: "no-store",
    });
    if (!res.ok) return null;
    const runs = (await res.json()) as Run[];
    return runs.find((r) => r.status === "done" && r.score != null)?.score ?? null;
  } catch {
    return null;
  }
}

export default async function PwLayout({ children }: { children: ReactNode }) {
  const token = (await cookies()).get(SESSION_COOKIE)?.value;
  if (!token) redirect(`/login?next=${encodeURIComponent(await here())}`);

  const person = await fetch(`${BACKEND}/v1/auth/me`, {
    headers: { "x-session-token": token },
    cache: "no-store",
  })
    .then((r) => (r.ok ? (r.json() as Promise<{ email: string; name: string }>) : null))
    .catch(() => null);
  if (!person) redirect(`/login?next=${encodeURIComponent(await here())}`);

  const [org, score] = await Promise.all([
    fetch(`${BACKEND}/v1/org`, { headers: { "x-session-token": token }, cache: "no-store" })
      .then((r) =>
        r.ok ? (r.json() as Promise<{ name: string; plan: string; currency: string }>) : null,
      )
      .catch(() => null),
    latestScore(token),
  ]);

  const business = org?.name || person.name || person.email;
  const plan = org
    ? `${org.plan[0].toUpperCase()}${org.plan.slice(1)} plan · ${org.currency}`
    : undefined;
  // Otto has nothing to show yet; the badge appears when it does.
  const tools = TOOLS.map((item) =>
    item.href === "/tools/audit" && score !== null ? { ...item, badge: score } : item,
  );

  // Which screen they are on, so the sidebar marks it rather than always Home.
  const path = (await here()).split("?")[0];

  return (
    <div className="bg-pw-ground text-pw-ink flex min-h-dvh">
      <Sidebar items={MAIN} tools={tools} active={path} business={business} plan={plan} />
      <div className="min-w-0 flex-1">{children}</div>
    </div>
  );
}
