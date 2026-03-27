.PHONY: install lint format test clean docker-build docker-run

# Installation
install:
	uv pip install -e ".[dev]"

# Linting and formatting
lint:
	uv run ruff check src tests
	uv run mypy src

format:
	uv run ruff format src tests
	uv run ruff check --fix src tests

# Testing
test:
	uv run pytest

test-cov:
	uv run pytest --cov=src --cov-report=xml --cov-report=term-missing

# Cleanup
clean:
	rm -rf .pytest_cache .ruff_cache .coverage .mypy_cache
	find . -type d -name "__pycache__" -exec rm -rf {} +

# Docker
docker-build:
	docker build -t query-engine:latest .

docker-run:
	docker run --rm -it --env-file .env query-engine:latest
