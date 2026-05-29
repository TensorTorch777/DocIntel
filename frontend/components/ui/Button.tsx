import { cn } from "@/lib/utils";
import { ButtonHTMLAttributes, forwardRef } from "react";

type Variant = "primary" | "secondary" | "ghost" | "outline";

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant;
}

const variants: Record<Variant, string> = {
  primary:
    "bg-electric-violet text-paper-white hover:bg-electric-violet/90 disabled:opacity-50",
  secondary:
    "bg-midnight-ink text-paper-white hover:bg-midnight-ink/90 disabled:opacity-50",
  ghost:
    "bg-cloud-canvas text-midnight-ink hover:bg-ghost-border disabled:opacity-50",
  outline:
    "bg-paper-white text-midnight-ink border border-ghost-border hover:bg-cloud-canvas disabled:opacity-50",
};

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant = "primary", children, ...props }, ref) => (
    <button
      ref={ref}
      className={cn(
        "inline-flex items-center justify-center gap-2 rounded-pill px-5 py-2.5 text-body font-medium transition-colors",
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
