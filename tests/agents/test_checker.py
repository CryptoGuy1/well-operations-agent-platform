"""Claim checker tests on the synthetic warehouse of conftest.py (fictional data)."""

from __future__ import annotations

from typing import Any

import pytest

from well_ops.agents.checker import Checker, ClaimResult, Verdict
from well_ops.agents.schema import Claim, Document

T2 = "9001:T2"
V, C, U, X = Verdict.VERIFIED, Verdict.CONTRADICTED, Verdict.UNSUPPORTED, Verdict.UNVERIFIABLE
UNITS = {"hours": "h", "depth_m": "m", "rate_m_per_h": "m/h", "hole_size_in": "in"}
UNITS |= {"volume_sm3": "Sm3", "days": "d", "percent": "%"}


def lost(section: int, code: str) -> str:
    return f"ddr:lost-time:{T2}#{section}|{code}"


def claim(type_: str, value: Any, evidence: list[str], **what: Any) -> Claim:
    return Claim.model_validate(
        {
            "id": "c1",
            "type": type_,
            "value": value,
            "unit": UNITS.get(type_),
            "evidence_ids": evidence,
            "what": what,
        }
    )


def check(checker: Checker, c: Claim) -> ClaimResult:
    return checker.check_claim(c)


SECTION2 = f"ddr:hole-section:{T2}#2"
WELL = {"wellbore": "XX/1-A-1 T2"}

