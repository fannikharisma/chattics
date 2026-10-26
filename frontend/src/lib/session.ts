/**
 * Server-side session helpers. Presence only — the backend validates the token
 * on every request, so there is nothing to decode here.
 */

import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import { cache } from "react";

import { ApiError, SESSION_COOKIE } from "./api";
import { serverFetch } from "./api.server";
import type { Me } from "./types";

/** Token presence only — the backend validates it on every request. */
export async function getSession(): Promise<string | null> {
  return (await cookies()).get(SESSION_COOKIE)?.value ?? null;
}

/** Server-only guard: no cookie → /sign-in. */
export async function requireSession(): Promise<string> {
  const token = await getSession();
  if (!token) redirect("/sign-in");
  return token;
}

/** One /auth/me per request, shared by the layout and the page. */
export const getMe = cache(async (): Promise<Me> => {
  try {
    return await serverFetch<Me>("/auth/me");
  } catch (error) {
    if (error instanceof ApiError && error.status === 401) redirect("/sign-in");
    throw error;
  }
});