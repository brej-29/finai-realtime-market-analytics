# Key Decisions

This document captures **architectural and design decisions** that shape the project. It is intentionally high-level and append-only (do not rewrite history; add new decisions with dates).

---

## 2026-01-26 – Initial Architecture (Prompt 1)

### D1: Monorepo with `apps/api` and `apps/web`

**Options considered:**

- Separate repos for backend and frontend
- Single repo with nested `backend/` and `frontend/`
- **Monorepo** with `apps/api` and `apps/web`

**Decision:**

- Use a **monorepo** with `apps/api` (FastAPI) and `apps/web` (Next.js) plus shared tooling at the root.

**Rationale:**

- Simplifies CI and shared configs
- Easier to coordinate API and UI changes in a single PR
- Matches common modern patterns (e.g., Turborepo-style layout)

---

### D2: Backend Stack – FastAPI + SQLAlchemy + Alembic

**Options considered:**

- FastAPI + SQLAlchemy + Alembic
- FastAPI + SQLModel
- Django / DRF
- Flask + extensions

**Decision:**

- Use **FastAPI** for the API layer and **SQLAlchemy + Alembic** for persistence and migrations.

**Rationale:**

- FastAPI is well-suited for async I/O and WebSockets
- SQLAlchemy+Alembic is a well-known, flexible stack for relational DBs
- Easier for future contributors to reason about and extend

---

### D3: Provider Choice – Twelve Data (stocks) + CoinGecko (crypto)

**Options considered:**

- Twelve Data, Alpha Vantage, Yahoo Finance (unofficial) for stocks
- CoinGecko, CryptoCompare for crypto

**Decision:**

- Use **Twelve Data** for stock quotes and OHLC
- Use **CoinGecko** for crypto prices and market charts
- Avoid any paid providers

**Rationale:**

- Both have free tiers suitable for hobby / portfolio projects
- Well-documented APIs and broad community usage
- Clear separation between stock and crypto providers

---

### D4: Caching & Rate Limiting – In-Memory + Token Bucket

**Options considered:**

- No caching
- Redis from day one
- In-memory cache per instance, optionally replaceable later

**Decision:**

- Use an **in-memory TTL cache** and a **token-bucket rate limiter** per provider.
- Design APIs such that adding Redis later is straightforward.

**Rationale:**

- Keeps infrastructure minimal and free-tier friendly
- Satisfies rate-limit needs for early versions
- Easy to run locally without extra services

---

### D5: Real-Time Strategy – WebSockets + REST Fallback

**Options considered:**

- WebSockets only
- SSE (Server-Sent Events)
- REST-only (polling)
- Hybrid

**Decision:**

- Use WebSockets as the **primary** real-time channel.
- Provide **REST endpoints** as a fallback for:
  - Initial data load
  - Situations where WebSockets are unavailable or flaky

**Rationale:**

- WebSockets provide good UX for real-time ticks
- Some platforms (and corporate networks) may limit WebSockets, so a fallback is needed
- REST endpoints are also easier to test and integrate

---

### D6: Frontend Stack – Next.js + TS + Tailwind + Zustand

**Options considered:**

- Next.js vs. CRA vs. Vite + React
- TypeScript vs. JavaScript
- Tailwind vs. CSS-in-JS vs. CSS Modules
- Zustand vs. Redux Toolkit vs. React Query for global state

**Decision:**

- **Next.js (App Router)**, **TypeScript**, **Tailwind**, **Zustand**

**Rationale:**

- Next.js gives a strong default for routing, SSR/SSG, and deployment to Vercel
- TypeScript is important for typed contracts with the backend
- Tailwind accelerates building a clean, modern UI
- Zustand is simpler and more lightweight than Redux for this scale

---

### D7: Testing & CI

**Decision:**

- Backend:
  - pytest for unit + API + WebSocket tests
  - ruff + mypy for linting / static typing
