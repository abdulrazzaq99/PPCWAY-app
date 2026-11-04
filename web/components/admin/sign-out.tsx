"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

/*
  Signing out of the internal panel.

  A small client component because the bar around it is server-rendered and
  this is the only part of it that needs to do something. The POST revokes the
  session at the backend and drops the cookie, then `refresh()` throws away
  every server-rendered page the old session saw -- which matters more here
  than on a merchant screen, because those pages hold somebody else's figures.

  It lives in the staff bar rather than an account menu because that bar is the
  one thing on every internal screen. Somebody who is signed in as staff should
  never have to go looking for the way out -- and on these screens, looking for
  it means clicking around somebody else's business while still signed in.
*/
export function SignOut() {
  const router = useRouter();
  const [going, setGoing] = useState(false);

  async function out() {
    setGoing(true);
    try {
      await fetch("/api/auth/signout", { method: "POST" });
    } catch {
      /* The cookie is dropped by the server either way, and a session nobody
         can reach is already over. Either way we leave. */
    }
    router.replace("/login?reason=signed-out");
    // After the navigation, not before: this is what drops the cached renders
    // of the internal pages, and they are the ones worth dropping.
    router.refresh();
  }

  return (
    <button
      type="button"
      onClick={out}
      disabled={going}
      className="text-pw-ink-600 hover:text-pw-ink underline underline-offset-2 disabled:opacity-60"
    >
      {going ? "Signing out…" : "Sign out"}
    </button>
  );
}
