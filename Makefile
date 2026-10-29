.PHONY: setup lint test download download-volve audit stage dbt-build

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
	uv run python scripts/audit.py

stage:
	uv run python scripts/stage.py

DBT_ARGS = --project-dir warehouse --profiles-dir warehouse

dbt-build:
	mkdir -p data/warehouse
	uv run dbt build $(DBT_ARGS)
