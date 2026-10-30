.PHONY: setup lint test download download-volve audit stage extract-log dbt-build \
	dbt-compile rebuild quality

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

# Compiles the models without data (used in CI).
dbt-compile:
	mkdir -p data/warehouse
	uv run dbt compile $(DBT_ARGS)

# From data/raw/ to a tested warehouse: delete staging and the database, parse, build and test.
# Real-time logs are restaged for the wellbores already extracted with make extract-log.
rebuild:
	rm -rf data/staging
	rm -f data/warehouse/well_ops.duckdb data/warehouse/well_ops.duckdb.wal
	$(MAKE) stage
	$(MAKE) dbt-build

quality:
	uv run python scripts/quality.py
