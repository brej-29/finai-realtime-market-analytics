# FinAI — Real-Time Stock & Crypto Analytics

A production-style, full-stack **real-time market analytics platform**: live stock & crypto prices over WebSockets, portfolio tracking with P&L, technical indicators, news sentiment, scheduled alerts, and baseline ML forecasting — deployable entirely on free-tier infrastructure.

> **Live demo:** _coming soon (Vercel + Render + Neon)_ &nbsp;·&nbsp; **API docs:** `/docs` on the backend

<!-- TODO: hero screenshot / GIF of the dashboard after deployment -->

---

## What it does

| Feature | How it works |
| --- | --- |
| **Real-time prices** | Background streamer polls Twelve Data (stocks) & CoinGecko (crypto), pushes ticks to browsers over WebSockets; clients auto-reconnect with REST-polling fallback |
| **Watchlist** | Shared default watchlist for stocks + crypto, live-updating table |
| **Portfolio & P&L** | Holdings with cost basis, live market value, unrealized P&L, allocation by asset class |
| **Technical indicators** | MA20, Bollinger Bands, RSI, MACD — computed server-side and charted on candlesticks |
| **News & sentiment** | GDELT headlines per symbol scored with VADER, with word-level explanations |
| **Alerts** | APScheduler evaluates price / RSI / MA-cross rules on an interval; events persist to Postgres and broadcast over WebSocket to a notification center |
| **Baseline ML insights** | 7-day linear-regression forecast (lagged closes, ±RMSE band) and IsolationForest anomaly flags on returns — deliberately lightweight, clearly labeled as educational |
| **Analytics & reports** | Volatility, max drawdown, Sharpe ratio, benchmark comparison, one-click PDF export |
| **Demo mode** | `SEED_DEMO_DATA=true` seeds a populated watchlist, portfolio, and alerts on first boot, so a fresh deployment isn't an empty dashboard |

## Architecture

```text
                +-----------------------------+
                |     Next.js 14 (Vercel)     |
                |  Dashboard / Watchlist      |
                |  Symbol detail / Portfolio  |
                |  Alerts + Notifications     |
                +---------------+-------------+
                                |
            HTTPS (REST JSON)   |   WebSocket (ticks + alerts)
                                v
                +-----------------------------+
                |     FastAPI (Render)        |
                |  REST API  ·  /ws/stream    |
                |  RealtimeStreamer (poll->WS)|
                |  AlertScheduler (APScheduler)|
                |  Rate limiter · TTL cache   |
                +---+-----------+---------+---+
                    |           |         |
                    v           v         v
             +----------+  +----------------+  +----------------+
             | Postgres |  | Twelve Data /  |  |  GDELT Doc 2.0 |
             |  (Neon)  |  |   CoinGecko    |  | (news feed)    |
             +----------+  +----------------+  +----------------+
```

**Stack:** FastAPI · SQLAlchemy + Alembic · APScheduler · scikit-learn · Next.js 14 (App Router) · TypeScript · Tailwind · Zustand · lightweight-charts · Chart.js · GitHub Actions CI

## Engineering highlights

- **Free-tier-aware resilience:** token-bucket rate limiting toward providers, TTL caching, exponential-backoff retries, stale-cache fallback, and graceful degradation (portfolio summary falls back to cost basis when a provider is down).
- **Typed contracts end to end:** Pydantic v2 schemas on the API, mirrored TypeScript interfaces on the client.
- **Realtime done carefully:** WebSocket manager with heartbeats; client hook re-subscribes when the symbol set changes and falls back to REST polling when disconnected.
- **Operational hygiene:** structured JSON logging with request IDs, global exception handlers, Alembic migrations, Dockerized backend, CI running ruff + mypy + pytest and ESLint + tsc + Vitest on every push.

## Quickstart (local)

```bash
# Backend — http://localhost:8000 (docs at /docs)
cd apps/api
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env                                 # set SEED_DEMO_DATA=true for demo data
uvicorn app.main:app --reload --port 8000

# Frontend — http://localhost:3000
cd apps/web
npm install
cp .env.example .env.local
npm run dev
```

Works out of the box with SQLite and keyless CoinGecko crypto data. For live **stock** quotes, add a free [Twelve Data](https://twelvedata.com/) API key to `apps/api/.env`.

Detailed guides: [`context/LOCAL_RUN.md`](context/LOCAL_RUN.md) (incl. Windows scripts, docker-compose Postgres) and [`context/DEPLOY_FREE.md`](context/DEPLOY_FREE.md) (Vercel + Render + Neon walkthrough).

### Tests & checks

```bash
make test   # backend pytest + frontend vitest
make lint   # ruff + mypy + eslint + tsc
```

## Honest limitations (and what I'd do differently)

This is a portfolio project engineered for free-tier constraints; these are conscious trade-offs, not oversights:

- **Single-user by design.** No auth; watchlist, holdings, and alerts are global. Multi-tenancy is the first thing I'd add for real users (NextAuth + per-user rows).
- **In-memory cache and rate limiter** don't survive multiple workers or restarts. Fine for one free-tier dyno; production would use Redis (e.g. Upstash).
- **The ML is a baseline, not alpha.** A linear regression on 5 lagged daily closes with a naive ±RMSE band exists to demonstrate an end-to-end ML-serving path, not to predict markets — the UI says so. Next step is a proper agentic research layer (see roadmap).
- **Free provider limits are real.** Twelve Data free tier is 8 requests/min; the app degrades to cached/stale data rather than erroring, but bursts of symbols will show gaps.
- **WebSockets on free hosting sleep.** Render free instances idle out; the client's auto-reconnect + REST fallback masks most of it, but the first hit after idle is slow (~30s cold start).

## Roadmap

- **Phase 2 — AI research layer:** an MCP server exposing quotes/indicators/news/portfolio as tools, plus an orchestrated multi-agent research endpoint (parallel technical / sentiment / risk analysts → synthesized, cited brief).
- **Phase 3 — production polish:** agent tracing & cost observability, small eval suite for the research agent, Playwright E2E, Upstash Redis cache.

## Repo layout

```text
apps/api/    FastAPI backend (routes, services, ML, alembic, tests)
apps/web/    Next.js frontend (App Router pages, hooks, components, tests)
context/     Architecture, data sources, decisions, deployment guides
notebooks/   EDA / modeling notebook
```

Design decisions and their rationale live in [`context/DECISIONS.md`](context/DECISIONS.md); the changelog convention for PRs is described in [`context/CHANGELOG.md`](context/CHANGELOG.md).

## License

[MIT](LICENSE)
