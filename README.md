# finai-realtime-market-analytics

Production-style, portfolio-grade **Real-Time Stock &amp; Crypto Analytics Dashboard** built as a monorepo:

- **Backend:** FastAPI, SQLAlchemy, Alembic, WebSockets, APScheduler, lightweight ML
- **Frontend:** Next.js (App Router), TypeScript, Tailwind, Zustand, Chart.js
- **CI:** GitHub Actions (lint + typecheck + tests)
- **Deployment target:** Render (API + Postgres) and Vercel (web), free-tier friendly

This README focuses on **local development**, **testing**, and **deployment readiness**.

For high-level goals and architecture, see the `/context` folder:

- `context/GOAL.md`
- `context/ARCHITECTURE.md`
- `context/DATA_SOURCES.md`
- `context/DECISIONS.md`
- `context/COSINE_RULES.md`
- `context/CHANGELOG.md`

For detailed, copy-paste guides:

- `context/LOCAL_RUN.md` – how to run everything locally (Mac/Linux + Windows)
- `context/DEPLOY_FREE.md` – how to deploy on free tiers (Vercel + Render + Neon/Supabase)

---

## High-level architecture

```text
                +-----------------------------+
                |        Next.js (web)        |
                |   - Dashboard / Watchlist   |
                |   - Symbol detail (AI)      |
                |   - Portfolio / Analytics   |
                |   - Alerts + Notifications  |
                +---------------+-------------+
                                |
            HTTPS (REST JSON)   |   WebSocket (ticks + alerts)
                                v
                +-----------------------------+
                |          FastAPI API        |
                |  /quotes  /history  /news   |
                |  /portfolio  /analytics     |
                |  /alerts  /alerts/events   |
                |  /ai/insights  /reports    |
                +-----------------------------+
                  |       |            |
                  |       |            |
                  v       v            v
           +----------+  +-----------------+   +------------------------+
           | Postgres |  | Market Data APIs|   |   GDELT Doc 2.0 API    |
           |  (or SQLite)  |  TwelveData / CG |   | (news + headlines)     |
           +----------+  +-----------------+   +------------------------+

   - Background jobs:
     - RealtimeStreamer: polls providers, pushes ticks via WebSocket
     - AlertScheduler: APScheduler job evaluating alerts → DB + WebSocket
```

---

## Repo Structure

```text
apps/
  api/         # FastAPI backend
  web/         # Next.js frontend

context/       # Grounding docs for goals, architecture, decisions, rules
notebooks/     # EDA / modeling notebooks

.github/
  workflows/
    ci.yml     # Backend + frontend CI

docker-compose.yml  # Optional local Postgres + API
Makefile            # One-command scripts
README.md
```

---

## Backend – FastAPI (apps/api)

### Features

- REST API:
  - `GET /health`
  - Market data:
    - `GET /api/v1/quotes?symbols=...&asset_type=stock|crypto`
    - `GET /api/v1/history?symbol=...&asset_type=...&interval=...&range=...`
  - Watchlists:
    - `POST /api/v1/watchlists`
    - `GET /api/v1/watchlists/{id}`
    - `POST /api/v1/watchlists/{id}/items`
    - `DELETE /api/v1/watchlists/{id}/items/{item_id}`
  - Portfolio:
    - `POST /api/v1/holdings`
    - `GET /api/v1/holdings`
    - `GET /api/v1/portfolio/summary`
  - Alerts:
    - `POST /api/v1/alerts`
    - `GET /api/v1/alerts`
    - `GET /api/v1/alerts/events`
    - `POST /api/v1/alerts/{id}/test-evaluate` (price-only smoke test)
  - News & sentiment (GDELT, free tier):
    - `GET /api/v1/news?symbol=...&asset_type=stock|crypto`
      - Returns recent headlines, per-article sentiment score and explanation.
  - Analytics:
    - `GET /api/v1/analytics/portfolio` – volatility, max drawdown, Sharpe, daily series
    - `GET /api/v1/analytics/benchmark?symbol=SPY&asset_type=stock`
  - Reports:
    - `POST /api/v1/reports/portfolio.pdf` – simple portfolio PDF (holdings + summary)
  - AI / ML insights (lightweight, local training):
    - `GET /api/v1/ai/insights?symbol=...&asset_type=...`
      - Technical view (RSI / MACD state)
      - Short-horizon linear regression forecast (with naive interval)
      - IsolationForest-based anomaly flags on returns
      - Strong disclaimer that this is **not investment advice**
