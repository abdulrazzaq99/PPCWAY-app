import { count } from "@/lib/admin";

/*
  What happened to every change Otto proposed. The one element on this panel
  that could not belong to another product.

  The rest of the internal screens are a well-applied kit: figures, a table, a
  sidebar. Any admin panel has those, which is why they read as anonymous. This
  is PPCWay's actual shape, drawn from its own things: Otto proposes a change,
  the guardrails judge it, a merchant answers it, it is applied, and for thirty
  days it can be put back. Nothing else in the product matters as much, and
  nothing else in the industry works quite this way.

  **Not a progress bar.** A filled grey track with a partial fill is dashboard
  clutter and says nothing: these five numbers are not parts of one whole
  moving toward a target, they are five fates a change can meet. So it is a
  unit strip: each segment is its real share of the total, in its own meaning's
  colour, labelled with the count.

  **Refused is not a failure.** A guardrail refusing a change is the product
  working, and the colour says so: it is the neutral tone, not the bad one. The
  only thing coloured bad here is a change that was applied and then put back,
  because that is the one outcome nobody wanted.
*/

export type Pipeline = {
  proposed: number;
  refused: number;
  waiting: number;
  applied: number;
  reverted: number;
};

const PARTS = [
  {
    key: "waiting" as const,
    label: "Waiting on a merchant",
    bar: "bg-pw-blue",
    ink: "text-pw-blue-ink",
    what: "proposed, nobody has answered",
  },
  {
    key: "applied" as const,
    label: "Applied",
    bar: "bg-pw-good-solid",
    ink: "text-pw-good",
    what: "answered yes and sent to Google",
  },
  {
    key: "refused" as const,
    label: "Refused by a guardrail",
    bar: "bg-pw-ink-300",
    ink: "text-pw-ink-600",
    what: "stopped before anybody saw it",
  },
  {
    key: "reverted" as const,
    label: "Put back",
    bar: "bg-pw-bad-solid",
    ink: "text-pw-bad",
    what: "applied, then undone",
  },
];

export function Funnel({ data, window }: { data: Pipeline; window: string }) {
  const total = PARTS.reduce((n, one) => n + (data[one.key] || 0), 0);
  const shown = PARTS.filter((one) => data[one.key] > 0);

  return (
    <section className="border-pw-border rounded-[12px] border bg-white p-4 sm:p-5">
      <div className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1">
        <h2 className="text-pw-ink text-[15px] leading-[21px] font-semibold">
          What happened to every change Otto proposed
        </h2>
        <p className="text-pw-ink-500 text-[13px] leading-[18px]">
          {total ? `${count(total)} in the last ${window}` : `Nothing in the last ${window}`}
        </p>
      </div>

      {total ? (
        <>
          {/*
            One strip, each segment its real share. A minimum width so a
            single change in a thousand is still visible: a segment rounded
            to nothing would be a lie about whether it happened.
          */}
          <div className="mt-3 flex h-2 gap-0.5 overflow-hidden rounded-[4px]">
            {shown.map((one) => (
              <div
                key={one.key}
                className={one.bar}
                style={{ width: `${Math.max(2, (data[one.key] / total) * 100)}%` }}
              />
            ))}
          </div>

          <dl className="mt-4 grid grid-cols-2 gap-x-4 gap-y-3 sm:grid-cols-4">
            {PARTS.map((one) => (
              <div key={one.key}>
                <dt className="flex items-center gap-1.5">
                  <span
                    aria-hidden
                    className={`${one.bar} h-2 w-2 shrink-0 rounded-[2px] ${
                      data[one.key] ? "" : "opacity-30"
                    }`}
                  />
                  <span className="text-pw-ink-600 text-[13px] leading-[18px]">{one.label}</span>
                </dt>
                <dd
                  className={`pw-num mt-0.5 pl-3.5 text-[20px] leading-[26px] ${
                    data[one.key] ? one.ink : "text-pw-ink-300"
                  }`}
                >
                  {count(data[one.key])}
                </dd>
                <dd className="text-pw-ink-500 pl-3.5 text-[12px] leading-[16px]">{one.what}</dd>
              </div>
            ))}
          </dl>
        </>
      ) : (
        <p className="text-pw-ink-500 mt-2 text-[14px] leading-[20px]">
          Otto has proposed nothing in this window. On a healthy platform with connected accounts
          that is unusual: check the nightly pass ran.
        </p>
      )}
    </section>
  );
}

/*
  The same shape at row scale, for a merchant in a list. No labels and no
  numbers: at this size it is a glance, and the figures are in the columns
  beside it. A merchant with nothing proposed gets a hairline rather than an
  empty box, because an empty box reads as a thing that failed to load.
*/
export function RowStrip({ data }: { data: Pipeline }) {
  const total = PARTS.reduce((n, one) => n + (data[one.key] || 0), 0);
  if (!total) {
    return (
      <span
        className="bg-pw-border inline-block h-1 w-16 rounded-[2px] align-middle"
        title="Nothing proposed yet"
      />
    );
  }
  const shown = PARTS.filter((one) => data[one.key] > 0);
  return (
    <span
      className="inline-flex h-1 w-16 gap-px overflow-hidden rounded-[2px] align-middle"
      title={shown.map((one) => `${one.label}: ${data[one.key]}`).join(", ")}
    >
      {shown.map((one) => (
        <span
          key={one.key}
          className={one.bar}
          style={{ width: `${Math.max(6, (data[one.key] / total) * 100)}%` }}
        />
      ))}
    </span>
  );
}
