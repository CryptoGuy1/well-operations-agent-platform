"""WITSML staging on hand-written XML for a fictional wellbore, with planted personal fields."""

import json
import re
import zipfile
from datetime import datetime
from pathlib import Path

import duckdb
import pytest

from well_ops.ingestion.volve_witsml import (
    LOG_DIR,
    OBJECTS,
    WITSML_DIR,
    WITSML_ZIP,
    extract_logs,
    heldout_keys,
    stage_witsml_logs,
    stage_witsml_objects,
    zip_log_members,
)

NS = 'xmlns="http://www.witsml.org/schemas/1series"'
PERSONAL = "<priv_userOwner>jdoe</priv_userOwner><priv_ipOwner>10.1.2.3</priv_ipOwner>"

TRAJECTORY = f"""<trajectorys {NS} version="1.4.1.1">
<trajectory uid="t1" uidWell="w" uidWellbore="wb"><name>Survey</name>
<trajectoryStation uid="s1"><dTimStn>2014-04-07T06:00:00.000Z</dTimStn>
<md uom="m">1500.5</md><tvd uom="m">1450.2</tvd><incl uom="rad">0.5</incl>
<azi uom="dega">210.0</azi><dls uom="dega/30m">1.2</dls>
<commonData>{PERSONAL}</commonData></trajectoryStation>
<commonData><priv_userLastChange>jdoe</priv_userLastChange></commonData>
</trajectory></trajectorys>"""

BHA = f"""<bhaRuns {NS}><bhaRun uid="b1"><name>X-1 - 3</name><tubular uidRef="tub1"/>
<dTimStart>2014-04-07T06:00:00.000+01:00</dTimStart><dTimStop>2014-04-09T18:30:00.000Z</dTimStop>
<numStringRun>3</numStringRun>
<drillingParams uid="d"><mdHoleStart uom="m">1400</mdHoleStart><mdHoleStop uom="m">2100</mdHoleStop>
</drillingParams><commonData>{PERSONAL}</commonData></bhaRun></bhaRuns>"""

MESSAGE = f"""<messages {NS}><message uid="m1"><name>Note</name>
<dTim>2014-04-08T12:00:00.000Z</dTim><md uom="m">1800</md><typeMessage>unknown</typeMessage>
<messageText>Pumped sweep</messageText><commonData>{PERSONAL}</commonData></message></messages>"""


def write_witsml(raw: Path) -> None:
    well = raw / WITSML_DIR / "NA-NA-15_$47$_9-X-1"
    well.mkdir(parents=True)
    (well / "MetaFileInfo.txt").write_text("1  NO 15_$47$_9-X-1 (abc)  ID1\n", encoding="utf-8")
    for folder, text in (("trajectory", TRAJECTORY), ("bhaRun", BHA), ("message", MESSAGE)):
        (well / "1" / folder).mkdir(parents=True)
        (well / "1" / folder / "1.xml").write_text(text, encoding="utf-8")


def test_no_field_reads_a_personal_element() -> None:
    paths = [f.path for spec in OBJECTS for f in (*spec.fields, *spec.object_fields)]
    assert not [p for p in paths if "priv" in p.lower()]


def test_stage_objects(tmp_path: Path) -> None:
    raw, staging = tmp_path / "raw", tmp_path / "staging"
    write_witsml(raw)

    counts = stage_witsml_objects(raw, staging)

    assert counts["trajectory_station"] == 1
    assert counts["bha_run"] == 1
    assert counts["message"] == 1
    assert counts["rig"] == 0
    con = duckdb.connect()
    station = con.execute(
        "select source_wellbore_name, row_uid, station_utc, md, md_uom, incl, incl_uom, azi"
        f" from '{staging}/witsml/trajectory_station.parquet'"
    ).fetchall()
    assert station == [
        ("NO 15/9-X-1", "s1", datetime(2014, 4, 7, 6), 1500.5, "m", 0.5, "rad", 210.0)
    ]
    bha = con.execute(
        "select tubular_uid, run_start_utc, run_start_offset, md_hole_stop, md_hole_stop_uom"
        f" from '{staging}/witsml/bha_run.parquet'"
    ).fetchall()
    assert bha == [("tub1", datetime(2014, 4, 7, 5), "+01:00", 2100.0, "m")]


