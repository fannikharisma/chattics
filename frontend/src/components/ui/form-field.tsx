import type { ReactNode } from "react";

import { Label } from "@/components/ui/label";

export function FormField({
  id,
  label,
  error,
  help,
  children,
}: {
  id: string;
  label: string;
  error?: string;
  help?: string;
  children: ReactNode;
}) {
  return (
    <div className="mt-3">
      <Label htmlFor={id}>{label}</Label>
      <div className="mt-1.5">{children}</div>
      {help && !error && (
        <p className="mt-1 text-meta text-muted-foreground">{help}</p>
      )}
      {error && (
        <p
          id={`${id}-error`}
          role="alert"
          className="mt-1 text-meta text-destructive"
        >
          {error}
        </p>
      )}
    </div>
  );
}