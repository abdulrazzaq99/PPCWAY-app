"use client";

import { useEffect, useState } from "react";
import { StartAudit } from "./start-audit";
import { Card, Pill } from "./shell";

/*
  "We already know this."

  Somebody who has connected their Google Ads account has told us the name of
  their business and, in the pages their ads send people to, their website.
  Asking for both again is asking them to repeat themselves — and it lets the
  two disagree, which is how one business's website ends up audited beside
  another's spending.

  So this fills it in and shows its working: every line says where it came
  from, and nothing is hidden behind a guess. The form underneath stays exactly
  where it was for anybody checking a different business.
*/
type Choice = {
  place_id: string;
  name: string;
  address: string;
  website: string;
  category: string;
};

type Known = {
  connected: boolean;
  enough: boolean;
  name: string;
  site: string;
  place_id: string;
  listing_name: string;
  city: string;
  trade: string;
  sure: boolean;
  choices: Choice[];
  whence: { name?: string; site?: string; listing?: string };
};

function Line({ label, value, from }: { label: string; value: string; from?: string }) {
  return (
    <div className="border-line-soft flex flex-wrap items-baseline justify-between gap-x-6 gap-y-1 border-t py-3">
      <span className="min-w-[120px] text-[14px] leading-[20px] font-semibold">{label}</span>
      <span className="flex-1 text-[16px] leading-[22px] font-semibold">{value}</span>
      {from && <span className="text-faint w-full text-[13px] leading-[18px]">{from}</span>}
    </div>
  );
}

export function FromAccount() {
  const [known, setKnown] = useState<Known | null>(null);
  const [picked, setPicked] = useState("");
  const [away, setAway] = useState(false);

  useEffect(() => {
    let stop = false;
    fetch("/api/ads/business", { cache: "no-store" })
      .then((r) => (r.ok ? (r.json() as Promise<Known>) : null))
      .then((said) => !stop && setKnown(said))
      .catch(() => undefined);
    return () => {
      stop = true;
    };
  }, []);

  if (!known || !known.connected || !known.enough || away) return null;

  const place = known.sure ? known.place_id : picked;
  const chosen = known.choices.find((one) => one.place_id === picked);
  const city = known.sure ? known.city : (chosen?.address.split(",").pop()?.trim() ?? "");
  // The ads usually say which website. A new account has none running, so the
  // listing they pick is where the address comes from instead.
  const site = known.site || (chosen?.website ?? "");
  const trade = known.sure ? known.trade : (chosen?.category ?? "");

  return (
    <Card className="mt-7 p-5 sm:p-7">
      <Pill>From your Google Ads account</Pill>
      <h2 className="mt-4 text-[22px] leading-[28px] font-semibold">
        We already know what to check.
      </h2>
      <p className="text-muted mt-2 max-w-[640px] text-[15px] leading-[23px]">
        This is what your connected account tells us. Nothing here was typed, so nothing here can
        disagree with where your money is actually going.
      </p>

      <div className="mt-5">
        <Line label="Business" value={known.name} from={known.whence.name} />
        {site ? (
          <Line
            label="Website"
            value={site.replace(/^https?:\/\//, "").replace(/\/$/, "")}
            from={known.whence.site ?? "the website on your Google listing"}
          />
        ) : (
          <Line
            label="Website"
            value="Pick your listing below"
            from="None of your ads are running, so they cannot tell us the address"
          />
        )}
        {known.sure && known.listing_name && (
          <Line
            label="Google listing"
            value={`${known.listing_name}${known.city ? ` · ${known.city}` : ""}`}
            from={known.whence.listing}
          />
        )}
      </div>

      {!known.sure && known.choices.length > 0 && (
        <div className="border-line-soft mt-1 border-t pt-4">
          <p className="text-[14px] leading-[20px] font-semibold">
            Which of these is your Google listing?
          </p>
          <p className="text-faint mt-1 text-[13px] leading-[18px]">
            None of them carries your website address, so we will not assume. Leave it blank and we
            check the website alone.
          </p>
          <div className="mt-3 flex flex-col gap-2">
            {known.choices.map((one) => (
              <label
                key={one.place_id}
                className="border-line hover:bg-line-soft flex cursor-pointer items-start gap-3 rounded-[12px] border p-3"
              >
                <input
                  type="radio"
                  name="listing"
                  className="mt-1"
                  checked={picked === one.place_id}
                  onChange={() => setPicked(one.place_id)}
                />
                <span className="min-w-0">
                  <span className="block text-[15px] leading-[21px] font-semibold">{one.name}</span>
                  <span className="text-faint block text-[13px] leading-[18px]">
                    {one.address}
                    {one.category ? ` · ${one.category}` : ""}
                  </span>
                </span>
              </label>
            ))}
          </div>
        </div>
      )}

      <div className="mt-5 flex flex-wrap items-center gap-4">
        {site ? (
          <StartAudit
            business={known.name}
            city={city}
            site={site}
            placeId={place}
            trade={trade}
            label={`Check ${site.replace(/^https?:\/\//, "").replace(/\/$/, "")}`}
          />
        ) : (
          <p className="text-muted text-[15px] leading-[22px] font-semibold">
            Choose your listing above and we will check its website.
          </p>
        )}
        <button
          type="button"
          onClick={() => setAway(true)}
          className="text-muted hover:text-ink text-[15px] font-semibold underline"
        >
          Check a different business
        </button>
      </div>
    </Card>
  );
}
