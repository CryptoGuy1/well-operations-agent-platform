# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.0-data-audit] - 2026-10-28

### Added

- Repository scaffold: Python package `well_ops` (src layout, uv, Python 3.12), Makefile,
  CI running ruff, mypy and pytest, licence and data attribution files, and ADR 0001.
- `make download`: fetches the CIRA pump dataset from Zenodo (MD5-verified) and four Sodir
  FactPages tables (header-checked) into `data/raw/`, and writes `data/manifest.json`.
- `make download-volve`: resumable copy of the Volve drilling reports, WITSML data, production
  data, well picks, perforations, EDM file and licence terms from Databricks into
  `data/raw/volve/`, recorded in `data/manifest.json`. See `docs/data/volve-access.md`.
- Manifest entries now include a `source` field.
- `make audit`: Phase 1 data audit (`well_ops.ingestion.audit`) computed from `data/raw/` and
  written into `docs/data/data-audit-report.md`.
- Sodir `field_production_gross_monthly` (sum wellbores) download, and a three-way monthly
  comparison of workbook, Sodir gross and Sodir net production in the data audit.
