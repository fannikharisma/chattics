/**
 * Server-only API access. Reads the cookie here, so BACKEND_URL and the token
 * never enter a client bundle. Never import this from a Client Component.
 */

import { cookies } from "next/headers";

import {
  ApiError,
  SESSION_COOKIE,
  readResponse,
} from "./api";

const BACKEND_URL = process.env.BACKEND_URL ?? "http://localhost:8000";
const UNREACHABLE_MESSAGE =
  "The server could not be reached. Please try again shortly.";

export async function serverFetch<T>(
  path: string,
  init: RequestInit = {},
): Promise<T> {
  const isForm = init.body instanceof FormData;
  const headers = new Headers(init.headers);
  if (!isForm && init.body !== undefined && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  // Overwrite last: a caller cannot supply their own Authorization.
  const token = (await cookies()).get(SESSION_COOKIE)?.value;
  if (token) headers.set("Authorization", `Bearer ${token}`);

  let response: Response;
  try {
    response = await fetch(`${BACKEND_URL}/api${path}`, {
      ...init,
      headers,
      cache: "no-store",
      redirect: "manual",
    });
  } catch {
    throw new ApiError(503, "backend_unreachable", UNREACHABLE_MESSAGE);
  }

  return readResponse<T>(response);
}