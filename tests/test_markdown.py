import pytest

from well_ops.markdown import fill_report, table


def test_fill_report_replaces_only_marked_sections() -> None:
    template = "# Title\n\n<!-- audit:a -->\nold\n<!-- /audit:a -->\n\nhand text\n"

    filled = fill_report(template, {"a": "new"})

    assert filled == "# Title\n\n<!-- audit:a -->\nnew\n<!-- /audit:a -->\n\nhand text\n"
    assert fill_report(filled, {"a": "new"}) == filled


def test_fill_report_rejects_missing_or_unknown_sections() -> None:
    with pytest.raises(KeyError, match="no markers"):
        fill_report("text", {"a": "x"})
    with pytest.raises(KeyError, match="no audit section"):
        fill_report("<!-- audit:b -->\n<!-- /audit:b -->", {})


def test_fill_report_uses_the_given_prefix() -> None:
    other = "<!-- audit:a -->\n<!-- /audit:a -->\n"
    template = "<!-- quality:a -->\n<!-- /quality:a -->\n" + other

    filled = fill_report(template, {"a": "x"}, prefix="quality")

    assert filled == "<!-- quality:a -->\nx\n<!-- /quality:a -->\n" + other


def test_table_escapes_pipes() -> None:
    assert table(["a", "b"], [(1, "x|y")]) == "| a | b |\n|---|---|\n| 1 | x\\|y |"
