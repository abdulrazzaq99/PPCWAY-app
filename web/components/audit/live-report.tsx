"use client";

import { useEffect, useState } from "react";
import type { Listing } from "@/lib/listing";
import type { Run } from "@/lib/report-from-run";
import { reportFromRun } from "@/lib/report-from-run";
import { Checking } from "./checking";
import { ScoreReport } from "./score-report";
import { AuditPage } from "./shell";

/*
  One real run, drawn as the report's cards. It polls until the run is done, then
  reads the Google listing and the competitors nearby and hands all three to the
  same component the sample report uses, so the design has one home.

  The listing is read here rather than stored, which is what Google's terms
  require: we keep the place id and nothing else.
*/
export function LiveReport({ id }: { id: string }) {
  const [run, setRun] = useState<Run | null>(null);
  const [status, setStatus] = useState<"queued" | "running" | "done" | "failed" | "lost">("queued");
  const [listing, setListing] = useState<Listing | null>(null);
  const [rivals, setRivals] = useState<Listing[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let stop = false;
    let timer: number | undefined;
    async function tick() {
      try {
        const res = await fetch(`/api/audit/${id}`, { cache: "no-store" });
        const data = (await res.json()) as Run & { status: typeof status; error?: string };
        if (stop) return;
        if (!res.ok) {
          setError(data.error ?? "We could not find that audit.");
          setStatus("lost");
          return;
        }
        setRun(data);
        setStatus(data.status);
        if (data.status === "queued" || data.status === "running")
          timer = window.setTimeout(tick, 3000);
      } catch {
        if (!stop) {
          setError("We could not reach the audit service.");
          setStatus("lost");
        }
      }
    }
    tick();
    return () => {
      stop = true;
      if (timer) window.clearTimeout(timer);
    };
  }, [id]);

  const placeId = run?.place_id ?? "";
  const city = run?.city ?? "";
  useEffect(() => {
    if (status !== "done" || !placeId) return;
    let stop = false;
    (async () => {
      const [one, near] = await Promise.all([
        fetch(`/api/places/${placeId}`, { cache: "no-store" })
          .then((r) => (r.ok ? (r.json() as Promise<Listing>) : null))
          .catch(() => null),
        fetch(`/api/places/${placeId}/nearby?city=${encodeURIComponent(city)}`, {
          cache: "no-store",
        })
          .then((r) => (r.ok ? (r.json() as Promise<Listing[]>) : []))
          .catch(() => []),
      ]);
      if (stop) return;
      setListing(one);
      setRivals(Array.isArray(near) ? near : []);
    })();
    return () => {
      stop = true;
    };
  }, [status, placeId, city]);

  if (status === "lost" || status === "failed") {
    return (
      <AuditPage>
        <h1 className="text-[28px] leading-[34px] font-bold sm:text-[38px] sm:leading-[46px]">
          {status === "failed"
            ? `We could not finish checking ${run?.site ?? "that site"}.`
            : "We could not find that audit."}
        </h1>
        <p className="text-muted mt-4 max-w-[700px] text-[17px] leading-[22px]">
          {error ??
            "The site did not answer the way we expected. We will look at it by hand and email you. Nothing more to do on your side."}
        </p>
      </AuditPage>
    );
  }

  if (status !== "done" || !run?.report) {
    const site = (run?.site ?? "").replace(/^https?:\/\//, "").replace(/\/$/, "");
    return (
      <AuditPage>
        <Checking
          site={site || "your website"}
          stage={(run?.stage ?? "") as "crawling" | "rendering" | "speed" | "checks" | "done" | ""}
          pagesRead={run?.pages_read ?? 0}
        />
      </AuditPage>
    );
  }

  return <ScoreReport sample={reportFromRun(run, listing, rivals)} />;
}
