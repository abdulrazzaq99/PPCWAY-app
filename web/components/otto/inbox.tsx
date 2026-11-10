"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { type Card, type Change, type Inbox, money, when } from "@/lib/otto";

/*
  The inbox. The client's brief calls it the product, and the thing it has to
  get right is not the list but the card: a merchant reads one of these in
  about fifteen seconds and decides whether to let somebody change their
  advertising. So every card shows the figures it rests on, when they were
  read, what we expect it to be worth, and how to put it back — and says which
  of those words are ours rather than a model's.

  Approving is what changes a Google Ads account: the server checks the change
  again, sends it through the one door, and answers with what happened — done,
  Google's reason for refusing, or that writes are switched off and nothing in
  the account has changed. Below the cards is what became of every change said
  yes to, with a way to put back what was made.
*/

type Answered = { status: string; words: string; refused_by?: string };

function Figures({ card }: { card: Card }) {
  if (card.evidence.length === 0) return null;
  return (
    <dl className="mt-4 grid gap-x-6 gap-y-2 sm:grid-cols-2">
      {card.evidence.map((cite) => (
        <div key={cite.id} className="flex items-baseline justify-between gap-3">
          <dt className="text-pw-ink-500 text-[13px] leading-4">
            {cite.id.split(":")[0].replace(/_/g, " ")}
          </dt>
          <dd className="text-[14px] leading-[18px] font-semibold tabular-nums">
            {cite.unit === "money"
              ? money(cite.value, card.impact.currency)
              : cite.unit === "ratio"
                ? `${Math.round(cite.value * 100)}%`
                : cite.value.toLocaleString("en-GB")}
          </dd>
        </div>
      ))}
    </dl>
  );
}

function OneCard({ card, onAnswered }: { card: Card; onAnswered: (said: Answered) => void }) {
  const [busy, setBusy] = useState("");
  const [trouble, setTrouble] = useState("");

  const answer = async (what: "approve" | "reject") => {
    setBusy(what);
    setTrouble("");
    try {
      const res = await fetch(`/api/otto/actions/${card.id}/${what}`, {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: what === "reject" ? JSON.stringify({ because: "" }) : undefined,
      });
      const said = (await res.json().catch(() => ({}))) as Answered & { error?: string };
      if (!res.ok) {
        setTrouble(said.error ?? "That did not work.");
        return;
      }
      onAnswered(said);
    } catch {
      setTrouble("We could not reach Otto. Nothing was changed.");
    } finally {
      setBusy("");
    }
  };

  return (
    <article className="border-pw-border bg-pw-card rounded-[var(--pw-r-card)] border p-5 sm:p-6">
      <div className="flex flex-wrap items-start justify-between gap-x-4 gap-y-2">
        <div className="min-w-0">
          <h3 className="text-[18px] leading-[22px] font-bold">{card.title}</h3>
          <p className="text-pw-ink-500 mt-1 text-[13px] leading-4">{card.target.label}</p>
        </div>
        {card.impact.blocking ? (
          <span className="rounded-full bg-amber-100 px-3 py-1 text-[12px] font-semibold text-amber-900">
            Not running
          </span>
        ) : card.impact.money_a_month > 0 ? (
          <span className="bg-pw-blue-tint text-pw-blue-ink rounded-full px-3 py-1 text-[12px] font-semibold tabular-nums">
            {money(card.impact.money_a_month, card.impact.currency)} a month
          </span>
        ) : null}
      </div>

      <p className="mt-3 text-[16px] leading-[22px]">{card.reason}</p>
      <p className="text-pw-ink-700 mt-2 text-[14px] leading-[19px]">{card.impact.words}</p>

      <Figures card={card} />

      <div className="border-pw-divider mt-4 border-t pt-4">
        <p className="text-pw-ink-500 text-[13px] leading-[17px]">
          <span className="font-semibold">If you change your mind:</span> {card.undo}
        </p>
        <p className="text-pw-ink-500 mt-1 text-[12px] leading-4">
          {card.rule_id} · {card.risk} risk ·{" "}
          {card.route === "expert" ? "a PPCWay expert signs this off" : "your decision"}
          {card.as_of ? ` · figures read ${when(card.as_of)}` : ""}
          {card.reason_is_ours ? "" : " · wording by Otto, figures by PPCWay"}
        </p>
      </div>

      {trouble ? (
        <p className="mt-3 text-[14px] leading-[19px] font-semibold text-red-700">{trouble}</p>
      ) : null}

      {card.answerable ? (
        <div className="mt-4 flex flex-wrap gap-3">
          <Button onClick={() => answer("approve")} disabled={Boolean(busy)}>
            {busy === "approve" ? "Checking again…" : "Yes, do it"}
          </Button>
          <Button variant="secondary" onClick={() => answer("reject")} disabled={Boolean(busy)}>
            {busy === "reject" ? "Noting that…" : "No thanks"}
          </Button>
        </div>
      ) : (
        <p className="text-pw-ink-500 mt-4 text-[13px] leading-[17px]">
          Otto found this on its last look round. It will be offered to you properly tonight.
        </p>
      )}
    </article>
  );
}

