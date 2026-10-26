/**
 * Authenticated proxy. The browser calls /api/<path>; this handler overwrites
 * Authorization with the cookie's token and forwards to the backend.
 * A client-supplied Authorization header is never trusted or forwarded.
 */

import { cookies } from "next/headers";

import { SESSION_COOKIE } from "@/lib/api";

const INVALID_SESSION = {
  error: {
    code: "invalid_session",
    message: "Your session is not valid. Please sign in again.",
  },
};

const BACKEND_UNREACHABLE = {
  error: {
    code: "backend_unreachable",
    message: "The server could not be reached. Please try again shortly.",
  },
};

async function forward(request: Request, path: string[]): Promise<Response> {
  const token = (await cookies()).get(SESSION_COOKIE)?.value;
  if (!token) {
    return Response.json(INVALID_SESSION, { status: 401 });
  }

  const target =
    `${process.env.BACKEND_URL ?? "http://localhost:8000"}` +
    `/api/${path.join("/")}${new URL(request.url).search}`;

  const headers = new Headers();
  const contentType = request.headers.get("content-type");
  if (contentType) headers.set("Content-Type", contentType);
  headers.set("Authorization", `Bearer ${token}`);

  const hasBody = request.method !== "GET" && request.method !== "HEAD";
  const body = hasBody ? await request.arrayBuffer() : undefined;

  let response: Response;
  try {
    response = await fetch(target, {
      method: request.method,
      headers,
      body,
      cache: "no-store",
      redirect: "manual",
    });
  } catch {
    return Response.json(BACKEND_UNREACHABLE, { status: 503 });
  }

  const responseHeaders = new Headers();
  const responseType = response.headers.get("content-type");
  if (responseType) responseHeaders.set("Content-Type", responseType);

  return new Response(response.body, {
    status: response.status,
    headers: responseHeaders,
  });
}

type RouteContext = { params: Promise<{ path: string[] }> };

export async function GET(request: Request, { params }: RouteContext) {
  return forward(request, (await params).path);
}

export async function POST(request: Request, { params }: RouteContext) {
  return forward(request, (await params).path);
}

export async function PUT(request: Request, { params }: RouteContext) {
  return forward(request, (await params).path);
}

export async function PATCH(request: Request, { params }: RouteContext) {
  return forward(request, (await params).path);
}

export async function DELETE(request: Request, { params }: RouteContext) {
  return forward(request, (await params).path);
}