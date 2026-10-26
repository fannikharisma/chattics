import { Suspense, type ReactNode } from "react";

import { AppShell } from "@/components/app/app-shell";
import { getMe, requireSession } from "@/lib/session";

export default function AppLayout({ children }: { children: ReactNode }) {
  return (
    <Suspense fallback={<div className="min-h-dvh bg-background" />}>
      <AuthenticatedShell>{children}</AuthenticatedShell>
    </Suspense>
  );
}

async function AuthenticatedShell({ children }: { children: ReactNode }) {
  await requireSession();
  const me = await getMe();
  return (
    <AppShell user={me.user} menus={me.menus}>
      {children}
    </AppShell>
  );
}