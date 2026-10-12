import { cookies } from "next/headers";
import { SESSION_COOKIE } from "@/lib/session";

/*
  One way for a signed-in page to ask the backend something. It never throws:
  a screen that cannot reach the service shows what it does know and says the
  rest is missing, which is more use than an error page.
*/
const BACKEND = process.env.BACKEND_URL ?? "http://localhost:8300";

export async function ask<T>(path: string, fallback: T): Promise<T> {
  const token = (await cookies()).get(SESSION_COOKIE)?.value;
  if (!token) return fallback;
  try {
    const res = await fetch(`${BACKEND}${path}`, {
      headers: { "x-session-token": token },
      cache: "no-store",
    });
    return res.ok ? ((await res.json()) as T) : fallback;
  } catch {
    return fallback;
  }
}
