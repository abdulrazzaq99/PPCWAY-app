import { cookies } from "next/headers";
import type { Inbox } from "@/lib/otto";
import { SESSION_COOKIE } from "@/lib/session";

/*
  The inbox, read on the server while the page renders. Not fetched from the
  browser on mount: that gives a merchant a blank panel and then a flash of
  content, and the figures are already in hand by the time the HTML is built.
*/
const BACKEND = process.env.BACKEND_URL ?? "http://localhost:8300";

export type Loaded = { inbox: Inbox | null; trouble: string };

export async function readInbox(): Promise<Loaded> {
  const token = (await cookies()).get(SESSION_COOKIE)?.value;
  if (!token) return { inbox: null, trouble: "Sign in to see what Otto found." };
  try {
    const res = await fetch(`${BACKEND}/v1/otto/inbox`, {
      headers: { "x-session-token": token },
      cache: "no-store",
    });
    const said = (await res.json().catch(() => ({}))) as Inbox & { detail?: string };
    if (!res.ok) {
      return { inbox: null, trouble: said.detail ?? "Otto could not read your account." };
    }
    return { inbox: said, trouble: "" };
  } catch {
    return { inbox: null, trouble: "Otto is not reachable right now." };
  }
}
