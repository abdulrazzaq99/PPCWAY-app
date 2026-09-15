import type { ReactNode } from "react";
import { cn } from "@/lib/cn";

/*
  The "Advanced view" table from the Campaigns frames: 13/16 faint headers over a
  hairline, 14/17 rows, and a bold Total row. Numbers align right. On a phone the
  panel scrolls sideways rather than wrapping.
*/
export type Column = { key: string; label: string; align?: "left" | "right"; width?: number };
export type Cell = ReactNode;

export function DataTable({
  columns,
  rows,
  total,
  className,
}: {
  columns: Column[];
  rows: Record<string, Cell>[];
  total?: Record<string, Cell>;
  className?: string;
}) {
  return (
    <div
      className={cn(
        "bg-panel border-line mt-[26px] overflow-x-auto rounded-[16px] border px-6 py-[22px]",
        className,
      )}
    >
      <table className="w-full min-w-[820px] border-collapse">
        <thead>
          <tr className="border-line border-b">
            {columns.map((c) => (
              <th
                key={c.key}
                scope="col"
                style={{ width: c.width }}
                className={cn(
                  "text-faint pb-4 text-[13px] leading-4 font-semibold",
                  c.align === "right" ? "text-right" : "text-left",
                )}
              >
                {c.label}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((r, i) => (
            <tr
              key={i}
              className="hover:bg-line-soft transition-colors duration-[var(--dur-hover)]"
            >
              {columns.map((c) => (
                <td
                  key={c.key}
                  className={cn(
                    "text-ink py-2 text-[14px] leading-[17px] first:pt-4",
                    c.align === "right" ? "text-right" : "text-left",
                  )}
                >
                  {r[c.key]}
                </td>
              ))}
            </tr>
          ))}
          {total ? (
            <tr>
              {columns.map((c) => (
                <td
                  key={c.key}
                  className={cn(
                    "text-ink pt-2 text-[14px] leading-[17px] font-semibold",
                    c.align === "right" ? "text-right" : "text-left",
                  )}
                >
                  {total[c.key]}
                </td>
              ))}
            </tr>
          ) : null}
        </tbody>
      </table>
    </div>
  );
}

/** A status word in a table cell: brand for Enabled, faint for Paused. */
export function StatusWord({
  children,
  tone = "brand",
}: {
  children: ReactNode;
  tone?: "brand" | "faint" | "amber" | "red";
}) {
  return (
    <span
      className={cn(
        { brand: "text-brand", faint: "text-faint", amber: "text-amber", red: "text-red-strong" }[
          tone
        ],
      )}
    >
      {children}
    </span>
  );
}
