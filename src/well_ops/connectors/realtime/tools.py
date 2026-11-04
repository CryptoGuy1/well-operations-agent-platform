"""Real-time (WITSML log) tools over the staged log values of extracted wellbores (ADR 0002 D6).

Log values are staged wide: one column per mnemonic, plus the index column named by the log's
index curve. A mnemonic is only ever used as a column name after it has been matched to the log's
curve list and to an existing numeric column, so no caller text reaches the SQL. Mnemonics are
not mapped between vendors or logs.
"""

from __future__ import annotations

import datetime as dt
import re
from typing import Any, Literal

from well_ops.connectors import evidence
from well_ops.connectors.base import ConnectorTools, invalid_arguments, utc_iso
from well_ops.connectors.errors import ToolError

IndexType = Literal["measured depth", "date time"]

LOG = "staging.stg_witsml__log"
LOG_CURVE = "staging.stg_witsml__log_curve"
LOG_VALUE = "staging.stg_witsml__log_value"
LOG_FLAG = "intermediate.int_witsml__log_flag"

LOG_ID = re.compile(r"\d+(?::T\d+)?#[\w/.-]{1,60}")
MNEMONIC = re.compile(r"[\w.:-]{1,64}")
NUMERIC = ("DOUBLE", "BIGINT", "INTEGER", "FLOAT")


def logs_not_extracted() -> ToolError:
    return ToolError(
        "logs_not_extracted",
        "No real-time logs are staged for this wellbore.",
        "Logs are extracted on demand: make extract-log WELLBORE=<key>, then make stage.",
    )


def log_not_found() -> ToolError:
    return ToolError(
        "log_not_found",
        "This wellbore has no log with this id.",
        "Use list_logs for the wellbore's log ids.",
    )


def curve_not_found() -> ToolError:
    return ToolError(
        "curve_not_found",
        "This log has no curve with this mnemonic.",
        "Use list_logs for the log's curve count, and the exact mnemonic from the log.",
    )


def curve_not_numeric() -> ToolError:
    return ToolError(
        "curve_not_numeric",
        "This curve has no numeric values to summarise.",
        "Choose a numeric curve of the log.",
    )


def _quote(column: str) -> str:
    return '"' + column.replace('"', '""') + '"'


def _bound(value: float | dt.datetime | None, index_type: str, name: str) -> Any:
    """A range bound of the log's index type: metres for depth logs, UTC for time logs."""
    if value is None:
        return None
    if index_type == "date time":
        if not isinstance(value, dt.datetime):
            raise invalid_arguments([name])
        if value.tzinfo is not None:
            value = value.astimezone(dt.UTC).replace(tzinfo=None)
        return value
    if isinstance(value, dt.datetime):
        raise invalid_arguments([name])
    return float(value)


