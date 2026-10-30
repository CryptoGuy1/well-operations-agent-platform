"""Runtime configuration from environment variables (prefix WELL_OPS_) and an optional .env file.

Model, temperature and step limits are configuration, never constants in agent code (ADR 0004).
The model has no default: it must be set before an agent runs.
"""

from __future__ import annotations

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="WELL_OPS_", env_file=".env", extra="ignore")

    # Data locations, relative to the repository root.
    warehouse_path: Path = Path("data/warehouse/well_ops.duckdb")
    runs_dir: Path = Path("data/runs")
    prompts_dir: Path = Path("prompts")
    splits_path: Path = Path("evaluation/splits.json")

    # Set only by the evaluation harness; lets connectors serve held-out wellbores.
    evaluation_mode: bool = False

    # Agent runtime.
    model: str | None = None
    temperature: float = Field(default=0.0, ge=0.0, le=1.0)
    max_tokens: int = Field(default=8192, ge=1)
    max_steps: int = Field(default=20, ge=1)

    # Connectors.
    tool_row_cap: int = Field(default=200, ge=1)
    redaction_denylist_path: Path | None = None  # personal names, kept outside the repository

    def require_model(self) -> str:
        """The configured model, or an error naming the variable to set."""
        if not self.model:
            raise ValueError("no model configured; set WELL_OPS_MODEL")
        return self.model
