.PHONY: help install install-dev test test-cov lint format type-check pre-commit clean build publish release

help: ## Show this help message
	@echo "Available commands:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

install: ## Install the package
	uv pip install -e .

install-dev: ## Install development dependencies
	uv pip install -e ".[dev]"

install-test: ## Install test dependencies
	uv pip install -e ".[test]"

test: ## Run tests
	uv run pytest

test-integration: ## Run integration tests
	uv run pytest tests/test_api_integration.py -v

test-cov: ## Run tests with coverage
	uv run pytest --cov=conversation_manager --cov=ohc --cov-report=html --cov-report=term-missing

update-fixtures: ## Update API test fixtures
	python scripts/update_fixtures.py

record-fixtures: ## Record API responses only
	python scripts/record_api_responses.py

sanitize-fixtures: ## Sanitize existing fixtures only
	python scripts/sanitize_fixtures.py

lint: ## Run linting
	uv run ruff check .

format: ## Format code
	uv run ruff format .

format-check: ## Check code formatting
	uv run ruff format --check .

type-check: ## Run type checking
	uv run mypy conversation_manager ohc

pre-commit-install: ## Install pre-commit hooks
	uv run pre-commit install
	uv run pre-commit install --hook-type commit-msg

pre-commit: ## Run pre-commit hooks on all files
	uv run pre-commit run --all-files

clean: ## Clean build artifacts
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/
	rm -rf .pytest_cache/
	rm -rf .coverage
	rm -rf htmlcov/
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

build: ## Build the package
	uv build

publish-test: ## Publish to test PyPI (placeholder)
	@echo "future state package publishing to test PyPI"

publish: ## Publish to PyPI (placeholder)
	@echo "future state package publishing to PyPI"

release: ## Create a new release
	uv run cz bump --changelog

dev-setup: install-dev pre-commit-install ## Complete development setup

ci: lint type-check test ## Run CI checks locally

all: clean install-dev pre-commit ci ## Run all checks
