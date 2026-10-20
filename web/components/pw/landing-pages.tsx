import { Chip, PwCard } from "@/components/pw/shell";
import type { LandingPage } from "@/lib/audit";

/*
  Every page the ads send people to, one card each.

  The list is not a guess about which pages matter: it comes out of the mirror,
  from the ads themselves, so these are the pages Google is charging this
  business to send people to. A site can score well overall and still have the
  one page people land on missing its conversion tag.
*/
export function LandingPages({ pages }: { pages: LandingPage[] }) {
  if (pages.length === 0) {
    return (
      <PwCard className="p-5 sm:p-6">
        <h2 className="text-[17px] leading-[22px] font-semibold">Page by page</h2>
        <p className="text-pw-ink-500 mt-2 text-[15px] leading-[23px]">
          Once your Google Ads account is connected, every page your ads send people to is checked
          here on its own: the conversion tag, the phone number, the form, and whether a pop-up
          meets people who just clicked an ad.
        </p>
      </PwCard>
    );
  }

  const jobs = pages.reduce((n, page) => n + page.jobs.length, 0);

  return (
    <PwCard className="overflow-hidden">
      <div className="flex flex-wrap items-baseline justify-between gap-3 px-5 py-5 sm:px-6">
        <h2 className="text-[17px] leading-[22px] font-semibold">
          Page by page, where the ads land
        </h2>
        <p className="text-pw-ink-400 text-[12px]">
          {pages.length} {pages.length === 1 ? "page" : "pages"} ·{" "}
          {jobs === 0 ? "nothing to fix" : `${jobs} ${jobs === 1 ? "thing" : "things"} to fix`}
        </p>
      </div>
      <ul className="divide-pw-divider divide-y border-t border-[color:var(--pw-divider)]">
        {pages.map((page) => (
          <li key={page.url} className="flex flex-col gap-2 px-5 py-4 sm:px-6">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <p className="min-w-0 truncate text-[15px] font-semibold">
                {page.url.replace(/^https?:\/\//, "")}
              </p>
              {page.ok ? (
                <Chip tone="good">Ready for ads</Chip>
              ) : (
                <Chip tone={page.read ? "warn" : "bad"}>
                  {page.read
                    ? `${page.jobs.length} ${page.jobs.length === 1 ? "thing" : "things"}`
                    : "Would not open"}
                </Chip>
              )}
            </div>

            {page.campaigns.length ? (
              <p className="text-pw-ink-400 text-[13px]">
                {page.campaigns.length === 1 ? "Sent people by" : "Sent people by"}{" "}
                {page.campaigns.join(", ")}
              </p>
            ) : null}

            {page.jobs.length ? (
              <ul className="text-pw-ink-600 flex list-disc flex-col gap-1 pl-5 text-[14px] leading-[21px]">
                {page.jobs.map((job) => (
                  <li key={job}>{job}</li>
                ))}
              </ul>
            ) : (
              <p className="text-pw-ink-500 text-[14px] leading-[21px]">
                The tag fires, the phone number is in view, and it fits a phone.
              </p>
            )}

            <div className="flex flex-wrap gap-2">
              <Chip tone={page.conversion_tag ? "good" : "bad"}>
                {page.conversion_tag ? "Conversion tag" : "No conversion tag"}
              </Chip>
              {page.conversion_tag ? (
                <Chip tone={page.tag_fired ? "good" : "warn"}>
                  {page.tag_fired ? "Tag fired" : "Tag did not fire"}
                </Chip>
              ) : null}
              <Chip tone={page.phone_in_view ? "good" : "warn"}>
                {page.phone_in_view ? "Phone in view" : "Phone below the fold"}
              </Chip>
              <Chip tone={page.has_form || page.call_to_action?.length ? "good" : "warn"}>
                {page.has_form
                  ? "Has a form"
                  : page.call_to_action?.length
                    ? `Button: ${page.call_to_action[0]}`
                    : "Nothing to do"}
              </Chip>
              <Chip tone={page.fits_a_phone ? "good" : "warn"}>
                {page.fits_a_phone ? "Fits a phone" : "Does not fit a phone"}
              </Chip>
            </div>
          </li>
        ))}
      </ul>
    </PwCard>
  );
}
