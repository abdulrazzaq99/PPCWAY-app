"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { LinkButton } from "@/components/ui/button";
import { AuditPage, Card } from "./shell";

/*
  Every audit this person ran while signed in. The report itself is read again
  when it is opened, so what is kept here is only which runs were theirs.
*/
type Run = { id: string; site: string; status: string; stage?: string };

export function MyAudits() {
  const [runs, setRuns] = useState<Run[] | null>(null);
  const [signedOut, setSignedOut] = useState(false);

  useEffect(() => {
    let stop = false;
    fetch("/api/audit/mine", { cache: "no-store" })
      .then(async (r) => {
        if (stop) return;
        if (r.status === 401) {
          setSignedOut(true);
          setRuns([]);
          return;
        }
        setRuns((await r.json()) as Run[]);
      })
      .catch(() => !stop && setRuns([]));
    return () => {
      stop = true;
    };
  }, []);

  return (
    <AuditPage>
      <h1 className="text-[34px] leading-[40px] font-semibold sm:text-[42px] sm:leading-[50px]">
        Your audits
      </h1>
      {signedOut ? (
        <>
          <p className="text-muted mt-4 text-[17px] leading-[26px]">
            Sign in and every audit you run is kept here, so you can open it again.
          </p>
          <div className="mt-6 flex gap-3">
            <LinkButton href="/login">Sign in</LinkButton>
            <LinkButton href="/audit" variant="secondary">
              Run a free audit
            </LinkButton>
          </div>
        </>
      ) : runs === null ? (
        <p className="text-muted mt-4 text-[17px] leading-[26px]">Looking…</p>
      ) : runs.length === 0 ? (
        <>
          <p className="text-muted mt-4 text-[17px] leading-[26px]">
            Nothing here yet. The next audit you run while signed in will be.
          </p>
          <div className="mt-6">
            <LinkButton href="/audit">Run a free audit</LinkButton>
          </div>
        </>
      ) : (
        <Card className="mt-6 overflow-hidden">
          <ul className="divide-line-soft divide-y">
            {runs.map((run) => (
              <li
                key={run.id}
                className="flex items-center justify-between gap-4 px-5 py-4 sm:px-7"
              >
                <span className="min-w-0">
                  <span className="block truncate text-[16px] leading-[21px] font-semibold">
                    {run.site.replace(/^https?:\/\//, "").replace(/\/$/, "")}
                  </span>
                  <span className="text-faint text-[13px] leading-4">
                    {run.status === "done"
                      ? "Finished"
                      : run.status === "failed"
                        ? "Did not finish"
                        : "Still running"}
                  </span>
                </span>
                <Link
                  href={`/audit/${run.id}`}
                  className="text-brand shrink-0 text-[15px] leading-[18px] font-semibold"
                >
                  Open
                </Link>
              </li>
            ))}
          </ul>
        </Card>
      )}
    </AuditPage>
  );
}
