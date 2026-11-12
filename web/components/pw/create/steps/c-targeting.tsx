"use client";

import { Button } from "@/components/ui/button";
import type { Segment } from "@/lib/creation";
import { Finder, Pill, Tick } from "../kit";
import { Lookup } from "./a-parts";

/*
  Audience pickers for the ad group and settings steps. Display takes
  segments on its ad group, each added or excluded; App engagement takes
  only lists of the app's own users. Both search the account's segments and
  Google's, as the Search settings' audience box does.
*/

// Google lets custom and combined segments be added, not excluded.
const EXCLUDABLE: Segment["kind"][] = ["user_list", "user_interest"];

/** Audience segments on a Display ad group: added, or excluded where Google allows it. */
export function SegmentsEditor({
  value,
  onChange,
}: {
  value: Segment[];
  onChange: (next: Segment[]) => void;
}) {
  const has = (s: Segment) => value.some((x) => x.resource === s.resource);
  return (
    <div className="flex flex-col gap-4">
      <Lookup<Segment>
        path={(q) => `audiences?q=${encodeURIComponent(q)}`}
        pick={(data) =>
          ((data as { segments?: Segment[] }).segments ?? []).filter((s) => s.resource)
        }
        keyOf={(s) => s.resource}
        group={(s) => s.group ?? ""}
        placeholder="Search for segments, such as fitness or website visitors"
        ariaLabel="Search audience segments"
        empty="Google has no segment by that name in this account or its own lists."
        row={(s) => (
          <>
            <span className="min-w-0">
              <span className="text-pw-ink font-medium">{s.name}</span>
              {s.size ? (
                <span className="text-pw-ink-500 ml-2 text-[12px]">
                  About {s.size.toLocaleString()} people
                </span>
              ) : null}
            </span>
            <Button
              size="sm"
              variant={has(s) ? "quiet" : "secondary"}
              disabled={has(s)}
              onClick={() =>
                onChange([
                  ...value,
                  {
                    kind: s.kind,
                    resource: s.resource,
                    name: s.name,
                    group: s.group,
                    excluded: false,
                  },
                ])
              }
            >
              {has(s) ? "Added" : "Add"}
            </Button>
          </>
        )}
      />
      {value.length ? (
        <ul className="flex flex-col gap-2">
          {value.map((s) => (
            <li key={s.resource} className="flex flex-wrap items-center justify-between gap-3">
              <Pill
                tone={s.excluded ? "red" : "blue"}
                onRemove={() => onChange(value.filter((x) => x.resource !== s.resource))}
              >
                {s.excluded ? "Excluded: " : ""}
                {s.name || s.resource}
              </Pill>
              {EXCLUDABLE.includes(s.kind) ? (
                <Tick
                  checked={Boolean(s.excluded)}
                  onChange={(v) =>
                    onChange(
                      value.map((x) => (x.resource === s.resource ? { ...x, excluded: v } : x)),
                    )
                  }
                >
                  Exclude
                </Tick>
              ) : null}
            </li>
          ))}
        </ul>
      ) : (
        <p className="text-pw-ink-500 text-[13px]">No segments yet.</p>
      )}
    </div>
  );
}

/** Lists of the app's users, for an App engagement campaign. Other segments are not offered. */
export function UserListsEditor({
  value,
  onChange,
}: {
  value: Segment[];
  onChange: (next: Segment[]) => void;
}) {
  const lists = value.filter((s) => s.kind === "user_list");
  return (
    <div className="flex flex-col gap-3">
      <Finder<Segment>
        path={(q) => `audiences?q=${encodeURIComponent(q)}`}
        pick={(d) =>
          ((d as { segments?: Segment[] }).segments ?? []).filter(
            (s) => s.resource && s.kind === "user_list",
          )
        }
        keyOf={(s) => s.resource}
        render={(s) => (
          <>
            <span className="text-pw-ink min-w-0 truncate">{s.name}</span>
            <span className="text-pw-ink-500 shrink-0 text-[12px]">
              {value.some((x) => x.resource === s.resource)
                ? "Already added"
                : s.size
                  ? `About ${s.size.toLocaleString()} people`
                  : "Your data"}
            </span>
          </>
        )}
        placeholder="Search your lists, such as app users or purchasers"
        ariaLabel="Search lists of your app's users"
        empty="No list of yours by that name. Lists are made in Google Ads, under Tools, Audience manager."
        onPick={(s) => {
          if (!value.some((x) => x.resource === s.resource)) {
            onChange([...value, { kind: "user_list", resource: s.resource, name: s.name }]);
          }
        }}
      />
      {lists.length ? (
        <div className="flex flex-wrap gap-2">
          {lists.map((s) => (
            <Pill
              key={s.resource}
              onRemove={() => onChange(value.filter((x) => x.resource !== s.resource))}
            >
              {s.name || s.resource}
            </Pill>
          ))}
        </div>
      ) : null}
    </div>
  );
}