CASES: list[tuple[str, Claim, Verdict, str]] = [
    # Drilling reports: correct, within tolerance, wrong.
    (
        "lost hours in a section",
        claim(
            "hours",
            3.5,
            [lost(2, "interruption -- repair")],
            metric="lost_hours",
            tier="primary",
            section=2,
            **WELL,
        ),
        V,
        "within_tolerance",
    ),
    (
        "lost hours of a wellbore, rounded within 0.25 h",
        claim(
            "hours",
            8.6,
            [lost(1, "interruption -- wait"), lost(2, "interruption -- repair")],
            metric="lost_hours",
            tier="primary",
            **WELL,
        ),
        V,
        "within_tolerance",
    ),
    (
        "lost hours of a wellbore, wrong",
        claim(
            "hours",
            9.0,
            [lost(1, "interruption -- wait")],
            metric="lost_hours",
            tier="primary",
            **WELL,
        ),
        C,
        "outside_tolerance",
    ),
    (
        "possible tier counted separately",
        claim(
            "count",
            1,
            [lost(2, "drilling -- ream")],
            metric="lost_time_activities",
            tier="possible",
            **WELL,
        ),
        V,
        "exact",
    ),
    (
        "hours of one code, any tier",
        claim(
            "hours",
            112.5,
            [lost(1, "drilling -- drill"), lost(2, "drilling -- drill")],
            metric="code_hours",
            code="drilling -- drill",
            **WELL,
        ),
        V,
        "within_tolerance",
    ),
    (
        "zero lost hours, citing the section",
        claim(
            "hours",
            0,
            [f"ddr:hole-section:{T2}#3"],
            metric="lost_hours",
            tier="primary",
            section=3,
            **WELL,
        ),
        V,
        "within_tolerance",
    ),
    (
        "rate within 2 %",
        claim(
            "rate_m_per_h",
            20.3,
            [SECTION2, lost(2, "drilling -- drill")],
            metric="section_drilling_rate",
            section=2,
            **WELL,
        ),
        V,
        "within_tolerance",
    ),
    (
        "rate outside 2 %",
        claim("rate_m_per_h", 21.0, [SECTION2], metric="section_drilling_rate", section=2, **WELL),
        C,
        "outside_tolerance",
    ),
    (
        "rate where the warehouse has none (no drilling hours)",
        claim(
            "rate_m_per_h",
            10.0,
            [f"ddr:hole-section:{T2}#3"],
            metric="section_drilling_rate",
            section=3,
            **WELL,
        ),
        C,
        "no_value",
    ),
    (
        "hole size",
        claim("hole_size_in", 12.25, [SECTION2], metric="section_hole_size", section=2, **WELL),
        V,
        "within_tolerance",
    ),
    (
        "depth within 1 m",
        claim("depth_m", 1000.8, [SECTION2], metric="section_start_md", section=2, **WELL),
        V,
        "within_tolerance",
    ),
    (
        "a section-1 depth citing section 2",
        claim("depth_m", 1000.0, [SECTION2], metric="section_end_md", section=1, **WELL),
        U,
        "evidence_not_for_claim",
    ),
    (
        "report depth on an operations day",
        claim("depth_m", 500.4, ["ddr:report:R1"], metric="report_md", date="2020-01-02", **WELL),
        V,
        "within_tolerance",
    ),
    (
        "deepest depth citing the deepest report",
        claim("depth_m", 1500, ["ddr:report:R2"], metric="deepest_md", **WELL),
        V,
        "within_tolerance",
    ),
    (
        "deepest depth citing a shallower report",
        claim("depth_m", 1500, ["ddr:report:R1"], metric="deepest_md", **WELL),
        U,
        "evidence_not_for_claim",
    ),
    (
        "first report date includes the flagged placeholder",
        claim("date", "1980-01-01", [f"well:wellbore:{T2}"], metric="first_report_date", **WELL),
        V,
        "exact",
    ),
    (
        "first unflagged report date",
        claim(
            "date",
            "2020-01-02",
            [f"well:wellbore:{T2}"],
            metric="first_unflagged_report_date",
            **WELL,
        ),
        V,
        "exact",
    ),
    (
        "wrong date",
        claim(
            "date",
            "2020-01-01",
            [f"well:wellbore:{T2}"],
            metric="first_unflagged_report_date",
            **WELL,
        ),
        C,
        "different",
    ),
    (
        "report count, exact",
        claim("count", 3, [f"well:wellbore:{T2}"], metric="report_count", **WELL),
        V,
        "exact",
    ),
    (
        "report count, off by one",
        claim("count", 2, [f"well:wellbore:{T2}"], metric="report_count", **WELL),
        C,
        "different",
    ),
    (
        "section start date, a local date",
        claim("date", "2020-01-02", [SECTION2], metric="section_start_date", section=2, **WELL),
        V,
        "exact",
    ),
    (
        "section end date, wrong day",
        claim("date", "2020-01-03", [SECTION2], metric="section_end_date", section=2, **WELL),
        C,
        "different",
    ),
    (
        "sidetrack completion date is the parent's Sodir date",
        claim("date", "2020-03-01", ["sodir:wellbore:9001"], metric="completion_date", **WELL),
        V,
        "exact",
    ),
    (
        "duration of cited activities",
        claim("hours", 5.5, ["ddr:activity:R1#1", "ddr:activity:R1#2"], metric="activity_duration"),
        V,
        "within_tolerance",
    ),
    (
        "activity code",
        claim("code", "drilling -- drill", ["ddr:activity:R1#2"], metric="activity_code", **WELL),
        V,
        "exact",
    ),
    (
        "wrong activity code",
        claim("code", "drilling -- drill", ["ddr:activity:R1#1"], metric="activity_code"),
        C,
        "different",
    ),
    (
        "exact quotation",
        claim("quote", "Waited on weather.", ["ddr:activity:R1#1"], metric="quote"),
        V,
        "exact",
    ),
    (
        "quotation not in the cited text",
        claim("quote", "Waited on fog.", ["ddr:activity:R1#1"], metric="quote"),
        C,
        "not_in_evidence",
    ),
    (
        "a redacted name is not in the evidence",
        claim("quote", "Alex Placeholder on deck", ["ddr:activity:R1#1"], metric="quote"),
        C,
        "not_in_evidence",
    ),
    # Casing, tvd, duration and lost-time share.
    (
        "casing set during a section",
        claim("depth_m", 1990, [SECTION2], metric="section_casing_shoe_md", section=2, **WELL),
        V,
        "within_tolerance",
    ),
    (
        "no casing set in a section",
        claim(
            "depth_m",
            1990,
            [f"ddr:hole-section:{T2}#3"],
            metric="section_casing_shoe_md",
            section=3,
            **WELL,
        ),
        C,
        "no_value",
    ),
    (
        "casing shoe at the start of a section",
        claim("depth_m", 990, [SECTION2], metric="section_start_casing_shoe_md", section=2, **WELL),
        V,
        "within_tolerance",
    ),
    (
        "tvd at the end of a section",
        claim("depth_m", 1900, [SECTION2], metric="section_end_tvd", section=2, **WELL),
        V,
        "within_tolerance",
    ),
    (
        "tvd on the deepest report",
        claim("depth_m", 1400, ["ddr:report:R2"], metric="deepest_tvd", **WELL),
        V,
        "within_tolerance",
    ),
    (
        "tvd on an operations day",
        claim("depth_m", 450, ["ddr:report:R1"], metric="report_tvd", date="2020-01-02", **WELL),
        C,
        "outside_tolerance",  # 400 m
    ),
    (
        "well duration in days, from the first unflagged report",
        claim("days", 2.0, [f"well:wellbore:{T2}"], metric="report_span_days", **WELL),
        V,
        "within_tolerance",
    ),
    (
        "active days: operations days with an unflagged report",
        claim("count", 2, [f"well:wellbore:{T2}"], metric="active_days", **WELL),
        V,
        "exact",
    ),
    (
        "campaign count",
        claim("count", 1, [f"ddr:campaign:{T2}#1"], metric="campaign_count", **WELL),
        V,
        "exact",
    ),
    (
        "campaign end date",
        claim(
            "date",
            "2020-01-03",
            [f"ddr:campaign:{T2}#1"],
            metric="campaign_end_date",
            campaign=1,
            **WELL,
        ),
        V,
        "exact",
    ),
    (
        "campaign span in days, wrong",
        claim("days", 3.0, [f"ddr:campaign:{T2}#1"], metric="campaign_days", campaign=1, **WELL),
        C,
        "outside_tolerance",
    ),
    (
        "campaign operation phase",
        claim(
            "code",
            "drilling",
            [f"ddr:campaign:{T2}#1"],
            metric="campaign_operation_phase",
            campaign=1,
            **WELL,
        ),
        V,
        "exact",
    ),
    (
        "a campaign that does not exist",
        claim(
            "count", 2, [f"ddr:campaign:{T2}#1"], metric="campaign_active_days", campaign=2, **WELL
        ),
        U,
        "campaign_not_found",
    ),
    (
        "total activity hours",
        claim("hours", 216, [f"well:wellbore:{T2}"], metric="total_activity_hours", **WELL),
        V,
        "within_tolerance",
    ),
    (
        "primary lost-time share of the wellbore",
        claim(
            "percent",
            3.94,
            [lost(1, "interruption -- wait"), lost(2, "interruption -- repair")],
            metric="lost_time_share",
            tier="primary",
            **WELL,
        ),
        V,
        "within_tolerance",
    ),
    (
        "primary lost-time share of a section, outside 0.1 percentage points",
        claim(
            "percent",
            5.0,
            [lost(2, "interruption -- repair")],
            metric="lost_time_share",
            tier="primary",
            section=2,
            **WELL,
        ),
        C,
        "outside_tolerance",  # 4.86 %
    ),
    (
        "activity date, a local date",
        claim(
            "date",
            "2020-01-02",
            ["ddr:activity:R1#1", "ddr:activity:R1#2"],
            metric="activity_date",
            **WELL,
        ),
        V,
        "exact",
    ),
    (
        "activity date stated as the UTC date",
        claim("date", "2020-01-01", ["ddr:activity:R1#1"], metric="activity_date"),
        C,
        "different",
    ),
    # Production, by attributed wellbore.
    (
        "attributed wellbore cites the published NPDID",
        claim(
            "volume_sm3",
            1000,
            ["prod:monthly:9004:2020-01"],
            metric="wellbore_volume",
            wellbore="XX/1-A-4 B",
            fluid="oil",
            month="2020-01",
        ),
        V,
        "within_tolerance",
    ),
    (
        "summed over months, stated to three significant figures",
        claim(
            "volume_sm3",
            3010,
            ["prod:monthly:9004:2020-01", "prod:monthly:9004:2020-02"],
            metric="wellbore_volume",
            wellbore="9005",
            fluid="oil",
            start="2020-01",
            end="2020-02",
        ),
        V,
        "within_tolerance",
    ),
    (
        "the published wellbore no longer holds the production",
        claim(
            "volume_sm3",
            1000,
            ["prod:monthly:9004:2020-01"],
            metric="wellbore_volume",
            wellbore="9004",
            fluid="oil",
            month="2020-01",
        ),
        C,
        "attributed_to_other_wellbore",
    ),
    (
        "an id built from the attributed key names no workbook row",
        claim(
            "volume_sm3",
            1000,
            ["prod:monthly:9005:2020-01"],
            metric="wellbore_volume",
            wellbore="9005",
            fluid="oil",
            month="2020-01",
        ),
        U,
        "unknown_evidence",
    ),
    (
        "field volume on the Sodir gross basis",
        claim(
            "volume_sm3",
            1510,
            ["sodir:field-gross:777:2020-01"],
            metric="field_volume",
            field="volve",
            fluid="oil",
            basis="sodir_gross",
            month="2020-01",
        ),
        V,
        "within_tolerance",
    ),
    (
        "field volume quoted on the wrong basis",
        claim(
            "volume_sm3",
            1510,
            ["prod:reconciliation:2020-01"],
            metric="field_volume",
            field="VOLVE",
            fluid="oil",
            basis="workbook",
            month="2020-01",
        ),
        C,
        "outside_tolerance",
    ),
    # Unsupported.
    (
        "no evidence",
        claim("hours", 3.5, [], metric="lost_hours", tier="primary", section=2, **WELL),
        U,
        "no_evidence",
    ),
    (
        "malformed evidence id",
        claim("hours", 3.5, ["not an id"], metric="lost_hours", tier="primary", **WELL),
        U,
        "malformed_evidence",
    ),
    (
        "unknown evidence id",
        claim("depth_m", 1500, ["ddr:report:R9"], metric="deepest_md", **WELL),
        U,
        "unknown_evidence",
    ),
    (
        "held-out wellbore",
        claim("depth_m", 900, ["ddr:report:RH"], metric="deepest_md", wellbore="XX/1-A-2"),
        U,
        "wellbore_not_available",
    ),
    (
        "citing a held-out wellbore's row",
        claim("hours", 1.0, ["ddr:activity:RH#1"], metric="activity_duration"),
        U,
        "wellbore_not_available",
    ),
    (
        "unknown wellbore",
        claim("depth_m", 1500, ["ddr:report:R2"], metric="deepest_md", wellbore="XX/9-Z-9"),
        U,
        "wellbore_not_found",
    ),
    (
        "real-time value ids name no single row",
        claim("depth_m", 1500, ["rt:log-value:9001:T2#1/1/1@100"], metric="deepest_md", **WELL),
        U,
        "evidence_not_checkable",
    ),
    # Unverifiable.
    (
        "unknown metric",
        claim("hours", 3.5, [lost(2, "interruption -- repair")], metric="npt_guess", **WELL),
        X,
        "unknown_metric",
    ),
    (
        "metric does not fit the claim type",
        claim(
            "depth_m",
            3.5,
            [lost(2, "interruption -- repair")],
            metric="lost_hours",
            tier="primary",
            **WELL,
        ),
        X,
        "metric_not_for_type",
    ),
    (
        "unknown scope key",
        claim(
            "hours",
            3.5,
            [lost(2, "interruption -- repair")],
            metric="lost_hours",
            tier="primary",
            phase="drilling",
            **WELL,
        ),
        X,
        "invalid_scope",
    ),
    (
        "missing scope key",
        claim("hours", 3.5, [lost(2, "interruption -- repair")], metric="lost_hours", **WELL),
        X,
        "invalid_scope",
    ),
]


