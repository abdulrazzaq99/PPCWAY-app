/*
  Asking the backend for something that needs no sign-in: a shared report, a
  shared fix list. Separate from `ask` on purpose — there is no session to pass
  here, and a page that reads this must never be given one by accident.
*/
const BACKEND = process.env.BACKEND_URL ?? "http://localhost:8300";

export async function askPublic<T>(path: string): Promise<T | null> {
  try {
    const res = await fetch(`${BACKEND}${path}`, { cache: "no-store" });
    return res.ok ? ((await res.json()) as T) : null;
  } catch {
    return null;
  }
}