- WebSockets:
  - `GET /ws/stream`
  - Protocol:
    - Client → server: `{"type":"subscribe","symbols":["AAPL","MSFT"],"assetType":"stock"}`
    - Server → client:
      - Ticks: `{"type":"tick","symbol":"AAPL","assetType":"stock","price":..., ...}`
      - Alerts: `{"type":"alert","alertId":1,"symbol":"AAPL","message":"...","ts":"..."}`  
      - Heartbeats: `{"type":"heartbeat"}` periodically

### Tech stack

- Python 3.11+
- FastAPI
- SQLAlchemy + Alembic (Postgres in production, SQLite allowed locally)
- Pydantic v2 + pydantic-settings
- httpx for Twelve Data / CoinGecko / GDELT Doc API
- APScheduler for alert evaluation
- Lightweight ML: scikit-learn (LinearRegression, IsolationForest)
- pytest, pytest-asyncio
- ruff, mypy

### Environment variables

See `apps/api/.env.example`:

- `DATABASE_URL`
  - Local default: `sqlite:///./dev.db`
  - Production example: `postgresql+psycopg2://user:password@host:5432/dbname`
- `TWELVE_DATA_API_KEY`
- `TWELVE_DATA_BASE_URL` (default `https://api.twelvedata.com`)
- `COINGECKO_BASE_URL` (default `https://api.coingecko.com/api/v3`)
- `GDELT_BASE_URL` (default `https://api.gdeltproject.org/api/v2/doc/doc`)
- `NEWS_TTL_SECONDS` – cache TTL per symbol for news
- `QUOTES_TTL_SECONDS`, `HISTORY_TTL_SECONDS`
- `PROVIDER_RATE_LIMIT_CAPACITY`, `PROVIDER_RATE_LIMIT_REFILL_PER_SECOND`
- `WEBSOCKET_HEARTBEAT_INTERVAL_SECONDS`, `WEBSOCKET_STREAM_INTERVAL_SECONDS`
- `ALERTS_SCHEDULER_INTERVAL_SECONDS`, `ALERTS_MIN_EVENT_INTERVAL_SECONDS`
- `ALERTS_RSI_PERIOD`, `ALERTS_MA_SHORT_WINDOW`, `ALERTS_MA_LONG_WINDOW`

Copy `.env.example` to `.env` and adjust as needed.

### Local backend setup

```bash
cd apps/api

# Create a virtualenv and activate it (optional but recommended)
python -m venv .venv
source .venv/bin/activate  # on Windows: .venv\Scripts\activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt

# Run the API (hot reload)
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Then open:

- Docs: http://localhost:8000/docs
- Health: http://localhost:8000/health

### Backend tests &amp; quality checks

```bash
cd apps/api

# Run unit + API + WebSocket tests
pytest

# Lint
ruff check .

# Type check
mypy app tests
```

You can also use the root `Makefile`:

```bash
# From repo root
make api-test
make api-lint
```

---

## Frontend – Next.js (apps/web)

### Features (MVP)

Pages (App Router):

- `/` – Home:
  - Portfolio summary placeholders
  - Sample live tick + API health indicator
- `/watchlist`:
  - Simple watchlist table with add-symbol form
  - Real-time prices via WebSocket hook
- `/symbol/[symbol]`:
  - Candlestick chart with overlays (MA20 + Bollinger Bands)
  - Indicator explanation panels
- `/portfolio`:
  - Holdings table
  - Allocation pie chart (Chart.js)
- `/alerts`:
  - Create/list basic price alerts

State &amp; realtime:

- Zustand store for watchlist, holdings, alerts and server status
- `useRealtimePrices` hook:
  - Manages WebSocket lifecycle with auto-reconnect and backoff
  - Subscribes to desired symbols
  - Falls back to REST polling (`/api/v1/quotes`) when disconnected

### Environment variables

See `apps/web/.env.example`:

- `NEXT_PUBLIC_API_BASE_URL`
  - Example (local): `http://localhost:8000`
  - Example (Render backend): `https://your-api.onrender.com`
