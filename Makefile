.PHONY: setup lint test download download-volve audit stage extract-log dbt-build

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

# Real-time logs for one wellbore, on demand (ADR 0002 D6): make extract-log WELLBORE=7078:T2
extract-log:
	@test -n "$(WELLBORE)" || { echo "usage: make extract-log WELLBORE=<key>"; exit 2; }
	uv run python scripts/extract_log.py --wellbore "$(WELLBORE)"

DBT_ARGS = --project-dir warehouse --profiles-dir warehouse

dbt-build:
	mkdir -p data/warehouse
	uv run dbt build $(DBT_ARGS)
