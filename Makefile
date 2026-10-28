.PHONY: setup lint test download download-volve audit

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

download-volve:
	uv run python scripts/download_volve.py

audit:
	@echo "audit: not implemented yet (Phase 1, after download)" >&2
	@exit 1
