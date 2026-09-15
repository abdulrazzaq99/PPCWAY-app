export default function Home() {
  return (
    <main className="flex flex-1 items-center justify-center p-8">
      <div className="border-line bg-panel w-full max-w-[620px] rounded-[var(--radius-shell)] border p-8">
        <p className="text-headline text-ink">PPCWay is ready to be built.</p>
        <p className="text-subline mt-3">
          The tokens, typeface and shell radius here match the Figma file. Every screen from Version
          2 gets implemented on top of this base.
        </p>
        <div className="mt-6 flex flex-wrap gap-2">
          <span className="bg-brand text-meta rounded-[var(--radius-pill)] px-3 py-1 font-semibold text-white">
            Brand
          </span>
          <span className="bg-brand-pale text-meta text-brand-dark rounded-[var(--radius-pill)] px-3 py-1 font-semibold">
            Done
          </span>
          <span className="bg-amber-pale text-meta text-amber-dark rounded-[var(--radius-pill)] px-3 py-1 font-semibold">
            Waiting for you
          </span>
          <span className="bg-red-pale text-meta text-red rounded-[var(--radius-pill)] px-3 py-1 font-semibold">
            Money at risk
          </span>
          <span className="bg-line-soft text-meta text-muted rounded-[var(--radius-pill)] px-3 py-1 font-semibold">
            For your information
          </span>
        </div>
      </div>
    </main>
  );
}