- Frontend:
  - Vitest + React Testing Library for smoke tests
  - ESLint + TypeScript for static analysis
- CI:
  - GitHub Actions workflow running on every PR:
    - Backend: ruff, mypy, pytest
    - Frontend: lint, typecheck, vitest

**Rationale:**

- Good coverage across layers
- Lightweight, with fast feedback for PRs
- Infrastructure-free (GitHub-hosted runners only)

---

### D8: Deployment Targets – Render + Vercel (Free Tier)

**Decision:**

- Backend: design for deployment to **Render** web service:
  - Use `apps/api/Dockerfile`
  - Postgres via Render free-tier DB
- Frontend: design for deployment to **Vercel**:
  - `apps/web` as the project root
  - Environment variables for API base URL and WebSocket URL

**Rationale:**

- Both have generous free tiers
- Common choices in the developer community
- Easy to configure via environment variables

---

### D9: Context-First Approach

**Decision:**

- Use the `/context` folder as the **source of truth** for:
  - Goals
  - Architecture
  - Data sources
  - Decisions
  - Cosine-specific rules
  - Changelog

**Rationale:**

- Ensures future Cosine agents can quickly understand the constraints
- Reduces risk of architectural drift
- Supports append-only history of decisions

---

## 2026-01-27 – Alerts, News, and Lightweight AI (Prompt 2)

### D10: Scheduled Alert Evaluation + Event Table

**Decision:**

- Introduce an `alert_events` table to persist fired alerts (with `payload` + `status`).
- Use **APScheduler** in the backend to run an `AlertScheduler.evaluate_alerts` job on a configurable interval.
- Broadcast alert events over WebSocket as `{"type":"alert", ...}` and expose them over REST at `GET /api/v1/alerts/events`.

**Rationale:**

- Avoids evaluating alert conditions in request/response flows (keeps endpoints responsive).
- Makes alert history auditable and queryable from the UI (notification centre).
- WebSocket broadcasts give real-time UX without polling while REST remains available for pull-based views.

### D11: Technical Alert Types (RSI / MA Cross)

**Decision:**

- Extend `AlertDirection` with:
  - `rsi_above`, `rsi_below`, `ma_cross`
- Implement lightweight indicator helpers (`compute_simple_rsi`, `moving_average`) instead of adding heavy dependencies.

**Rationale:**

- Keeps evaluation logic simple and CPU-friendly for free-tier deployments.
- Still gives users more expressive, educational alert types beyond raw price levels.

### D12: News & Sentiment via GDELT + VADER

**Decision:**

- Use **GDELT Doc 2.0 API** as the news source (no key, free, global coverage).
- Restrict to English-language headlines and compute sentiment using **VADER**.
- Cache responses per `(symbol, asset_type)` with a configurable TTL.

**Rationale:**

- Stays within free-tier constraints without introducing paid providers.
- VADER is lightweight and well-suited to short texts like headlines.
- Caching avoids overusing the free Doc API and keeps UIs snappy.

### D13: Lightweight AI / ML for Insights (No Heavy Infra)

**Decision:**

- Implement simple, in-process models:
  - Linear regression on lag features for short-horizon forecasts.
  - IsolationForest on returns/volume for anomaly flags.
- Expose them via `GET /api/v1/ai/insights` with strong disclaimers that results are **not investment advice**.

**Rationale:**

- Keeps the stack easy to run on local machines and free-tier containers (no external ML services).
- Demonstrates ML-backed insights without overpromising model sophistication.
- Aligns with educational goals of the project.

### D14: Portfolio Analytics & Reports

**Decision:**

- Add `/api/v1/analytics/portfolio` and `/api/v1/analytics/benchmark` for:
  - Volatility, max drawdown, and Sharpe ratio.
  - Daily return series for charts.
- Add `/api/v1/reports/portfolio.pdf` using ReportLab for a small, exportable PDF.

**Rationale:**

