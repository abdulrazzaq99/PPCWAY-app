import { SettingsPage } from "@/components/app/settings-views";
import { SETTINGS_VIEWS } from "@/components/app/view-names";
import { pickView } from "@/lib/view-param";

export default async function Settings({
  searchParams,
}: {
  searchParams: Promise<{ view?: string }>;
}) {
  const { view } = await searchParams;
  return <SettingsPage view={pickView(SETTINGS_VIEWS, view)} />;
}
