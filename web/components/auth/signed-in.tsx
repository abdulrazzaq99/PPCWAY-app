"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

/*
  Who is signed in, in the public header. It asks the server, because the cookie
  that answers the question is httpOnly and this page cannot read it.
*/
type Person = { email: string; name: string; picture: string };

export function SignedIn() {
  const router = useRouter();
  const [person, setPerson] = useState<Person | null>(null);
  const [asked, setAsked] = useState(false);

  useEffect(() => {
    let stop = false;
    fetch("/api/auth/me", { cache: "no-store" })
      .then((r) => (r.ok ? (r.json() as Promise<{ person: Person }>) : null))
      .then((said) => {
        if (!stop) {
          setPerson(said?.person ?? null);
          setAsked(true);
        }
      })
      .catch(() => !stop && setAsked(true));
    return () => {
      stop = true;
    };
  }, []);

  async function signOut() {
    await fetch("/api/auth/signout", { method: "POST" }).catch(() => undefined);
    setPerson(null);
    router.refresh();
  }

  if (!asked || !person) {
    return (
      <Link href="/login" className="text-ink text-[15px] leading-[18px] font-semibold">
        Log in
      </Link>
    );
  }

  const first = person.name.split(" ")[0] || person.email;
  return (
    <div className="flex items-center gap-4">
      <Link href="/audit/mine" className="text-ink text-[15px] leading-[18px] font-semibold">
        {first}
      </Link>
      <button
        type="button"
        onClick={signOut}
        className="text-muted hover:text-ink text-[15px] leading-[18px] font-semibold"
      >
        Sign out
      </button>
    </div>
  );
}
