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
    monkeypatch.setenv("WELL_OPS_EFFORT", "high")
    monkeypatch.setenv("WELL_OPS_MAX_STEPS", "5")
    monkeypatch.setenv("WELL_OPS_EVALUATION_MODE", "true")

    settings = Settings()

    assert settings.require_model() == "some-model"
    assert (settings.effort, settings.max_steps, settings.evaluation_mode) == ("high", 5, True)


def test_the_provider_key_is_secret(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "not-a-real-key")
    settings = Settings()
    assert settings.provider_api_key is not None
    assert "not-a-real-key" not in repr(settings) and "not-a-real-key" not in str(settings)
    assert settings.provider_api_key.get_secret_value() == "not-a-real-key"


def test_env_file_is_read(tmp_path: Path) -> None:
    (tmp_path / ".env").write_text("WELL_OPS_TOOL_ROW_CAP=50\n", encoding="utf-8")

    assert Settings().tool_row_cap == 50


def test_rejects_out_of_range_values(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("WELL_OPS_MAX_STEPS", "0")
    with pytest.raises(ValidationError):
        Settings()


def test_prices_are_set_together(monkeypatch: pytest.MonkeyPatch) -> None:
    assert Settings().price_input_per_mtok_usd is None
    monkeypatch.setenv("WELL_OPS_PRICE_INPUT_PER_MTOK_USD", "1.5")
    with pytest.raises(ValidationError, match="together"):
        Settings()
    monkeypatch.setenv("WELL_OPS_PRICE_OUTPUT_PER_MTOK_USD", "7.5")
    monkeypatch.setenv("WELL_OPS_PRICE_CHECKED_ON", "2020-01-01")
    assert Settings().price_output_per_mtok_usd == 7.5
