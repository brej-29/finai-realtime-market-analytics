# Architecture

This project is a **monorepo** with separate applications for the backend API and the web frontend, plus shared context and tooling.

---

## Repository Layout

```text
apps/
  api/         # FastAPI backend (Python)
  web/         # Next.js + TypeScript frontend

context/       # Grounding docs for architecture, decisions, rules
notebooks/     # Data / research notebooks (placeholder for now)
.github/
  workflows/   # CI configuration

docker-compose.yml  # Optional local dev orchestration
Makefile            # One-command scripts for common tasks
README.md           # Root documentation
LICENSE
```

---

## Backend (apps/api) – FastAPI

**Technology:**

- Python 3.11+
- FastAPI
- SQLAlchemy + Alembic
- Pydantic (v2) + pydantic-settings
- httpx for HTTP calls to external APIs
- pytest for tests
- ruff, mypy for linting & static analysis

**Structure (high level):**

```text
apps/api/
  app/
    main.py              # App factory, router registration, startup/shutdown
    core/
      config.py          # Settings via pydantic-settings (.env)
      logging.py         # Structured logging configuration
      errors.py          # Custom exception types + handlers
      deps.py            # Common FastAPI dependencies
    db/
      session.py         # Engine and Session factory
      base.py            # Declarative base
      models.py          # ORM models (watchlists, holdings, alerts)
    schemas/
      ...                # Pydantic models for API I/O
    services/
      market_data/
        base.py          # MarketDataProvider interface definition
        providers.py     # TwelveDataProvider, CoinGeckoProvider
        cache.py         # InMemoryCache with TTL
        rate_limiter.py  # Token-bucket-style rate limit guard
        service.py       # Aggregation, caching, provider orchestration
      realtime/
        manager.py       # WebSocket connection and subscription manager
        streamer.py      # Background polling + broadcasting
      research/
        tools.py         # ResearchToolbox: wraps market data/news/ML as agent tools
        agents.py        # Multi-agent orchestration (parallel analysts + synthesis)
    api/
      v1/
        routes/
          health.py
          quotes.py
          history.py
          watchlists.py
          portfolio.py
          alerts.py
          research.py    # Multi-agent research runs (POST/GET /api/v1/research)
          websocket.py   # /ws/stream endpoint
        router.py        # Versioned API router
    mcp_server.py         # FinAI MCP server (stdio) — exposes ResearchToolbox as MCP tools

  alembic/
    env.py               # Alembic env config
    versions/
      *.py               # Migration scripts

  requirements.txt
  pyproject.toml         # Tooling config (ruff, mypy, etc.)
  tests/
    ...                  # Unit, API, and WebSocket tests
```

**Key runtime responsibilities:**

- Expose REST endpoints for:
  - health, quotes, history
  - watchlists, holdings, alerts
- Expose WebSocket endpoint `/ws/stream` for real-time ticks
- Poll external providers (Twelve Data, CoinGecko) via background tasks
- Cache data in-process with TTL to protect rate limits
- Enforce simple per-provider rate limits
- Log every request with:
  - request_id
  - path, method, status_code
  - latency
- Protect secrets (API keys, DB URLs) via environment variables and `.env` files (not committed)

---

## AI Research Layer (apps/api) – Multi-Agent + MCP

**Technology:**

- `anthropic` Python SDK (Claude Messages API, manual tool-use loop)
- `mcp` Python SDK (`FastMCP`) for the standalone MCP server

**Design:**

- `ResearchToolbox` (`services/research/tools.py`) exposes the platform's market data, indicators, news sentiment, forecast, and anomaly detection as a small set of JSON-in/JSON-out tools. It is the single implementation shared by both consumers below.
- `services/research/agents.py` runs three specialist agents (technical, news/sentiment, risk) concurrently via `asyncio.gather`, each executing its own manual tool-use loop against a narrow tool subset, then merges their notes with one synthesis call into a cited markdown brief.
- `POST /api/v1/research` starts a run as a FastAPI background task and returns immediately with a `running` report; the frontend polls `GET /api/v1/research/{id}` until it's `completed` or `failed`. Reports (including per-agent notes, tool calls, and token usage) persist in the `research_reports` table.
- `app/mcp_server.py` runs the same `ResearchToolbox` as an MCP server over stdio, so any MCP client (Claude Desktop, Claude Code) can query live quotes, indicators, sentiment, and the demo portfolio directly.

**Cost & availability controls:**

- The endpoint returns `503 research_disabled` when `ANTHROPIC_API_KEY` is unset — the rest of the app works without it.
- `RESEARCH_DAILY_LIMIT` (default 25) caps runs per UTC day; exceeding it returns `429 research_daily_limit`.
- Defaults to `claude-haiku-4-5` (`RESEARCH_MODEL`), keeping a full run at roughly a cent.

