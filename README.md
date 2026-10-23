# Chattics

Chattics turns a business Question into a live Result Table, then a Dataset,
Chart or Dashboard. A Python/FastAPI backend is the only authority; the Next.js
frontend only renders what the backend returns. App data lives in Supabase
(Postgres); Tenant business data stays in BigQuery.

This README is the command source of truth — keep it current when setup, run or
test steps change.

## Prerequisites

- **Node.js 20+** and npm (`node -v`).
- **uv** — installs dependencies and pins **Python 3.12** (`uv --version`;
  install with `curl -LsSf https://astral.sh/uv/install.sh | sh`).
- **Supabase CLI** (`supabase --version`).
- **Two Supabase databases**: one for development and a **separate** one for
  tests. Copy the **Session pooler** connection string (port `5432`) for each —
  not the transaction pooler. Never point the test suite at the development
  database.
- Optional, for real Tenant data: a Google Cloud project with BigQuery access.
  Tests and local development use a fake connector and a fake AI, so no real
  BigQuery or model credentials are needed to run the app or the suite.

## Run locally

Apply the database schema once, from the repo root:

```bash
supabase link --project-ref <your-project-ref>
supabase db push
```

Never edit an applied migration. Create a new numbered file with
`supabase migration new <short_name>`, write the SQL, then `supabase db push`.

Start the backend (port 8000):

```bash
cd backend
uv sync
cp .env.example .env          # fill in real values; .env is never committed
uv run uvicorn app.main:app --reload --port 8000
```

`DATABASE_URL`, `TEST_DATABASE_URL`, `JWT_SECRET` and `ENCRYPTION_KEY` are
required; `.env.example` lists every name with dummy values. The API description
is at http://localhost:8000/docs.

Start the frontend (port 3000) in a second terminal:

```bash
cd frontend
npm install
cp .env.example .env.local    # BACKEND_URL defaults to http://localhost:8000
npm run dev
```

Open http://localhost:3000. `TEST_MODE_LOGIN=true` in the backend `.env` gives
you local sign-in; it must be `false` anywhere real people use the app.

## Run tests

The backend suite drives the real HTTP API against the **test** database and
asserts on responses and database state. It uses the fake connector and fake AI,
so it never calls BigQuery or a real model. `TEST_DATABASE_URL` must be set and
different from `DATABASE_URL`, and the schema must already be applied to that
database.

```bash
cd backend
uv run pytest -q
```

Frontend proof — tests plus a production build with no new failures or skipped
tests:

```bash
cd frontend
npm test
npm run build
```

A change is done only when both suites pass.