def test_personal_fields_never_staged(tmp_path: Path) -> None:
    raw, staging = tmp_path / "raw", tmp_path / "staging"
    write_witsml(raw)
    stage_witsml_objects(raw, staging)

    con = duckdb.connect()
    for path in (staging / "witsml").glob("*.parquet"):
        columns = [r[0] for r in con.execute(f"describe select * from '{path}'").fetchall()]
        assert not [c for c in columns if re.search(r"priv|user|(^|_)ip($|_)", c)], path.name
        text = " ".join(str(v) for row in con.execute(f"from '{path}'").fetchall() for v in row)
        assert "jdoe" not in text and "10.1.2.3" not in text, path.name


def test_timestamp_without_offset_is_rejected(tmp_path: Path) -> None:
    raw = tmp_path / "raw"
    write_witsml(raw)
    message = next((raw / WITSML_DIR).rglob("message/1.xml"))
    message.write_text(MESSAGE.replace(".000Z", ""), encoding="utf-8")

    with pytest.raises(ValueError, match=r"message/1\.xml"):
        stage_witsml_objects(raw, tmp_path / "staging")


def log_chunk(index: str, start: str, end: str, rows: int) -> str:
    data = "".join(f"<data>{start},1.0</data>" for _ in range(rows))
    return f"""<logs {NS}><log uid="l"><nameWellbore>NO 15/9-X-1</nameWellbore><name>Gamma</name>
<indexType>{index}</indexType><startIndex uom="m">{start}</startIndex>
<endIndex uom="m">{end}</endIndex><direction>increasing</direction><indexCurve>Depth</indexCurve>
<logCurveInfo uid="Depth"><mnemonic>Depth</mnemonic><unit>m</unit>
<typeLogData>double</typeLogData></logCurveInfo>
<logCurveInfo uid="GR"><mnemonic>GR</mnemonic><unit>gAPI</unit>
<typeLogData>double</typeLogData></logCurveInfo>
<logData><mnemonicList>Depth,GR</mnemonicList><data>{start},1.0</data>{data}</logData>
<commonData>{PERSONAL}</commonData></log></logs>"""


def write_zip(raw: Path) -> None:
    path = raw / WITSML_ZIP
    path.parent.mkdir(parents=True, exist_ok=True)
    base = "root/NA-NA-15_$47$_9-X-1"
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr(f"{base}/MetaFileInfo.txt", "1  NO 15_$47$_9-X-1 (abc)  ID1\n")
        archive.writestr(
            f"{base}/1/log/1/1/1/00001.xml", log_chunk("measured depth", "95", "100", 1)
        )
        archive.writestr(
            f"{base}/1/log/1/1/1/00002.xml", log_chunk("measured depth", "100", "200", 2)
        )
        archive.writestr(f"{base}/1/message/1.xml", MESSAGE)
        archive.writestr("root/NA-NA-15_$47$_9-X-2/1/log/1/1/1/00001.xml", "other wellbore")


def test_zip_log_members_selects_one_wellbore(tmp_path: Path) -> None:
    write_zip(tmp_path)
    with zipfile.ZipFile(tmp_path / WITSML_ZIP) as archive:
        members = zip_log_members(archive, {"NO 15/9-X-1"})
    assert sorted(m.filename.rsplit("/", 1)[1] for m in members) == ["00001.xml", "00002.xml"]
    assert all("9-X-1/1/log/" in m.filename for m in members)


def test_extract_and_summarise_logs(tmp_path: Path) -> None:
    data = tmp_path / "data"
    write_zip(data / "raw")

    entries = extract_logs(data, "90001", {"NO 15/9-X-1"})

    assert len(entries) == 2
    assert all(e.file.startswith(f"raw/{LOG_DIR.as_posix()}/90001/") for e in entries)
    assert all(".zip!/root/" in e.source_url for e in entries)
    assert extract_logs(data, "90001", {"NO 15/9-X-1"})[0].bytes == entries[0].bytes  # rerun

    logs, curves = stage_witsml_logs(data / "raw", data / "staging")

    assert (logs, curves) == (1, 2)
    con = duckdb.connect()
    log = con.execute(
        "select log_id, wellbore_key, index_type, start_index, end_index, chunks, rows"
        f" from '{data}/staging/witsml_log/log.parquet'"
    ).fetchall()
    assert log == [("90001#1/1/1", "90001", "measured depth", "95", "200", 2, 5)]


