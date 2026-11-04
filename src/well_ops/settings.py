"""Runtime configuration from environment variables (prefix WELL_OPS_) and an optional .env file.

Model, temperature and step limits are configuration, never constants in agent code (ADR 0004).
The model has no default: it must be set before an agent runs.
"""

from __future__ import annotations

import datetime as dt
from pathlib import Path
from typing import Self

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="WELL_OPS_", env_file=".env", extra="ignore")

    # Data locations, relative to the repository root.
    warehouse_path: Path = Path("data/warehouse/well_ops.duckdb")
    runs_dir: Path = Path("data/runs")
    runs_db_path: Path = Path("data/runs/runs.duckdb")  # built from the logs by `make runs-db`
    prompts_dir: Path = Path("prompts")
    splits_path: Path = Path("evaluation/splits.json")

    # Set only by the evaluation harness; lets connectors serve held-out wellbores.
    evaluation_mode: bool = False

    # Agent runtime.
    model: str | None = None
    temperature: float = Field(default=0.0, ge=0.0, le=1.0)
    max_tokens: int = Field(default=8192, ge=1)
    max_steps: int = Field(default=20, ge=1)

    # Model prices in USD per million tokens, from the provider's price list on price_checked_on.
    # No defaults: set all three or none. Without them, run cost stays unknown.
    price_input_per_mtok_usd: float | None = Field(default=None, ge=0)
    price_output_per_mtok_usd: float | None = Field(default=None, ge=0)
    price_checked_on: dt.date | None = None

    # Connectors.
    tool_row_cap: int = Field(default=200, ge=1)
    # Personal names, built by `make stage`; never committed or printed.
    redaction_denylist_path: Path = Path("data/private/redaction_denylist.txt")

    @model_validator(mode="after")
    def _prices_together(self) -> Self:
        prices = (
            self.price_input_per_mtok_usd,
            self.price_output_per_mtok_usd,
            self.price_checked_on,
        )
        if any(p is not None for p in prices) and any(p is None for p in prices):
            raise ValueError(
                "set WELL_OPS_PRICE_INPUT_PER_MTOK_USD, WELL_OPS_PRICE_OUTPUT_PER_MTOK_USD and "
                "WELL_OPS_PRICE_CHECKED_ON together, or none of them"
            )
        return self

    def require_model(self) -> str:
        """The configured model, or an error naming the variable to set."""
        if not self.model:
            raise ValueError("no model configured; set WELL_OPS_MODEL")
        return self.model
