"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { BOX, fieldBorder } from "@/components/audit/funnel/bits";
import { cn } from "@/lib/cn";

/*
  A phone number, shaped as the country it belongs to writes it.

  The page is sold worldwide, so it cannot assume +1. The country comes from
  what they type: a number beginning with + carries its own country code and
  the mask follows it, so somebody in Dublin types +353 and sees 1 234 5678,
  not a Canadian shape. Without a +, we fall back to the country the browser
  says it is in, and say which one we used, because a silent assumption about
  somebody's phone number is how you end up with an unreachable lead.

  Google's own phone library does the shaping — the formats of 240-odd
  countries are not something to keep by hand. It is loaded only when somebody
  reaches this field, which on this page is after a two minute audit, so the
  landing page itself never carries the weight.
*/
type Shaper = {
  AsYouType: new (country?: string) => { input: (text: string) => string };
  parsePhoneNumberFromString: (
    text: string,
    country?: string,
  ) => { isValid: () => boolean; number: string; country?: string } | undefined;
};

let shaper: Shaper | null = null;
let loading: Promise<Shaper> | null = null;

/** Loaded once per page, and never before somebody needs it. */
function load(): Promise<Shaper> {
  if (shaper) return Promise.resolve(shaper);
  loading ??= import("libphonenumber-js/min").then((mod) => {
    shaper = mod as unknown as Shaper;
    return shaper;
  });
  return loading;
}

/** Where the browser thinks it is, which is the best guess we have for free. */
function here(): string {
  try {
    const tag = navigator.language || "en-CA";
    const region = new Intl.Locale(tag).region;
    return region && /^[A-Z]{2}$/.test(region) ? region : "CA";
  } catch {
    return "CA";
  }
}

function countryName(code: string): string {
  try {
    return new Intl.DisplayNames([navigator.language || "en"], { type: "region" }).of(code) ?? code;
  } catch {
    return code;
  }
}

export function PhoneField({
  value,
  onChange,
  invalid,
}: {
  value: string;
  /** The text as typed, and the dialable form when it is a real number. */
  onChange: (text: string, dialable: string) => void;
  invalid?: boolean;
}) {
  const [country, setCountry] = useState("CA");
  const [ready, setReady] = useState(false);
  const mine = useRef(here());

  useEffect(() => {
    mine.current = here();
    setCountry(mine.current);
  }, []);

  const shape = useCallback(
    (raw: string) => {
      if (!shaper) return { text: raw, dialable: "", from: country };
      // A leading + means the number names its own country, so the mask
      // follows the number rather than the browser.
      const international = raw.trim().startsWith("+");
      const typed = new shaper.AsYouType(international ? undefined : country).input(raw);
      const parsed = shaper.parsePhoneNumberFromString(raw, international ? undefined : country);
      return {
        text: typed,
        dialable: parsed?.isValid() ? parsed.number : "",
        from: parsed?.country ?? (international ? "" : country),
      };
    },
    [country],
  );

  function wake() {
    if (ready) return;
    load()
      .then(() => {
        setReady(true);
        // Shape whatever is already in the box, so arriving with a pasted
        // number does not leave it unformatted.
        if (value) {
          const done = shape(value);
          onChange(done.text, done.dialable);
          if (done.from) setCountry(done.from);
        }
      })
      .catch(() => undefined);
  }

  const shown = ready ? shape(value) : { text: value, dialable: "", from: country };

  return (
    <>
      <input
        id="tel"
        type="tel"
        inputMode="tel"
        autoComplete="tel"
        placeholder="+1 416 555 0123"
        value={value}
        onFocus={wake}
        onChange={(e) => {
          const done = shape(e.target.value);
          if (done.from && done.from !== country) setCountry(done.from);
          onChange(done.text, done.dialable);
        }}
        className={cn(BOX, fieldBorder(invalid), "font-normal")}
      />
      {ready && value.trim() && (
        <span className="text-[12.5px] leading-[16px] text-[#6B6680]">
          {/* "a Ireland number" — so the country goes after the noun, which
              reads correctly for every country without an article to pick. */}
          {shown.dialable
            ? `Reading this as a number in ${countryName(shown.from || country)}.`
            : `Shaping for ${countryName(country)}. Start with + for another country.`}
        </span>
      )}
    </>
  );
}
