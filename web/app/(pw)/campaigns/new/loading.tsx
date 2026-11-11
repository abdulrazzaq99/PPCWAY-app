import { CircleNotch } from "@phosphor-icons/react/dist/ssr";
import { Header, PwCard, PwPage } from "@/components/pw/shell";

/*
  Shown the moment "New campaign" is pressed, while the builder reads the
  account's currency, its kinds of business and the website its ads use. The
  page used to stay as it was until all of that came back, so the button
  looked as if it had done nothing.
*/
function Bar({ className }: { className: string }) {
  return (
    <span
      className={`bg-pw-muted block animate-pulse rounded-[8px] motion-reduce:animate-none ${className}`}
    />
  );
}

export default function LoadingNewCampaign() {
  return (
    <>
      <Header eyebrow="Campaigns" title="Start a new campaign." />
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
          Getting the campaign builder ready: reading your account and the website your ads use.
        </p>
        <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_380px]">
          <PwCard className="p-6 sm:p-8">
            <div className="flex gap-2">
              {[0, 1, 2, 3, 4].map((n) => (
                <Bar key={n} className="h-[6px] flex-1 rounded-full" />
              ))}
            </div>
            <Bar className="mt-8 h-8 w-[70%]" />
            <Bar className="mt-3 h-8 w-[52%]" />
            <Bar className="mt-8 h-4 w-40" />
            <div className="mt-4 grid gap-3 sm:grid-cols-3">
              {[0, 1, 2, 3, 4, 5].map((n) => (
                <Bar key={n} className="h-[74px]" />
              ))}
            </div>
            <div className="border-pw-divider mt-8 flex justify-end border-t pt-5">
              <Bar className="h-[42px] w-44 rounded-[12px]" />
            </div>
          </PwCard>
          <PwCard className="hidden p-6 lg:block">
            <Bar className="h-4 w-28" />
            <Bar className="mt-5 h-5 w-[85%]" />
            <Bar className="mt-2 h-4 w-[60%]" />
            <Bar className="mt-4 h-16 w-full" />
          </PwCard>
        </div>
      </PwPage>
    </>
  );
}
