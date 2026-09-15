"use client";

import { Button, LinkButton } from "@/components/ui/button";
import { ExclamationGlyph, ProblemPage } from "@/components/auth/problem-page";

export default function ErrorPage({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  const reference = (error.digest ?? "0000-0000").slice(0, 9).toUpperCase();
  return (
    <ProblemPage
      tone="amber"
      icon={<ExclamationGlyph />}
      code="500 · Something broke on our side"
      headline="That one is on us."
      body="Something went wrong inside PPCWay, not in your Google Ads account. Your ads keep running and the daily budget you set in Google still holds while we fix it. Try again in a minute."
      actions={
        <>
          <Button onClick={reset}>Try again</Button>
          <LinkButton href="/status" variant="secondary">
            Check system status
          </LinkButton>
        </>
      }
      footer={`Reference ${reference}. Give this to support and we can see exactly what happened.`}
    />
  );
}
