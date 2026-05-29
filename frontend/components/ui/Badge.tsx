import { cn } from "@/lib/utils";

interface BadgeProps {
  children: React.ReactNode;
  variant?: "default" | "accent" | "success" | "warning";
  className?: string;
}

const styles = {
  default: "bg-cloud-canvas text-muted-ash border-ghost-border",
  accent: "bg-electric-violet/10 text-electric-violet border-electric-violet/20",
  success: "bg-emerald-50 text-emerald-700 border-emerald-200",
  warning: "bg-amber-50 text-amber-700 border-amber-200",
};

export function Badge({ children, variant = "default", className }: BadgeProps) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-pill border px-3 py-1 text-caption font-medium",
        styles[variant],
        className
      )}
    >
      {children}
    </span>
  );
}
