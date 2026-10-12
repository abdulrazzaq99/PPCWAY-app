import type { Metadata } from "next";
import { AcceptInvite } from "@/components/pw/accept-invite";
import { Header, PwPage } from "@/components/pw/shell";

export const metadata: Metadata = { title: "Join · PPCway" };

export default async function InvitePage({
  searchParams,
}: {
  searchParams: Promise<{ token?: string }>;
}) {
  const { token } = await searchParams;
  return (
    <>
      <Header eyebrow="Invitation" title="Join this business on PPCway" />
      <PwPage>
        <AcceptInvite token={token ?? ""} />
      </PwPage>
    </>
  );
}
