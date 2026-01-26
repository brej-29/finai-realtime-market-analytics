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

Future decisions should be **added below with a timestamp**, never retroactively edited, to preserve historical reasoning.