.PHONY: setup lint test download download-volve audit stage extract-log dbt-build \
	dbt-compile rebuild quality serve-ddr \
	serve-prod serve-sodir serve-rt runs-db replay review answer-key evaluate \
	console-data

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

# Copies the build's results and manifest beside the warehouse, so a later dbt compile (which
# rewrites warehouse/target/) cannot change what make console-data reads.
dbt-build:
	mkdir -p data/warehouse
	uv run dbt build $(DBT_ARGS); status=$$?; \
		cp warehouse/target/run_results.json data/warehouse/dbt_run_results.json; \
		cp warehouse/target/manifest.json data/warehouse/dbt_manifest.json; \
		exit $$status

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

# Connector MCP servers on stdio (ADR 0004).
serve-ddr:
	uv run python -m well_ops.connectors.drilling_reports

serve-prod:
	uv run python -m well_ops.connectors.production

serve-sodir:
	uv run python -m well_ops.connectors.sodir

serve-rt:
	uv run python -m well_ops.connectors.realtime

# Run logs (ADR 0004): the runs database, and one run replayed to data/runs/<id>.md.
runs-db:
	uv run python scripts/runs.py load

# make replay RUN=<run_id> [RECHECK=1]
replay:
	@test -n "$(RUN)" || { echo "usage: make replay RUN=<run_id> [RECHECK=1]"; exit 2; }
	uv run python scripts/runs.py replay "$(RUN)" $(if $(RECHECK),--recheck)

# Post-well review agent on one development wellbore: make review WELLBORE="15/9-F-11 T2"
review:
	@test -n "$(WELLBORE)" || { echo "usage: make review WELLBORE=<key or name>"; exit 2; }
	uv run python scripts/review.py --wellbore "$(WELLBORE)"

# Evaluation answer key (local, holds held-out facts; prints counts only).
answer-key:
	uv run python scripts/answer_key.py

# One evaluation release (evaluation/RULES.md): make evaluate RELEASE=r1
evaluate:
	@test -n "$(RELEASE)" || { echo "usage: make evaluate RELEASE=r<n>"; exit 2; }
	uv run python scripts/evaluate.py --release "$(RELEASE)"

# The console's data bundle (ADR 0005), exported locally and committed: console/public/data/.
console-data:
	uv run python scripts/console_data.py
