import { redirect } from "next/navigation";
import { OverviewView } from "@/components/app/overview-views";
import { OVERVIEW_VIEWS } from "@/components/app/view-names";
import { pickView } from "@/lib/view-param";

/*
  The signed-in app moved to the client's dashboard design, at /home. This route
  stays for the links and bookmarks that point at it, and for the drawn states,
  which are still reachable with ?view= until each screen is rebuilt.
*/
export default async function OverviewPage({
  searchParams,
}: {
  searchParams: Promise<{ view?: string }>;
}) {
  const { view } = await searchParams;
  if (view) return <OverviewView view={pickView(OVERVIEW_VIEWS, view)} />;
  redirect("/home");
}
