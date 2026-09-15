import type { ComponentProps, ReactNode } from "react";
import { AppShell } from "./shell";
import {
  ActivityRow,
  AdMock,
  Columns,
  Footnote,
  Legend,
  ListRow,
  MiniBars,
  NoticeCard,
  PageHead,
  Panel,
  Rows,
  Summary,
  Tile,
  Tiles,
} from "./blocks";

/*
  Most Activity, alert and Campaign-review frames share one anatomy:
  headline, four tiles, then a "why" panel (a sentence, sometimes with a small
  chart), a record panel (rows), a "what next" panel (the grey inner card), with a
  notice card and a short list on the right. This turns that anatomy into data.
*/
export type DetailSpec = {
  shell: Omit<ComponentProps<typeof AppShell>, "children">;
  head: { title: string; lead: ReactNode };
  tiles: ComponentProps<typeof Tile>[];
  why?: {
    title: string;
    legend?: string | { label: string; tone: "brand" | "red" | "amber" };
    summary: ReactNode;
    then?: ReactNode;
    note?: ReactNode;
    bars?: ComponentProps<typeof MiniBars>;
  };
  record?: {
    title: string;
    action?: string;
    rows: ComponentProps<typeof ActivityRow>[];
  };
  next?: {
    title: string;
    action?: string;
    mock: ComponentProps<typeof AdMock>;
    footnote?: ReactNode;
  };
  extra?: ReactNode;
  notice?: ComponentProps<typeof NoticeCard>;
  list?: { title: string; rows: ComponentProps<typeof ListRow>[]; action?: string; text?: string };
  asideExtra?: ReactNode;
};

export function DetailPage({ spec }: { spec: DetailSpec }) {
  const { shell, head, tiles, why, record, next, extra, notice, list, asideExtra } = spec;
  return (
    <AppShell {...shell}>
      <PageHead title={head.title} lead={head.lead} />
      <Tiles>
        {tiles.map((t, i) => (
          <Tile key={i} {...t} />
        ))}
      </Tiles>
      <Columns
        aside={
          notice || list || asideExtra ? (
            <>
              {notice ? <NoticeCard {...notice} /> : null}
              {list ? (
                <Panel title={list.title} action={list.action ? { label: list.action } : undefined}>
                  {list.text ? (
                    <p className="text-muted mt-[10px] text-[14px] leading-[17px]">{list.text}</p>
                  ) : null}
                  <Rows className="mt-1">
                    {list.rows.map((r, i) => (
                      <ListRow key={i} {...r} />
                    ))}
                  </Rows>
                </Panel>
              ) : null}
              {asideExtra}
            </>
          ) : undefined
        }
      >
        {why ? (
          <Panel
            title={why.title}
            action={
              typeof why.legend === "string" ? (
                <span className="text-brand shrink-0 text-[13px] leading-4 font-medium">
                  {why.legend}
                </span>
              ) : why.legend ? (
                <Legend {...why.legend} />
              ) : undefined
            }
          >
            <Summary>{why.summary}</Summary>
            {why.then ? (
              <p className="text-muted mt-[18px] text-[15px] leading-[18px]">{why.then}</p>
            ) : null}
            {why.bars ? <MiniBars {...why.bars} /> : null}
            {why.note ? <Footnote className="mt-[18px]">{why.note}</Footnote> : null}
          </Panel>
        ) : null}
        {record ? (
          <Panel title={record.title} action={record.action ? { label: record.action } : undefined}>
            <Rows>
              {record.rows.map((r, i) => (
                <ActivityRow key={i} {...r} />
              ))}
            </Rows>
          </Panel>
        ) : null}
        {next ? (
          <Panel title={next.title} action={next.action ? { label: next.action } : undefined}>
            <AdMock {...next.mock} />
            {next.footnote ? <Footnote>{next.footnote}</Footnote> : null}
          </Panel>
        ) : null}
        {extra}
      </Columns>
    </AppShell>
  );
}