- `NEXT_PUBLIC_WS_URL`
  - Example (local): `ws://localhost:8000/ws/stream`
  - Example (Render backend): `wss://your-api.onrender.com/ws/stream`

Copy `.env.example` to `.env.local` and update values.

### Local frontend setup

```bash
cd apps/web

npm install
npm run dev
```

Then open: http://localhost:3000

The frontend expects the backend at `NEXT_PUBLIC_API_BASE_URL` (by default `http://localhost:8000`).

### Frontend tests &amp; quality checks

```bash
cd apps/web

# Lint
npm run lint

# Typecheck
npm run typecheck

# Tests (Vitest + RTL)
npm run test
```

Or from repo root:

```bash
make web-lint
make web-test
```

---

## Running everything with docker-compose (optional)

For a local Postgres + API stack:

```bash
# From repo root
docker-compose up --build
```

This starts:

- `db` – Postgres 15 on `localhost:5432`
- `api` – FastAPI on `localhost:8000`, connected to the Postgres container

You can still run the frontend with `npm run dev` in another terminal.

---

## CI

GitHub Actions workflow: `.github/workflows/ci.yml`

On every **push** and **pull request**:

- **Backend job**
  - Setup Python 3.11
  - Install `apps/api/requirements.txt`
  - Run:
    - `ruff check .`
    - `mypy app tests`
    - `pytest`
- **Frontend job**
  - Setup Node.js 20
  - `npm install`
  - `npm run lint`
  - `npm run typecheck`
  - `npm run test`

CI must remain green for PRs to be considered healthy.

---

## Deployment Readiness (Render + Vercel)

### Backend on Render

- Use `apps/api/Dockerfile` as the Render service source.
- Recommended environment:
  - `DATABASE_URL` pointing to a Render-managed free Postgres instance
  - `TWELVE_DATA_API_KEY` set as a secret
  - Other settings optional (see `.env.example`)

WebSockets:

- Render supports WebSockets on web services.
- On free tier:
  - Services may **sleep** when idle, which will close WebSocket connections.
  - Expect **cold starts** and reconnect logic to be important; the frontend hook already handles auto-reconnect and REST fallback.

### Frontend on Vercel

- Root for deployment: `apps/web`
- `next.config.mjs` enables standalone output.
- Configure environment variables in Vercel:
  - `NEXT_PUBLIC_API_BASE_URL` – Render backend URL
  - `NEXT_PUBLIC_WS_URL` – Render WebSocket URL (`wss://.../ws/stream`)

A minimal `vercel.json` is included in `apps/web/vercel.json` as a reference.

---

## Typed Contracts &amp; Future Work

The current MVP defines Pydantic schemas for:

- Quotes &amp; history
- Watchlists &amp; watchlist items
- Holdings &amp; portfolio summary
- Alerts &amp; alert evaluation

The Next.js app consumes these contracts through JSON responses. Future work can:

- Introduce shared TypeScript types generated from Pydantic models
- Add RSI/MACD computation and visualization
- Add news/sentiment (e.g. via GDELT)
- Implement scheduled alert evaluation and notifications

---

## PR Summary Template

When updating this repo, PRs should:

1. Update `context/CHANGELOG.md` with a new dated entry.
2. Optionally update `context/DECISIONS.md` and `context/ARCHITECTURE.md` if new patterns are introduced.
3. Ensure CI passes.

A suggested PR description template:

- **Features**
  - Short bullet list of endpoints, UI, or infra added/changed.
- **How to run**
  - Commands for backend, frontend, and any migrations.
- **Env vars**
  - Any new or changed environment variables and their purpose.

For details on guiding principles and constraints, see `context/COSINE_RULES.md`.