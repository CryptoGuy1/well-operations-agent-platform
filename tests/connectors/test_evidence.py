from datetime import date

import pytest

from well_ops.connectors.evidence import KINDS, EvidenceIdError, build, month, parse

EXAMPLES = {
    "ddr:report": {"report_file": "99_9_Z_1_2001_02_03.xml"},
    "ddr:activity": {"report_file": "99_9_Z_1_2001_02_03.xml", "activity_number": "7"},
    "ddr:hole-section": {"wellbore_key": "90001:T2", "section": "3"},
    "ddr:campaign": {"wellbore_key": "90001:T2", "campaign": "2"},
    "ddr:lost-time": {
        "section_id": "90001#before_first_section",
        "category": "interruption",
        "subcategory": "rig up/down",
    },
    "prod:daily": {"npdid": "90001", "day": "2001-02-03"},
    "prod:monthly": {"npdid": "90001", "month": "2001-02"},
    "prod:reconciliation": {"month": "2001-12"},
    "sodir:wellbore": {"npdid": "90001"},
    "sodir:field-net": {"field_npdid": "80001", "month": "2001-02"},
    "sodir:field-gross": {"field_npdid": "80001", "month": "2001-02"},
    "well:wellbore": {"wellbore_key": "90001:T2"},
    "rt:log": {"log_id": "90001:T2#1/16/1"},
    "rt:log-curve": {"log_curve_id": "90001:T2#1/16/1|DEPT|m"},
    "rt:log-value": {"log_id": "90001:T2#2/5/1", "index": "2001-02-03T04:05:06Z"},
    **{
        name: {"object_id": "Norway-Op-99_$47$_9-Z-1/1/rig/1.xml#uid 1"}
        for name in KINDS
        if name.startswith("witsml:")
    },
}


def test_every_kind_has_an_example() -> None:
    assert set(EXAMPLES) == set(KINDS)


@pytest.mark.parametrize("kind", sorted(KINDS))
def test_round_trip(kind: str) -> None:
    text = build(kind, **EXAMPLES[kind])

    parsed = parse(text)

    assert parsed.kind == kind
    assert parsed.values == EXAMPLES[kind]
    assert str(parsed) == text
    assert parsed.relation == KINDS[kind].relation


def test_documented_formats() -> None:
    assert build("ddr:activity", report_file="r.xml", activity_number=3) == "ddr:activity:r.xml#3"
    assert build("prod:monthly", npdid=90001, month=month(date(2001, 2, 1))) == (
        "prod:monthly:90001:2001-02"
    )
    assert build("prod:daily", npdid=90001, day=date(2001, 2, 3)) == "prod:daily:90001:2001-02-03"


@pytest.mark.parametrize(
    "text",
    [
        "",
        "ddr:activity",
        "nope:thing:1",
        "ddr:activity:r.xml",
        "ddr:activity:r.xml#x",
        "prod:monthly:90001:2001-13",
        "prod:daily:90001:2001-02-30",
        "well:wellbore:90001:X2",
        "ddr:lost-time:90001#1|Interruption -- repair",
        "rt:log-value:90001#1/1/1@",
    ],
)
def test_malformed_ids_are_rejected(text: str) -> None:
    with pytest.raises(EvidenceIdError):
        parse(text)


def test_build_checks_fields_and_values() -> None:
    with pytest.raises(EvidenceIdError):
        build("prod:monthly", npdid=90001)
    with pytest.raises(EvidenceIdError):
        build("prod:monthly", npdid="x", month="2001-02")
    with pytest.raises(EvidenceIdError):
        build("unknown:kind", x=1)


def test_errors_do_not_echo_the_id() -> None:
    with pytest.raises(EvidenceIdError) as error:
        parse("ddr:activity:secret-value")
    assert "secret-value" not in str(error.value)
