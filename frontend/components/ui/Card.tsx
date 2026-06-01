import { cn } from "@/lib/utils";
import { HTMLAttributes } from "react";

interface CardProps extends HTMLAttributes<HTMLDivElement> {
  elevated?: boolean;
}

export function Card({ className, elevated, children, ...props }: CardProps) {
  return (
    <div
      className={cn(
        "rounded-card p-card",
        elevated ? "obsidian-glass" : "bg-charcoal shadow-inset",
        className
      )}
      {...props}
    >
      {children}
    </div>
  );
}
