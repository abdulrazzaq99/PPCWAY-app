import { CircleNotch } from "@phosphor-icons/react/dist/ssr";
import { Header, PwCard, PwPage } from "@/components/pw/shell";

/* Shown while a campaign being created is opened. */
function Bar({ className }: { className: string }) {
  return (
    <span
      className={`bg-pw-muted block animate-pulse rounded-[8px] motion-reduce:animate-none ${className}`}
    />
  );
}

export default function LoadingDraft() {
  return (
    <>
      <Header eyebrow="Campaigns" title="New campaign" />
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
          Opening your campaign. Nothing goes live until you publish it.
        </p>
        <PwCard className="p-6 sm:p-8">
          <div className="flex gap-6">
            <Bar className="h-5 w-16" />
            <Bar className="h-5 w-24" />
            <Bar className="h-5 w-20" />
          </div>
          <Bar className="mt-8 h-6 w-[60%]" />
          <Bar className="mt-3 h-4 w-[80%]" />
          <div className="mt-6 grid gap-3 md:grid-cols-2">
            {[0, 1, 2, 3].map((n) => (
              <Bar key={n} className="h-[96px]" />
            ))}
          </div>
        </PwCard>
      </PwPage>
    </>
  );
}
