"use client";

import Link from "next/link";
import { FirstSync } from "@/components/pw/first-sync";
import { useEffect, useState } from "react";

/*
  What a newly connected account sees: the import happening, and the way on once
  it has. Connecting used to end on two buttons and an empty dashboard behind
  them; ninety days have to be read before the home screen has anything to say.

  Once the first pass is done the panel steps out of the way and the buttons are
  what is left, which is where this screen started.
*/
export function FirstLook() {
  const [reading, setReading] = useState<boolean | null>(null);

  useEffect(() => {
    let stop = false;
    fetch("/api/ads/sync", { cache: "no-store" })
      .then(async (res) => {
        if (!res.ok || stop) return;
        // What matters is whether we hold their past, not whether a pass has
        // run: an account connected before the mirror existed has runs behind
        // it and no history in front of anybody.
        const now = (await res.json()) as { held?: { days?: number } };
        setReading(!now.held?.days);
      })
      .catch(() => {
        if (!stop) setReading(false);
      });
    return () => {
      stop = true;
    };
  }, []);

  return (
    <>
      {reading ? (
        <div className="mt-5">
          <FirstSync onDone={() => setReading(false)} />
        </div>
      ) : null}
      <div className="mt-5 flex flex-wrap gap-3">
        <Link
          href="/home"
          className="bg-pw-blue hover:bg-pw-blue-hover rounded-[10px] px-4 py-2 text-[14px] font-semibold text-white"
        >
          Go to your dashboard
        </Link>
        <Link
          href="/campaigns"
          className="border-pw-border-strong hover:bg-pw-muted rounded-[10px] border px-4 py-2 text-[14px] font-semibold"
        >
          See your campaigns
        </Link>
      </div>
    </>
  );
}
