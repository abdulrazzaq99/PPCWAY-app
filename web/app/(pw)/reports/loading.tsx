import { Header, PwCard, PwPage } from "@/components/pw/shell";

/* The report's own shape, grey, while its figures are read. */
function Bar({ className }: { className: string }) {
  return (
    <span
      className={`bg-pw-muted block animate-pulse rounded-[6px] motion-reduce:animate-none ${className}`}
    />
  );
}

export default function LoadingReports() {
  return (
    <>
      <Header eyebrow="Reading your account" title="Reports" />
      <PwPage>
        <div className="flex gap-2">
          <Bar className="h-[34px] w-[74px] rounded-full" />
          <Bar className="h-[34px] w-[80px] rounded-full" />
          <Bar className="h-[34px] w-[80px] rounded-full" />
        </div>
        <PwCard className="overflow-hidden">
          <div className="grid lg:grid-cols-[minmax(0,1.2fr)_minmax(0,1fr)]">
            <div className="flex flex-col gap-4 p-6 sm:p-8">
              <Bar className="h-4 w-48" />
              <Bar className="h-9 w-[85%]" />
              <Bar className="h-9 w-[70%]" />
              <Bar className="mt-10 h-4 w-[60%]" />
            </div>
            <div className="border-pw-border divide-pw-border divide-y border-t lg:border-t-0 lg:border-l">
              {[0, 1, 2].map((n) => (
                <div key={n} className="flex flex-col gap-2 px-6 py-5 sm:px-8">
                  <Bar className="h-4 w-24" />
                  <Bar className="h-9 w-32" />
                  <Bar className="h-3.5 w-[75%]" />
                </div>
              ))}
            </div>
          </div>
        </PwCard>
        <PwCard className="p-6 sm:p-8">
          <Bar className="h-4 w-28" />
          <Bar className="mt-6 h-[132px] w-full" />
          <Bar className="mt-4 h-[56px] w-full" />
        </PwCard>
      </PwPage>
    </>
  );
}
