import hashlib
from pathlib import Path
from typing import Any

import pytest

from well_ops.ingestion.cira_pumps import ChecksumError, parse_record, verify_md5


def _record(names: list[str]) -> dict[str, Any]:
    return {
        "files": [
            {"key": n, "size": 1, "checksum": "md5:abc", "links": {"self": f"https://z/{n}"}}
            for n in names
        ]
    }


def test_parse_record_accepts_eight_csv_and_readme() -> None:
    names = [f"{i}.csv" for i in range(8)] + ["README.md"]

    files = parse_record(_record(names))

    assert len(files) == 9
    assert files[0].md5 == "abc"


def test_parse_record_rejects_changed_file_list() -> None:
    with pytest.raises(ValueError, match="changed"):
        parse_record(_record(["a.csv", "README.md"]))


def test_verify_md5(tmp_path: Path) -> None:
    path = tmp_path / "a.csv"
    path.write_bytes(b"data")

    verify_md5(path, hashlib.md5(b"data").hexdigest())
    with pytest.raises(ChecksumError):
        verify_md5(path, "0" * 32)
