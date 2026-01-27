# Project Goal

Build a **production-style, portfolio-grade Real-Time Stock & Crypto Analytics Dashboard** that can be deployed entirely on **free tiers** (Vercel for frontend, Render for backend, free Postgres).

This repo should serve as:

- A realistic reference implementation of a **full-stack real-time analytics product**
- A foundation that future Cosine tasks can extend safely
- A deployable app that an individual engineer can run and maintain with minimal cost

---

## High-Level Objectives

1. **Real-time market data**
   - Live quote streaming for stocks and crypto via WebSockets
   - Fallback to REST polling when WebSocket connectivity is limited
   - Free-tier friendly rate limiting and caching

2. **Core product features (MVP)**
   - **Watchlists** for stocks and crypto
   - **Symbol detail pages** with candlestick charts and technical indicators:
     - Moving Averages (MA)
     - Relative Strength Index (RSI)
     - MACD
     - Bollinger Bands
   - **Portfolio tracking** with P&L summary
   - **Alerts (MVP)** – store and evaluate basic price-above / price-below rules on demand

3. **Robust engineering**
   - Typed contracts between frontend and backend
   - Structured logging and global exception handling
   - Clean architecture with clear separation between:
     - API layer
     - Domain/services layer
     - Infrastructure (DB, providers, cache)
   - Automated tests and CI:
     - Backend: unit + API + WebSocket smoke tests
     - Frontend: component smoke tests + basic integration

4. **Deployment-ready (but not deployed here)**
   - Configs + docs for:
     - Render (FastAPI backend + Postgres)
     - Vercel (Next.js frontend)
   - Environment variable documentation
   - Dockerfile for backend, optional docker-compose for local dev

5. **Context-aware evolution**
   - `/context` folder acts as a **single source of truth** for:
     - Architecture
     - Data sources and rate limits
     - Design decisions and trade-offs
     - Rules for future Cosine work on this repo
   - `context/CHANGELOG.md` records each PR chunk at a high level

---

## Non-Goals (for now)

- No paid APIs, managed schedulers, or external queues
- No heavy workflow managers (e.g. Airflow); use lightweight schedulers instead
- No complex auth / user management (later extension)
- No high-frequency trading or order execution features

---

## Success Criteria

This project is successful if:

- A developer can:
  - Clone the repo
  - Follow the README
  - Run backend + frontend locally with minimal setup
- CI passes consistently (lint + typecheck + tests)
- The system can:
  - Serve basic real-time quotes via WebSockets
  - Persist and manage watchlists, holdings, and alerts
  - Provide responsive UI pages for:
    - Home (portfolio summary)
    - Watchlist
    - Symbol detail
    - Portfolio
    - Alerts
- Future Cosine tasks can extend the system by:
  - Reading `/context/*.md` to understand constraints and patterns
  - Updating the `CHANGELOG` and `DECISIONS` as they introduce new behavior