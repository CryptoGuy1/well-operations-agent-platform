import json
from pathlib import Path

import pytest

from well_ops.connectors.errors import ToolError
from well_ops.connectors.guard import HeldOutGuard, held_out_keys
from well_ops.settings import Settings


@pytest.fixture
def splits(tmp_path: Path) -> Path:
    path = tmp_path / "splits.json"
    path.write_text(
        json.dumps(
            {
                "held_out": [
                    {"key": "90001", "name": "99/9-Z-1"},
                    {"key": "90002:T2", "name": "99/9-Z-2 T2"},
                ],
                "development": [{"key": "90003", "name": "99/9-Z-3"}],
            }
        ),
        encoding="utf-8",
    )
    return path


def test_held_out_keys(splits: Path) -> None:
    assert held_out_keys(splits) == frozenset({"90001", "90002:T2"})


def test_held_out_key_is_refused_outside_evaluation_mode(splits: Path) -> None:
    guard = HeldOutGuard(held_out_keys(splits), evaluation_mode=False)

    with pytest.raises(ToolError) as first:
        guard.check("90001")
    with pytest.raises(ToolError) as second:
        guard.check("90002:T2")

    assert first.value.as_dict() == second.value.as_dict()
    assert first.value.error == "wellbore_not_available"
    assert "90001" not in str(first.value.as_dict())
    guard.check("90003")
    guard.check("90002")  # the parent of a held-out sidetrack is its own wellbore


def test_evaluation_mode_allows_held_out(splits: Path) -> None:
    guard = HeldOutGuard(held_out_keys(splits), evaluation_mode=True)

    guard.check("90001")
    assert guard.allows("90002:T2")


def test_visible_filters_rows_in_order(splits: Path) -> None:
    guard = HeldOutGuard(held_out_keys(splits), evaluation_mode=False)
    rows = [("90003", 1), ("90001", 2), ("90004", 3)]

    assert guard.visible(rows, key=lambda r: r[0]) == [("90003", 1), ("90004", 3)]


def test_from_settings_reads_the_flag(splits: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(splits.parent)  # no .env file
    monkeypatch.setenv("WELL_OPS_SPLITS_PATH", str(splits))
    monkeypatch.setenv("WELL_OPS_EVALUATION_MODE", "false")
    assert not HeldOutGuard.from_settings(Settings()).allows("90001")
    monkeypatch.setenv("WELL_OPS_EVALUATION_MODE", "true")
    assert HeldOutGuard.from_settings(Settings()).allows("90001")
