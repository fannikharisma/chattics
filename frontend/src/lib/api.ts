/**
 * Browser-side API access. Calls this app's proxy, which attaches the token.
 * Never import server-only code here: this file enters the client bundle.
 */

export const SESSION_COOKIE = "chattics_session";
export const SESSION_MAX_AGE_SECONDS = 12 * 60 * 60;

const UNKNOWN_MESSAGE = "Something went wrong. Please try again.";
const UNREACHABLE_MESSAGE =
  "The server could not be reached. Please try again shortly.";

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

export async function readResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const body = (await response
      .json()
      .catch(() => null)) as ErrorEnvelope | null;
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

export async function apiFetch<T>(
  path: string,
  init: RequestInit = {},
): Promise<T> {
  const isForm = init.body instanceof FormData;
  const headers = new Headers(init.headers);
  if (!isForm && init.body !== undefined && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  let response: Response;
  try {
    response = await fetch(`/api${path}`, {
      ...init,
      headers,
      cache: "no-store",
    });
  } catch {
    throw new ApiError(503, "backend_unreachable", UNREACHABLE_MESSAGE);
  }

  return readResponse<T>(response);
}