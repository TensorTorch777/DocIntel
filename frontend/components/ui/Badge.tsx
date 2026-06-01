import { cn } from "@/lib/utils";

interface BadgeProps {
  children: React.ReactNode;
  variant?: "default" | "accent" | "success" | "warning";
  className?: string;
}

const styles = {
  default: "bg-charcoal text-slate border-charcoal",
  accent: "bg-charcoal text-iridescent border-charcoal",
  success: "bg-charcoal text-ghost-ash border-ghost-ash/20",
  warning: "bg-charcoal text-accent border-accent/30",
};

export function Badge({ children, variant = "default", className }: BadgeProps) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-btn border px-3 py-1 text-caption font-medium",
        styles[variant],
        className
      )}
    >
      {children}
    </span>
  );
}
