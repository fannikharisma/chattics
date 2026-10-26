/**
 * Sign-in is server-only work: ask the backend, keep the token in an HttpOnly
 * cookie, and return only the user. The token never enters the response body.
 */

import { NextResponse } from "next/server";

import { SESSION_COOKIE, SESSION_MAX_AGE_SECONDS } from "@/lib/api";

const SIGN_IN_FAILED = {
  error: { code: "sign_in_failed", message: "Sign-in failed. Please try again." },
};

const BACKEND_UNREACHABLE = {
  error: {
    code: "backend_unreachable",
    message: "The server could not be reached. Please try again shortly.",
  },
};

export async function POST(request: Request): Promise<NextResponse> {
  const raw = await request.text();

  let response: Response;
  try {
    response = await fetch(
      `${process.env.BACKEND_URL ?? "http://localhost:8000"}/api/auth/sign-in`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: raw,
        cache: "no-store",
      },
    );
  } catch {
    return NextResponse.json(BACKEND_UNREACHABLE, { status: 503 });
  }

  const body = (await response.json().catch(() => null)) as Record<
    string,
    unknown
  > | null;

  const token = typeof body?.token === "string" ? body.token : null;

  if (!response.ok || token === null) {
    return NextResponse.json(body ?? SIGN_IN_FAILED, {
      status: response.ok ? 502 : response.status,
    });
  }

  const result = NextResponse.json({ user: body?.user });
  result.cookies.set({
    name: SESSION_COOKIE,
    value: token,
    httpOnly: true,
    sameSite: "lax",
    secure: process.env.NODE_ENV === "production",
    path: "/",
    maxAge: SESSION_MAX_AGE_SECONDS,
  });
  return result;
}