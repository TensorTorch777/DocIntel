import { cn } from "@/lib/utils";
import { ButtonHTMLAttributes, forwardRef } from "react";

type Variant = "primary" | "ghost" | "outline" | "flat";

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant;
}

const variants: Record<Variant, string> = {
  primary:
    "bg-ghost-ash text-midnight hover:bg-smoke disabled:opacity-50 shadow-inset",
  ghost:
    "bg-charcoal text-ghost-ash hover:bg-charcoal/80 border border-charcoal disabled:opacity-50",
  outline:
    "bg-transparent text-ghost-ash border border-ghost-ash/30 hover:border-ghost-ash/60 disabled:opacity-50",
  flat:
    "bg-transparent text-slate hover:text-ghost-ash disabled:opacity-50",
};

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant = "primary", children, ...props }, ref) => (
    <button
      ref={ref}
      className={cn(
        "inline-flex items-center justify-center gap-2 rounded-btn px-5 py-2.5 text-body font-medium transition-colors duration-300",
        variants[variant],
        className
      )}
      {...props}
    >
      {children}
    </button>
  )
);

Button.displayName = "Button";
