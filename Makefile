.PHONY: setup lint test download audit

setup:
	uv sync

lint:
	uv run ruff check .
	uv run ruff format --check .
	uv run mypy

test:
	uv run pytest

download:
	uv run python scripts/download.py

audit:
	@echo "audit: not implemented yet (Phase 1, after download)" >&2
	@exit 1
