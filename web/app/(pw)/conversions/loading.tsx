import { CircleNotch } from "@phosphor-icons/react/dist/ssr";
import { Header, PwCard, PwPage } from "@/components/pw/shell";

/* Shown while Google is asked for the account's conversions and the site is read for the tag. */
function Bar({ className }: { className: string }) {
  return (
    <span
      className={`bg-pw-muted block animate-pulse rounded-[8px] motion-reduce:animate-none ${className}`}
    />
  );
}

export default function LoadingConversions() {
  return (
    <>
      <Header eyebrow="Goals" title="Conversions" />
      <PwPage>
        <p
          role="status"
          aria-live="polite"
          className="text-pw-ink-600 flex items-center gap-2.5 text-[15px] leading-[21px]"
        >
          <CircleNotch
            size={18}
            weight="bold"
            aria-hidden
            className="text-pw-blue shrink-0 animate-spin motion-reduce:animate-none"
          />
          Reading your conversion actions from Google and looking for the tag on your site.
        </p>
        <PwCard className="p-6 sm:p-8">
          <Bar className="h-6 w-40" />
          <Bar className="mt-3 h-4 w-[70%]" />
          <Bar className="mt-6 h-10 w-36" />
        </PwCard>
        <PwCard className="p-6 sm:p-8">
          <Bar className="h-6 w-48" />
          <div className="mt-6 flex flex-col gap-3">
            {[0, 1, 2, 3].map((n) => (
              <Bar key={n} className="h-11" />
            ))}
          </div>
        </PwCard>
      </PwPage>
    </>
  );
}
