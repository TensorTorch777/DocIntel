import { cn } from "@/lib/utils";
import { InputHTMLAttributes, forwardRef } from "react";

interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  filled?: boolean;
}

export const Input = forwardRef<HTMLInputElement, InputProps>(
  ({ className, filled, ...props }, ref) => (
    <input
      ref={ref}
      className={cn(
        "w-full rounded-input border border-ghost-border px-5 py-4 text-body text-muted-ash placeholder:text-muted-ash/60 outline-none transition-colors focus:border-electric-violet/40 focus:ring-2 focus:ring-electric-violet/10",
        filled ? "bg-cloud-canvas" : "bg-paper-white",
        className
      )}
      {...props}
    />
  )
);

Input.displayName = "Input";
