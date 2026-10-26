/**
 * Server-side session helpers. Presence only — the backend validates the token
 * on every request, so there is nothing to decode here.
 */

import { cookies } from "next/headers";
import { redirect } from "next/navigation";

import { SESSION_COOKIE } from "./api";

/** The raw token, or null when the browser has no session cookie. */
export async function getSession(): Promise<string | null> {
  return (await cookies()).get(SESSION_COOKIE)?.value ?? null;
}

/** Server-only guard: no cookie → /sign-in. */
export async function requireSession(): Promise<string> {
  const token = await getSession();
  if (!token) redirect("/sign-in");
  return token;
}