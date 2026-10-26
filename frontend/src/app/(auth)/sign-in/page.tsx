import { Suspense } from "react";
import { redirect } from "next/navigation";

import { serverFetch } from "@/lib/api.server";
import { getSession } from "@/lib/session";
import type { Me, PublicTenant } from "@/lib/types";

import { SignInForm } from "./sign-in-form";

export default function SignInPage() {
  return (
    <Suspense fallback={<SignInShell />}>
      <SignInContent />
    </Suspense>
  );
}

function SignInShell() {
  return (
    <main className="flex min-h-dvh items-center justify-center bg-background px-4">
      <p className="text-sm text-muted-foreground">Loading…</p>
    </main>
  );
}

async function SignInContent() {
  if (await getSession()) {
    let signedIn = false;
    try {
      await serverFetch<Me>("/auth/me");
      signedIn = true;
    } catch {
      // Stale cookie: show the form. Signing in replaces it.
    }
    if (signedIn) redirect("/conversations");
  }

  let tenants: PublicTenant[] = [];
  let tenantsUnavailable = false;
  try {
    tenants = await serverFetch<PublicTenant[]>("/tenants/public");
  } catch {
    tenantsUnavailable = true;
  }

  return (
    <SignInForm tenants={tenants} tenantsUnavailable={tenantsUnavailable} />
  );
}