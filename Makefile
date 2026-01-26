.PHONY: api-dev api-test api-lint web-dev web-test web-lint ci

api-dev:
	cd apps/api &amp;&amp; uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

api-test:
	cd apps/api &amp;&amp; pytest

api-lint:
	cd apps/api &amp;&amp; ruff check . &amp;&amp; mypy app tests

web-dev:
	cd apps/web &amp;&amp; npm run dev

web-test:
	cd apps/web &amp;&amp; npm run test

web-lint:
	cd apps/web &amp;&amp; npm run lint

ci:
	@echo "Running backend and frontend checks..."
	cd apps/api &amp;&amp; ruff check . &amp;&amp; mypy app tests &amp;&amp; pytest
	cd apps/web &amp;&amp; npm run lint &amp;&amp; npm run typecheck &amp;&amp; npm run test