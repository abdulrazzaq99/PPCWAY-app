import { NotePencilIcon } from "@phosphor-icons/react/dist/ssr";
import Link from "next/link";

/*
  Campaigns started and not yet published. Google keeps drafts at the top of
  its campaigns list so one left half-done can be picked up; so does this.
*/
export type DraftRow = {
  id: string;
  name: string;
  type: string;
  v: number;
  created_at: string | null;
};

const TYPE: Record<string, string> = {
  SEARCH: "Search",
  PERFORMANCE_MAX: "Performance Max",
  DEMAND_GEN: "Demand Gen",
  DISPLAY: "Display",
  SHOPPING: "Shopping",
  APP: "App",
};

export function Drafts({ drafts }: { drafts: DraftRow[] }) {
  if (!drafts.length) return null;
  return (
    <section className="bg-pw-card border-pw-border rounded-[18px] border">
      <header className="border-pw-border flex items-center justify-between border-b px-6 py-3">
        <h2 className="text-pw-ink text-[15px] font-semibold">
          Drafts <span className="text-pw-ink-400 font-normal">({drafts.length})</span>
        </h2>
        <p className="text-pw-ink-500 text-[13px]">Not live until you publish them.</p>
      </header>
      <ul className="divide-pw-border divide-y">
        {drafts.map((d) => (
          <li key={d.id}>
            <Link
              href={`/campaigns/new/${d.id}`}
              className="hover:bg-pw-row-hover flex items-center gap-3 px-6 py-3 text-[14px]"
            >
              <NotePencilIcon className="text-pw-ink-400 size-5 shrink-0" />
              <span className="text-pw-ink min-w-0 flex-1 truncate font-medium">{d.name}</span>
              <span className="text-pw-ink-500 shrink-0">{TYPE[d.type] ?? d.type}</span>
              <span className="text-pw-ink-400 hidden shrink-0 sm:inline">
                {d.created_at
                  ? `Started ${new Date(d.created_at).toLocaleDateString(undefined, { month: "short", day: "numeric" })}`
                  : ""}
              </span>
              <span className="text-pw-blue shrink-0 font-semibold">Continue</span>
            </Link>
          </li>
        ))}
      </ul>
    </section>
  );
}
