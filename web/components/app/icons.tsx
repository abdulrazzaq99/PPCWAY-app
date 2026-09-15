import { cn } from "@/lib/cn";
import type { IconName } from "./nav";

/*
  The nav icons, drawn from simple shapes exactly as in the file: four squares,
  three bars, a box with a fill, three rising bars, a ring with a handle, two
  sliders, a ring with a dot and stem. `tone` is the current colour; the shapes
  use currentColor so the active state only changes the text colour.
*/
export function NavIcon({ name, className }: { name: IconName; className?: string }) {
  const c = "bg-current";
  const box = cn("relative block size-[22px] shrink-0", className);
  switch (name) {
    case "overview":
      return (
        <span aria-hidden className={box}>
          <span className={cn(c, "absolute top-[2px] left-[2px] size-2 rounded-[2.5px]")} />
          <span className={cn(c, "absolute top-[2px] left-3 size-2 rounded-[2.5px]")} />
          <span className={cn(c, "absolute top-3 left-[2px] size-2 rounded-[2.5px]")} />
          <span className={cn(c, "absolute top-3 left-3 size-2 rounded-[2.5px]")} />
        </span>
      );
    case "activity":
      return (
        <span aria-hidden className={box}>
          <span className={cn(c, "absolute top-1 left-[2px] h-[3px] w-[18px] rounded-[1.5px]")} />
          <span
            className={cn(c, "absolute top-[10px] left-[2px] h-[3px] w-[13px] rounded-[1.5px]")}
          />
          <span className={cn(c, "absolute top-4 left-[2px] h-[3px] w-2 rounded-[1.5px]")} />
        </span>
      );
    case "approvals":
      return (
        <span aria-hidden className={box}>
          <span className="absolute top-[2px] left-[2px] size-[18px] rounded-[5px] border border-current" />
          <span className={cn(c, "absolute top-[7px] left-[7px] size-2 rounded-[2px]")} />
        </span>
      );
    case "campaigns":
      return (
        <span aria-hidden className={box}>
          <span className={cn(c, "absolute top-3 left-[3px] h-2 w-1 rounded-[1.5px]")} />
          <span className={cn(c, "absolute top-[7px] left-[9px] h-[13px] w-1 rounded-[1.5px]")} />
          <span className={cn(c, "absolute top-[3px] left-[15px] h-[17px] w-1 rounded-[1.5px]")} />
        </span>
      );
    case "searches":
      return (
        <span aria-hidden className={box}>
          <span className="absolute top-[2px] left-[2px] size-[15px] rounded-full border border-current" />
          <span
            className={cn(
              c,
              "absolute top-[15px] left-[14px] h-[3px] w-[6px] rotate-45 rounded-[1.5px]",
            )}
          />
        </span>
      );
    case "settings":
      return (
        <span aria-hidden className={box}>
          <span
            className={cn(c, "absolute top-[6px] left-[2px] h-[3px] w-[18px] rounded-[1.5px]")}
          />
          <span
            className={cn(c, "absolute top-[14px] left-[2px] h-[3px] w-[18px] rounded-[1.5px]")}
          />
          <span className="bg-panel absolute top-1 left-3 size-[7px] rounded-full" />
          <span className="bg-panel absolute top-3 left-1 size-[7px] rounded-full" />
        </span>
      );
    case "help":
      return (
        <span aria-hidden className={box}>
          <span className="absolute top-[2px] left-[2px] size-[18px] rounded-full border border-current" />
          <span className={cn(c, "absolute top-[6px] left-[9.5px] size-[3px] rounded-full")} />
          <span
            className={cn(c, "absolute top-[11px] left-[9.5px] h-[6px] w-[3px] rounded-[1.5px]")}
          />
        </span>
      );
    case "more":
      return (
        <span aria-hidden className={box}>
          <span className={cn(c, "absolute top-[9px] left-[2px] size-1 rounded-full")} />
          <span className={cn(c, "absolute top-[9px] left-[9px] size-1 rounded-full")} />
          <span className={cn(c, "absolute top-[9px] left-4 size-1 rounded-full")} />
        </span>
      );
  }
}

/** The small magnifier inside the toolbar search box. */
export function SearchGlyph() {
  return (
    <span aria-hidden className="text-faint relative block size-[18px] shrink-0">
      <span className="absolute top-[2px] left-[2px] size-3 rounded-full border border-current" />
      <span className="absolute top-[12px] left-[11px] h-[3px] w-[6px] rotate-45 rounded-[1.5px] bg-current" />
    </span>
  );
}
