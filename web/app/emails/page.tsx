import Link from "next/link";
import { EMAIL_SETS, EMAIL_VIEWS } from "@/components/emails/catalogue";
import { EmailGallery } from "@/components/emails/email";
import { pickView } from "@/lib/view-param";

/* Every email PPCWay sends, one set per "V2 · Email" frame, picked with ?view=. */
export default async function Emails({
  searchParams,
}: {
  searchParams: Promise<{ view?: string }>;
}) {
  const view = pickView(EMAIL_VIEWS, (await searchParams).view);
  const set = EMAIL_SETS[view];
  return (
    <EmailGallery title={set.title} lead={set.lead} emails={set.emails}>
      <nav className="mt-6 flex flex-wrap gap-2" aria-label="Email sets">
        {EMAIL_VIEWS.map((v) => (
          <Link
            key={v}
            href={`/emails?view=${v}`}
            className={
              v === view
                ? "bg-rail h-[33px] rounded-full px-4 text-[14px] leading-[33px] font-semibold text-white"
                : "text-muted hover:text-ink h-[33px] px-2 text-[14px] leading-[33px] font-medium"
            }
          >
            {EMAIL_SETS[v].title}
          </Link>
        ))}
      </nav>
    </EmailGallery>
  );
}
