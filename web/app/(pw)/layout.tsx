import {
  ChartBar,
  ChatCircleDots,
  Gauge,
  House,
  MagnifyingGlass,
  Megaphone,
  PencilSimple,
  Sparkle,
  TrendUp,
} from "@phosphor-icons/react/dist/ssr";
import { cookies } from "next/headers";
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

export default async function PwLayout({ children }: { children: ReactNode }) {
  const token = (await cookies()).get(SESSION_COOKIE)?.value;
  if (!token) redirect("/login?next=/home");

  const person = await fetch(`${BACKEND}/v1/auth/me`, {
    headers: { "x-session-token": token },
    cache: "no-store",
  })
    .then((r) => (r.ok ? (r.json() as Promise<{ email: string; name: string }>) : null))
    .catch(() => null);
  if (!person) redirect("/login?next=/home");

  const business = person.name || person.email;

  return (
    <div className="bg-pw-ground text-pw-ink flex min-h-dvh">
      <Sidebar items={MAIN} tools={TOOLS} active="/home" business={business} />
      <div className="min-w-0 flex-1">{children}</div>
    </div>
  );
}
