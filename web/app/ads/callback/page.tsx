import type { Metadata } from "next";
import { AdsCallback } from "@/components/app/ads-callback";

export const metadata: Metadata = { title: "Connecting Google Ads: PPCWay" };

/*
  Where Google sends a merchant back. The code is handed to the backend, which
  exchanges it for the lasting permission; this page only waits and reports.
*/
export default async function AdsCallbackPage({
  searchParams,
}: {
  searchParams: Promise<{ code?: string; state?: string; error?: string }>;
}) {
  const { code, state, error } = await searchParams;
  return <AdsCallback code={code ?? ""} state={state ?? ""} refused={error ?? ""} />;
}
