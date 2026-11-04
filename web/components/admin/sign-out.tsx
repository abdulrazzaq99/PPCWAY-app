"use client";

import { SignOutIcon } from "@phosphor-icons/react";
import { useRouter } from "next/navigation";
import { useState } from "react";

/*
  Signing out of the internal console.

  A small client component because the shell around it is rendered on the
  server and this is the only part of it that needs to do something. The POST
  revokes the session at the backend and drops the cookie, then `refresh()`
  throws away every server-rendered page the old session saw -- which matters
  more here than on a merchant screen, because those pages hold somebody
  else's figures.

  It sits beside your name at the foot of the sidebar, on every screen, and in
  the phone menu. Somebody signed in as staff should never have to go looking
  for the way out.
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
      title="Sign out"
      aria-label={going ? "Signing out" : "Sign out"}
      className="text-ad-faint hover:text-ad-text hover:border-ad-control flex h-8 w-7 flex-none items-center justify-center rounded-full border border-transparent transition-colors disabled:opacity-60"
    >
      <SignOutIcon size={16} aria-hidden />
    </button>
  );
}