@pytest.mark.parametrize(("case", "c", "verdict", "reason"), CASES, ids=[c[0] for c in CASES])
def test_claims(checker: Checker, case: str, c: Claim, verdict: Verdict, reason: str) -> None:
    result = check(checker, c)
    assert (result.verdict, result.reason) == (verdict, reason), result


def test_contradiction_states_the_recomputed_value(checker: Checker) -> None:
    c = claim(
        "hours", 9.0, [lost(1, "interruption -- wait")], metric="lost_hours", tier="primary", **WELL
    )
    assert check(checker, c).expected == 8.5


def test_attribution_contradiction_names_the_attributed_wellbore(checker: Checker) -> None:
    c = claim(
        "volume_sm3",
        1000,
        ["prod:monthly:9004:2020-01"],
        metric="wellbore_volume",
        wellbore="9004",
        fluid="oil",
        month="2020-01",
    )
    assert check(checker, c).detail == "the cited month is attributed to 9005"


def test_document_results_in_claim_order(checker: Checker) -> None:
    document = Document.model_validate(
        {
            "agent": "test",
            "title": "Fictional review",
            "sections": [
                {
                    "heading": "Drilling",
                    "sentences": [
                        {
                            "text": "Section 2 was drilled at 20 m/h with 3.5 h primary lost time.",
                            "claims": [
                                {**c.model_dump(mode="json"), "id": cid}
                                for cid, c in (("rate", CASES[6][1]), ("lost", CASES[0][1]))
                            ],
                        },
                        {"text": "No claim here."},
                    ],
                }
            ],
        }
    )
    results = checker.check(document)
    assert [(r.claim_id, r.verdict) for r in results] == [("rate", V), ("lost", V)]


