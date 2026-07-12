.PHONY: \
	api-dev api-test api-lint \
	web-dev web-test web-lint \
	setup api web dev test lint fmt \
	db-up db-down db-migrate db-seed \
	clean ci

# --- Backend (FastAPI) ---

api-dev:
	cd apps/api &amp;&amp; uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

api-test:
	cd apps/api &amp;&amp; pytest

api-lint:
	cd apps/api &amp;&amp; ruff check . &amp;&amp; mypy app tests

# --- Frontend (Next.js) ---

web-dev:
	cd apps/web &amp;&amp; npm run dev

web-test:
	cd apps/web &amp;&amp; npm run test

web-lint:
	cd apps/web &amp;&amp; npm run lint

# --- Composite targets (DX) ---

setup:
	@echo "Installing backend dependencies..."
	cd apps/api &amp;&amp; python -m pip install --upgrade pip &amp;&amp; pip install -r requirements.txt
	@echo "Installing frontend dependencies..."
	cd apps/web &amp;&amp; npm install

api: api-dev

web: web-dev

dev:
	@echo "Run backend and frontend in separate terminals:"
	@echo "  Terminal 1: make api"
	@echo "  Terminal 2: make web"

test:
	@echo "Running backend tests..."
	cd apps/api &amp;&amp; pytest
	@echo "Running frontend tests..."
	cd apps/web &amp;&amp; npm run test

lint:
	@echo "Linting backend..."
	cd apps/api &amp;&amp; ruff check .
	@echo "Linting frontend..."
	cd apps/web &amp;&amp; npm run lint &amp;&amp; npm run typecheck

fmt:
	@echo "Formatting backend (ruff --fix)..."
	cd apps/api &amp;&amp; ruff check . --fix
	@echo "Formatting frontend (prettier)..."
	cd apps/web &amp;&amp; npx prettier --write .

# --- Database (local Postgres via docker-compose) ---

db-up:
	docker-compose up -d db

db-down:
	docker-compose stop db

db-migrate:
	cd apps/api &amp;&amp; alembic upgrade head

db-seed:
	cd apps/api && python -m app.db.seed

# --- Cleanup ---

clean:
	@echo "Removing Python and test caches..."
	find . -type d -name "__pycache__" -exec rm -rf {} + || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + || true
	@echo "Removing frontend build artifacts..."
	rm -rf apps/web/.next apps/web/out || true

# --- CI helper (kept for compatibility) ---

ci:
	@echo "Running backend and frontend checks..."
	cd apps/api &amp;&amp; ruff check . &amp;&amp; mypy app tests &amp;&amp; pytest
	cd apps/web &amp;&amp; npm run lint &amp;&amp; npm run typecheck &amp;&amp; npm run test