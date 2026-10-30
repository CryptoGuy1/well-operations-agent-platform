from well_ops.keys import wellbore_key


def test_wellbore_key() -> None:
    assert wellbore_key("7078") == "7078"
    assert wellbore_key("7078", "T2") == "7078:T2"
    assert wellbore_key("90001", "T3") == "90001:T3"


def test_wellbore_key_empty_suffix_is_no_suffix() -> None:
    assert wellbore_key("7078", "") == "7078"
