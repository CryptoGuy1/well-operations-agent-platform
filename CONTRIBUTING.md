# Contributing

## Setup

Install [uv](https://docs.astral.sh/uv/), then run `make setup`.

## Before opening a pull request

- `make lint` and `make test` pass.
- New modules have type hints and pass `mypy --strict`.
- Tests live under `tests/`, mirroring `src/well_ops/`.

## Commits

Use [Conventional Commits](https://www.conventionalcommits.org/) (`feat:`, `fix:`, `docs:`,
`chore:`, `test:`, `refactor:`). Keep commits small and focused.

## Data

Never commit raw or derived data, credentials or notebooks with outputs. Every data source keeps
its attribution in `NOTICE`.

## Evaluation

Evaluation rules are committed before any scored run. Do not tune on held-out wells. Any change
made after a scored run is disclosed in `evaluation/CHANGELOG.md`.

## Architecture decisions

Significant decisions are recorded as ADRs in `docs/adr/`. See
[ADR 0001](docs/adr/0001-record-architecture-decisions.md).
