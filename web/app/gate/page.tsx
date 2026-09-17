import type { Metadata } from "next";
import { GateForm } from "@/components/auth/gate-form";

export const metadata: Metadata = { title: "Preview: PPCWay" };

export default async function GatePage({
  searchParams,
}: {
  searchParams: Promise<{ next?: string }>;
}) {
  const { next } = await searchParams;
  const target = next && next.startsWith("/") && !next.startsWith("//") ? next : "/";
  return <GateForm next={target} />;
}
