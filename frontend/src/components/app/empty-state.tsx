import type { ReactNode } from "react";

export function EmptyState({
  title,
  children,
  action,
}: {
  title?: string;
  children: ReactNode;
  action?: ReactNode;
}) {
  return (
    <div className="px-6 py-7 text-center text-muted-foreground">
      {title && (
        <h2 className="text-xl font-semibold text-foreground">{title}</h2>
      )}
      <p className={title ? "mt-1" : undefined}>{children}</p>
      {action && <div className="mt-3">{action}</div>}
    </div>
  );
}