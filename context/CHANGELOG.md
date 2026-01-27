# Changelog (Append-Only)

This file tracks high-level changes to the repository. New entries should be **appended** to the bottom with the most recent date.

---

## 2026-01-26 – Prompt 1 Backend & Frontend Skeleton

**Scope:**

- Established monorepo structure:
  - `apps/api` – FastAPI backend
  - `apps/web` – Next.js frontend
  - `context/`, `notebooks/`, `.github/workflows/`
- Added context documents:
  - `GOAL.md`, `ARCHITECTURE.md`, `DATA_SOURCES.md`, `DECISIONS.md`, `COSINE_RULES.md`, `CHANGELOG.md`
- Implemented backend MVP structure:
  - Core FastAPI app with settings, logging, error handling
  - Database setup (SQLAlchemy + Alembic) targeting Postgres (SQLite allowed for dev/tests)
  - Service layer for market data providers, caching, rate limiting
  - Realtime module for WebSocket management and background streaming
  - API endpoints for health, quotes, history, watchlists, portfolio, alerts
  - Testing setup and sample tests (providers, cache, rate limiter, API, WebSocket)
- Implemented frontend MVP structure:
  - Next.js App Router + TypeScript + Tailwind CSS
  - Pages for Home, Watchlist, Portfolio, Alerts, Symbol detail (with charts)
  - Zustand store and realtime WebSocket hook with REST fallback
  - Testing setup via Vitest + React Testing Library (home page smoke test)
- Added CI workflow:
  - Backend: ruff, mypy, pytest
  - Frontend: lint, typecheck, unit tests
- Added deployment-related artifacts:
  - `apps/api/Dockerfile`
  - `.env.example` files
  - `docker-compose.yml` and `Makefile` for local development

Details of implementation are in the corresponding PR description and context documents.

---

## 2026-01-27 – Prompt 2 Alerts, News, Analytics, and AI Insights

**Scope:**

- **Alerting & notifications**
  - Extended `AlertDirection` with `rsi_above`, `rsi_below`, `ma_cross`.
  - Added `alert_events` table and SQLAlchemy model with JSON payload + status enum.
  - Implemented `AlertScheduler` using APScheduler:
    - Evaluates active alerts on a configurable interval.
    - Creates `alert_events` rows with contextual payload (price, RSI, MA values).
    - Broadcasts alert events over WebSocket as `{"type":"alert", ...}`.
  - Added `GET /api/v1/alerts/events` for recent alert history.
  - Frontend:
    - New `NotificationCenter` (bell icon) in layout with unread badge and list of recent alerts.

- **News & sentiment**
  - Introduced `GDELTClient` with in-memory caching and conservative request pattern.
  - Implemented `HeadlineSentimentAnalyzer` using VADER.
  - Added `NewsArticle` and `NewsResponse` schemas.
  - New endpoint: `GET /api/v1/news?symbol=...&asset_type=...`.
  - Frontend:
    - Symbol detail page now has a “News & Sentiment” panel with headlines, sentiment scores, and explanations.

- **Portfolio analytics & reports**
  - Added endpoints:
    - `GET /api/v1/analytics/portfolio`
    - `GET /api/v1/analytics/benchmark`
  - Metrics: volatility, max drawdown, Sharpe ratio, daily return series.
  - Implemented `POST /api/v1/reports/portfolio.pdf` using ReportLab for a lightweight portfolio PDF.
  - Frontend:
    - New `/analytics` page with:
      - Risk metric cards.
      - Portfolio vs benchmark line chart.
      - Drawdown chart.
      - “Export PDF” button wired to the report endpoint.

- **AI / ML insights**
  - Created small ML utilities:
    - Linear regression on lag features for short-horizon forecasts.
    - IsolationForest-based anomaly detection on returns + volume.
  - Added `ai` schemas and `GET /api/v1/ai/insights` endpoint:
    - Technical summary (RSI/MACD state and labels).
    - Forecast summary with direction and confidence.
    - Recent anomaly points.
    - Strong educational disclaimer.
  - Frontend:
    - Symbol detail page now shows an “AI Forecast” mini-chart and textual technical summary.

