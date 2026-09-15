import { ConnectView } from "@/components/onboarding/connect-views";
import { CONNECT_VIEWS } from "@/components/onboarding/view-names";
import { pickView } from "@/lib/view-param";

/* Step 2 has nine drawn states. `?view=` picks one until the backend drives it. */
export default async function ConnectStep({
  searchParams,
}: {
  searchParams: Promise<{ view?: string }>;
}) {
  const { view } = await searchParams;
  return <ConnectView view={pickView(CONNECT_VIEWS, view)} />;
}
