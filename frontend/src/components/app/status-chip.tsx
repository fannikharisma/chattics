import type { ReactNode } from "react";

import { cn } from "@/lib/utils";

const tones = {
  success: "bg-success-bg text-success",
  warning: "bg-warning-bg text-warning",
  danger: "bg-danger-bg text-destructive",
  neutral: "bg-secondary text-secondary-foreground",
} as const;

export type StatusTone = keyof typeof tones;

export function StatusChip({
  tone,
  children,
}: {
  tone: StatusTone;
  children: ReactNode;
}) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full border border-border px-2.5 py-0.5 text-meta font-medium whitespace-nowrap",
        tones[tone],
      )}
    >
      {children}
    </span>
  );
}