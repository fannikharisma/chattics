/**
 * The one API client.
 *
 * On the server it calls the backend directly with the cookie's token.
 * In the browser it calls this app's proxy, which attaches the token.
 * BACKEND_URL is read only on the server, so it never reaches a client bundle.
 */

export const SESSION_COOKIE = "chattics_session";
export const SESSION_MAX_AGE_SECONDS = 12 * 60 * 60;

const UNKNOWN_MESSAGE = "Something went wrong. Please try again.";

export class ApiError extends Error {
  readonly status: number;
  readonly code: string;
  readonly fields?: Record<string, string>;

  constructor(
    status: number,
    code: string,
    message: string,
    fields?: Record<string, string>,
  ) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
    this.fields = fields;
  }
}

type ErrorEnvelope = {
  error?: { code?: string; message?: string; fields?: Record<string, string> };
};

export async function apiFetch<T>(
  path: string,
  init: RequestInit = {},
): Promise<T> {
  const isServer = typeof window === "undefined";
  const isForm = init.body instanceof FormData;

  const headers = new Headers(init.headers);
  if (!isForm && init.body !== undefined && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  let url = `/api${path}`;

  if (isServer) {
    // Dynamic import keeps next/headers out of the client bundle.
    const { cookies } = await import("next/headers");
    const token = (await cookies()).get(SESSION_COOKIE)?.value;
    if (token) headers.set("Authorization", `Bearer ${token}`);
    url = `${process.env.BACKEND_URL ?? "http://localhost:8000"}/api${path}`;
  }

  let response: Response;
  try {
    response = await fetch(url, {
      ...init,
      headers,
      cache: "no-store",
      redirect: "manual",
    });
  } catch {
    throw new ApiError(
      503,
      "backend_unreachable",
      "The server could not be reached. Please try again shortly.",
    );
  }

  if (!response.ok) {
    const body = (await response.json().catch(() => null)) as ErrorEnvelope | null;
    throw new ApiError(
      response.status,
      body?.error?.code ?? "unknown",
      body?.error?.message ?? UNKNOWN_MESSAGE,
      body?.error?.fields,
    );
  }

  const data = response.status === 204 ? undefined : await response.json();
  return data as T;
}