def test_time_log_range(tmp_path: Path) -> None:
    from well_ops.ingestion.volve_witsml import parse_log_chunk

    path = tmp_path / "00001.xml"
    text = log_chunk("date time", "x", "y", 0)
    text = text.replace(
        '<startIndex uom="m">x</startIndex>',
        "<startDateTimeIndex>2014-04-07T06:00:00.000Z</startDateTimeIndex>",
    )
    text = text.replace(
        '<endIndex uom="m">y</endIndex>',
        "<endDateTimeIndex>2014-04-08T06:00:00.000Z</endDateTimeIndex>",
    )
    path.write_text(text, encoding="utf-8")

    header, curves, rows = parse_log_chunk(path)

    assert (header["start_index"], header["end_index"]) == (
        "2014-04-07T06:00:00.000Z",
        "2014-04-08T06:00:00.000Z",
    )
    assert [c[0] for c in curves] == ["Depth", "GR"]
    assert rows == 1


def test_extract_logs_needs_a_name(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="no WITSML wellbore name"):
        extract_logs(tmp_path, "90001", set())


def test_heldout_keys(tmp_path: Path) -> None:
    splits = tmp_path / "splits.json"
    splits.write_text(json.dumps({"held_out": [{"key": "90002", "name": "15/9-X-2"}]}))
    assert heldout_keys(splits) == {"90002"}


def value_chunk(columns: str, rows: list[str]) -> str:
    curves = {
        "Time": "<typeLogData>date time</typeLogData>",
        "Depth": "<typeLogData>double</typeLogData>",
        "GR": "<typeLogData>double</typeLogData><nullValue>-9999</nullValue>",
        "Code": "<typeLogData>long</typeLogData>",
        "IMG": "<typeLogData>double</typeLogData><axisDefinition uid='a'><count>3</count>"
        "</axisDefinition>",
    }
    info = "".join(
        f"<logCurveInfo uid='{c}'><mnemonic>{c}</mnemonic>{curves[c]}</logCurveInfo>"
        for c in curves
    )
    data = "".join(f"<data>{r}</data>" for r in rows)
    return f"""<logs {NS}><log uid="l"><nameWellbore>NO 15/9-X-1</nameWellbore><name>Mixed</name>
<indexType>date time</indexType><nullValue>-999.25</nullValue>{info}
<logData><mnemonicList>{columns}</mnemonicList>{data}</logData></log></logs>"""


def test_stage_log_values(tmp_path: Path) -> None:
    from well_ops.ingestion.volve_witsml import stage_log_values

    log_dir = tmp_path / "raw" / "w" / "1" / "log" / "2" / "5" / "1"
    log_dir.mkdir(parents=True)
    (log_dir / "00001.xml").write_text(
        value_chunk(
            "Time,Depth,GR,Code,IMG",
            [
                "2014-04-07T06:00:00.000Z,1500.5,80.2,3,1 -999.25 2",
                "2014-04-07T06:00:05.000Z,-999.25,-9999,,4 5 6",
            ],
        ),
        encoding="utf-8",
    )
    # A later chunk lists fewer curves, in another order.
    (log_dir / "00002.xml").write_text(
        value_chunk("Time,GR,Depth", ["2014-04-07T06:00:10.000Z,75.0,1501.0"]),
        encoding="utf-8",
    )
    out = tmp_path / "staging" / "90001"

    files, rows, nulled = stage_log_values(tmp_path / "raw", "90001", out)

    assert (files, rows, nulled) == (1, 3, 3)
    con = duckdb.connect()
    got = con.execute(
        f"select Time, Depth, GR, Code, IMG from '{out}/2_5_1.parquet' order by Time"
    ).fetchall()
    assert got == [
        (datetime(2014, 4, 7, 6, 0, 0), 1500.5, 80.2, 3, [1.0, None, 2.0]),
        (datetime(2014, 4, 7, 6, 0, 5), None, None, None, [4.0, 5.0, 6.0]),
        (datetime(2014, 4, 7, 6, 0, 10), 1501.0, 75.0, None, None),
    ]
    assert not list(out.parent.glob("*.part"))
