# LOCAL\_RUN – FinAI Real-Time Market Analytics

This guide walks you through running the **entire FinAI stack locally**:

- **Backend (FastAPI)** – `apps/api` on **http://localhost:8000**
- **Frontend (Next.js)** – `apps/web` on **http://localhost:3000**
- **Database (optional Postgres)** – via `docker-compose` on **localhost:5432**  
  (or SQLite for a zero-dependency quick start)

Everything here is **copy-paste friendly** and aligned with the actual commands and files in this repo.

---

## 1. Overview

### Components & ports

- Backend API (FastAPI)
  - URL: `http://localhost:8000`
  - Health: `GET /health`
  - Docs: `http://localhost:8000/docs`
  - WebSocket: `ws://localhost:8000/ws/stream`
- Frontend (Next.js)
  - URL: `http://localhost:3000`
- Database
  - **Quick start:** SQLite (`apps/api/dev.db`, created automatically)
  - **Full stack:** Postgres via `docker-compose`  
    - Host: `localhost`
    - Port: `5432`
    - Default credentials (from `docker-compose.yml`):
      - `POSTGRES_USER=finai`
      - `POSTGRES_PASSWORD=finai`
      - `POSTGRES_DB=finai`

---

## 2. Prerequisites

### Common (Mac, Linux, Windows)

- **Git**
- **Python**: 3.11+  
  - Check: `python --version`
- **Node.js**: 18+ (20 recommended) with npm  
  - Check: `node --version`, `npm --version`
- **Docker Desktop** (recommended, for local Postgres)
- **Make** (optional, for Mac/Linux convenience)

### Windows-specific

- **PowerShell** (5+ is fine; 7+ recommended)
- Docker Desktop with WSL2 integration if you plan to run Postgres via `docker-compose`.

---

## 3. One-time Setup

You only need to do these steps once per machine.

### 3.1 Clone the repo

```bash
git clone <your-fork-or-origin-url> finai
cd finai
```

### 3.2 Environment files

#### Backend (`apps/api`)

```bash
cd apps/api
cp .env.example .env
cd ../..
```

By default, `.env` uses **SQLite**:

```env
DATABASE_URL=sqlite:///./dev.db
```

For **local Postgres** (docker-compose), edit `apps/api/.env`:

```env
DATABASE_URL=postgresql+psycopg2://finai:finai@localhost:5432/finai
```

Optionally, set your Twelve Data API key:

```env
TWELVE_DATA_API_KEY=your-twelvedata-api-key-here
```

CORS for local frontend is already set:

```env
BACKEND_CORS_ORIGINS=http://localhost:3000
```

#### Frontend (`apps/web`)

```bash
cd apps/web
cp .env.example .env.local
cd ../..
```

Defaults (good for local dev):

```env
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
NEXT_PUBLIC_WS_URL=ws://localhost:8000/ws/stream
```

#### (Optional) Root `.env`

There is a root `.env.example` summarising key variables. It’s **not read directly by the apps**; use it as a reference when editing `apps/api/.env` and `apps/web/.env.local`.

---

### 3.3 Install dependencies

#### Mac / Linux (Makefile-based)

From repo root:

```bash
make setup
```

This runs:

- Backend: `cd apps/api && python -m pip install --upgrade pip && pip install -r requirements.txt`
- Frontend: `cd apps/web && npm install`

If you don’t have `make`, run those commands manually.

#### Windows (PowerShell)

From repo root:

```powershell
.\scripts\setup.ps1
```

This does the same as `make setup` using PowerShell.

---

### 3.4 Database (optional Postgres)

You can **skip this section** and stay on SQLite (default) if you just want to try things quickly.  
For a more production-like setup, use Postgres via Docker.

#### Start Postgres (Docker)

Mac / Linux:

```bash
make db-up
```

Windows (PowerShell):

```powershell
.\scripts\db.ps1 -Action up
```

This uses `docker-compose.yml` to start a `db` container with:

- User: `finai`
- Password: `finai`
- DB: `finai`

Ensure `DATABASE_URL` in `apps/api/.env` matches:

```env
DATABASE_URL=postgresql+psycopg2://finai:finai@localhost:5432/finai
```

