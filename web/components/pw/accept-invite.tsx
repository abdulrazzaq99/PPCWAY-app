"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { PwCard } from "@/components/pw/shell";

/*
  Taking up an invitation. The address has to match the one invited, so a link
  that reaches the wrong inbox is useless — which is the whole point of having
  roles at all.
*/
export function AcceptInvite({ token }: { token: string }) {
  const router = useRouter();
  const [state, setState] = useState<"ready" | "joining" | "joined">("ready");
  const [trouble, setTrouble] = useState("");

  async function join() {
    setState("joining");
    setTrouble("");
    try {
      const res = await fetch("/api/org/accept", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ token }),
      });
      if (res.ok) {
        setState("joined");
        router.push("/home");
        router.refresh();
        return;
      }
      const said = (await res.json().catch(() => ({}))) as { error?: string };
      setTrouble(said.error ?? "That invitation is not valid for this account.");
      setState("ready");
    } catch {
      setTrouble("We could not reach the service.");
      setState("ready");
    }
  }

  if (!token) {
    return (
      <PwCard className="p-6 sm:p-8">
        <p className="text-pw-ink-500 text-[16px]">
          This link is missing its invitation. Ask whoever invited you to send it again.
        </p>
      </PwCard>
    );
  }

  return (
    <PwCard className="p-6 sm:p-8">
      <p className="max-w-[620px] text-[16px] leading-[25px]">
        Somebody has asked you to join their business on PPCway. Accepting adds you to it with the
        role they chose; it does not give you their Google Ads account, and it changes nothing you
        already have.
      </p>
      <div className="mt-5">
        <button
          type="button"
          onClick={join}
          disabled={state !== "ready"}
          className="bg-pw-blue hover:bg-pw-blue-hover rounded-[10px] px-4 py-2 text-[15px] font-semibold text-white disabled:opacity-70"
        >
          {state === "joining" ? "Joining…" : state === "joined" ? "Joined" : "Accept and join"}
        </button>
      </div>
      {trouble ? (
        <p className="text-pw-bad mt-3 text-[14px]" role="alert">
          {trouble}
        </p>
      ) : null}
    </PwCard>
  );
}
