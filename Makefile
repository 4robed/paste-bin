.PHONY: run dev install test test-v lint docker-build docker-up docker-down docker-prod clean

# ── Local dev ──────────────────────────────────────────────────────────────────

install:
	pip install -r requirements.txt
	pip install pytest pytest-cov httpx

run:
	uvicorn main:app --host 0.0.0.0 --port 8000

dev:
	uvicorn main:app --host 0.0.0.0 --port 8000 --reload

# ── Tests ──────────────────────────────────────────────────────────────────────

test:
	pytest tests/ -q --tb=short

test-v:
	pytest tests/ -v --tb=short --cov=. --cov-report=term-missing

test-cov:
	pytest tests/ --cov=. --cov-report=html
	@echo "Coverage report: htmlcov/index.html"

# ── Lint ───────────────────────────────────────────────────────────────────────

lint:
	@command -v ruff >/dev/null 2>&1 || pip install -q ruff
	ruff check .

fmt:
	@command -v ruff >/dev/null 2>&1 || pip install -q ruff
	ruff format .

# ── Docker ─────────────────────────────────────────────────────────────────────

docker-build:
	docker compose build

docker-up:
	docker compose up -d --build
	@echo "Running at http://localhost:8000"

docker-down:
	docker compose down

docker-logs:
	docker compose logs -f app

docker-prod:
	docker compose -f docker-compose.prod.yml up -d --build
	@echo "Running at http://localhost:80"

docker-prod-down:
	docker compose -f docker-compose.prod.yml down

# ── Cleanup ────────────────────────────────────────────────────────────────────

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -delete
	rm -f test_pastebin.db test_crud.db pastebin.db
	rm -rf htmlcov .coverage