def _document(*sentences: tuple[str, list[Claim]]) -> Document:
    return Document.model_validate(
        {
            "agent": "test",
            "title": "t",
            "sections": [
                {
                    "heading": "h",
                    "sentences": [
                        {"text": text, "claims": [c.model_dump(mode="json") for c in claims]}
                        for text, claims in sentences
                    ],
                }
            ],
        }
    )


def test_unclaimed_numbers_are_flagged() -> None:
    rate = claim("rate_m_per_h", 14.871166, [SECTION2], metric="m")
    day = claim("date", "2013-03-24", [SECTION2], metric="m").model_copy(update={"id": "d1"})
    document = _document(
        # Identifiers, a rounded claim value and a claimed date: nothing to flag.
        ("15/9-F-11 T2 sections 1, 2 and 4 drilled at 14.87 m/h on 2013-03-24.", [rate, day]),
        # Unclaimed: a number, a date and a month.
        ("The bit evidence points to 8.5 in, from 2013-05-09 and in 2014-01.", []),
        ("Activity `ddr:activity:R1#2` in section 3.", []),
    )
    found = [(u.sentence, u.text) for u in Checker.unclaimed(document)]
    assert found == [(1, "2013-05-09"), (1, "2014-01"), (1, "8.5")]


def test_campaign_numbers_are_identifiers() -> None:
    document = _document(
        ("Campaign 1 came before campaigns 2 and 3; the second campaign had 4 casings.", []),
    )
    assert [u.text for u in Checker.unclaimed(document)] == ["4"]


