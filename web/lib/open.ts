/*
  Whether anybody may make an account yet.

  The free audit never asks this: it is open to everybody and always was. This
  is only about the door behind it, and it is only a courtesy — the backend
  refuses a stranger whatever this says, so a screen that gets it wrong costs a
  confusing moment rather than a way in.

  Unreachable counts as closed. While PPCWay is opening gradually that is the
  true answer, and a form that leads to a refusal is worse than a page saying
  plainly that it is not time yet.
*/
const BACKEND = process.env.BACKEND_URL ?? "http://localhost:8300";

export async function isOpen(): Promise<boolean> {
  try {
    const res = await fetch(`${BACKEND}/v1/open`, { cache: "no-store" });
    if (!res.ok) return false;
    const said = (await res.json()) as { open?: boolean };
    return said.open === true;
  } catch {
    return false;
  }
}
