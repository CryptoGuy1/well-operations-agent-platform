import os
from pathlib import Path

import pytest
from pydantic import ValidationError

from well_ops.settings import Settings


@pytest.fixture(autouse=True)
def clean_env(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    for name in list(os.environ):
        if name.startswith("WELL_OPS_"):
            monkeypatch.delenv(name)
    monkeypatch.chdir(tmp_path)  # no .env file


def test_defaults() -> None:
    settings = Settings()

    assert settings.warehouse_path == Path("data/warehouse/well_ops.duckdb")
    assert settings.evaluation_mode is False
    assert settings.model is None
    with pytest.raises(ValueError, match="WELL_OPS_MODEL"):
        settings.require_model()


def test_environment_overrides(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("WELL_OPS_MODEL", "some-model")
    monkeypatch.setenv("WELL_OPS_TEMPERATURE", "0.2")
    monkeypatch.setenv("WELL_OPS_MAX_STEPS", "5")
    monkeypatch.setenv("WELL_OPS_EVALUATION_MODE", "true")

    settings = Settings()

    assert settings.require_model() == "some-model"
    assert (settings.temperature, settings.max_steps, settings.evaluation_mode) == (0.2, 5, True)


def test_env_file_is_read(tmp_path: Path) -> None:
    (tmp_path / ".env").write_text("WELL_OPS_TOOL_ROW_CAP=50\n", encoding="utf-8")

    assert Settings().tool_row_cap == 50


def test_rejects_out_of_range_values(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("WELL_OPS_MAX_STEPS", "0")
    with pytest.raises(ValidationError):
        Settings()