class Realtime(ConnectorTools):
    def _columns(self) -> dict[str, tuple[str, str]]:
        """Log value columns by lower-case name: (column name, type)."""
        rows = (
            self._cursor()
            .execute(
                """
            select column_name, data_type from information_schema.columns
            where table_schema = 'staging' and table_name = 'stg_witsml__log_value'
            """
            )
            .fetchall()
        )
        return {name.lower(): (name, kind) for name, kind in rows}

    def list_logs(self, wellbore_key: str, index_type: IndexType | None = None) -> dict[str, Any]:
        cur = self._cursor()
        key = self._wellbore(cur, wellbore_key)
        if not cur.execute(
            f"select 1 from {LOG_VALUE} where wellbore_key = ? limit 1", [key]
        ).fetchall():
            raise logs_not_extracted()
        rows = cur.execute(
            f"""
            select l.log_id, l.log_name, l.index_type, l.index_curve, l.index_uom,
                   l.start_index, l.end_index, l.direction, l.service_company, l.run_number,
                   l.rows,
                   (select count(*) from {LOG_CURVE} c where c.log_id = l.log_id),
                   (select list(f.flag order by f.flag) from {LOG_FLAG} f
                    where f.log_id = l.log_id)
            from {LOG} l
            where l.wellbore_key = ? and (cast(? as varchar) is null or l.index_type = ?)
            order by l.log_id
            """,
            [key, index_type, index_type],
        ).fetchall()
        return self._envelope(
            [LOG, LOG_CURVE, LOG_FLAG],
            {"wellbore_key": key, "index_type": index_type},
            [
                {
                    "evidence_id": evidence.build("rt:log", log_id=r[0]),
                    "log_id": r[0],
                    "log_name": r[1],
                    "index_type": r[2],
                    "index_curve": r[3],
                    "index_uom": r[4],
                    "start_index": r[5],
                    "end_index": r[6],
                    "direction": r[7],
                    "service_company": r[8],
                    "run_number": r[9],
                    "rows": r[10],
                    "curve_count": r[11],
                    "flags": r[12] or [],
                }
                for r in rows
            ],
        )

    def curve_summary(
        self,
        wellbore_key: str,
        log: str,
        mnemonic: str,
        start: float | dt.datetime | None = None,
        end: float | dt.datetime | None = None,
    ) -> dict[str, Any]:
        if not LOG_ID.fullmatch(log):
            raise invalid_arguments(["log"])
        if not MNEMONIC.fullmatch(mnemonic):
            raise invalid_arguments(["mnemonic"])
        cur = self._cursor()
        key = self._wellbore(cur, wellbore_key)
        found = cur.execute(
            f"select index_type, index_curve, index_uom from {LOG}"
            " where log_id = ? and wellbore_key = ?",
            [log, key],
        ).fetchall()
        if not found:
            raise log_not_found()
        index_type, index_curve, index_uom = found[0]
        curve = cur.execute(
            f"""
            select log_curve_id, mnemonic, unit, curve_description from {LOG_CURVE}
            where log_id = ? and mnemonic = ?
            """,
            [log, mnemonic],
        ).fetchall()
        if not curve:
            raise curve_not_found()
        curve_id, mnemonic, unit, description = curve[0]
        columns = self._columns()
        value = columns.get(mnemonic.lower())
        index = columns.get(index_curve.lower())
        if value is None or index is None or value[1] not in NUMERIC:
            raise curve_not_numeric()
        low = _bound(start, index_type, "start")
        high = _bound(end, index_type, "end")
        if low is not None and high is not None and high < low:
            raise invalid_arguments(["end"])

        v, i = _quote(value[0]), _quote(index[0])
        stats = cur.execute(
            f"""
            select count(*), count(distinct {i}), count({v}), min({v}), max({v}),
                   round(avg({v}), 6), min({i}), max({i})
            from {LOG_VALUE}
            where log_id = ?
              and (cast(? as {index[1]}) is null or {i} >= ?)
              and (cast(? as {index[1]}) is null or {i} <= ?)
            """,
            [log, low, low, high, high],
        ).fetchall()[0]
        rows_in_range, distinct_index, count, minimum, maximum, mean, first, last = stats

        def shown(x: Any) -> Any:
            return utc_iso(x) if isinstance(x, dt.datetime) else x

        row = {
            "evidence_id": evidence.build("rt:log-curve", log_curve_id=curve_id),
            "log_evidence_id": evidence.build("rt:log", log_id=log),
            "mnemonic": mnemonic,
            "unit": unit,
            "curve_description": description,
            "index_type": index_type,
            "index_uom": index_uom,
            "first_index": shown(first),
            "last_index": shown(last),
            "rows_in_range": rows_in_range,
            "distinct_index_values": distinct_index,
            "count": count,
            "min": minimum,
            "max": maximum,
            "mean": mean,
        }
        return self._envelope(
            [LOG, LOG_CURVE, LOG_VALUE],
            {
                "wellbore_key": key,
                "log": log,
                "mnemonic": mnemonic,
                "start": shown(low),
                "end": shown(high),
            },
            [row],
        )
