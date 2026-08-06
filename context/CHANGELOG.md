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

---

## 2026-07-12 – Phase 1: Finish & Ship (demo mode, asset-type fixes, deploy readiness)

**Scope:**

- **Demo data seeding**
  - New `app/db/seed.py`: idempotent seeder for a default watchlist (5 symbols), sample portfolio (5 holdings), and 3 alerts.
  - `SEED_DEMO_DATA` env flag seeds on startup when the DB is empty (needed on free tiers without shell access); also runnable via `python -m app.db.seed`, `make db-seed`, and `scripts/db.ps1 -Action seed`.

- **Bug fixes (backend)**
  - CoinGecko provider now maps ticker symbols to CoinGecko coin ids (`BTC` → `bitcoin`); previously all crypto quotes and history silently returned empty/404.
  - `GET /api/v1/portfolio/summary` degrades to cost basis when a market-data provider errors instead of returning `provider_error`.
  - New `GET /api/v1/watchlists/default` (get-or-create) so the frontend no longer creates a duplicate watchlist on every add.
  - Logging: third-party log records (uvicorn, apscheduler, httpx) no longer crash the JSON formatter with `KeyError: 'request_id'`.
  - mypy `python_version` bumped to 3.12 so modern numpy stubs (PEP 695 `type` statements) parse.

- **Bug fixes / features (frontend)**
  - Home page now renders the real portfolio summary (market value, unrealized P&L $ and %, allocation by asset class) instead of hardcoded `$0.00` placeholders.
  - Symbol detail page reads `?asset_type=` (stock|crypto) instead of hardcoding stock for history/news/AI insights; shows an asset-type badge; wrapped in Suspense for `useSearchParams`.
  - Watchlist page: uses the default-watchlist endpoint, adds a stock/crypto selector, links symbols to their detail pages, supports item removal, and streams mixed stock+crypto ticks.
  - Alerts page: asset-type selector and correct labels for RSI/MA-cross alert conditions.
  - `useRealtimePrices` re-sends the subscribe message when the symbol list changes after the socket is open (previously symbols loaded after connect were never subscribed).
  - Next.js upgraded 14.1.0 → 14.2.35 (security patches).

- **Docs**
  - README rewritten as a recruiter-facing overview: features, architecture, engineering highlights, honest limitations, roadmap (MCP + multi-agent research layer next).

---

## 2026-07-12 – Phase 2: AI Research Layer (MCP server + multi-agent research desk)

**Scope:**

- **Research tool layer**
  - New `app/services/research/tools.py`: `ResearchToolbox` wraps existing services (market data, GDELT news, indicators, ML forecast/anomaly detection) as six compact JSON-in/JSON-out tools (`get_quote`, `get_price_history`, `get_technical_indicators`, `get_news_sentiment`, `get_forecast`, `get_anomalies`). No new external data sources — same providers, same caching, same rate limits.

