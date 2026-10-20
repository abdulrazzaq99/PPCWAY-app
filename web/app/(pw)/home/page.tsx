import { cookies } from "next/headers";
import type { Metadata } from "next";
import { Home, type LatestAudit, type Summary } from "@/components/pw/home";
import type { History } from "@/lib/audit";
import { AskOttoButton, Header, PwPage } from "@/components/pw/shell";
import { SESSION_COOKIE } from "@/lib/session";

export const metadata: Metadata = { title: "Home · PPCway" };

const BACKEND = process.env.BACKEND_URL ?? "http://localhost:8300";

type Run = { id: string; site: string; status: string; score?: number | null };

function greeting(now: Date): string {
  const hour = now.getHours();
  if (hour < 12) return "Good morning";
  return hour < 18 ? "Good afternoon" : "Good evening";
}

export default async function HomePage() {
  const token = (await cookies()).get(SESSION_COOKIE)?.value ?? "";
  const headers = { "x-session-token": token };
  const ask = async <T,>(path: string, fallback: T): Promise<T> => {
    try {
      const res = await fetch(`${BACKEND}${path}`, { headers, cache: "no-store" });
      return res.ok ? ((await res.json()) as T) : fallback;
    } catch {
      return fallback;
    }
  };

  const [person, summary, runs, ads, history] = await Promise.all([
    ask<{ email: string; name: string; email_verified?: boolean }>("/v1/auth/me", {
      email: "",
      name: "",
    }),
    ask<Summary>("/v1/ads/summary?days=30", { read: false }),
    ask<Run[]>("/v1/audits/mine", []),
    ask<{ connected: boolean; customer_name?: string }>("/v1/ads/status", { connected: false }),
    ask<History>("/v1/audits/history", { site: "", points: [], changed: null }),
  ]);

  const done = runs.find((r) => r.status === "done");
  const audit: LatestAudit = done
    ? { id: done.id, site: done.site, score: done.score ?? null, when: "" }
    : null;

  const first = (person.name || person.email).split(/[\s@]/)[0] ?? "there";
  const business = ads.customer_name || person.name || person.email;
  const today = new Date();

  return (
    <>
      <Header
        eyebrow={`${today.toLocaleDateString(undefined, { weekday: "long", month: "long", day: "numeric" })} · ${business}`}
        title={`${greeting(today)}, ${first}`}
        right={<AskOttoButton />}
      />
      <PwPage>
        <Home
          firstName={first}
          business={business}
          summary={summary}
          audit={audit}
          connected={Boolean(ads.connected)}
          emailVerified={person.email_verified !== false}
          scores={history.points}
        />
      </PwPage>
    </>
  );
}
