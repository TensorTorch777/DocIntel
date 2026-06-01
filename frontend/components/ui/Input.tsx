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
        "w-full rounded-input px-4 py-3 text-body text-ghost-ash placeholder:text-slate outline-none transition-colors duration-300",
        filled !== false
          ? "bg-charcoal shadow-inset focus:ring-1 focus:ring-ghost-ash/20"
          : "border border-charcoal bg-transparent focus:border-ghost-ash/30",
        className
      )}
      {...props}
    />
  )
);

Input.displayName = "Input";
