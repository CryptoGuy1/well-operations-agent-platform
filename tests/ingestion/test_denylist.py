import stat
from pathlib import Path

from well_ops.ingestion.denylist import DENYLIST_FILE, denylist_entries, write_denylist
from well_ops.ingestion.identifiers import EDM_XML
from well_ops.ingestion.volve_witsml import LOG_DIR, WITSML_DIR


def test_entries_dedupe_add_email_local_parts_and_drop_short_and_organisations() -> None:
    values = [" xqzuser ", "XQZUSER", "kari.nordmann@example.org", "ab", "Statoil", "Kari Nordmann"]

    assert denylist_entries(values) == [
        "Kari Nordmann",
        "kari.nordmann",
        "kari.nordmann@example.org",
        "xqzuser",
    ]


def test_write_denylist_reads_every_source(tmp_path: Path) -> None:
    raw = tmp_path / "raw"
    (raw / EDM_XML).parent.mkdir(parents=True)
    (raw / EDM_XML).write_text(
        '<export><CD_WELL well_common_name="Z-1" create_user_id="edmuser1" '
        'engineer="Ola Testesen"/></export>',
        encoding="utf-8",
    )
    obj = raw / WITSML_DIR / "w" / "1" / "rig"
    obj.mkdir(parents=True)
    (obj / "1.xml").write_text(
        "<rigs><priv_userOwner>owner&amp;co</priv_userOwner>"
        "<priv_ipOwner>192.0.2.1</priv_ipOwner></rigs>",
        encoding="utf-8",
    )
    log = raw / LOG_DIR / "90001" / "w" / "1" / "log"
    log.mkdir(parents=True)
    (log / "1.xml").write_text("<logs><priv_userLastChange>loguser</priv_userLastChange></logs>")
    (raw / "cira").mkdir()
    (raw / "cira" / "README.md").write_text("Contact: a.author@example.edu\n", encoding="utf-8")

    n = write_denylist(raw, tmp_path / "private")

    path = tmp_path / "private" / DENYLIST_FILE
    assert path.read_text(encoding="utf-8").splitlines() == [
        "a.author",
        "a.author@example.edu",
        "edmuser1",
        "loguser",
        "Ola Testesen",
        "owner&co",
    ]
    assert n == 6
    assert stat.S_IMODE(path.stat().st_mode) == 0o600
