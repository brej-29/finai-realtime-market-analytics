# Cosine Rules for This Repo

This document describes how **Cosine agents** must work with this repository.

The goal is to keep future tasks **aligned with the project’s architecture, constraints, and style**.

---

## 1. Always Read the Context First

Before making any changes, Cosine agents must:

1. Read:
   - `context/GOAL.md`
   - `context/ARCHITECTURE.md`
   - `context/DATA_SOURCES.md`
   - `context/DECISIONS.md`
2. Skim:
   - `context/CHANGELOG.md` (latest entries)
3. Check the root `README.md` for run/deploy instructions.

If a future change seems to contradict any of these documents, agents should:

- Prefer updating the **context documents first**, then implementing code changes.
- Add new entries rather than rewriting history.

---

## 2. Respect Free-Tier and Cost Constraints

All work must respect:

- **No paid APIs** unless explicitly approved and documented in `DECISIONS.md`.
- Design for:
  - **Render** (backend + Postgres) free tier
  - **Vercel** (frontend) free tier
- Assume:
  - Backends may **sleep** when idle
  - Cold starts may be frequent
  - WebSockets may be closed by platforms during idle periods

Agents must:

- Use caching and conservative polling intervals
- Batch external API calls where possible
- Avoid heavy background workloads or schedulers beyond a lightweight approach

---

## 3. Maintain Architecture Boundaries

Agents must keep the following boundaries clear:

- **Backend:**
  - API layer (FastAPI routes) should be thin.
  - Service layer (e.g., `services/market_data`, `services/realtime`) owns business logic.
  - DB layer (`db/models.py`, `db/session.py`) owns persistence concerns.
- **Frontend:**
  - UI components focus on display and user interaction.
  - Hooks and services handle data fetching and WebSocket connections.
  - Zustand store owns shared state.

When adding new features:

- Prefer **extending existing patterns** over introducing new ones.
- If a new pattern is justified, document it in:
  - `context/DECISIONS.md` (with rationale)
  - Update `context/ARCHITECTURE.md` if structure changes

---

## 4. Logging, Errors, and Observability

All backend changes must:

- Use the existing **structured logging** setup
- Avoid logging secrets:
  - API keys
  - DB credentials
  - Access tokens

Error handling:

- Prefer custom exceptions derived from the shared error types in `app/core/errors.py`
- Register FastAPI exception handlers for new error categories if needed
- Ensure error responses:
  - Are JSON
  - Have clear `code` and `message` fields
  - Use appropriate HTTP status codes

---

## 5. Testing and CI Discipline

Agents must:

- **Add or update tests** whenever behavior changes:
  - Backend: pytest tests for services, endpoints, and WebSockets
  - Frontend: Vitest tests for UI and hooks
- Ensure CI remains green:
  - Lint (ruff, ESLint)
  - Typecheck (mypy, TypeScript)
  - Tests (pytest, Vitest)

If tests are flaky or slow:

- Prefer identifying and fixing root causes.
- Only mark tests as skipped or xfailed with clear justification in comments and in `context/DECISIONS.md` if it’s long-term.

---

## 6. Updating Context

When making non-trivial changes, agents must:

1. **Update `context/CHANGELOG.md`**:
   - Append a new entry with date, PR/chunk identifier (if applicable), and a short summary of changes.
2. **Update `context/DECISIONS.md`**:
   - When a new architectural or product decision is made.
3. **Update `context/DATA_SOURCES.md`**:
   - When adding/changing data providers or endpoints.
4. **Update `context/ARCHITECTURE.md`**:
   - When structure or deployment assumptions change.

Changes to these documents should be treated like code changes:
- Reviewed mentally for consistency
- Kept concise and factual

---

## 7. Backwards Compatibility and Refactors

- Avoid large, breaking refactors unless explicitly requested.
- When refactoring:
  - Preserve existing public API contracts (REST endpoints, WebSocket payload shapes) unless a change is necessary and documented.
  - Use adapters or transitional shims temporarily, but:
    - Remove them once consumers are migrated
    - Record the transition in `context/CHANGELOG.md`

---

## 8. Security and Privacy

- Do not commit secrets:
  - Use `.env.example` files and environment variables.
- For logs and telemetry:
  - Avoid storing personally identifiable information (PII).
- If future authentication/authorization is added:
  - Document the model and rules in `context/DECISIONS.md` and `context/ARCHITECTURE.md`.

---

## 9. Style and Code Quality

Backend:

- Follow the patterns and configurations defined by:
  - `ruff` (code style)
  - `mypy` (type hints)
- Keep functions and modules small and focused.
- Prefer explicitness over magic.

Frontend:

- Follow ESLint and Prettier configs.
- Keep components presentational where possible; push logic to hooks/services/stores.
- Ensure TypeScript types are clear and not overly permissive (`any` should be rare and justified).

---

## 10. When in Doubt

If a future task introduces ambiguity, agents should:

1. Look for precedents in:
   - Existing code
   - Context documents
2. Choose the path that:
   - Best respects free-tier constraints
   - Preserves simplicity and composability
   - Minimizes surprises for future maintainers
3. Document the decision and rationale in:
   - `context/DECISIONS.md`
   - And the PR description

This document itself should be **extended, not rewritten**, as the project evolves.