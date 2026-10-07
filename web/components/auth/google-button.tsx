"use client";

import Script from "next/script";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useRef, useState } from "react";

/*
  Signing in with Google. Google's own script draws the button and hands back a
  signed token saying who the person is; that token goes to our server once, which
  checks the signature with Google and sets the session cookie. The cookie is
  httpOnly, so nothing on this page can read it.

  Without a client id the drawn button is shown instead, and says so when pressed,
  rather than a button that silently does nothing.
*/
type Credential = { credential?: string };

declare global {
  interface Window {
    google?: {
      accounts: {
        id: {
          initialize: (options: {
            client_id: string;
            callback: (reply: Credential) => void;
          }) => void;
          renderButton: (into: HTMLElement, options: Record<string, string | number>) => void;
        };
      };
    };
  }
}

export function GoogleButton({
  label = "Continue with Google",
  next = "/overview",
}: {
  label?: string;
  next?: string;
}) {
  const router = useRouter();
  const [clientId, setClientId] = useState<string | null>(null);
  const holder = useRef<HTMLDivElement>(null);
  const [ready, setReady] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const signIn = useCallback(
    async (reply: Credential) => {
      if (!reply.credential) return;
      setError(null);
      try {
        const res = await fetch("/api/auth/google", {
          method: "POST",
          headers: { "content-type": "application/json" },
          body: JSON.stringify({ credential: reply.credential }),
        });
        if (!res.ok) {
          const said = (await res.json().catch(() => ({}))) as { error?: string };
          setError(said.error ?? "Google signed you in, but we could not finish. Try again.");
          return;
        }
        router.replace(next);
        router.refresh();
      } catch {
        setError("We could not reach the sign-in service. Try again in a minute.");
      }
    },
    [next, router],
  );

  useEffect(() => {
    let stop = false;
    fetch("/api/auth/config", { cache: "no-store" })
      .then((r) => r.json() as Promise<{ clientId: string }>)
      .then((said) => !stop && setClientId(said.clientId))
      .catch(() => !stop && setClientId(""));
    return () => {
      stop = true;
    };
  }, []);

  useEffect(() => {
    if (!ready || !clientId || !holder.current || !window.google) return;
    window.google.accounts.id.initialize({ client_id: clientId, callback: signIn });
    window.google.accounts.id.renderButton(holder.current, {
      type: "standard",
      theme: "outline",
      size: "large",
      text: "continue_with",
      shape: "rectangular",
      logo_alignment: "center",
      width: 360,
    });
  }, [ready, clientId, signIn]);

  if (clientId === null) {
    return <div className="min-h-[50px]" aria-hidden />;
  }

  if (!clientId) {
    return (
      <div>
        <button
          type="button"
          onClick={() => setError("Signing in with Google is not switched on yet.")}
          className="border-line-input bg-panel text-ink hover:bg-line-soft flex h-[50px] w-full items-center justify-center gap-2 rounded-[12px] border text-[15px] font-semibold"
        >
          {label}
        </button>
        {error ? <Message text={error} /> : null}
      </div>
    );
  }

  return (
    <div>
      <Script src="https://accounts.google.com/gsi/client" onReady={() => setReady(true)} />
      <div ref={holder} className="flex min-h-[50px] justify-center [&>div]:w-full" />
      {error ? <Message text={error} /> : null}
    </div>
  );
}

function Message({ text }: { text: string }) {
  return (
    <p className="text-red mt-2 text-[14px] leading-[18px] font-medium" role="alert">
      {text}
    </p>
  );
}
