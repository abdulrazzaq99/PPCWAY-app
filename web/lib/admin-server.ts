import { cookies } from "next/headers";
import { doorOf, type Chrome, type Door } from "@/lib/admin";
import type {
  Fault,
  Grant,
  JobsPage,
  Look,
  Merchant,
  MerchantShow,
  MerchantsPage,
  Overview,
  PlatformView,
  Quota,
  Room,
  Whoami,
} from "@/lib/admin";
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

export async function readMerchants(
  lookFor = "",
  {
    show = "all",
    limit = 100,
    offset = 0,
  }: { show?: MerchantShow; limit?: number; offset?: number } = {},
): Promise<Read<MerchantsPage>> {
  const q = new URLSearchParams({ show, limit: String(limit), offset: String(offset) });
  if (lookFor) q.set("look_for", lookFor);
  return get<MerchantsPage>(`/v1/admin/merchants?${q}`);
}

export async function readMerchant(id: string): Promise<Read<Merchant>> {
  return get<Merchant>(`/v1/admin/merchants/${encodeURIComponent(id)}`);
}

export async function readPlatform(): Promise<Read<PlatformView>> {
  return get<PlatformView>("/v1/admin/platform");
}

export async function readJobs(
  failedOnly = false,
  { limit = 100, offset = 0 }: { limit?: number; offset?: number } = {},
): Promise<Read<JobsPage>> {
  const q = new URLSearchParams({ limit: String(limit), offset: String(offset) });
  if (failedOnly) q.set("failed_only", "true");
  return get<JobsPage>(`/v1/admin/jobs?${q}`);
}

export async function readErrors(window = "7d"): Promise<Read<{ faults: Fault[] }>> {
  return get<{ faults: Fault[] }>(`/v1/admin/errors?window=${encodeURIComponent(window)}`);
}

export async function readQuotaAll(): Promise<Read<{ accounts: Room[] }>> {
  return get<{ accounts: Room[] }>("/v1/admin/quota/all");
}

export async function readGrants(): Promise<Read<{ grants: Grant[] }>> {
  return get<{ grants: Grant[] }>("/v1/admin/staff");
}

export async function readWhoLooked(id: string): Promise<Read<{ looks: Look[] }>> {
  return get<{ looks: Look[] }>(`/v1/admin/merchants/${encodeURIComponent(id)}/who-looked`);
}

export async function readQuota(customerId: string): Promise<Read<Quota>> {
  return get<Quota>(`/v1/admin/quota?customer_id=${encodeURIComponent(customerId)}`);
}

/*
  The door's state for the shell, read beside each screen's own data. Only for
  staff who may read the platform: support does not get a chip that would
  answer 403 on every page.
*/
export async function readDoor(who: Whoami): Promise<Door | undefined> {
  if (!who.may.includes("read_platform")) return undefined;
  const { data } = await readPlatform();
  return doorOf(data);
}

/*
  What the shell shows on every screen, read beside the screen's own data: the
  door, and the count on Failures. The count is always the last 7 days, the
  failures screen's default, so the number in the sidebar means the same thing
  whichever screen it is read on.
*/
export async function readChrome(
  who: Whoami,
  { door: withDoor = true }: { door?: boolean } = {},
): Promise<Chrome> {
  const [door, errors] = await Promise.all([
    /* A screen that reads the platform itself passes the door in instead. */
    withDoor ? readDoor(who) : Promise.resolve(undefined),
    who.may.includes("read_errors") ? readErrors("7d") : Promise.resolve(null),
  ]);
  return { door, failures: errors?.data?.faults.length };
}
