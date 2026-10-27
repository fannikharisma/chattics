/**
 * Server-side session helpers. Presence only — the backend validates the token
 * on every request, so there is nothing to decode here.
 */

import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import { cache } from "react";

import { ApiError, SESSION_COOKIE } from "./api";
import { serverFetch } from "./api.server";
import type { Context } from "./types";

export type SessionContext = {
  context: Context;
  /** The selected Tenant became disabled; the backend cleared it for us. */
  tenantDisabled: boolean;
};

/** Token presence only — the backend validates it on every request. */
export async function getSession(): Promise<string | null> {
  return (await cookies()).get(SESSION_COOKIE)?.value ?? null;
}

/**
 * One /context per request, shared by the layout and the page.
 *
 * When the backend reports that the Selected Tenant is disabled, it has
 * already cleared the selection. Read the context once more so the shell can
 * reopen the picker with an explanation instead of showing an error page.
 */
export const getContext = cache(async (): Promise<SessionContext> => {
  try {
    return {
      context: await serverFetch<Context>("/context"),
      tenantDisabled: false,
    };
  } catch (error) {
    if (!(error instanceof ApiError)) throw error;
    if (error.status === 401) redirect("/sign-in");
    if (error.code === "tenant_disabled") {
      // A distinct URL keeps Next's request-level GET memoization from
      // handing back the refused response instead of the cleared context.
      const context = await serverFetch<Context>("/context?after=disabled");
      return { context, tenantDisabled: true };
    }
    throw error;
  }
});

/** Server-only guard: no cookie → /sign-in. */
export async function requireSession(): Promise<SessionContext> {
  const token = await getSession();
  if (!token) redirect("/sign-in");
  return getContext();
}