---

## Frontend (apps/web) – Next.js

**Technology:**

- Next.js (App Router, React, TypeScript)
- Tailwind CSS
- Zustand for client-side state
- TradingView Lightweight Charts for candlesticks
- Chart.js (via react-chartjs-2) for simple charts
- Vitest + React Testing Library for tests
- ESLint + Prettier

**Structure (high level):**

```text
apps/web/
  app/
    layout.tsx           # Root layout
    page.tsx             # Home (portfolio summary, server status)
    watchlist/
      page.tsx
    portfolio/
      page.tsx
    alerts/
      page.tsx
    symbol/
      [symbol]/
        page.tsx         # Symbol detail

    globals.css          # Tailwind base styles

  components/
    layout/              # Shell, header, sidebar, etc.
    charts/              # Candlestick, overlays, allocation chart
    realtime/            # WebSocket status, connection banner, etc.
    shared/              # Buttons, cards, loading states, etc.

  hooks/
    useRealtimePrices.ts # WebSocket client + REST fallback

  store/
    useAppStore.ts       # Zustand store for watchlists, holdings, alerts

  tests/
    ...                  # Vitest + RTL tests

  package.json
  tsconfig.json
  next.config.mjs
  tailwind.config.ts
  postcss.config.mjs
  .eslintrc.cjs
  .prettierrc
```

**Key runtime responsibilities:**

- Consume REST endpoints for:
  - quotes, history, watchlists, holdings, alerts
- Maintain client-side state (watchlist, portfolio, alerts) via Zustand
- Connect to `/ws/stream`:
  - Auto-reconnect with backoff
  - Resubscribe to symbols on reconnect
  - Surface connection status in the UI
- Render charts and indicators:
  - Candlestick chart with overlays (MA, Bollinger)
  - Indicator panels (RSI, MACD)
  - Allocation chart for portfolio

---

## Data Flow Overview

1. **External Providers → Backend**

   - `MarketDataService` orchestrates calls to:
     - Twelve Data for stock quotes & OHLC history
     - CoinGecko for crypto prices & market charts
   - Responses are normalized into internal models
   - Results are cached in `InMemoryCache` with TTL
   - Rate limiting is enforced per provider via `RateLimitGuard`

2. **Backend → Clients (REST)**

   - REST endpoints use:
     - DB (Postgres) for persisted entities (watchlists, holdings, alerts)
     - Market data cache for latest quotes
   - Errors are wrapped by custom exceptions and exception handlers to return JSON with clear error codes.

3. **Backend → Clients (WebSockets)**

   - `WebSocketConnectionManager` (RealtimeManager) maintains:
     - Connected clients
     - Their symbol subscriptions (grouped by symbol + asset_type)
   - `RealtimeStreamer` loop:
     - Aggregates subscribed symbols
     - Fetches latest quotes from the market data service
     - Broadcasts tick messages to subscribers
     - Sends periodic heartbeat messages

4. **Clients (Frontend)**

   - Pages use:
     - Zustand store for app state
     - Reusable hooks for data fetching:
       - WebSocket hook for streaming
       - REST fallback for polling and initial loads
   - Charts and UI components are decoupled from data fetching:
     - They accept typed props for data
     - They can be reused across pages

---

## Environments & Deployment Targets

**Local:**

- Optional `docker-compose.yml` to run:
  - Postgres
  - API
- Makefile commands:
  - `make api-dev`, `make web-dev`, `make test`, etc.

**Render (Backend):**

- Deployable as a Render Web Service:
  - Uses `apps/api/Dockerfile`
  - Connects to a free-tier managed Postgres
  - WebSockets are supported but can be affected by free-tier sleep/idle behavior (see `DATA_SOURCES` and README).

**Vercel (Frontend):**

- Deployable as a Next.js app:
  - `apps/web` is the root for the deployment
  - Uses environment variables for API base URL and WS URL
  - Can be configured via `vercel.json` if necessary

---

## Cross-Cutting Concerns

- **Logging & Monitoring**
  - Structured JSON-style logs (suitable for hosted platforms)
  - Per-request logging via middleware
  - Provider call logs at INFO/DEBUG level with correlation IDs where possible

- **Error Handling**
  - Custom exception classes for:
    - Provider errors
    - Rate limit violations
    - Validation / domain errors
  - FastAPI exception handlers return:
    - Consistent error shape
    - Appropriate HTTP status codes

- **Testing & CI**
  - Backend:
    - Unit tests for services, cache, rate limiter, and alert evaluation
    - API tests (TestClient)
    - WebSocket smoke tests
  - Frontend:
    - Component smoke tests
    - Linting and type checking
  - GitHub Actions workflow runs on every PR

---

For more detail on data providers and rate limits, see:

- `context/DATA_SOURCES.md`
- `context/DECISIONS.md`