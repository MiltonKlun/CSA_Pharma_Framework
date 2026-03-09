# CSA Validation Automation Framework — Makefile
# Common commands for development and validation

.PHONY: help install dev setup test validate lint clean

# Default target
help: ## Show this help message
	@echo "CSA Validation Automation Framework"
	@echo "===================================="
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-18s\033[0m %s\n", $$1, $$2}'

# ── Environment Setup ──────────────────────────────────────────

install: ## Install production dependencies
	pip install -e .

dev: ## Install all dependencies (production + dev)
	pip install -e ".[dev]"
	playwright install chromium

setup: dev ## Full environment setup (install + Playwright browsers)
	@echo "✅ Environment ready!"

# ── Testing ────────────────────────────────────────────────────

test: ## Run unit tests for framework modules
	pytest tests/ -v --tb=short

test-scripted: ## Run scripted tests for HIGH risk features (CSA Step 3a)
	pytest test_suites/scripted/ -v -m scripted --tb=long

test-unscripted: ## Launch exploratory testing logger (CSA Step 3b)
	python test_suites/unscripted/exploratory_logger.py

test-all: ## Run all automated tests
	pytest tests/ test_suites/scripted/ -v --tb=short

# ── CSA Validation Pipeline ───────────────────────────────────

validate: ## Run full CSA validation lifecycle
	@echo "🔬 CSA Validation Pipeline"
	@echo "========================="
	@echo ""
	@echo "Step 1: System Inventory (Intended Use)..."
	python -m system_inventory.inventory
	@echo ""
	@echo "Step 2: Risk Assessment (FMEA)..."
	python -m risk_engine.risk_assessor
	@echo ""
	@echo "Step 3: Assurance Activities..."
	pytest test_suites/scripted/ -v --alluredir=allure-results
	@echo ""
	@echo "Step 4: Evidence Capture & Report Generation..."
	python -m evidence_capture.audit_trail_collector
	python -m report_generator.generator
	@echo ""
	@echo "✅ Validation complete. Report: report_generator/outputs/"

# ── Demo App ───────────────────────────────────────────────────

app-up: ## Start the demo QMS app (Docker)
	cd demo_app && docker-compose up -d

app-down: ## Stop the demo QMS app
	cd demo_app && docker-compose down

app-logs: ## View demo app logs
	cd demo_app && docker-compose logs -f app

app-seed: ## Seed demo app with test data
	cd demo_app && python -m app.seed

# ── Code Quality ───────────────────────────────────────────────

lint: ## Run linter (ruff)
	ruff check .

lint-fix: ## Auto-fix lint issues
	ruff check --fix .

typecheck: ## Run type checker (mypy)
	mypy system_inventory/ risk_engine/ evidence_capture/ report_generator/

# ── Reports ────────────────────────────────────────────────────

report: ## Generate Validation Summary Report
	python -m report_generator.generator

allure: ## Serve Allure test report
	allure serve allure-results/

# ── Cleanup ────────────────────────────────────────────────────

clean: ## Remove generated files and caches
	rm -rf __pycache__ .pytest_cache .mypy_cache allure-results/
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	@echo "✅ Cleaned."
