/**
 * The backend keeps no token list, so signing out is just discarding the cookie.
 */

import { NextResponse } from "next/server";

import { SESSION_COOKIE } from "@/lib/api";

export async function POST(): Promise<NextResponse> {
  const response = new NextResponse(null, { status: 204 });
  response.cookies.set({
    name: SESSION_COOKIE,
    value: "",
    httpOnly: true,
    sameSite: "lax",
    secure: process.env.NODE_ENV === "production",
    path: "/",
    maxAge: 0,
  });
  return response;
}