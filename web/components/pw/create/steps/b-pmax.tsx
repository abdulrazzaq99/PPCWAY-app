"use client";

import { YoutubeLogoIcon } from "@phosphor-icons/react";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/field";
import type { Segment } from "@/lib/creation";
import { Finder, Pill } from "../kit";

/*
  The two Performance Max inputs the kit has no control for: YouTube videos,
  pasted as links and kept as Google's 11-character video ids, and the
  audience signal, picked from the account's segments and Google's.
*/

const ID = /^[A-Za-z0-9_-]{11}$/;

/** The video id from any YouTube link: watch?v=, youtu.be/, shorts/, embed/, live/, or the bare id. */
export function youtubeId(input: string): string | null {
  const raw = input.trim();
  if (ID.test(raw)) return raw;
  try {
    const url = new URL(/^https?:\/\//i.test(raw) ? raw : `https://${raw}`);
    const host = url.hostname.replace(/^(www|m|music)\./, "");
    if (host === "youtu.be") {
      const id = url.pathname.split("/")[1] ?? "";
      return ID.test(id) ? id : null;
    }
    if (host === "youtube.com" || host === "youtube-nocookie.com") {
      const v = url.searchParams.get("v");
      if (v && ID.test(v)) return v;
      const m = url.pathname.match(/^\/(shorts|embed|live|v)\/([A-Za-z0-9_-]{11})/);
      if (m) return m[2];
    }
  } catch {
    return null;
  }
  return null;
}

export function Videos({
  videos,
  onChange,
  most = 15,
}: {
  videos: string[];
  onChange: (next: string[]) => void;
  most?: number;
}) {
  const [typed, setTyped] = useState("");
  const [trouble, setTrouble] = useState("");
  const add = () => {
    const id = youtubeId(typed);
    if (!id) {
      setTrouble(
        "That is not a YouTube link PPCWay can read. Paste the video's address from YouTube.",
      );
      return;
    }
    setTrouble("");
    setTyped("");
    if (!videos.includes(id)) onChange([...videos, id]);
  };
  const full = videos.length >= most;
  return (
    <div className="flex flex-col gap-3">
      <div className="flex gap-2">
        <Input
          value={typed}
          aria-label="YouTube video link"
          disabled={full}
          placeholder={
            full ? "That is as many as Google allows" : "https://www.youtube.com/watch?v=..."
          }
          onChange={(e) => setTyped(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter") {
              e.preventDefault();
              add();
            }
          }}
          className="flex-1"
        />
        <Button variant="secondary" size="sm" onClick={add} disabled={!typed.trim() || full}>
          Add
        </Button>
      </div>
      {trouble ? <p className="text-pw-bad text-[13px]">{trouble}</p> : null}
      {videos.length ? (
        <ul className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          {videos.map((id) => (
            <li
              key={id}
              className="border-pw-border flex flex-col overflow-hidden rounded-[12px] border"
            >
              <div className="bg-pw-muted relative aspect-video">
                {ID.test(id) ? (
                  // YouTube's own thumbnail for the video.
                  // eslint-disable-next-line @next/next/no-img-element
                  <img
                    src={`https://i.ytimg.com/vi/${id}/mqdefault.jpg`}
                    alt=""
                    className="size-full object-cover"
                  />
                ) : (
                  <YoutubeLogoIcon className="text-pw-ink-300 absolute inset-0 m-auto size-8" />
                )}
              </div>
              <div className="flex items-center justify-between gap-2 px-2 py-1">
                <span className="text-pw-ink-500 truncate font-mono text-[11px]">{id}</span>
                <button
                  type="button"
                  onClick={() => onChange(videos.filter((v) => v !== id))}
                  aria-label={`Remove video ${id}`}
                  className="text-pw-ink-400 hover:text-pw-bad text-[12px] font-semibold"
                >
                  Remove
                </button>
              </div>
            </li>
          ))}
        </ul>
      ) : null}
      <p className="text-pw-ink-400 text-[12px]">
        {videos.length} of {most}. Videos must be on YouTube, public or unlisted, and at least 10
        seconds.
      </p>
    </div>
  );
}

const KIND: Record<Segment["kind"], string> = {
  user_list: "Your data",
  custom_audience: "Custom segment",
  user_interest: "Interests and detailed demographics",
  combined_audience: "Combined segment",
};

/** The audience signal: segments that tell Google who is likely to buy. A hint, not a fence. */
export function AudienceSignal({
  signal,
  onChange,
}: {
  signal: Segment[];
  onChange: (next: Segment[]) => void;
}) {
  return (
    <div className="flex flex-col gap-3">
      <Finder<Segment>
        path={(q) => `audiences?q=${encodeURIComponent(q)}`}
        pick={(d) => (d as { segments?: Segment[] }).segments ?? []}
        keyOf={(s) => s.resource}
        render={(s) => (
          <>
            <span className="text-pw-ink min-w-0 truncate">{s.name}</span>
            <span className="text-pw-ink-500 shrink-0 text-[12px]">
              {s.group || KIND[s.kind]}
              {s.size ? `, about ${s.size.toLocaleString()} people` : ""}
            </span>
          </>
        )}
        placeholder="Search your customer lists, website visitors, interests"
        ariaLabel="Add an audience segment to the signal"
        empty="No segment matches that. Try a broader word."
        onPick={(s) => {
          if (!signal.some((x) => x.resource === s.resource)) {
            onChange([...signal, { kind: s.kind, resource: s.resource, name: s.name }]);
          }
        }}
      />
      {signal.length ? (
        <div className="flex flex-wrap gap-2">
          {signal.map((s) => (
            <Pill
              key={s.resource}
              onRemove={() => onChange(signal.filter((x) => x.resource !== s.resource))}
            >
              {s.name || s.resource}
            </Pill>
          ))}
        </div>
      ) : null}
    </div>
  );
}
