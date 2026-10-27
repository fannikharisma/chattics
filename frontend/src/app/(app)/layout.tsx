import { Suspense, type ReactNode } from "react";

import { AppShell } from "@/components/app/app-shell";
import { requireSession } from "@/lib/session";

export default function AppLayout({ children }: { children: ReactNode }) {
  return (
    <Suspense fallback={<div className="min-h-dvh bg-background" />}>
      <AuthenticatedShell>{children}</AuthenticatedShell>
    </Suspense>
  );
}

async function AuthenticatedShell({ children }: { children: ReactNode }) {
  const { context, tenantDisabled } = await requireSession();
  return (
    <AppShell
      identity={context.identity}
      tenant={context.tenant}
      menus={context.menus}
      tenantDisabled={tenantDisabled}
    >
      {children}
    </AppShell>
  );
}