- Gives users a portfolio-level view (risk and performance) beyond single-ticker charts.
- PDF export supports “presentation ready” artifacts while staying lightweight and server-side only.

---

## 2026-07-12 – Multi-Agent Research Desk + MCP Server (Phase 2)

### D15: Manual Tool-Use Loop over Anthropic SDK Agent/Runner Helpers

**Options considered:**

- Anthropic SDK's beta tool runner (`client.beta.messages.tool_runner`)
- A hand-rolled manual agentic loop (`client.messages.create` + explicit `tool_use` handling)
- A third-party agent framework (LangChain, CrewAI, etc.)

**Decision:**

- Implement a small manual tool-use loop (`app/services/research/agents.py: run_agent`) instead of a framework or the beta runner.

**Rationale:**

- The loop is ~40 lines and fully visible — no framework abstraction to explain in an interview.
- Full control over per-agent max iterations, error isolation (one analyst failing must not sink the run), and token accounting.
- Avoids a beta-only SDK surface and a third-party dependency for a three-tool, few-iteration workflow.

### D16: Three Parallel Specialist Agents + One Synthesis Call

**Decision:**

- Run a technical analyst, a news/sentiment analyst, and a risk analyst concurrently (`asyncio.gather`), each with its own system prompt and a narrow tool subset.
- Merge their notes with a final synthesis call into a single cited markdown brief.

**Rationale:**

- Narrow per-agent tool sets keep each agent's context small and its behavior predictable (the technical analyst never fetches news, etc.).
- Running agents in parallel keeps wall-clock latency close to a single agent's, not 3x.
- A separate synthesis step forces explicit reconciliation of disagreeing analysts, which reads as a genuine "lead analyst" pass rather than string concatenation.

### D17: Tools Wrap Existing Services — No New Data Sources

**Decision:**

- `ResearchToolbox` (`app/services/research/tools.py`) wraps the platform's existing `MarketDataService`, `GDELTClient`, indicator functions, and ML models. No new external APIs were introduced for Phase 2.

**Rationale:**

- Keeps Phase 2 free-tier friendly — no new provider rate limits or costs beyond the LLM calls themselves.
- Guarantees the agents' claims are traceable to the same data the rest of the UI shows.
- The same toolbox backs both the research agents and the MCP server (D19), so behavior is identical across both surfaces.

### D18: Model Choice — Claude Haiku by Default, Cost Guards on the Demo

**Options considered:**

- Claude Sonnet/Opus for every agent (higher quality, higher cost)
- Claude Haiku for every agent (near-free, good enough for a scoped research task)
- Groq or another low-cost/free-tier LLM provider

**Decision:**

- Default `RESEARCH_MODEL` to `claude-haiku-4-5` (configurable via env var). Add a daily run cap (`RESEARCH_DAILY_LIMIT`, default 25) and disable the endpoint entirely (503) when `ANTHROPIC_API_KEY` is unset.

**Rationale:**

- A full 3-agent-plus-synthesis run on Haiku costs roughly a cent, which keeps a public demo affordable on a few dollars of credit.
- Anthropic's tool-use ergonomics (typed `tool_use`/`tool_result` blocks, mature SDK, MCP interoperability) outweigh chasing a nominally free provider for a demo-scale workload.
- The daily cap and the disabled-by-default state are the actual cost control for a public deployment — model choice alone isn't sufficient.

### D19: MCP Server as a Thin Wrapper, Not a Second Implementation

**Decision:**

- `app/mcp_server.py` uses the official `mcp` Python SDK (`FastMCP`) and calls `ResearchToolbox.execute` for every tool — no separate business logic.

**Rationale:**

- One code path for "what data can an agent see," reused by both the in-app research agents and any external MCP client (Claude Desktop, Claude Code).
- Demonstrates a real, working MCP integration without duplicating the service layer.

---

Future decisions should be **added below with a timestamp**, never retroactively edited, to preserve historical reasoning.