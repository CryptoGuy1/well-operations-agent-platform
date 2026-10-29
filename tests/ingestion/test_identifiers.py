"""Key builder and D2 status rules, on 15/9-F-11 T2 and fictional wellbores only."""

import pytest

from well_ops.ingestion.identifiers import (
    NameObservation,
    alias_status,
    build_aliases,
    sidetrack_name,
    sidetrack_suffix,
    wellbore_key,
)
from well_ops.ingestion.sodir_factpages import SodirWellbore

SODIR = [
    SodirWellbore("15/9-F-11", "7078", "VOLVE"),
    SodirWellbore("15/9-X-1", "90001", "VOLVE"),
    SodirWellbore("15/9-X-2 B", "90002", "VOLVE"),
]


def test_wellbore_key() -> None:
    assert wellbore_key("7078") == "7078"
    assert wellbore_key("7078", "T2") == "7078:T2"


@pytest.mark.parametrize(
    ("name", "parent", "expected"),
    [
        ("15/9-F-11 T2", "15/9-F-11", "T2"),
        ("15/9-X-2 BT3", "15/9-X-2 B", "T3"),
        ("15/9-F-11", "15/9-F-11", None),
        ("15/9-X-1 A", "15/9-X-1", None),
        ("15/9-X-12 T2", "15/9-X-1", None),
    ],
)
def test_sidetrack_suffix(name: str, parent: str, expected: str | None) -> None:
    assert sidetrack_suffix(name, parent) == expected


def test_sidetrack_name_follows_source_spelling() -> None:
    assert sidetrack_name("15/9-F-11", "T2") == "15/9-F-11 T2"
    assert sidetrack_name("15/9-X-2 B", "T2") == "15/9-X-2 BT2"


@pytest.mark.parametrize(
    ("normalised", "expected"),
    [
        ("Relief well 100m North", "planning_object"),
        ('X-1 A 9 5/8" csg.shoe', "planning_object"),
        ('X-1 9 5/8" csg. shoe', "planning_object"),
        ("X-1 Top Reservoir Intersection", "planning_object"),
        ("test", "not_a_wellbore"),
        ("Vendor_Run2", "not_a_wellbore"),
        ('12 1/4" Final Data', "not_a_wellbore"),
        ("X-1", "unresolved"),
        ("X-1 A", "unresolved"),
        ("15/9-X-3", "unresolved"),
        ("15/9-X-1 S", "unresolved"),
        ("1 BT2", "unresolved"),
        ("15/9-X-1 pilot", "unresolved"),
    ],
)
def test_alias_status_for_unmatched_names(normalised: str, expected: str) -> None:
    assert alias_status(normalised, matched=False) == expected


def test_alias_status_matched_is_wellbore() -> None:
    assert alias_status("Relief well 100m North", matched=True) == "wellbore"


def test_build_aliases_keys_and_methods() -> None:
    observations = [
        NameObservation("DDR", "NO 15/9-F-11 T2", "7078"),
        NameObservation("Well picks", "NO 15/9-F-11 T2"),
        NameObservation("WITSML", "NO 15_$47$_9-F-11 T2 - Main Wellbore"),
        NameObservation("Production daily", "NO 15/9-X-1", "90001"),
        NameObservation("Well picks", "NO 15/9-X-2 BT2"),
        NameObservation("EDM wellbore_name", "X-1"),
        NameObservation("Production daily", "15/9-X-9", "NULL"),
        NameObservation("WITSML", "test"),
    ]

    aliases = {(a.source, a.source_name): a for a in build_aliases(observations, SODIR)}

    ddr = aliases[("DDR", "NO 15/9-F-11 T2")]
    assert (ddr.match_method, ddr.wellbore_key, ddr.wellbore_name, ddr.status) == (
        "npdid",
        "7078:T2",
        "15/9-F-11 T2",
        "wellbore",
    )
    assert ddr.source_npdid == 7078
    picks = aliases[("Well picks", "NO 15/9-F-11 T2")]
    assert (picks.match_method, picks.wellbore_key) == ("name", "7078:T2")
    witsml = aliases[("WITSML", "NO 15_$47$_9-F-11 T2 - Main Wellbore")]
    assert (witsml.normalised_name, witsml.wellbore_key) == ("15/9-F-11 T2", "7078:T2")
    assert aliases[("Production daily", "NO 15/9-X-1")].wellbore_key == "90001"
    glued = aliases[("Well picks", "NO 15/9-X-2 BT2")]
    assert (glued.wellbore_key, glued.wellbore_name) == ("90002:T2", "15/9-X-2 BT2")
    short = aliases[("EDM wellbore_name", "X-1")]
    assert (short.match_method, short.wellbore_key, short.status) == ("none", None, "unresolved")
    no_npdid = aliases[("Production daily", "15/9-X-9")]
    assert (no_npdid.source_npdid, no_npdid.match_method) == (None, "none")
    assert aliases[("WITSML", "test")].status == "not_a_wellbore"


def test_unknown_npdid_falls_back_to_name() -> None:
    observations = [NameObservation("DDR", "NO 15/9-X-1", "99999")]

    (alias,) = build_aliases(observations, SODIR)

    assert (alias.match_method, alias.wellbore_key) == ("name", "90001")
