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