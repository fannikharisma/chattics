import { forwardRef, type InputHTMLAttributes } from "react";

import { cn } from "@/lib/utils";

export const Input = forwardRef<
  HTMLInputElement,
  InputHTMLAttributes<HTMLInputElement>
>(function Input({ className, ...props }, ref) {
  return (
    <input
      ref={ref}
      className={cn(
        "h-11 w-full rounded-control border border-input bg-card px-3 text-base text-foreground placeholder:text-muted-foreground aria-invalid:border-destructive disabled:opacity-60",
        className,
      )}
      {...props}
    />
  );
});