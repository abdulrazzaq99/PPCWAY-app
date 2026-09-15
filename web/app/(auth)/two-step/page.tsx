"use client";

import { Suspense, useState, type FormEvent } from "react";
import { useSearchParams } from "next/navigation";
import { AuthCard, AuthShell } from "@/components/auth/auth-shell";
import { CodeField } from "@/components/auth/code-field";
import { Button, TextLink } from "@/components/ui/button";

/*
  Two frames share this route. Plain: enter the six-digit code. With ?view=setup:
  a PPCWay staff account that must set two-step up before it can open any merchant.
*/
function TwoStepPageInner() {
  const setup = useSearchParams().get("view") === "setup";
  const [working, setWorking] = useState(false);
  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setWorking(true);
  }
  if (setup) {
    return (
      <AuthShell
        headline="Admin accounts need two-step sign-in."
        body="You can't open any merchant's account until it is set up. It takes two minutes, and it is the same for every PPCWay staff account."
        footnote="PPCWay admin · required for all staff"
        below={
          <>
            No phone with you? <TextLink href="#">Ask a super admin</TextLink>
          </>
        }
      >
        <AuthCard
          title="Set up two-step to continue"
          intro="Scan the code with your authenticator app, then type the six-digit code it shows."
          onSubmit={submit}
        >
          <SetupCode />
          <p className="text-muted text-[13px] leading-4 font-semibold">
            Or type this key: KZXW 6YTB OI3D 4P2M
          </p>
          <CodeField label="Six-digit code" />
          <Button type="submit" full className="h-12" working={working && "Checking"}>
            Turn on and continue
          </Button>
        </AuthCard>
      </AuthShell>
    );
  }
  return (
    <AuthShell
      headline="One more step."
      body="Two-step sign-in keeps your ad spend out of the wrong hands."
      footnote="Free for 14 days. No card needed to look around."
      below={
        <>
          Lost your phone? <TextLink href="#">Use a backup code</TextLink>
        </>
      }
    >
      <AuthCard
        title="Enter your code"
        intro="Open your authenticator app and type the six-digit code for PPCWay."
        onSubmit={submit}
      >
        <CodeField label="Six-digit code" defaultValue="418 902" />
        <Button type="submit" full className="h-12" working={working && "Checking"}>
          Confirm
        </Button>
      </AuthCard>
    </AuthShell>
  );
}

/** A drawn placeholder for the set-up QR code: three finders and a scatter of modules. */
function SetupCode() {
  const cells = [
    [8, 0],
    [9, 0],
    [10, 0],
    [11, 0],
    [8, 1],
    [12, 1],
    [8, 2],
    [10, 2],
    [11, 2],
    [9, 3],
    [10, 3],
    [11, 3],
    [11, 4],
    [12, 4],
    [9, 5],
    [10, 5],
    [8, 6],
    [9, 6],
    [12, 6],
    [10, 7],
    [12, 7],
    [3, 8],
    [4, 8],
    [10, 8],
    [11, 8],
    [13, 8],
    [16, 8],
    [18, 8],
    [4, 9],
    [7, 9],
    [10, 9],
    [11, 9],
    [12, 9],
    [14, 9],
    [15, 9],
    [17, 9],
    [19, 9],
    [20, 9],
    [0, 10],
    [4, 10],
    [9, 10],
    [13, 10],
    [15, 10],
    [19, 10],
    [20, 10],
    [2, 11],
    [4, 11],
    [8, 11],
    [9, 11],
    [12, 11],
    [14, 11],
    [16, 11],
    [17, 11],
    [18, 11],
    [19, 11],
    [0, 12],
    [2, 12],
    [7, 12],
    [10, 12],
    [11, 12],
    [15, 12],
    [18, 12],
    [10, 13],
    [12, 13],
    [13, 13],
    [15, 13],
    [16, 13],
    [19, 13],
    [20, 13],
    [11, 14],
    [12, 14],
    [13, 14],
    [14, 14],
    [18, 14],
    [20, 14],
    [9, 15],
    [12, 15],
    [16, 15],
    [20, 15],
    [8, 16],
    [9, 16],
    [14, 16],
    [18, 16],
    [19, 16],
    [10, 17],
    [15, 17],
    [16, 17],
    [19, 17],
    [8, 18],
    [11, 18],
    [16, 18],
    [17, 18],
    [20, 18],
    [10, 19],
    [11, 19],
    [13, 19],
    [14, 19],
    [8, 20],
    [14, 20],
    [16, 20],
    [17, 20],
  ];
  const finder = (x: number, y: number) => (
    <g key={`${x}-${y}`}>
      <rect x={x} y={y} width={7} height={7} fill="#0f1720" />
      <rect x={x + 1} y={y + 1} width={5} height={5} fill="#fff" />
      <rect x={x + 2} y={y + 2} width={3} height={3} fill="#0f1720" />
    </g>
  );
  return (
    <svg
      viewBox="-2 -2 25 25"
      width={125}
      height={125}
      aria-label="Two-step set-up code"
      className="border-line rounded-[10px] border bg-white"
    >
      {finder(0, 0)}
      {finder(14, 0)}
      {finder(0, 14)}
      {cells.map(([x, y]) => (
        <rect key={`${x}.${y}`} x={x} y={y} width={1} height={1} fill="#0f1720" />
      ))}
    </svg>
  );
}

/* useSearchParams needs a Suspense boundary so the page can still be prerendered. */
export default function TwoStepPage() {
  return (
    <Suspense fallback={null}>
      <TwoStepPageInner />
    </Suspense>
  );
}
