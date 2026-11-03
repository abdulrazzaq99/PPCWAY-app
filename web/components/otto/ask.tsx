"use client";

import { useEffect, useRef, useState } from "react";
import { Button } from "@/components/ui/button";

/*
  Ask Otto. The thing this screen has to get right is the waiting: a question
  about a year of search terms takes several seconds, and several seconds of
  nothing reads as broken. So the status lines the server streams are shown as
  they arrive — "reading what people searched for" — and the answer replaces
  them when it comes.

  The header and the first message both say Otto is an AI, which the client's
  brief requires. Both come from the server, so the words a merchant is shown
  and the words PPCWay can prove it showed them are the same string.
*/

type Turn = { who: "them" | "otto"; words: string };

export function AskOtto() {
  const [disclosure, setDisclosure] = useState({
    first_message: "",
    header: "Otto · AI assistant",
  });
  const [said, setSaid] = useState<Turn[]>([]);
  const [doing, setDoing] = useState<string[]>([]);
  const [question, setQuestion] = useState("");
  const [busy, setBusy] = useState(false);
  const [trouble, setTrouble] = useState("");
  const bottom = useRef<HTMLDivElement>(null);

  useEffect(() => {
    void (async () => {
      try {
        const res = await fetch("/api/otto/disclosure", { cache: "no-store" });
        if (res.ok) setDisclosure(await res.json());
      } catch {
        // The header has a sensible default; a missing disclosure endpoint
        // must not leave the panel without one.
      }
    })();
  }, []);

  useEffect(() => {
    bottom.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [said, doing]);

  const ask = async () => {
    const asking = question.trim();
    if (!asking || busy) return;
    setQuestion("");
    setTrouble("");
    setSaid((was) => [...was, { who: "them", words: asking }]);
    setDoing([]);
    setBusy(true);

    try {
      const res = await fetch("/api/otto/ask", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ question: asking }),
      });
      if (!res.ok || !res.body) {
        const problem = (await res.json().catch(() => ({}))) as { error?: string };
        setTrouble(problem.error ?? "Otto could not answer that.");
        return;
      }

      // Server-sent events, read as they arrive. Buffered by line, because a
      // chunk boundary can land in the middle of one.
      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let rest = "";
      for (;;) {
        const { done, value } = await reader.read();
        if (done) break;
        rest += decoder.decode(value, { stream: true });
        const lines = rest.split("\n");
        rest = lines.pop() ?? "";
        for (const line of lines) {
          if (!line.startsWith("data: ")) continue;
          let step: { kind?: string; words?: string };
          try {
            step = JSON.parse(line.slice(6));
          } catch {
            continue;
          }
          if (step.kind === "looking" || step.kind === "writing") {
            setDoing((was) => [...was, step.words ?? ""]);
          }
          if (step.kind === "answer" || step.kind === "trouble") {
            setSaid((was) => [...was, { who: "otto", words: step.words ?? "" }]);
            setDoing([]);
          }
        }
      }
    } catch {
      setTrouble("We lost the connection to Otto. Nothing was changed.");
    } finally {
      setBusy(false);
      setDoing([]);
    }
  };

  return (
    <section className="border-pw-border bg-pw-card flex min-h-[520px] flex-col rounded-[var(--pw-r-card)] border">
      <header className="border-pw-divider border-b px-5 py-4">
        <p className="text-[15px] leading-[19px] font-bold">{disclosure.header}</p>
        <p className="text-pw-ink-500 mt-1 text-[13px] leading-4">
          Otto reads your account. It cannot change anything here.
        </p>
      </header>

      <div className="flex-1 space-y-4 overflow-y-auto px-5 py-5">
        {disclosure.first_message ? (
          <p className="text-pw-ink-700 text-[15px] leading-[21px]">{disclosure.first_message}</p>
        ) : null}

        {said.map((turn, n) => (
          <p
            key={n}
            className={
              turn.who === "them"
                ? "bg-pw-blue-tint ml-auto max-w-[85%] rounded-[12px] px-4 py-3 text-[15px] leading-[21px]"
                : "max-w-[90%] text-[15px] leading-[21px]"
            }
          >
            {turn.words}
          </p>
        ))}

        {doing.map((line, n) => (
          <p key={`doing-${n}`} className="text-pw-ink-500 text-[14px] leading-[19px] italic">
            {line}…
          </p>
        ))}

        {trouble ? (
          <p className="text-[15px] leading-[21px] font-semibold text-red-700">{trouble}</p>
        ) : null}
        <div ref={bottom} />
      </div>

      <footer className="border-pw-divider border-t px-5 py-4">
        <div className="flex gap-3">
          <label className="sr-only" htmlFor="otto-question">
            Ask Otto a question
          </label>
          <input
            id="otto-question"
            value={question}
            onChange={(event) => setQuestion(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === "Enter" && !event.shiftKey) {
                event.preventDefault();
                void ask();
              }
            }}
            placeholder="Why did my cost per lead go up?"
            disabled={busy}
            className="border-pw-border-input focus:border-pw-blue min-w-0 flex-1 rounded-[10px] border px-3 py-2 text-[16px] leading-[22px] outline-none"
          />
          <Button onClick={() => void ask()} disabled={busy || !question.trim()}>
            {busy ? "Thinking…" : "Ask"}
          </Button>
        </div>
      </footer>
    </section>
  );
}
