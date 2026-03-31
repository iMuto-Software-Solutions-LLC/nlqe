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
	rm -rf .pytest_cache .ruff_cache .coverage .mypy_cache dist
	find . -type d -name "__pycache__" -exec rm -rf {} +

# Docker
docker-build:
	docker build -t nlqe:latest .

# Release / Publish
build: clean
	uv build

publish-test: build
	uv publish --repository-url https://test.pypi.org/legacy/

publish: build
	uv publish
docker-run:
	docker run --rm -it --env-file .env nlqe:latest


# Usage: make bump-version VERSION=0.2.0
bump-version:
	@if [ -z "$(VERSION)" ]; then \
		echo "Error: VERSION is required. Usage: make bump-version VERSION=x.y.z"; \
		exit 1; \
	fi
	sed -i 's/^version = ".*"/version = "$(VERSION)"/' pyproject.toml
	sed -i 's/^__version__ = ".*"/__version__ = "$(VERSION)"/' src/nlqe/__init__.py
	git add pyproject.toml src/nlqe/__init__.py
	git commit -m "chore: bump version to v$(VERSION)"
	git tag -a "v$(VERSION)" -m "Release v$(VERSION)"
	@echo "Version bumped to $(VERSION) and tagged as v$(VERSION)."
	@echo "Run 'git push origin main --tags' to publish."
