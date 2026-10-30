"""Evidence ids: stable ids for every warehouse row a tool can return (ADR 0004).

An id is `<source>:<entity>:<key>`, where the key is built from the row's natural key in the
warehouse, so the claim checker can find the row again. Kinds and keys (`KINDS` names each
kind's warehouse relation):

- `ddr:report:<report_file>` and `ddr:activity:<report_file>#<n>`
- `ddr:hole-section:<wellbore_key>#<n or before_first_section>`
- `ddr:lost-time:<section_id>|<category> -- <subcategory>`
- `prod:daily:<npdid>:<yyyy-mm-dd>`, `prod:monthly:<npdid>:<yyyy-mm>`,
  `prod:reconciliation:<yyyy-mm>`
- `sodir:wellbore:<npdid>`, `sodir:field-net:<field_npdid>:<yyyy-mm>`,
  `sodir:field-gross:<field_npdid>:<yyyy-mm>`
- `well:wellbore:<wellbore_key>`
- `witsml:<object>:<staged object id>` (source file `#` uid), for each object in WITSML_OBJECTS
- `rt:log:<log_id>`, `rt:log-curve:<log_curve_id>`, `rt:log-value:<log_id>@<index>`

A wellbore key is `<npdid>` or `<npdid>:T<n>` (ADR 0002 D1). The key may itself contain colons,
so an id is split on its first two colons only.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date

WELLBORE_KEY = r"\d+(?::T\d+)?"
MONTH = r"\d{4}-(?:0[1-9]|1[0-2])"
DAY = r"\d{4}-\d{2}-\d{2}"
TEXT = r"[^\s].*"  # any non-empty text not starting with a space


@dataclass(frozen=True)
class Kind:
    name: str  # `<source>:<entity>`
    relation: str  # the warehouse relation the row comes from
    fields: tuple[str, ...]
    pattern: re.Pattern[str]  # the key, with one named group per field
    template: str  # the key, as a str.format template over the fields


def _kind(name: str, relation: str, key: str, template: str) -> Kind:
    pattern = re.compile(key)
    return Kind(name, relation, tuple(pattern.groupindex), pattern, template)


WITSML_OBJECTS = {
    "trajectory-station": "stg_witsml__trajectory_station",
    "bha-run": "stg_witsml__bha_run",
    "tubular-component": "stg_witsml__tubular_component",
    "geometry-section": "stg_witsml__wb_geometry_section",
    "mud-log-interval": "stg_witsml__mud_log_interval",
    "rig": "stg_witsml__rig",
    "message": "stg_witsml__message",
}

KINDS: dict[str, Kind] = {
    k.name: k
    for k in (
        _kind(
            "ddr:report", "staging.stg_ddr__report", r"(?P<report_file>[^#\s]+)", "{report_file}"
        ),
        _kind(
            "ddr:activity",
            "staging.stg_ddr__activity",
            r"(?P<report_file>[^#\s]+)#(?P<activity_number>\d+)",
            "{report_file}#{activity_number}",
        ),
        _kind(
            "ddr:hole-section",
            "marts.dim_hole_section",
            rf"(?P<wellbore_key>{WELLBORE_KEY})#(?P<section>\d+|before_first_section)",
            "{wellbore_key}#{section}",
        ),
        _kind(
            "ddr:lost-time",
            "marts.fct_lost_time",
            rf"(?P<section_id>{WELLBORE_KEY}#(?:\d+|before_first_section))"
            r"\|(?P<category>[a-z][a-z ]*[a-z]) -- (?P<subcategory>[a-z][a-z /]*[a-z])",
            "{section_id}|{category} -- {subcategory}",
        ),
        _kind(
            "prod:daily",
            "staging.stg_production__daily",
            rf"(?P<npdid>\d+):(?P<day>{DAY})",
            "{npdid}:{day}",
        ),
        _kind(
            "prod:monthly",
            "staging.stg_production__monthly",
            rf"(?P<npdid>\d+):(?P<month>{MONTH})",
            "{npdid}:{month}",
        ),
        _kind(
            "prod:reconciliation",
            "marts.fct_production_monthly_reconciliation",
            rf"(?P<month>{MONTH})",
            "{month}",
        ),
        _kind("sodir:wellbore", "staging.stg_sodir__wellbore", r"(?P<npdid>\d+)", "{npdid}"),
        _kind(
            "sodir:field-net",
            "staging.stg_sodir__field_production_net_monthly",
            rf"(?P<field_npdid>\d+):(?P<month>{MONTH})",
            "{field_npdid}:{month}",
        ),
        _kind(
            "sodir:field-gross",
            "staging.stg_sodir__field_production_gross_monthly",
            rf"(?P<field_npdid>\d+):(?P<month>{MONTH})",
            "{field_npdid}:{month}",
        ),
        _kind(
            "well:wellbore",
            "marts.dim_wellbore",
            rf"(?P<wellbore_key>{WELLBORE_KEY})",
            "{wellbore_key}",
        ),
        *(
            _kind(f"witsml:{name}", f"staging.{table}", rf"(?P<object_id>{TEXT})", "{object_id}")
            for name, table in WITSML_OBJECTS.items()
        ),
        _kind("rt:log", "staging.stg_witsml__log", rf"(?P<log_id>{TEXT})", "{log_id}"),
        _kind(
            "rt:log-curve",
            "staging.stg_witsml__log_curve",
            rf"(?P<log_curve_id>{TEXT})",
            "{log_curve_id}",
        ),
        _kind(
            "rt:log-value",
            "staging.stg_witsml__log_value",
            r"(?P<log_id>[^@\s][^@]*)@(?P<index>[^@\s]+)",
            "{log_id}@{index}",
        ),
    )
}


class EvidenceIdError(ValueError):
    """An evidence id that is malformed or of an unknown kind (the id is not echoed)."""


@dataclass(frozen=True)
class EvidenceId:
    kind: str
    values: dict[str, str]

    @property
    def relation(self) -> str:
        return KINDS[self.kind].relation

    def __str__(self) -> str:
        return f"{self.kind}:{KINDS[self.kind].template.format(**self.values)}"


def _text(value: object) -> str:
    if isinstance(value, date):
        return value.isoformat()
    return str(value)


def build(kind: str, **values: object) -> str:
    """The evidence id of one row; raises EvidenceIdError if a value does not fit the kind."""
    spec = KINDS.get(kind)
    if spec is None:
        raise EvidenceIdError("unknown evidence kind")
    if set(values) != set(spec.fields):
        raise EvidenceIdError(f"{kind} needs exactly the fields {', '.join(spec.fields)}")
    text = f"{kind}:{spec.template.format(**{k: _text(v) for k, v in values.items()})}"
    parse(text)  # the built id must parse back to the same values
    return text


def month(value: date) -> str:
    """The `yyyy-mm` form used in monthly keys."""
    return value.strftime("%Y-%m")


def parse(text: str) -> EvidenceId:
    """Split an evidence id into its kind and key fields; raises EvidenceIdError if malformed."""
    parts = text.split(":", 2)
    if len(parts) != 3:
        raise EvidenceIdError("not an evidence id")
    kind = f"{parts[0]}:{parts[1]}"
    spec = KINDS.get(kind)
    if spec is None:
        raise EvidenceIdError("unknown evidence kind")
    match = spec.pattern.fullmatch(parts[2])
    if match is None:
        raise EvidenceIdError(f"malformed {kind} key")
    if kind in ("prod:daily",):
        try:
            date.fromisoformat(match["day"])
        except ValueError:
            raise EvidenceIdError("invalid date in prod:daily key") from None
    return EvidenceId(kind, match.groupdict())
