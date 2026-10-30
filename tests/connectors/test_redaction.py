from pathlib import Path

import pytest

from well_ops.connectors.redaction import REDACTED, Redactor

NAMES = ["Kari Nordmann", "xqzuser", "ola.testesen"]


@pytest.fixture
def redactor() -> Redactor:
    return Redactor(NAMES)


def test_email_ip_phone_and_name(redactor: Redactor) -> None:
    text = (
        "Called Kari Nordmann on +47 912 34 567 and mailed ola.testesen@example.org; "
        "server 192.0.2.10 and fe80::1 logged by XQZUSER."
    )

    result = redactor.redact(text)

    assert result.text == (
        f"Called {REDACTED} on {REDACTED} and mailed {REDACTED}; "
        f"server {REDACTED} and {REDACTED} logged by {REDACTED}."
    )
    assert dict(result.counts) == {"name": 2, "phone": 1, "email": 1, "ip": 2}


@pytest.mark.parametrize(
    "text",
    [
        "Drilled 8 1/2in hole from 2577 m to 4562.1 m MD, ROP 25 m/hr.",
        'Ran 13 3/8" casing to 1365 m; tested BOP to 345 bar for 10 min.',
        "Circulated 14:00-16:00, then POOH from 3,450 m to 1,200 m.",
        "Mud weight 1.25 sg, +5 m/hr improvement, version 1.2.3 of software.",
        "Pumped 12.5 m3 at 2013-05-09; values 10.20.30 and 999.1.2.3.4.",
        "Set plug at 4562 m. Pressure 250+/-5 bar.",
    ],
)
def test_drilling_text_is_unchanged(redactor: Redactor, text: str) -> None:
    result = redactor.redact(text)

    assert result.text == text
    assert not result.counts


def test_phone_needs_a_label_or_international_prefix(redactor: Redactor) -> None:
    assert redactor.redact("tel: 912 34 567").text == f"tel: {REDACTED}"
    assert redactor.redact("Phone 51 99 00 00").text == f"Phone {REDACTED}"
    assert redactor.redact("depth 912 34 567").text == "depth 912 34 567"


def test_names_match_whole_tokens_ignoring_case(redactor: Redactor) -> None:
    assert redactor.redact("xqzusers and axqzuser stay").text == "xqzusers and axqzuser stay"
    assert redactor.redact("by Xqzuser.").text == f"by {REDACTED}."


def test_invalid_ip_is_kept(redactor: Redactor) -> None:
    assert redactor.redact("value 300.1.2.3").text == "value 300.1.2.3"


def test_redact_tree_walks_values_not_keys(redactor: Redactor) -> None:
    tree = {"comments": ["by xqzuser", "ok"], "xqzuser": 3, "nested": {"note": "192.0.2.1"}}

    redacted, counts = redactor.redact_tree(tree)

    assert redacted == {
        "comments": [f"by {REDACTED}", "ok"],
        "xqzuser": 3,
        "nested": {"note": REDACTED},
    }
    assert dict(counts) == {"name": 1, "ip": 1}


def test_from_file_fails_closed(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError, match="make stage"):
        Redactor.from_file(tmp_path / "missing.txt")
    path = tmp_path / "list.txt"
    path.write_text("xqzuser\n\n", encoding="utf-8")

    assert Redactor.from_file(path).redact("xqzuser").text == REDACTED


def test_empty_denylist_still_redacts_patterns() -> None:
    assert Redactor().redact("a@b.example").text == REDACTED
