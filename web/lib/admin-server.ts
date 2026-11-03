import { cookies } from "next/headers";
import type { Merchant, MerchantRow, Overview, PlatformView, Whoami } from "@/lib/admin";
import { SESSION_COOKIE } from "@/lib/session";

/*
  The panel's reads, done on the server while the page renders.

  Each returns its data or a sentence saying why not, never a thrown error: an
  internal screen that white-screens during an incident is the worst possible
  time for it, and "we could not reach the API" is itself the most useful thing
  the panel could say at that moment.
*/
const BACKEND = process.env.BACKEND_URL ?? "http://localhost:8300";

export type Read<T> = { data: T | null; trouble: string };

async function get<T>(path: string): Promise<Read<T>> {
  const token = (await cookies()).get(SESSION_COOKIE)?.value;
  if (!token) return { data: null, trouble: "Sign in first." };
  try {
    const res = await fetch(`${BACKEND}${path}`, {
      headers: { "x-session-token": token },
      cache: "no-store",
    });
    const said = (await res.json().catch(() => ({}))) as T & { detail?: string };
    if (!res.ok) {
      return {
        data: null,
        trouble:
          said.detail ??
          (res.status === 403
            ? "This is PPCWay's internal panel and you do not have access to it."
            : "The panel could not read that."),
      };
    }
    return { data: said, trouble: "" };
  } catch {
    return { data: null, trouble: "The API is not reachable right now." };
  }
}

/*
  Asked first by every admin page. It answers 200 with `staff: false` for
  everybody who is not staff, so a person who wanders onto /admin gets a plain
  sentence rather than a console full of errors.
*/
export async function readWhoami(): Promise<Read<Whoami>> {
  return get<Whoami>("/v1/admin/whoami");
}

export async function readOverview(window = "7d"): Promise<Read<Overview>> {
  return get<Overview>(`/v1/admin/overview?window=${encodeURIComponent(window)}`);
}

export async function readMerchants(lookFor = ""): Promise<Read<{ merchants: MerchantRow[] }>> {
  const q = lookFor ? `?look_for=${encodeURIComponent(lookFor)}` : "";
  return get<{ merchants: MerchantRow[] }>(`/v1/admin/merchants${q}`);
}

export async function readMerchant(id: string): Promise<Read<Merchant>> {
  return get<Merchant>(`/v1/admin/merchants/${encodeURIComponent(id)}`);
}

export async function readPlatform(): Promise<Read<PlatformView>> {
  return get<PlatformView>("/v1/admin/platform");
}
