import { Suspense } from "react";

const BACKEND_URL = process.env.BACKEND_URL ?? "http://localhost:8000";

async function check(url: string): Promise<boolean> {
  try {
    const response = await fetch(url, { cache: "no-store" });
    return response.ok;
  } catch {
    return false;
  }
}

async function Status() {
  const [backend, database] = await Promise.all([
    check(`${BACKEND_URL}/api/health`),
    check(`${BACKEND_URL}/api/health/db`),
  ]);

  return (
    <div className="mt-4">
      <p className="text-base text-zinc-900">
        {backend ? "backend connected" : "backend not reachable"}
      </p>
      <p className="mt-1 text-sm text-zinc-600">
        Database: {database ? "ok" : "not reachable"}
      </p>
      {!backend && (
        <p className="mt-4 rounded-lg bg-sky-50 px-3 py-2 text-sm text-sky-900">
          Start the backend, then reload this page.
        </p>
      )}
    </div>
  );
}

export default function Home() {
  return (
    <main className="flex min-h-dvh items-center justify-center bg-zinc-50 px-4 py-16">
      <section className="w-full max-w-md rounded-2xl border border-zinc-200 bg-white p-8 shadow-sm">
        <h1 className="text-2xl font-semibold tracking-tight text-zinc-900">
          Chattics
        </h1>

        <Suspense
          fallback={
            <div className="mt-4">
              <p className="text-base text-zinc-600">checking the backend…</p>
              <p className="mt-1 text-sm text-zinc-500">Database: checking…</p>
            </div>
          }
        >
          <Status />
        </Suspense>
      </section>
    </main>
  );
}