- **Notebook**
  - Added `notebooks/FinAI_EDA_and_Modeling.ipynb`:
    - Can use backend (`MODE="backend"`) or CSV fallback (`MODE="csv"`).
    - Demonstrates EDA, indicators, simple linear forecasting, permutation importance, and anomaly detection.

- **Infrastructure / misc**
  - Extended config (`AppSettings`) and `.env.example` for news and alert scheduler settings.
  - Updated data source and decision docs for GDELT, alerts, and AI choices.
  - Added tests:
    - Alert scheduler end-to-end (creates events & broadcasts payloads).
    - GDELT client parsing and sentiment scoring.
    - Portfolio PDF report endpoint.
  - Kept all additions free-tier and CPU-friendly, with graceful degradation to cached or empty responses.

---

## 2026-01-27 – Prompt 3 Local DX & Free-Tier Deployment

**Scope:**

- **Developer experience & commands**
  - Extended root `Makefile` with:
    - `make setup` – install backend and frontend dependencies.
    - `make api` / `make web` – run backend and frontend dev servers.
    - `make dev` – documents two-terminal dev flow.
    - `make test` – backend + frontend tests.
    - `make lint` – backend ruff + frontend ESLint + TS typecheck.
    - `make fmt` – Python auto-fix via ruff and frontend formatting via Prettier.
    - `make db-up`, `make db-down` – manage local Postgres via `docker-compose`.
    - `make db-migrate` – run Alembic migrations.
    - `make db-seed` – placeholder seed target (no-op for now).
    - `make clean` – remove caches and frontend build artifacts.
  - Added Windows PowerShell helper scripts:
    - `scripts/setup.ps1` – mirrors `make setup`.
    - `scripts/dev.ps1` – starts backend and frontend as background jobs.
    - `scripts/db.ps1` – `-Action up|down|migrate|seed` for DB workflows.

- **Docs**
  - Added `context/LOCAL_RUN.md`:
    - End-to-end local run instructions (Mac/Linux + Windows).
    - Details on env files, Make targets, PowerShell scripts, troubleshooting, and smoke tests.
  - Added `context/DEPLOY_FREE.md`:
    - Free-tier deployment guide for:
      - Vercel (frontend, `apps/web`).
      - Render (backend, `apps/api`).
      - Neon (recommended) or Supabase (alternative) Postgres.
    - Environment variable reference and post-deploy validation checklist.
  - Updated `README.md` to link to `LOCAL_RUN` and `DEPLOY_FREE`.

- **Config & env hygiene**
  - Added root `.env.example` summarizing key backend and frontend env vars.
  - Updated `apps/api/.env.example`:
    - Documented Neon/Supabase-friendly `DATABASE_URL` usage.
    - Added `BACKEND_CORS_ORIGINS` for CORS configuration.
  - Updated `.gitignore` to ignore `*.db` files going forward.

- **Backend robustness**
  - Introduced CORS middleware in `app.main`:
    - Reads allowed origins from `BACKEND_CORS_ORIGINS`.
    - Defaults to allowing `http://localhost:3000`.
  - Implemented exponential backoff + retries for external providers:
    - Twelve Data and CoinGecko now retry on 429/5xx with bounded exponential backoff.
    - GDELT client uses similar retry logic, still degrading to an empty list on failure.
  - Fixed a bug in the GDELT client where headline sentiment scoring was not correctly bound to the class.
  - Kept existing rate limiting and caching behaviour, now aligned with the documented design in `DATA_SOURCES.md`.

- **Tests & cleanup**
  - Refactored `apps/api/tests/test_api_endpoints.py`:
    - Unified around a single `TestClient` fixture with a stubbed `MarketDataService`.
    - Ensures API tests do not hit real external providers.
    - Fixed a syntax/merge issue and clarified health/CRUD tests.
  - Ensured new commands and scripts used in docs correspond to real Make targets and PowerShell scripts.