function OneChange({ change }: { change: Change }) {
  const router = useRouter();
  const [busy, setBusy] = useState(false);
  const [said, setSaid] = useState("");
  const [trouble, setTrouble] = useState("");

  const putBack = async () => {
    setBusy(true);
    setTrouble("");
    try {
      const res = await fetch(`/api/otto/actions/${change.id}/undo`, { method: "POST" });
      const answer = (await res.json().catch(() => ({}))) as { words?: string; error?: string };
      if (!res.ok) {
        setTrouble(answer.error ?? "That did not work.");
        return;
      }
      setSaid(answer.words ?? "");
      router.refresh();
    } catch {
      setTrouble("We could not reach Otto. Nothing was changed.");
    } finally {
      setBusy(false);
    }
  };

  return (
    <li className="border-pw-divider flex flex-wrap items-start justify-between gap-x-4 gap-y-2 border-t py-4 first:border-t-0">
      <div className="max-w-[560px] min-w-0">
        <p className="text-[15px] leading-[20px] font-semibold">{change.title}</p>
        <p className="text-pw-ink-500 mt-0.5 text-[13px] leading-4">{change.target.label}</p>
        <p className="text-pw-ink-700 mt-2 text-[14px] leading-[19px]">{said || change.words}</p>
        {trouble ? (
          <p className="mt-2 text-[14px] leading-[19px] font-semibold text-red-700">{trouble}</p>
        ) : null}
      </div>
      {change.may_undo && !said ? (
        <Button variant="secondary" onClick={putBack} disabled={busy}>
          {busy ? "Putting it back…" : "Undo"}
        </Button>
      ) : null}
    </li>
  );
}

/*
  Why the wasted-search check stood down on this account: it counts no
  enquiries, so every search would look wasted. Shown beside any cards there
  are; with none, the empty inbox already says it.
*/
export function CannotCheck({ inbox }: { inbox: Inbox }) {
  const said = [
    ...(inbox.cannot_check && inbox.cards.length > 0 ? [inbox.cannot_check] : []),
    ...(inbox.notes ?? []).map((note) => note.words),
  ];
  if (said.length === 0) return null;
  return (
    <div className="flex flex-col gap-2">
      {said.map((line) => (
        <div
          key={line}
          className="border-pw-warn-border bg-pw-warn-bg text-pw-warn-ink rounded-[14px] border px-4 py-3 text-[14px] leading-[20px]"
        >
          {line}
          {/ceiling/.test(line) ? (
            <>
              {" "}
              <a href="/settings" className="font-semibold underline">
                Open Settings
              </a>
            </>
          ) : null}
        </div>
      ))}
    </div>
  );
}

export function Changes({ changes }: { changes: Change[] }) {
  if (changes.length === 0) return null;
  return (
    <section className="border-pw-border bg-pw-card rounded-[var(--pw-r-card)] border p-5 sm:p-6">
      <h2 className="text-[17px] leading-[22px] font-semibold">Changes you said yes to</h2>
      <p className="text-pw-ink-500 mt-1 text-[13px] leading-[17px]">
        What happened to each one. Anything Otto made can be put back for thirty days.
      </p>
      <ul className="mt-2">
        {changes.map((change) => (
          <OneChange key={change.id} change={change} />
        ))}
      </ul>
    </section>
  );
}

/*
  The cards themselves, answered or not. Shared by the inbox and by a
  campaign's own panel, so a suggestion reads and answers the same wherever
  it is met. `onAnswered` is how the page around it reads itself again: the
  counts change with every answer, and an approval can be overturned by the
  second guardrail run, so the page is re-read rather than patched locally.
*/
export function Cards({ cards, onAnswered }: { cards: Card[]; onAnswered: () => void }) {
  const [answered, setAnswered] = useState<Record<string, Answered>>({});
  return (
    <>
      {cards.map((card, n) => {
        const key = card.id || `found-${n}`;
        const said = answered[card.id];
        if (said) {
          return (
            <article
              key={key}
              className="border-pw-border bg-pw-card rounded-[var(--pw-r-card)] border p-5 text-[15px] leading-[21px] sm:p-6"
            >
              <p className="font-semibold">{card.title}</p>
              <p className="text-pw-ink-700 mt-1">{said.words}</p>
            </article>
          );
        }
        // A card with no id has not been written down yet: Otto found it, and
        // the nightly pass will offer it. Shown without buttons rather than
        // hidden, because an empty inbox would be a lie about an account
        // somebody has only just connected.
        return (
          <OneCard
            key={key}
            card={card}
            onAnswered={(it) => {
              setAnswered((was) => ({ ...was, [card.id]: it }));
              onAnswered();
            }}
          />
        );
      })}
    </>
  );
}

export function OttoInbox({ inbox, trouble }: { inbox: Inbox | null; trouble: string }) {
  const router = useRouter();

  if (trouble) {
    return <p className="text-[16px] leading-[22px] font-semibold text-red-700">{trouble}</p>;
  }
  if (!inbox) {
    return <p className="text-pw-ink-700 text-[16px] leading-[22px]">Nothing to show yet.</p>;
  }
  if (!inbox.connected) {
    return (
      <p className="text-pw-ink-700 text-[16px] leading-[22px]">
        {inbox.nothing_because || "Connect your Google Ads account and Otto can start looking."}
      </p>
    );
  }

  return (
    <div className="grid gap-4">
      {inbox.cards.length === 0 ? (
        <p className="text-pw-ink-700 text-[16px] leading-[22px]">{inbox.nothing_because}</p>
      ) : null}
      <CannotCheck inbox={inbox} />

      <Cards cards={inbox.cards} onAnswered={() => router.refresh()} />

      <Changes changes={inbox.changes ?? []} />

      <p className="text-pw-ink-500 text-[13px] leading-[17px]">
        {inbox.used_this_week} of 10 changes used this week
        {inbox.held_back > 0 ? ` · ${inbox.held_back} more held back until next week` : ""}
        {inbox.not_specified.length > 0
          ? ` · ${inbox.not_specified.length} of Otto's checks are not switched on yet`
          : ""}
      </p>
    </div>
  );
}
