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
        elevated ? "bg-paper-white border border-ghost-border" : "bg-cloud-canvas",
        className
      )}
      {...props}
    >
      {children}
    </div>
  );
}
