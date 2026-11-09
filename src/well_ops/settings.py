"""Runtime configuration from environment variables (prefix WELL_OPS_) and an optional .env file.

Model, effort, response cap and step limits are configuration, never constants in agent code
(ADR 0004). There is no temperature setting: the API version the SDK sends rejects sampling
parameters (ADR 0004 amendment of 2026-11-04).
The model has no default: it must be set before an agent runs.
"""

from __future__ import annotations

import datetime as dt
from pathlib import Path
from typing import Literal, Self

from pydantic import Field, SecretStr, model_validator
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
    # The model provider's API key, from the environment or .env; never logged or printed.
    provider_api_key: SecretStr | None = Field(default=None, validation_alias="ANTHROPIC_API_KEY")
    # Per model response, thinking included; responses are streamed, so a high cap is safe.
    max_tokens: int = Field(default=64000, ge=1)
    # Thinking depth (output_config.effort); sent only when set.
    effort: Literal["low", "medium", "high", "xhigh", "max"] | None = None
    max_steps: int = Field(default=20, ge=1)

    # Model prices in USD per million tokens, from the provider's price list on price_checked_on.
    # No defaults: set all three or none. Without them, run cost stays unknown.
    price_input_per_mtok_usd: float | None = Field(default=None, ge=0)
    price_output_per_mtok_usd: float | None = Field(default=None, ge=0)
    price_checked_on: dt.date | None = None
    # Prompt-cache writes and reads, if the provider lists them; a call that writes or reads the
    # cache without its price has unknown cost.
    price_cache_write_per_mtok_usd: float | None = Field(default=None, ge=0)
    price_cache_read_per_mtok_usd: float | None = Field(default=None, ge=0)
    # Two-tier pricing: a call whose prompt (input, cache-write and cache-read tokens) is above
    # the threshold has all its tokens priced at the above-threshold prices. Unset: one tier.
    price_tier_threshold_tokens: int | None = Field(default=None, ge=1)
    price_above_input_per_mtok_usd: float | None = Field(default=None, ge=0)
    price_above_output_per_mtok_usd: float | None = Field(default=None, ge=0)
    price_above_cache_write_per_mtok_usd: float | None = Field(default=None, ge=0)
    price_above_cache_read_per_mtok_usd: float | None = Field(default=None, ge=0)

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
        cache = (self.price_cache_write_per_mtok_usd, self.price_cache_read_per_mtok_usd)
        if any(p is not None for p in cache) and prices[0] is None:
            raise ValueError("cache prices need the input and output prices")
        above = (
            self.price_above_input_per_mtok_usd,
            self.price_above_output_per_mtok_usd,
            self.price_above_cache_write_per_mtok_usd,
            self.price_above_cache_read_per_mtok_usd,
        )
        if self.price_tier_threshold_tokens is not None and (
            prices[0] is None or above[0] is None or above[1] is None
        ):
            raise ValueError(
                "WELL_OPS_PRICE_TIER_THRESHOLD_TOKENS needs the input and output prices and "
                "WELL_OPS_PRICE_ABOVE_INPUT_PER_MTOK_USD and "
                "WELL_OPS_PRICE_ABOVE_OUTPUT_PER_MTOK_USD"
            )
        if any(p is not None for p in above) and self.price_tier_threshold_tokens is None:
            raise ValueError("above-threshold prices need WELL_OPS_PRICE_TIER_THRESHOLD_TOKENS")
        return self

    def require_model(self) -> str:
        """The configured model, or an error naming the variable to set."""
        if not self.model:
            raise ValueError("no model configured; set WELL_OPS_MODEL")
        return self.model