def test_a_number_rounded_differently_is_unclaimed() -> None:
    rate = claim("rate_m_per_h", 14.871166, [SECTION2], metric="m")
    found = Checker.unclaimed(_document(("Drilled at 14.9 m/h, then 14.8 m/h.", [rate])))
    assert [u.text for u in found] == ["14.8"]


def test_years_npdids_and_quoted_sizes() -> None:
    day = claim("date", "2014-02-21", [SECTION2], metric="m")
    size = claim("quote", '9 5/8" casing', ["ddr:activity:R1#2"], metric="quote").model_copy(
        update={"id": "q1"}
    )
    depth = claim("depth_m", 2014, [SECTION2], metric="m").model_copy(update={"id": "c2"})
    document = _document(
        ("The 2014 campaign started on 2014-02-21; the 2016 one is later.", [day]),
        ("Sodir wellbore 5794 (NPDID 5794) ran 9 5/8 in casing, then 20 in casing.", [size]),
        ("The hole reached 2014 m.", [depth]),
    )
    found = [(u.sentence, u.text) for u in Checker.unclaimed(document)]
    # 2014 is covered by the date claim; 9 by the quote; 2014 m by the depth claim.
    assert found == [(0, "2016"), (1, "20")]


def test_section_zero_is_the_section_before_the_first(warehouse: Any) -> None:
    import duckdb

    from well_ops.connectors.base import connect
    from well_ops.connectors.guard import HeldOutGuard
    from well_ops.connectors.redaction import Redactor

    con = duckdb.connect(str(warehouse))
    con.execute(
        "insert into marts.dim_hole_section (section_id, wellbore_key, section_number, "
        "new_hole_drilled_m) values (?, ?, 0, 17.0)",
        [f"{T2}#before_first_section", T2],
    )
    con.close()
    checker = Checker(connect(warehouse), HeldOutGuard([], False), Redactor([]))
    zero = f"ddr:hole-section:{T2}#before_first_section"
    c = claim("depth_m", 17.0, [zero], metric="new_hole_drilled", section=0, **WELL)
    assert check(checker, c).verdict is V


def test_value_only_waives_evidence_for_scope_metrics(checker: Checker) -> None:
    size = claim("hole_size_in", 12.25, [], metric="section_hole_size", section=2, **WELL)
    wrong = size.model_copy(update={"id": "c2", "value": 8.5})
    unrelated = size.model_copy(update={"id": "c3", "evidence_ids": [f"ddr:hole-section:{T2}#1"]})
    text = claim("quote", "Waited on weather.", [], metric="quote")
    text = text.model_copy(update={"id": "c4"})
    results = {
        r.claim_id: r.verdict for r in (
            checker.check_claim(c, value_only=True) for c in (size, wrong, unrelated, text)
        )
    }  # fmt: skip
    assert results == {"c1": V, "c2": C, "c3": V, "c4": U}  # a quote still needs its row
    assert checker.check_claim(size).verdict is U  # the full check still needs evidence


def test_compute_gives_a_metric_without_a_claim(checker: Checker) -> None:
    scope: dict[str, Any] = {"wellbore": T2, "section": 2}
    assert checker.compute("section_hole_size", scope).value == 12.25
    assert checker.compute("lost_hours", {"wellbore": T2, "tier": "primary"}).value == 8.5
    with pytest.raises(ValueError, match="without a claim"):
        checker.compute("quote", {"wellbore": T2})
    with pytest.raises(ValueError, match="section_not_found"):
        checker.compute("section_hole_size", {"wellbore": T2, "section": 9})
    assert checker.wellbore_key("XX/1-A-1 T2") == T2 and checker.wellbore_key("nope") is None
