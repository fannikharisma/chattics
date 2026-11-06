import { CheckCircle2, XCircle } from "lucide-react";

import { cn } from "@/lib/utils";
import type { ConnectionChecklistItem } from "@/lib/types";

export function ConnectionChecklist({
  items,
  error,
}: {
  items: ConnectionChecklistItem[];
  error: string | null;
}) {
  return (
    <div>
      <ul className="space-y-2.5">
        {items.map((item) => {
          const Icon = item.passed ? CheckCircle2 : XCircle;

          return (
            <li key={item.key} className="flex items-start gap-2">
              <Icon
                aria-hidden="true"
                className={cn(
                  "mt-0.5 h-5 w-5 shrink-0",
                  item.passed ? "text-success" : "text-destructive",
                )}
              />
              <div className="min-w-0 flex-1">
                <p className="text-sm font-medium text-foreground">
                  {item.label}
                </p>
                {item.detail && (
                  <p className="mt-0.5 text-meta text-muted-foreground">
                    {item.detail}
                  </p>
                )}
              </div>
              <span
                className={cn(
                  "text-meta font-medium",
                  item.passed ? "text-success" : "text-destructive",
                )}
              >
                {item.passed ? "Passed" : "Failed"}
              </span>
            </li>
          );
        })}
      </ul>

      {error && (
        <div
          role="alert"
          className="mt-3 rounded-card bg-danger-bg px-4 py-3 text-sm text-destructive"
        >
          <p className="font-medium">Connection failed</p>
          <p className="mt-0.5">{error}</p>
        </div>
      )}
    </div>
  );
}