#### Apply migrations (for Postgres)

When using Postgres, run Alembic migrations once:

Mac / Linux:

```bash
make db-migrate
```

Windows (PowerShell):

```powershell
.\scripts\db.ps1 -Action migrate
```

If you stick with SQLite + `ENV=local`, the backend will auto-create tables on startup, and you can skip migrations.

#### Seed data (currently no-op)

There is a `db-seed` target, but no seed script yet:

- Mac / Linux:

  ```bash
  make db-seed
  ```

- Windows:

  ```powershell
  .\scripts\db.ps1 -Action seed
  ```

It simply prints a message and exits.

---

## 4. Running the Stack

You generally want **two terminals**: one for the backend, one for the frontend.

### 4.1 Using Make (Mac / Linux)

From repo root:

- Backend (FastAPI):

  ```bash
  make api
  ```

  This runs `uvicorn app.main:app --reload --host 0.0.0.0 --port 8000` in `apps/api`.

- Frontend (Next.js):

  ```bash
  make web
  ```

  This runs `npm run dev` in `apps/web`.

There is also a helper:

```bash
make dev
```

It prints instructions to run `make api` and `make web` in two terminals (Make itself does not daemonize both).

### 4.2 Using PowerShell scripts (Windows)

From repo root:

#### Option A – Start both as background jobs

```powershell
.\scripts\dev.ps1
```

This:

- Starts backend in `apps/api` via `uvicorn app.main:app --reload ...`
- Starts frontend in `apps/web` via `npm run dev`
- Runs them as **background PowerShell jobs**

Manage jobs from the same PowerShell session:

```powershell
Get-Job                     # list jobs
Receive-Job -Id <Id>        # view logs
Stop-Job -Id <Id>           # stop a job
```

#### Option B – Two terminals

1. Terminal 1:

   ```powershell
   cd apps/api
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

2. Terminal 2:

   ```powershell
   cd apps/web
   npm run dev
   ```

---

## 5. Troubleshooting

### 5.1 CORS errors (browser console)

Symptoms:

- Browser devtools show `CORS policy` errors when calling the API.

Checks:

1. Confirm backend is running on `http://localhost:8000`.
2. Confirm frontend points to that URL:

   - `apps/web/.env.local`:

     ```env
     NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
     ```

3. Check backend CORS setting:

   - `apps/api/.env`:

     ```env
     BACKEND_CORS_ORIGINS=http://localhost:3000
     ```

4. If you access from a different origin/port, add it to `BACKEND_CORS_ORIGINS` as a comma-separated list:

   ```env
   BACKEND_CORS_ORIGINS=http://localhost:3000,https://your-frontend.vercel.app
   ```

Restart the backend after changing env variables.

---

### 5.2 WebSocket connection issues

Symptoms:

- UI shows “disconnected” or realtime prices don’t update.
- Browser console shows WebSocket errors.

Checks:

1. Confirm backend is running and `/ws/stream` is reachable:

   ```bash
   # Health check
   curl http://localhost:8000/health
   ```

2. Confirm frontend WebSocket URL:

   - `apps/web/.env.local`:

     ```env
     NEXT_PUBLIC_WS_URL=ws://localhost:8000/ws/stream
     ```

3. Note:
   - On some corporate networks or when tunneling, WebSocket traffic may be blocked.
   - The frontend `useRealtimePrices` hook falls back to REST polling via `/api/v1/quotes` when disconnected.

---

### 5.3 429 / rate-limit or provider errors

The backend uses:

- **Token-bucket rate limiting** per provider
- **In-memory TTL caching**
- **Exponential backoff + retries** on 429/5xx for Twelve Data, CoinGecko, and GDELT

If you still see many provider errors (e.g. in logs):

- Reduce polling intensity:

  - Increase `WEBSOCKET_STREAM_INTERVAL_SECONDS` in `apps/api/.env` (e.g., from `5` to `10` or `15`).
  - Increase `QUOTES_TTL_SECONDS` (e.g., from `10` to `20` or `30`).

- Keep watchlists small in local dev (e.g., 5–10 symbols).

The API will try to **serve stale cached data** when fresh data fails, marking quotes as `is_stale=true`.