- **Multi-agent orchestrator**
  - New `app/services/research/agents.py`: three specialist agents (technical, news/sentiment, risk) run concurrently via `asyncio.gather`, each executing a manual Claude tool-use loop against a narrow tool subset; a fourth "lead analyst" call synthesizes their notes into a cited markdown brief.
  - Manual loop (not the Anthropic SDK's beta tool runner or a third-party framework) for full control over per-agent iteration caps, error isolation, and token accounting; one analyst failing degrades gracefully instead of failing the whole run.
  - Defaults to `claude-haiku-4-5` (`RESEARCH_MODEL` env var) — a full run costs roughly a cent; `claude-sonnet-5` is a drop-in upgrade for higher-quality synthesis.

- **Research API**
  - New `research_reports` table (Alembic `0003_research_reports`) persisting status, per-agent sections, tool calls, token usage, and the final report.
  - `POST /api/v1/research` starts a run as a background task and returns immediately (`202`, status `running`); `GET /api/v1/research/{id}` polls for the result; `GET /api/v1/research` lists recent runs.
  - Returns `503 research_disabled` when `ANTHROPIC_API_KEY` is unset (the rest of the app is unaffected) and `429 research_daily_limit` once `RESEARCH_DAILY_LIMIT` (default 25) runs have started that UTC day — a cost guard for a public demo deployment.

- **MCP server**
  - New `app/mcp_server.py`: exposes the same `ResearchToolbox`, plus a `get_portfolio_summary` tool, as an MCP server over stdio (`python -m app.mcp_server`) using the official `mcp` SDK. Connects to Claude Desktop, Claude Code, or any MCP client; config snippet documented in the module docstring and README.

- **Frontend**
  - New `/research` page: symbol + asset-type form, live status polling while a run is in progress, rendered markdown report, collapsible per-agent working notes with tool-call trace, and a history sidebar of past reports. Handles the disabled/rate-limited states with an inline banner instead of failing silently.
  - Added `react-markdown` + Tailwind prose-style rules (`.research-markdown` in `globals.css`) for report rendering.
  - New "Research" nav link in the header and sidebar.

- **Tests**
  - `apps/api/tests/test_research.py`: orchestrator unit tests against a scripted Anthropic stub (agent tool-use loop, per-agent failure isolation), full API flow test (start → poll → completed, with sections and token usage asserted), disabled/rate-limit/not-found error paths, and an MCP tool-registration smoke test.
  - All 32 backend tests, ruff, and mypy pass; frontend typecheck and lint pass.

- **Config**
  - New env vars: `ANTHROPIC_API_KEY`, `RESEARCH_MODEL` (default `claude-haiku-4-5`), `RESEARCH_DAILY_LIMIT` (default 25). Documented in `apps/api/.env.example`.
  - `requirements.txt`: added `anthropic` and `mcp`.

---

## 2026-07-13 – UI redesign + real Twelve Data integration fixes

**Scope:**

- **Design system**
  - New dependencies: `motion` (Framer Motion's successor), `sonner` (toasts), `vaul` (mobile nav drawer), `lucide-react` (icons, replacing emoji), `@radix-ui/react-tooltip`, `class-variance-authority`, `clsx`, `tailwind-merge`. Added `next/font` (Inter, self-hosted) and a `@/*` path alias.
  - New `components/ui/`: `Button`, `Card`, `Badge`, `Input`, `Select`, `Skeleton`, `Tooltip`, `EmptyState`, `StatCard`, `AnimatedNumber` (spring-animated counters), `PriceDelta` (up/down arrow + colored %).
  - New `components/charts/DonutChart.tsx`: hand-built animated SVG donut (replaces the Chart.js `AllocationPie`, now deleted) for portfolio/home allocation.
  - New `components/layout/NavLink.tsx` (shared-layout-animation active-tab pill) and `MobileNav.tsx` (Vaul drawer for small screens — nav links were previously always-visible in the header and crowded on mobile).
  - Extended `tailwind.config.ts` with a CSS-variable-backed color system (`background`, `surface`, `border`, `positive`/`negative`/`warning`, etc.), soft/elevated/glow shadows, and shimmer/pop-in keyframes.

- **Every page redesigned** (Home, Watchlist, Symbol detail, Portfolio, Alerts, Analytics, Research) on the shared design system: motion entrance/stagger animations, skeleton loading states, empty states, toast feedback on mutations (add/remove watchlist item, create alert, export PDF, research run), and icons throughout instead of emoji/plain text.
  - Portfolio page also gained a real functional improvement: holdings now show live market value and per-position P&L (previously only symbol/qty/avg-price with no live pricing).
  - Watchlist row add/remove now animates in/out (`AnimatePresence`) instead of an instant re-render.

- **Bug fixes found by testing with a real Twelve Data key** (previously only exercised via mocks, which shared the same wrong assumptions as the code):
  - **Quote parsing**: `TwelveDataProvider.get_quotes` read `payload["price"]`, but Twelve Data's `/quote` endpoint reports the live price under `close` — `price` only exists on their separate `/price` endpoint, which lacks `percent_change`. Every real stock quote was silently failing to parse ("Malformed Twelve Data quote") and falling back to stale/empty data.
  - **Invalid interval string**: our internal convention passes `interval="1d"` for daily bars, but Twelve Data's `/time_series` only accepts `"1day"` — `"1d"` returned a 400 on every call. `"1h"` coincidentally matched their format, which is why hourly history worked while daily history (used by `/ai/insights` and `/analytics/*`) never did. Fixed with a small translation map at the provider boundary; the rest of the app's `"1d"`/`"1h"` convention is unchanged.
  - **Nonsensical outputsize**: the bar-count-per-range map multiplied every range by a constant (96) meant for intraday bars, so a `"1mo"` daily-interval request asked for 2,880 *daily* bars instead of ~22 trading days. Replaced with a map keyed on `(interval, range)` pairs.
  - **429s not actually rate-limited**: `_request_with_backoff` retried up to 3× on a 429 without re-consulting the shared token bucket, so a single logical call could fire multiple real requests against a per-minute quota. 429 is now excluded from the retry set (fails fast to the stale-cache fallback instead); retrying a per-minute quota within a ~1-2s backoff window can't help anyway.
  - Lowered default/`.env.example` polling intervals (`PROVIDER_RATE_LIMIT_CAPACITY=8`, `WEBSOCKET_STREAM_INTERVAL_SECONDS=10`, `ALERTS_SCHEDULER_INTERVAL_SECONDS=120`) to match Twelve Data's actual free-tier cap (8 req/min, 800/day) instead of the previous, untested defaults (60 capacity, 5s/60s polling) which exceeded it once the realtime streamer, alert scheduler, and page loads ran concurrently.
  - Frontend: `Filler` plugin was never registered with Chart.js despite `fill: true` on the Analytics and Symbol-page line charts, so area fills were silently dropped (console warning only, no visual error) — registered on both.
  - All backend fixes are covered by the existing test suite (updated `test_providers.py` mock to match Twelve Data's real payload shape) — 32/32 backend tests, ruff, mypy, frontend typecheck/lint/vitest, and a production build all pass.

---

## 2026-07-13 – Groq fallback, cost-capped research budget, and design system v2

**Scope:**

- **Groq fallback provider for AI research**
  - New `app/services/research/pricing.py`: a small USD pricing table per model plus `estimate_cost_usd(model, input_tokens, output_tokens)`, used both to enforce the daily budget and to display cost transparently.
  - New `app/services/research/llm.py`: `GroqResearchClient`, a duck-typed adapter translating between Anthropic's Messages API shape (`system`/`tools`/`messages`, response `.content` blocks, `.stop_reason`, `.usage`) and Groq's OpenAI-compatible `chat.completions.create`. `agents.py`'s orchestration logic required zero changes — both clients satisfy the same `client.messages.create(...)` interface.
  - `research_reports` gained `provider` and `estimated_cost_usd` columns (Alembic `0004_research_provider_cost`).
  - Provider selection is cost-based, not just count-based: while today's estimated Anthropic spend is under `RESEARCH_DAILY_BUDGET_USD` (default `$0.20`), new runs use Anthropic (`claude-haiku-4-5`); once exhausted, they automatically use Groq (`llama-3.3-70b-versatile`) instead of failing. A second safety net retries the *entire* run on Groq if Anthropic is picked but totally unreachable mid-run (e.g. an outage) — required restructuring `_execute_research` to catch exceptions from `run_research()` itself, since `synthesize()` (unlike the per-agent-isolated `run_agent()`) has no error isolation and a fully-down client raises rather than returning an all-errored outcome.
  - New `GET /api/v1/research/budget` endpoint reports today's spend, remaining budget, and which provider the next run will use.
  - Tuned `agents.py` for cost efficiency without sacrificing research quality: added an efficiency instruction to each agent's system prompt (call at most 2 tools, don't repeat calls), capped `max_iterations` 6→3, and reduced `max_tokens` per call (agents 1500→600, synthesis 3000→1200). Verified against the real Anthropic API: a full 3-agent research run now costs ~$0.023, comfortably fitting 8-9 runs/day inside the $0.20 budget while still producing detailed, well-cited briefs.
  - New env vars: `GROQ_API_KEY`, `GROQ_RESEARCH_MODEL` (default `llama-3.3-70b-versatile`), `RESEARCH_DAILY_BUDGET_USD` (default `0.20`). `RESEARCH_DAILY_LIMIT` default raised 25→50 since it's now a secondary anti-abuse ceiling rather than the primary cost control.
  - `requirements.txt`: added `groq`.
  - Tests: 12 tests in `test_research.py` covering cost estimation, budget-exhaustion fallback to Groq, total-Anthropic-failure mid-run retry, and a detailed unit test of the Groq↔Anthropic translation layer (tool schema translation, tool-use round-trip). 37/37 backend tests, ruff, mypy all pass.

- **Frontend: provider + cost transparency**
  - `/research` page now shows a provider badge (Claude Haiku vs. Groq Llama, visually distinct) and the estimated cost alongside the token count on every completed report, plus a small animated daily-spend meter (fetches `GET /api/v1/research/budget`) showing spend vs. the $0.20 cap and which provider the next run will use.

- **Design system v2: fonts, color, motion**
  - New font pairing via `next/font`: Space Grotesk (`font-display`) for page headings, JetBrains Mono (`font-mono`) for all numeric/tabular displays — wired globally by overriding Tailwind's default `mono` family and adding a `.tabular-nums { font-family: ... }` rule, so every existing tabular-nums price/stat display picked up the mono treatment without per-file edits.
  - New `accent` (violet) color alongside `brand` (teal), a `.text-gradient-brand` utility (brand→accent gradient text) applied to the header wordmark and home page hero heading, and a `glow-accent` shadow token.
  - `Card` gained an opt-in `spotlight` prop: a mouse-tracked radial glow (CSS custom properties updated on `pointermove`) applied to `StatCard` and the completed research report card.
  - New `app/template.tsx` + `components/layout/PageTransition.tsx`: a subtle fade on every route change.
  - Primary `Button` gained a `.btn-shine` diagonal gradient sweep on hover.
  - Verified live in the browser (font-family/gradient computed styles, spotlight CSS-variable updates on simulated pointermove, button shine class, no console errors) rather than relying on typecheck/build alone.

---

## 2026-07-13 – Design-review polish pass (reduced motion, app-shell completeness)

**Scope:**

- **Design corrections from a structured design review** (impeccable / frontend-design / motion-principles pass, executed via orchestrated subagents):
  - Removed the gradient-text treatment from the header wordmark and home hero — gradient text is decorative rather than meaningful; both now render solid foreground with the display font carrying the emphasis.
  - Removed the shine-sweep hover effect from the primary button: motion on a product surface should convey state, not decorate the most frequently used control.
- **`prefers-reduced-motion` support (previously absent)**: a `MotionProvider` (`MotionConfig reducedMotion="user"`) now honors the OS accessibility setting for every motion/react animation app-wide, and a targeted CSS media query disables the raw keyframe effects (skeleton shimmer, spotlight glow) — no blanket animation kill.
- **App-shell professional completeness**: styled `error.tsx` (error boundary with "Try again" reset) and `not-found.tsx` (404) pages in the design system; an SVG favicon (`app/icon.svg`, brand-teal spark mark); rich metadata (title template `%s · FinAI`, description, OpenGraph/Twitter cards, theme color — `metadataBase` is a placeholder to update at deploy time); a skip-to-content link; `scope="col"` on all 15 data-table headers.
- Verified by a blind fresh-context reviewer against the diff (all criteria passed) plus a live browser check (404 renders, skip link present, no gradients, favicon served, zero console errors). Lint, typecheck, 4/4 vitest, and production build all pass.

---

## 2026-07-15 – Backtesting engine, full CRUD, cinema-dark shell + follow-up fixes

**Scope:**

- **Strategy backtesting engine** (`app/services/backtest/engine.py`, `POST /api/v1/backtest`): SMA-crossover and RSI mean-reversion strategies over real daily history, signals computed on close and executed at the next bar (no lookahead bias), long-only, no costs (documented). Returns total/buy-hold return, CAGR, Sharpe (√252-annualized), max drawdown, win rate (closed trades), trade count, and an equity curve normalized to 100 vs buy-and-hold. Daily ranges extended with `6mo`/`1y` on both Twelve Data (outputsize 130/260) and CoinGecko (days 180/365). Reuses the shared indicator helpers — no duplicated math. 12 new tests.
- **CRUD completeness**: `DELETE /api/v1/holdings/{id}` and `DELETE /api/v1/alerts/{id}` (+4 tests); Portfolio page gained an add-holding form and per-row removal, Alerts page gained per-row deletion — the demo is fully self-serve instead of seed-only.
- **Analytics: Strategy Backtest section** — form (symbol/asset type/strategy/range), metric tiles, Chart.js equity-curve chart (strategy vs buy & hold), error/empty states, educational disclaimer. Also gave the Analytics page the same max-width cap every other page already had.
- **Shell redesign ("Modern Dark Cinema", ui-ux-pro-max direction)**: fixed full-height glass sidebar flush to the viewport's left edge (removes the dead left gap of the old centered shell); sticky glass top bar; sidebar nav rows with animated active indicator; layered ambient background (three drifting aurora blobs + masked dot grid + film-grain noise — no more solid-color body) with drift disabled under reduced motion; glass cards with inner top highlight; gradient primary button; stat cards with gradient icon chips.
- **Follow-up fixes from user review**: top bar now carries route-aware page context (icon + label) and a global API-health chip polling `/health` every 60s (removed the duplicate pill from Home — the WebSocket "Live" pill stays, it's a different signal); new animated `BrandMark` (rotating conic teal→indigo→violet ring around a dark tile with a glowing gradient price-spark SVG) replacing the plain "F" tile; `DonutChart` legend rows rebuilt as dot + label + animated weight bar + value/pct so the allocation card no longer has a dead middle; new root `app/loading.tsx` branded skeleton so route changes give instant feedback (the remaining first-visit delay in dev is Next.js on-demand compilation; production builds don't have it).
- **Ops**: Neon Postgres provisioned by the user; `alembic upgrade head` applied migrations 0001–0004 and the demo seed ran against it — the API now runs on Postgres locally via `DATABASE_URL`.
- 50 backend tests + ruff + mypy, frontend lint/typecheck/vitest/build all pass.

---

## 2026-08-02 – Tier A: per-visitor workspaces, shared research cache, hermetic tests

**Scope:**

- **Per-visitor workspaces** (migration `0005_workspaces`): watchlists, holdings, and alerts carry a `workspace_id` resolved from a `finai_ws` cookie (uuid minted on first visit, demo data seeded into the new sandbox automatically). Before this, every visitor to a public deployment shared one mutable dataset — anyone could delete the demo for everyone else. Foreign rows 404 rather than leaking; CORS now allows credentials. Deliberately *not* auth: no login, no JWT, just sandbox partitioning. The alert scheduler stays global by design (it evaluates every workspace).
- **Shared research cache** — researching a symbol already researched within `RESEARCH_CACHE_DAYS` (default 4) returns the existing report (HTTP 200) instead of paying for a new LLM run, and a request for a symbol whose run is still in flight attaches to that run rather than duplicating it. Cache hits consume neither the daily budget nor the run counter. Expired reports are never deleted: they drop out of reuse and the recent list but remain retrievable by id. Implemented with no new tables or columns — it is a date-filtered query plus an early return. The UI labels a reused report with its generation date so nobody mistakes it for live analysis. Verified live: three requests for NVDA produced one run and $0.0245 of spend.
- **Two latent bugs found and fixed:**
  - `.gitignore` inherited a bare `lib/` from the standard Python template, which also matched `apps/web/lib`. `lib/utils.ts` — providing `cn`, `formatCurrency`, and `relativeTime` to nearly every component — had **never been committed**, so a fresh clone or a Vercel build would have failed on `Module not found: '@/lib/utils'`. Local builds passed only because the file existed on one machine. The rule is now anchored to `/lib/`.
  - The test suite imported the application engine and called `Base.metadata.drop_all()`, so pointing `DATABASE_URL` at a real database made `pytest` drop its tables — which is exactly what happened to the Neon database mid-session. Added `tests/conftest.py` forcing SQLite before the app imports settings; the suite is now hermetic and runs roughly 8× faster.
- **Cross-workspace leaks caught in blind review**: `/api/v1/analytics/portfolio` and the MCP `get_portfolio_summary` tool both queried holdings unscoped; the PDF report endpoint did too. All three now scope correctly (MCP, having no cookie, reads the shared `demo` workspace).
- **Frontend**: a single `lib/api.ts` replaced six copy-pasted `getApiBase` helpers and sends the sandbox cookie on every request.
- 55 backend tests + ruff + mypy, frontend lint/typecheck/vitest/build all pass.

---

## 2026-08-02 – Tier B: live agent streaming and honest model evaluation

**Scope:**

- **Live research streaming (SSE)** — `run_agent`/`run_research` gained an optional `on_event` callback (default `None`, so every existing caller and test is untouched) emitting `agent_started`, `tool_call`, `agent_completed`, and `synthesis_started`. An in-process queue per run feeds `GET /api/v1/research/{id}/stream` as Server-Sent Events with 15s heartbeats and `X-Accel-Buffering: no`. The research page replaces blind 3-second polling with a live activity feed: each analyst transitions idle → working → done, with its tool calls appearing as chips in real time. Polling is retained as a fallback because free-tier proxies do break SSE. Single-process only by design (marked in code); multi-worker deployment would need Redis pub/sub.
  - **Race fixed during live testing**: the queue was created inside the background task, so a client connecting immediately after the `202` found no queue and received a `done` event claiming the run had finished — leaving the UI stuck on "running" forever. The queue is now registered before the task is scheduled, and a missing queue on a still-running report emits an `error` event (triggering the polling fallback) rather than a false `done`.
- **Walk-forward forecast evaluation** — new `app/services/ml/forecast_eval.py` and `GET /api/v1/ai/forecast-accuracy`, plus a Model Scorecard section on Analytics. Computed on demand from history: no table, no migration, no scheduler job, and no cold-start empty state. Each fit trains only on bars up to its decision point; a test proves the absence of lookahead by mutating bars beyond the last evaluated target and asserting the metrics are unchanged. Reports MAE, RMSE, MAPE, directional accuracy, band coverage, and — the point of the exercise — skill against a naive "price stays flat" baseline.
  - **The honest result on real AAPL data: 36.2% directional accuracy, −7.9% skill versus the naive baseline, 24.1% band coverage.** The linear-regression forecast does not beat assuming the price stays put, and its ±RMSE band captures a quarter of outcomes rather than the ~68% a 1σ interval implies. The UI states this plainly instead of hiding it. Publishing a model's failure is more useful than implying success it does not have.
- Deferred: email/webhook notifications (needs an external account) and the portfolio-optimization pack.
- 62 backend tests + ruff + mypy, frontend lint/typecheck/vitest/build all pass. Verified live: a full AMD research run streamed all three analysts' tool calls and completed for $0.0228.