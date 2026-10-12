import type { Metadata } from "next";
import { ConnectionCard } from "@/components/pw/connection-card";
import { Header, PwPage } from "@/components/pw/shell";
import { Team, type Org } from "@/components/pw/team";
import { ask } from "@/lib/pw-fetch";

export const metadata: Metadata = { title: "Settings · PPCway" };

type Status = { connected: boolean; customer_id?: string; customer_name?: string };

export default async function SettingsPage() {
  const [org, ads] = await Promise.all([
    ask<Org | null>("/v1/org", null),
    ask<Status>("/v1/ads/status", { connected: false }),
  ]);

  return (
    <>
      <Header eyebrow={org?.name ?? "Your business"} title="Settings" />
      <PwPage>
        <ConnectionCard ads={ads} canDisconnect={Boolean(org?.can.includes("disconnect"))} />
        {org ? <Team org={org} /> : null}
      </PwPage>
    </>
  );
}
