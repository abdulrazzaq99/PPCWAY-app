"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { Button } from "@/components/ui/button";

/*
  The button that turns a chosen listing into a real run. With a website it posts
  to the backend and goes to the live checking page; without one it cannot run yet,
  so it says so.
*/
export function StartAudit({
  business,
  city,
  site,
  label,
}: {
  business: string;
  city: string;
  site: string;
  label: string;
}) {
  const router = useRouter();
  const [working, setWorking] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function start() {
    if (!site) {
      setError("Add the website address above so we can check it.");
      return;
    }
    setWorking(true);
    setError(null);
    try {
      const res = await fetch("/api/audit", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ business_name: business, city, site, source: "landing" }),
      });
      const data = (await res.json().catch(() => ({}))) as {
        id?: string;
        error?: string;
        detail?: { msg?: string }[];
      };
      if (res.ok && data.id) {
        router.push(`/audit/${data.id}`);
        return;
      }
      const first = Array.isArray(data.detail) ? data.detail[0]?.msg : undefined;
      setError(
        (first ?? data.error ?? "Something went wrong on our side. Try again in a minute.").replace(
          /^Value error, /,
          "",
        ),
      );
    } catch {
      setError("We could not reach the audit service. Try again in a minute.");
    } finally {
      setWorking(false);
    }
  }

  return (
    <div className="flex flex-col items-end gap-2">
      <Button
        type="button"
        size="sm"
        className="h-[42px]"
        onClick={start}
        working={working ? "Starting" : false}
      >
        {label}
      </Button>
      {error ? (
        <p className="text-meta font-medium text-[#c0392b]" role="alert">
          {error}
        </p>
      ) : null}
    </div>
  );
}
