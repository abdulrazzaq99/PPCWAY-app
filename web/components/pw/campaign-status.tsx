import { Chip } from "@/components/pw/shell";
import type { AdsRow } from "@/lib/ads";
import { dayMonth } from "@/lib/report-view";

/*
  A campaign's state in one word, the same on Home and on Campaigns. A campaign
  deleted in Google Ads keeps the last status PPCWay read for it (usually
  ENABLED) and is marked gone, so "gone" has to be asked first: asking only for
  ENABLED called a deleted campaign Active on Home.
*/
type Standing = Pick<AdsRow, "status" | "gone" | "gone_on">;

export function isDeleted(row: Standing): boolean {
  return Boolean(row.gone) || row.status === "REMOVED";
}

/** The sentence behind "Deleted", or nothing for a campaign still in the account. */
export function deletedWords(row: Standing): string {
  if (!isDeleted(row)) return "";
  const when = row.gone_on ? ` on ${dayMonth(row.gone_on)}` : "";
  return `Deleted in Google Ads${when}. It stays here for the days it spent money in.`;
}

export function CampaignStatus({ row }: { row: Standing }) {
  if (isDeleted(row)) {
    return (
      <span title={deletedWords(row)}>
        <Chip tone="neutral">Deleted</Chip>
      </span>
    );
  }
  const active = row.status === "ENABLED";
  return <Chip tone={active ? "good" : "neutral"}>{active ? "Active" : "Paused"}</Chip>;
}
