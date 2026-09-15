import Link from "next/link";
import type { ButtonHTMLAttributes, ReactNode } from "react";
import { cn } from "@/lib/cn";

type Variant = "primary" | "secondary" | "quiet" | "danger";
type Size = "md" | "sm";

/*
  Buttons, from the "States and motion" frame.
  Rest: brand. Hover: brand-dark, colour only. Pressed: darker and scale 0.98 for 80ms.
  Keyboard focus: a 4px ring in the pale brand tone. Working: the label swaps, no spinner.
  Disabled: line grey with muted text, and the reason is said nearby, never in a tooltip.
*/
const base =
  "inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-[var(--radius-pill)] font-semibold " +
  "transition-[background-color,color,border-color,transform] duration-[var(--dur-hover)] ease-out " +
  "active:scale-[0.98] active:duration-[var(--dur-press)] " +
  "focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-brand-bar " +
  "disabled:pointer-events-none disabled:bg-line disabled:text-rail-icon disabled:border-line";

const variants: Record<Variant, string> = {
  primary: "bg-brand text-white hover:bg-brand-dark active:bg-[#1e3d94]",
  secondary: "bg-panel text-ink border border-line-input hover:bg-line-soft active:bg-line",
  quiet: "bg-transparent text-brand hover:bg-brand-tint active:bg-brand-pale",
  danger: "bg-red text-white hover:bg-[#8a2119] active:bg-[#741b14]",
};

const sizes: Record<Size, string> = {
  md: "h-[46px] px-7 text-[15px] leading-[18px]",
  sm: "h-[38px] px-5 text-[14px] leading-[17px]",
};

type CommonProps = {
  variant?: Variant;
  size?: Size;
  /** Shown instead of children while an action runs. The spec swaps the label, no spinner. */
  working?: string | false;
  full?: boolean;
  className?: string;
  children: ReactNode;
};

type ButtonProps = CommonProps &
  Omit<ButtonHTMLAttributes<HTMLButtonElement>, "className" | "children">;

export function Button({
  variant = "primary",
  size = "md",
  working = false,
  full,
  className,
  children,
  disabled,
  ...rest
}: ButtonProps) {
  const isWorking = Boolean(working);
  return (
    <button
      type="button"
      className={cn(
        base,
        variants[variant],
        sizes[size],
        full && "w-full",
        isWorking && "bg-brand-dark text-brand-bar pointer-events-none",
        className,
      )}
      aria-busy={isWorking || undefined}
      disabled={disabled}
      {...rest}
    >
      {isWorking ? working : children}
    </button>
  );
}

type LinkButtonProps = CommonProps & { href: string; prefetch?: boolean };

export function LinkButton({
  href,
  variant = "primary",
  size = "md",
  full,
  className,
  children,
  prefetch,
}: LinkButtonProps) {
  return (
    <Link
      href={href}
      prefetch={prefetch}
      className={cn(base, variants[variant], sizes[size], full && "w-full", className)}
    >
      {children}
    </Link>
  );
}

/** The inline text link used for "Forgot it?", "Create an account", "See everything". */
export function TextLink({
  href,
  children,
  className,
  size = 14,
}: {
  href: string;
  children: ReactNode;
  className?: string;
  size?: 13 | 14 | 15;
}) {
  return (
    <Link
      href={href}
      className={cn(
        "text-brand hover:text-brand-dark focus-visible:ring-brand-bar rounded-sm font-semibold transition-colors duration-[var(--dur-hover)] focus-visible:ring-4 focus-visible:outline-none",
        size === 13 && "text-[13px] leading-4",
        size === 14 && "text-[14px] leading-[17px]",
        size === 15 && "text-[15px] leading-[18px]",
        className,
      )}
    >
      {children}
    </Link>
  );
}