---

### 5.4 Database connection errors

Common error messages:

- `psycopg2.OperationalError: could not connect to server`
- `connection refused`

Checklist:

1. If using Postgres:
   - Ensure Docker is running.
   - Check containers:

     ```bash
     docker ps
     ```

   - Start DB if needed:

     ```bash
     make db-up          # Mac/Linux
     # or
     .\scripts\db.ps1 -Action up  # Windows
     ```

   - Confirm `DATABASE_URL` in `apps/api/.env` matches the Docker configuration.

2. If using SQLite:
   - Ensure `DATABASE_URL=sqlite:///./dev.db` in `apps/api/.env`.
   - The file `dev.db` will be created automatically in `apps/api` when the app starts.

3. If you changed DB schema and things behave oddly:
   - For local-only development, you can delete `apps/api/dev.db` and let the app recreate it (SQLite).
   - For Postgres, rerun migrations:

     ```bash
     make db-migrate
     ```

---

## 6. Verification / Smoke Tests

After starting backend (`make api` / `uvicorn ...`) and frontend (`make web` / `npm run dev`):

### 6.1 Backend health

```bash
curl http://localhost:8000/health
```

Expected response (example):

```json
{
  "status": "ok",
  "message": "healthy",
  "timestamp": "2026-01-27T12:00:00Z"
}
```

### 6.2 API smoke

```bash
curl "http://localhost:8000/api/v1/quotes?symbols=AAPL&asset_type=stock"
```

You should get a JSON payload (may be an error if no API key; that’s fine – the app handles it gracefully).

### 6.3 Frontend

Open:

- `http://localhost:3000` – Home
- `http://localhost:3000/watchlist` – Watchlist
- `http://localhost:3000/portfolio` – Portfolio
- `http://localhost:3000/alerts` – Alerts

Try:

- Add a symbol (e.g., `AAPL`) to the watchlist.
- Confirm prices show up and tick updates appear over time (or via REST fallback).

### 6.4 Automated tests

Mac / Linux:

```bash
# From repo root
make test     # backend + frontend tests
make lint     # backend ruff + frontend ESLint + TS typecheck
```

Windows (PowerShell):

```powershell
# Backend tests
cd apps/api
pytest

# Frontend tests
cd ../web
npm run test
```

(You can also use `make` on WSL / Git Bash on Windows.)

---

## 7. Logs & Debugging

### 7.1 Backend logs

- Printed to stdout in **JSON-like** format (one line per request / event).
- Includes:
  - `ts`
  - `level`
  - `logger`
  - `message`
  - `request_id`
  - HTTP request metadata (path, method, status_code, duration)

View logs:

- Mac / Linux: in the terminal where you run `make api`.
- Windows:
  - If using `scripts/dev.ps1`, run:

    ```powershell
    Get-Job          # find backend job Id
    Receive-Job -Id <backendJobId>
    ```

### 7.2 Enabling DEBUG safely

In `apps/api/.env`:

```env
DEBUG=true
LOG_LEVEL=DEBUG
```

Then restart the backend (Ctrl+C and `make api` again). This will:

- Increase log verbosity.
- Help diagnose provider calls, alert scheduler behavior, etc.

For production / deployed environments, revert to:

```env
DEBUG=false
LOG_LEVEL=INFO
```

---

## 8. Cleanup

If you want to clean generated artifacts:

Mac / Linux:

```bash
make clean
```

This removes:

- Python `__pycache__` and `.pytest_cache`
- Frontend `.next` and `out` directories

Windows:

```powershell
# Remove frontend build artifacts
Remove-Item -Recurse -Force apps/web/.next, apps/web/out -ErrorAction SilentlyContinue

# Remove Python caches (PowerShell equivalent of make clean)
Get-ChildItem -Recurse -Directory -Filter "__pycache__" | Remove-Item -Recurse -Force
Get-ChildItem -Recurse -Directory -Filter ".pytest_cache" | Remove-Item -Recurse -Force
```

---

You now have a reproducible, fully local FinAI stack with:

- FastAPI backend
- Next.js frontend
- Optional Postgres via Docker
- Simple Make and PowerShell commands for common workflows.