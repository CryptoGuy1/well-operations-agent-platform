import well_ops


def test_package_exposes_version() -> None:
    assert isinstance(well_ops.__version__, str)
