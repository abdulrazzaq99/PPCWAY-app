import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import { OverviewView } from "@/components/app/overview-views";
import { SignedInHome } from "@/components/app/signed-in-home";
import { OVERVIEW_VIEWS } from "@/components/app/view-names";
import { SESSION_COOKIE } from "@/lib/session";
import { pickView } from "@/lib/view-param";

/*
  Signed in, this is their own account: the audit they ran, and what connecting
  Google Ads would add. The thirteen drawn states stay reachable with ?view=, for
  showing the design; they are never what a person is told about themselves.
*/
const BACKEND = process.env.BACKEND_URL ?? "http://localhost:8300";

export default async function OverviewPage({
  searchParams,
}: {
  searchParams: Promise<{ view?: string }>;
}) {
  const { view } = await searchParams;
  if (view) return <OverviewView view={pickView(OVERVIEW_VIEWS, view)} />;

  const token = (await cookies()).get(SESSION_COOKIE)?.value;
  if (!token) redirect("/login?next=/overview");

  const person = await fetch(`${BACKEND}/v1/auth/me`, {
    headers: { "x-session-token": token },
    cache: "no-store",
  })
    .then((r) => (r.ok ? (r.json() as Promise<{ email: string; name: string }>) : null))
    .catch(() => null);
  if (!person) redirect("/login?next=/overview");

  return <SignedInHome person={person} />;
}
