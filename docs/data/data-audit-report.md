# Data audit report (Phase 1)

This report states what the raw data contains, as downloaded into `data/raw/` and recorded in
`data/manifest.json`. It does not clean or interpret the data beyond what is needed to describe it.

**How it is produced.** Every number in this report is computed from `data/raw/` by
`src/well_ops/ingestion/audit.py` and written into the sections between `<!-- audit:... -->`
markers by `make audit`. Each computed section names the function that produced it. Text outside
the markers is written by hand, refers to the computed sections, and quotes only dates and
identifiers that appear in them. Re-running `make audit` on the same raw data reproduces this
report exactly.

**Sources.** Volve Data Village (Equinor ASA and the Volve licence partners, Equinor Open Data
Licence), Sodir FactPages (NLOD 2.0) and the CIRA Centrifugal Pump Dataset (CC BY 4.0). See
`NOTICE` and `docs/data/volve-access.md`.

**Held-out wellbores.** Per-wellbore tables in this report predate the held-out draw (ADR 0002
D8, commit e439314) and are kept as the Phase 1 record. From Phase 2 onwards, outputs name
development wellbores only.

## 1. Volve daily drilling reports

Files: `data/raw/volve/Well_technical_data/Daily Drilling Report - XML Version/`, one WITSML 1.4
`drillReport` per file, ISO-8859-1 encoded.

### 1.1 Reports, wellbores and date range

<!-- audit:ddr-coverage -->
1,759 reports covering 26 wellbores. The date in the file name equals the date of the report's `dTimEnd` in 1,759 files, of `dTimStart` in 0, and neither in 0. Dates below are the report `dTimStart` dates.

| Wellbore (nameWellbore) | NPD number | Reports | First report | Last report | Reports ending on or before spud |
|---|---|---|---|---|---|
| NO 15/9-19 A | 3145 | 110 | 1979-12-31 | 1997-11-09 | `15_9_19_A_1980_01_01.xml`, `15_9_19_A_1997_07_25.xml` |
| NO 15/9-19 B | 3251 | 27 | 1997-11-09 | 1997-12-05 | `15_9_19_B_1997_11_10.xml` |
| NO 15/9-19 BT2 | 3251 | 62 | 1997-12-05 | 1998-02-04 | 0 |
| NO 15/9-19 S | 2043 | 49 | 1992-09-08 | 1992-12-18 | `15_9_19_S_1992_09_09.xml`, `15_9_19_S_1992_09_10.xml`, `15_9_19_S_1992_09_11.xml`, `15_9_19_S_1992_09_12.xml`, `15_9_19_S_1992_09_13.xml`, `15_9_19_S_1992_09_14.xml`, `15_9_19_S_1992_09_15.xml`, `15_9_19_S_1992_09_16.xml`, `15_9_19_S_1992_09_17.xml`, `15_9_19_S_1992_09_18.xml` |
| NO 15/9-19 ST2 | 2043 | 127 | 1992-12-18 | 1997-07-25 | 0 |
| NO 15/9-F-1 | 7223 | 38 | 2007-12-01 | 2013-08-23 | 0 |
| NO 15/9-F-1 A | 7224 | 7 | 2013-08-23 | 2013-08-29 | 0 |
| NO 15/9-F-1 B | 7264 | 73 | 2013-08-29 | 2014-02-21 | 0 |
| NO 15/9-F-1 C | 7405 | 98 | 2014-02-21 | 2016-10-21 | 0 |
| NO 15/9-F-10 | 6099 | 71 | 2009-04-06 | 2009-06-15 | 0 |
| NO 15/9-F-11 | 7078 | 17 | 2013-03-07 | 2013-03-23 | 0 |
| NO 15/9-F-11 A | 7079 | 14 | 2013-05-14 | 2013-05-28 | 0 |
| NO 15/9-F-11 B | 7080 | 90 | 2013-05-28 | 2016-10-21 | 0 |
| NO 15/9-F-11 T2 | 7078 | 53 | 2013-03-23 | 2013-05-14 | 0 |
| NO 15/9-F-12 | 5599 | 165 | 2007-06-13 | 2016-10-20 | 0 |
| NO 15/9-F-14 | 5351 | 134 | 2007-11-05 | 2016-10-19 | 0 |
| NO 15/9-F-15 | 6184 | 69 | 2007-11-18 | 2018-01-24 | `15_9_F_15_2007_11_19.xml`, `15_9_F_15_2007_11_20.xml`, `15_9_F_15_2007_11_21.xml`, `15_9_F_15_2007_11_22.xml`, `15_9_F_15_2007_12_23.xml`, `15_9_F_15_2007_12_24.xml`, `15_9_F_15_2007_12_25.xml`, `15_9_F_15_2007_12_26.xml`, `15_9_F_15_2007_12_27.xml`, `15_9_F_15_2007_12_28.xml`, `15_9_F_15_2007_12_29.xml`, `15_9_F_15_2007_12_30.xml`, `15_9_F_15_2007_12_31.xml`, `15_9_F_15_2008_09_07.xml`, `15_9_F_15_2008_09_08.xml`, `15_9_F_15_2008_09_09.xml`, `15_9_F_15_2008_09_10.xml`, `15_9_F_15_2008_09_11.xml`, `15_9_F_15_2008_09_19.xml`, `15_9_F_15_2008_09_20.xml`, `15_9_F_15_2008_09_21.xml`, `15_9_F_15_2008_09_22.xml`, `15_9_F_15_2008_09_23.xml`, `15_9_F_15_2008_09_24.xml`, `15_9_F_15_2008_09_25.xml`, `15_9_F_15_2008_09_26.xml`, `15_9_F_15_2008_09_27.xml`, `15_9_F_15_2008_09_28.xml`, `15_9_F_15_2008_09_29.xml`, `15_9_F_15_2008_09_30.xml`, `15_9_F_15_2008_10_01.xml`, `15_9_F_15_2008_10_02.xml`, `15_9_F_15_2008_10_03.xml`, `15_9_F_15_2008_10_04.xml`, `15_9_F_15_2008_10_05.xml`, `15_9_F_15_2008_10_06.xml` |
| NO 15/9-F-15 A | 5785 | 34 | 2008-12-11 | 2009-01-13 | 0 |
| NO 15/9-F-15 B | 6046 | 6 | 2009-01-13 | 2009-01-18 | 0 |
| NO 15/9-F-15 C | 5794 | 84 | 2009-01-18 | 2013-11-10 | `15_9_F_15_C_2009_01_19.xml` |
| NO 15/9-F-15 D | 7289 | 99 | 2013-11-10 | 2016-10-18 | 0 |
| NO 15/9-F-4 | 5693 | 130 | 2007-06-09 | 2016-10-13 | 0 |
| NO 15/9-F-5 | 5769 | 103 | 2007-11-14 | 2016-10-16 | 0 |
| NO 15/9-F-7 | 5610 | 39 | 2007-09-14 | 2016-10-23 | 0 |
| NO 15/9-F-9 | 5927 | 32 | 2007-11-28 | 2009-07-03 | 0 |
| NO 15/9-F-9 A | 6163 | 28 | 2009-07-03 | 2016-10-23 | 0 |

Computed by `well_ops.ingestion.audit.load_drill_reports`, `well_ops.ingestion.audit.audit_ddr_coverage`, `well_ops.ingestion.audit.file_date_matches`.
<!-- /audit:ddr-coverage -->

A report's file name carries the date on which its period ends, so the file dated day N describes
the period ending at the start of day N. Wellbores ending in `T2` (technical sidetracks) carry the
same NPD number as their parent wellbore.

### 1.2 Activity records

<!-- audit:ddr-activities -->
23,447 activities; 9 reports have none. Every activity has `dTimStart` and `dTimEnd`, so a duration can be computed for each: 0 are negative and 0 are zero; 0 activity timestamps lack a UTC offset. In 1,529 reports the activity durations add up exactly to the report period (`dTimEnd` - `dTimStart` of the report); 24 reports have at least one gap or overlap between consecutive activities.

| Element | Activities with it |
|---|---|
| comments | 23447 |
| dTimEnd | 23447 |
| dTimStart | 23447 |
| md | 23447 |
| md@uom | 23447 |
| phase | 23447 |
| proprietaryCode | 23447 |
| state | 23447 |
| stateDetailActivity | 23447 |

Examples:

From `15_9_19_A_1997_07_26.xml`:

```
dTimStart: 1997-07-25T00:30:00+02:00
dTimEnd: 1997-07-25T06:00:00+02:00
md: 500
phase: fixed
proprietaryCode: drilling -- trip
state: ok
stateDetailActivity: success
comments: MU BAKER WINDOWMASTER WHIPSTOCK + MILLING ASSEMBLY & ASSOCIATED BHA. CONTINUE TIH WITH DP.
md@uom: m
```

From `15_9_19_A_1997_07_27.xml`:

```
dTimStart: 1997-07-26T00:00:00+02:00
dTimEnd: 1997-07-26T00:30:00+02:00
md: 2196
phase: fixed
proprietaryCode: drilling -- circulating conditioning
state: ok
stateDetailActivity: success
comments: COMPLETED CIRCULATING HOLE CLEAN. FLUSHED CHOKE & KILL LINES.
md@uom: m
```

From `15_9_19_A_1997_07_30.xml`:

```
dTimStart: 1997-07-29T00:00:00+02:00
dTimEnd: 1997-07-29T01:00:00+02:00
md: 2202
phase: fixed
proprietaryCode: interruption -- sidetrack
state: ok
stateDetailActivity: success
comments: FINISHED DRILLING TO 2202 M - TOTAL OF 19 M OF FORMATION DRILLED BEYOND WINDOW'S BOTTOM. PU & SO THROUGH WINDOW 5 TIMES - NO PROBLEMS.
md@uom: m
```

Computed by `well_ops.ingestion.audit.audit_ddr_activities`.
<!-- /audit:ddr-activities -->

Yes: a duration can be computed for every activity from `dTimStart` and `dTimEnd`. The activity
record has one `md` (measured depth) per activity, not a start and an end depth.

### 1.3 Activity classification codes

<!-- audit:ddr-codes -->
64 distinct codes in 7 categories. The code is the `proprietaryCode` element, written as `category -- subcategory`.

| Category | Activities |
|---|---|
| drilling | 9137 |
| plug abandon | 4595 |
| interruption | 3577 |
| completion | 2944 |
| workover | 2221 |
| formation evaluation | 732 |
| moving | 241 |

| Category | Subcategory | Activities |
|---|---|---|
| completion | bop/wellhead equipment | 930 |
| completion | circulating conditioning | 647 |
| completion | perforate | 469 |
| completion | completion string | 406 |
| completion | other | 298 |
| completion | test scsssv | 71 |
| completion | wire line | 65 |
| completion | sand control | 57 |
| completion | stimulate | 1 |
| drilling | casing | 3204 |
| drilling | drill | 1822 |
| drilling | trip | 1430 |
| drilling | bop/wellhead equipment | 1252 |
| drilling | other | 572 |
| drilling | circulating conditioning | 357 |
| drilling | bop activities | 226 |
| drilling | survey | 115 |
| drilling | ream | 97 |
| drilling | wait | 32 |
| drilling | pressure detection | 24 |
| drilling | hole open | 6 |
| formation evaluation | log | 206 |
| formation evaluation | rig up/down | 143 |
| formation evaluation | trip | 109 |
| formation evaluation | drill stem test | 86 |
| formation evaluation | circulating conditioning | 73 |
| formation evaluation | rft/fit | 69 |
| formation evaluation | core | 20 |
| formation evaluation | circulation samples | 11 |
| formation evaluation | other | 10 |
| formation evaluation | wait | 5 |
| interruption | other | 1202 |
| interruption | repair | 806 |
| interruption | waiting on weather | 445 |
| interruption | maintain | 310 |
| interruption | fish | 246 |
| interruption | wait | 229 |
| interruption | sidetrack | 202 |
| interruption | lost circulation | 75 |
| interruption | rig up/down | 33 |
| interruption | well control | 29 |
| moving | skid | 166 |
| moving | anchor | 32 |
| moving | transit | 27 |
| moving | position | 16 |
| plug abandon | other | 2332 |
| plug abandon | cement plug | 558 |
| plug abandon | cut | 421 |
| plug abandon | trip | 407 |
| plug abandon | equipment recovery | 248 |
| plug abandon | mill | 238 |
| plug abandon | mechanical plug | 156 |
| plug abandon | perforate | 113 |
| plug abandon | circulating conditioning | 97 |
| plug abandon | wait | 17 |
| plug abandon | squeeze | 8 |
| workover | wire line | 868 |
| workover | rig up/down | 429 |
| workover | perforate | 347 |
| workover | other | 326 |
| workover | bop/wellhead equipment | 104 |
| workover | completion string | 94 |
| workover | test scsssv | 28 |
| workover | wait | 25 |

Computed by `well_ops.ingestion.audit.audit_ddr_codes`.
<!-- /audit:ddr-codes -->

The activity record has no separate time classification (for example productive versus
non-productive time). The `interruption` category is the closest candidate, but treating it as
non-productive time would be a definition this project adopts, not something the reports state.

### 1.4 Depth and hole size in the report status

<!-- audit:ddr-status -->
Elements of `statusInfo` related to depth and hole size, over 1,759 reports. '-999.99' is the value used where nothing was recorded.

| Element | Reports with it | Value -999.99 | Unit (uom) | datum attribute |
|---|---|---|---|---|
| md | 1759 | 331 | m | none |
| tvd | 1229 | 0 | m | none |
| mdPlanned | 1759 | 1759 | m | none |
| distDrill | 1759 | 1247 | m | none |
| diaHole | 769 | 0 | in | none |
| dTimDiaHoleStart | 1752 | 0 |  | none |
| mdDiaHoleStart | 1632 | 0 | m | none |
| diaPilot | 19 | 0 | in | none |
| mdCsgLast | 1702 | 0 | m | none |
| tvdCsgLast | 1321 | 0 | m | none |
| mdKickoff | 248 | 0 | m | none |
| mdPlugTop | 329 | 0 | m | none |
| elevKelly | 1751 | 0 | m | none |
| waterDepth | 1759 | 0 | m | none |

Computed by `well_ops.ingestion.audit.audit_ddr_status`.
<!-- /audit:ddr-status -->

Depths are given in metres and hole and pilot diameters in inches, with the unit in the `uom`
attribute. None of these elements carries a `datum` attribute, so the depth reference is not
stated in the status block; the kelly bushing elevation is given separately in `elevKelly`.
`diaHole` is present in fewer than half of the reports; `mdDiaHoleStart` and `dTimDiaHoleStart`
say where and when the current hole section started. `-999.99` is a placeholder for "not recorded"
and must be treated as missing, never as a depth.

## 2. Volve real-time WITSML

Files: `data/raw/volve/WITSML Realtime drilling data/`. The folder holds a zip archive and, next to
it, extracted folders organised as `well folder / wellbore number / object type / files`.

<!-- audit:witsml -->
The zip `Volve - Real Time drilling data 13.05.2018.zip` lists 20,086 files, 19,337.7 MB uncompressed. The extracted folders next to it hold 11,893 files, 28.1 MB. 0 extracted files are absent from the zip. Files only in the zip, by object type: log: 8,193.

Totals by object type (zip):

| Object type | Files | MB |
|---|---|---|
| _wellboreInfo | 33 | 0.0 |
| bhaRun | 175 | 0.2 |
| log | 8,282 | 19,309.7 |
| message | 11,151 | 11.8 |
| mudLog | 16 | 3.6 |
| rig | 35 | 0.1 |
| trajectory | 92 | 10.6 |
| tubular | 208 | 1.6 |
| wbGeometry | 43 | 0.1 |

Per wellbore (33 wellbore folders; cells are files / MB, uncompressed). Wellbore names come from each well folder's `MetaFileInfo.txt`.

| Wellbore | Well folder | _wellboreInfo | bhaRun | log | message | mudLog | rig | trajectory | tubular | wbGeometry |
|---|---|---|---|---|---|---|---|---|---|---|
| 15/9-F-1 - Main Wellbore | Norway-NA-15/9-F-1 | 1 / 0.0 |  | 12 / 38.3 |  |  |  | 2 / 0.0 |  |  |
| 15/9-F-10 - Main Wellbore | Norway-StatoilHydro-15/9-F-10 | 1 / 0.0 |  | 288 / 1,620.2 |  |  |  | 6 / 1.7 |  |  |
| 15/9-F-12 - Main Wellbore | Norway-Statoil-15/9-F-12 | 1 / 0.0 |  | 256 / 1,024.9 |  |  |  | 9 / 1.6 |  |  |
| 15/9-F-14 - Main Wellbore | Norway-StatoilHydro-15/9-F-14 | 1 / 0.0 |  | 196 / 992.0 |  |  |  | 6 / 0.5 |  |  |
| 15/9-F-15 - Main Wellbore | Norway-StatoilHydro-15/9-F-15 | 1 / 0.0 |  | 100 / 556.1 |  |  |  | 3 / 0.4 |  |  |
| 15/9-F-15A - Main Wellbore | Norway-StatoilHydro-15/9-F-15A | 1 / 0.0 |  | 123 / 773.0 |  |  |  | 3 / 0.4 |  |  |
| 15/9-F-15B - Main Wellbore | Norway-StatoilHydro-15/9-F-15B | 1 / 0.0 |  | 22 / 104.6 |  |  |  | 2 / 0.2 |  |  |
| 15/9-F-15S - Main Wellbore | Norway-StatoilHydro-15/9-F-15S | 1 / 0.0 |  | 211 / 1,050.2 |  |  |  | 3 / 0.4 |  |  |
| 15/9-F-4 - Main Wellbore | Norway-StatoilHydro-15/9-F-4 | 1 / 0.0 |  | 243 / 1,342.8 | 6 / 0.0 |  |  | 6 / 0.7 |  |  |
| 15/9-F-5 - Main Wellbore | NA-NA-15/9-F-5 | 1 / 0.0 |  | 18 / 77.4 |  |  |  |  |  |  |
| 15/9-F-5 - Main Wellbore | Norway-StatoilHydro-15/9-F-5 | 1 / 0.0 |  | 145 / 673.5 |  |  |  | 5 / 0.5 |  |  |
| 15/9-F-7 - Main Wellbore | Norway-Statoil-15/9-F-7 | 1 / 0.0 |  | 82 / 304.4 |  |  |  | 4 / 0.2 |  |  |
| 15/9-F-9 - Main Wellbore | Norway-StatoilHydro-15/9-F-9 | 1 / 0.0 |  | 59 / 259.4 |  |  |  | 4 / 0.1 |  |  |
| 15/9-F-9 A - Main Wellbore | Norway-NA-15/9-F-9 A | 1 / 0.0 |  | 54 / 342.3 |  |  |  | 3 / 0.1 |  |  |
| 17 1/2" Final QAQCd Data | Norway-StatoilHydro-15/9-F-14 | 1 / 0.0 |  | 4 / 0.0 |  |  |  |  |  |  |
| EcoScope_Customer_Run5 | Norway-StatoilHydro-15/9-F-4 | 1 / 0.0 |  | 4 / 0.0 |  |  |  |  |  |  |
| NO 15/9-F-1 | Norway-Statoil-NO 15/9-F-1 C | 1 / 0.0 | 12 / 0.0 | 567 / 687.7 | 953 / 1.1 | 2 / 0.4 | 2 / 0.0 | 3 / 0.3 | 12 / 0.1 | 3 / 0.0 |
| NO 15/9-F-1 A | Norway-Statoil-NO 15/9-F-1 C | 1 / 0.0 | 4 / 0.0 | 300 / 252.1 | 256 / 0.3 | 2 / 0.4 | 2 / 0.0 | 2 / 0.2 | 4 / 0.0 | 3 / 0.0 |
| NO 15/9-F-1 B | Norway-Statoil-NO 15/9-F-1 C | 1 / 0.0 | 18 / 0.0 | 702 / 1,182.6 | 994 / 1.1 | 2 / 0.1 | 2 / 0.0 | 2 / 0.1 | 18 / 0.2 | 2 / 0.0 |
| NO 15/9-F-1 C | Norway-Statoil-NO 15/9-F-1 C | 1 / 0.0 | 27 / 0.0 | 990 / 1,465.4 | 2,052 / 2.1 | 2 / 0.2 | 3 / 0.0 | 3 / 0.4 | 30 / 0.2 | 5 / 0.0 |
| NO 15/9-F-11 | Norway-Statoil-NO 15/9-F-11 | 1 / 0.0 |  | 306 / 329.0 | 65 / 0.1 |  | 2 / 0.0 | 2 / 0.0 | 9 / 0.1 | 2 / 0.0 |
| NO 15/9-F-11 A | Norway-Statoil-NO 15/9-F-11 | 1 / 0.0 | 3 / 0.0 | 302 / 342.2 | 307 / 0.3 | 2 / 0.4 | 2 / 0.0 | 2 / 0.4 | 3 / 0.0 | 2 / 0.0 |
| NO 15/9-F-11 B | Norway-Statoil-NO 15/9-F-11 | 1 / 0.0 | 27 / 0.0 | 752 / 1,248.7 | 1,289 / 1.3 | 2 / 0.6 | 3 / 0.0 | 4 / 1.1 | 26 / 0.2 | 4 / 0.0 |
| NO 15/9-F-11 T2 | Norway-Statoil-NO 15/9-F-11 | 1 / 0.0 | 13 / 0.0 | 756 / 1,141.7 | 603 / 0.6 | 2 / 1.1 | 2 / 0.0 | 2 / 0.3 | 14 / 0.4 | 2 / 0.0 |
| NO 15/9-F-12 | Norway-Statoil-NO 15/9-F-12 | 1 / 0.0 | 11 / 0.0 | 122 / 280.0 | 660 / 0.7 |  | 2 / 0.0 | 2 / 0.3 | 10 / 0.0 | 4 / 0.0 |
| NO 15/9-F-14 | Norway-Statoil-NO 15/9-F-14 | 1 / 0.0 | 8 / 0.0 | 168 / 387.3 | 581 / 0.6 |  | 2 / 0.0 | 2 / 0.1 | 7 / 0.0 | 3 / 0.0 |
| NO 15/9-F-15 C | Norway-Statoil-NO 15/9-F-15 | 1 / 0.0 | 15 / 0.0 | 258 / 583.3 | 502 / 0.5 |  | 2 / 0.0 | 2 / 0.1 | 15 / 0.0 | 2 / 0.0 |
| NO 15/9-F-15 D | Norway-Statoil-NO 15/9-F-15 | 1 / 0.0 | 17 / 0.0 | 960 / 1,736.4 | 2,205 / 2.4 | 2 / 0.4 | 3 / 0.0 | 2 / 0.1 | 37 / 0.2 | 3 / 0.0 |
| NO 15/9-F-4 | Norway-Statoil-NO 15/9-F-4 | 1 / 0.0 | 5 / 0.0 | 71 / 143.7 | 93 / 0.1 |  | 2 / 0.0 | 2 / 0.1 | 4 / 0.0 | 2 / 0.0 |
| NO 15/9-F-5 | Norway-Statoil-NO 15/9-F-5 | 1 / 0.0 | 12 / 0.0 | 141 / 305.8 | 491 / 0.5 |  | 2 / 0.0 | 2 / 0.1 | 10 / 0.0 | 2 / 0.0 |
| NO 15/9-F-7 | Norway-Statoil-NO 15/9-F-7 | 1 / 0.0 |  | 34 / 35.9 | 37 / 0.0 |  | 2 / 0.0 | 2 / 0.1 | 6 / 0.0 | 2 / 0.0 |
| NO 15/9-F-9 A | Norway-Statoil-NO 15/9-F-9 | 1 / 0.0 | 3 / 0.0 | 32 / 28.5 | 57 / 0.1 |  | 2 / 0.0 | 2 / 0.0 | 3 / 0.0 | 2 / 0.0 |
| test | Norway-StatoilHydro-15/9-F-9 | 1 / 0.0 |  | 4 / 0.0 |  |  |  |  |  |  |

Computed by `well_ops.ingestion.audit.audit_witsml`.
<!-- /audit:witsml -->

The extracted folders are the zip's contents without the `log` data files: every extracted file is
also in the zip, and the files found only in the zip are all `log` files. The `log` object type,
which holds the real-time curves, makes up almost the entire volume and is only inside the zip.
Wellbore folders do not correspond one-to-one with wellbores: the same wellbore appears under
several well folders whose names carry different operator names (`NA`, `Statoil`, `StatoilHydro`),
and some wellbore folders are not named after a wellbore (`test`, `EcoScope_Customer_Run5`, a
"Final QAQCd Data" folder).

## 3. Volve production workbook

File: `data/raw/volve/Production_data/Volve production data.xlsx`.

<!-- audit:production -->
**Sheet 'Daily Production Data'**: 15,634 data rows, 2007-09-01 to 2016-12-01.

Columns: `DATEPRD`, `WELL_BORE_CODE`, `NPD_WELL_BORE_CODE`, `NPD_WELL_BORE_NAME`, `NPD_FIELD_CODE`, `NPD_FIELD_NAME`, `NPD_FACILITY_CODE`, `NPD_FACILITY_NAME`, `ON_STREAM_HRS`, `AVG_DOWNHOLE_PRESSURE`, `AVG_DOWNHOLE_TEMPERATURE`, `AVG_DP_TUBING`, `AVG_ANNULUS_PRESS`, `AVG_CHOKE_SIZE_P`, `AVG_CHOKE_UOM`, `AVG_WHP_P`, `AVG_WHT_P`, `DP_CHOKE_SIZE`, `BORE_OIL_VOL`, `BORE_GAS_VOL`, `BORE_WAT_VOL`, `BORE_WI_VOL`, `FLOW_KIND`, `WELL_TYPE`
- `AVG_CHOKE_UOM` values: '%' (9,161), '' (6,473)
- `FLOW_KIND` values: 'production' (9,161), 'injection' (6,473)
- `WELL_TYPE` values: 'OP' (9,143), 'WI' (6,491)

| Well | Rows |
|---|---|
| NO 15/9-F-1 C | 746 |
| NO 15/9-F-11 H | 1165 |
| NO 15/9-F-12 H | 3056 |
| NO 15/9-F-14 H | 3056 |
| NO 15/9-F-15 D | 978 |
| NO 15/9-F-4 AH | 3327 |
| NO 15/9-F-5 AH | 3306 |

Cells holding the text 'NULL': none.

This sheet has no units row and no unit in its column names; units are **unknown** from the workbook itself.

**Sheet 'Monthly Production Data'**: 526 data rows, 2007-09 to 2016-12.

Columns: `Wellbore name`, `NPDCode`, `Year`, `Month`, `On Stream`, `Oil`, `Gas`, `Water`, `GI`, `WI`

| Well | Rows |
|---|---|
| 15/9-F-1 C | 25 |
| 15/9-F-11 | 39 |
| 15/9-F-12 | 104 |
| 15/9-F-14 | 104 |
| 15/9-F-15 D | 33 |
| 15/9-F-4 | 112 |
| 15/9-F-5 | 109 |

Cells holding the text 'NULL': `On Stream` 11, `Oil` 215, `Gas` 215, `Water` 215, `GI` 526, `WI` 325.

Units, from the row under the header:

| Column | Unit |
|---|---|
| Wellbore name | (none) |
| NPDCode | (none) |
| Year | (none) |
| Month | (none) |
| On Stream | hrs |
| Oil | Sm3 |
| Gas | Sm3 |
| Water | Sm3 |
| GI | Sm3 |
| WI | Sm3 |

Computed by `well_ops.ingestion.audit.audit_production`.
<!-- /audit:production -->

The units of the daily sheet are **unknown**: it has no units row, and its volume, pressure and
temperature column names carry no unit. Its only unit column is `AVG_CHOKE_UOM`. The monthly
sheet states `Sm3` for volumes and `hrs` for on-stream time in the row under its header, and uses
the text `NULL` rather than empty cells where there is no value.

## 4. Well identifiers across sources

Sources compared: drilling reports (`nameWellbore`), WITSML (`MetaFileInfo.txt` names), the
production workbook (both sheets), well picks, well perforations, the EDM file (`well_legal_name`
and `wellbore_name` attributes only), and the Sodir wellbore tables.

<!-- audit:identifiers -->
223 distinct (source, name) pairs in Volve sources; 27 Sodir wellbores have `wlbField` VOLVE. Proposed canonical name: the Sodir `wlbWellboreName`. Matching uses the Sodir NPDID when the source carries one (drilling reports: `wellboreAlias` 'NPD number'; production: `NPD_WELL_BORE_CODE` / `NPDCode`), otherwise the normalised name (`normalise_well_name`: decode `$NN$`, drop a leading 'NO ' and a trailing ' - Main Wellbore', single spaces, split a glued suffix such as 'F-15A'). Raw names matched by NPDID are marked (NPDID).

NPDID and name disagree for 0 names.

| Canonical (Sodir) | Volve field in Sodir | Names in Volve sources |
|---|---|---|
| 15/5-7 A | no | Well picks: NO 15/5-7 A |
| 15/9-11 | no | Well picks: NO 15/9-11 |
| 15/9-17 | no | Well picks: NO 15/9-17 |
| 15/9-19 A | yes | DDR: NO 15/9-19 A (NPDID); EDM well_legal_name: NO 15/9-19 A; Well picks: NO 15/9-19 A |
| 15/9-19 B | yes | DDR: NO 15/9-19 B (NPDID); DDR: NO 15/9-19 BT2 (NPDID); EDM well_legal_name: NO 15/9-19 B; Well picks: NO 15/9-19 B |
| 15/9-19 S | yes | DDR: NO 15/9-19 S (NPDID); DDR: NO 15/9-19 ST2 (NPDID); EDM well_legal_name: NO 15/9-19 S |
| 15/9-19 SR | yes | EDM well_legal_name: NO 15/9-19 SR; Well picks: NO 15/9-19 SR |
| 15/9-19 SR2 | yes | (Sodir only) |
| 15/9-4 | no | Well picks: NO 15/9-4 |
| 15/9-8 | no | Well picks: NO 15/9-8 |
| 15/9-A-15 | no | Well perforations: NO 15/9-A-15; Well picks: NO 15/9-A-15 |
| 15/9-B-6 | no | Well perforations: NO 15/9-B-6; Well picks: NO 15/9-B-6 |
| 15/9-C-2 AH | no | Well perforations: NO 15/9-C-2 AH; Well picks: NO 15/9-C-2 AH |
| 15/9-C-2 H | no | Well perforations: NO 15/9-C-2 H; Well picks: NO 15/9-C-2 H |
| 15/9-F-1 | yes | DDR: NO 15/9-F-1 (NPDID); EDM well_legal_name: NO 15/9-F-1; WITSML: 15/9-F-1; WITSML: 15/9-F-1 - Main Wellbore; WITSML: NO 15/9-F-1; Well picks: NO 15/9-F-1 |
| 15/9-F-1 A | yes | DDR: NO 15/9-F-1 A (NPDID); EDM well_legal_name: NO 15/9-F-1 A; WITSML: NO 15/9-F-1 A; Well picks: NO 15/9-F-1 A |
| 15/9-F-1 B | yes | DDR: NO 15/9-F-1 B (NPDID); EDM well_legal_name: NO 15/9-F-1 B; WITSML: NO 15/9-F-1 B; Well perforations: NO 15/9-F-1 B; Well picks: NO 15/9-F-1 B |
| 15/9-F-1 C | yes | DDR: NO 15/9-F-1 C (NPDID); EDM well_legal_name: NO 15/9-F-1 C; Production daily: 15/9-F-1 C (NPDID); Production daily: NO 15/9-F-1 C (NPDID); Production monthly: 15/9-F-1 C (NPDID); WITSML: 15/9-F-1 C; WITSML: NO 15/9-F-1 C; Well picks: NO 15/9-F-1 C |
| 15/9-F-10 | yes | DDR: NO 15/9-F-10 (NPDID); EDM well_legal_name: NO 15/9-F-10; WITSML: 15/9-F-10; WITSML: 15/9-F-10 - Main Wellbore; Well picks: NO 15/9-F-10 |
| 15/9-F-10 A | yes | (Sodir only) |
| 15/9-F-10 B | yes | (Sodir only) |
| 15/9-F-11 | yes | DDR: NO 15/9-F-11 (NPDID); DDR: NO 15/9-F-11 T2 (NPDID); EDM well_legal_name: NO 15/9-F-11; EDM wellbore_name: 15/9-F-11; Production daily: 15/9-F-11 (NPDID); Production daily: NO 15/9-F-11 H (NPDID); Production monthly: 15/9-F-11 (NPDID); WITSML: NO 15/9-F-11; Well picks: NO 15/9-F-11 |
| 15/9-F-11 A | yes | DDR: NO 15/9-F-11 A (NPDID); EDM well_legal_name: NO 15/9-F-11 A; EDM wellbore_name: 15/9-F-11 A; WITSML: NO 15/9-F-11 A; Well picks: NO 15/9-F-11 A |
| 15/9-F-11 B | yes | DDR: NO 15/9-F-11 B (NPDID); EDM well_legal_name: NO 15/9-F-11 B; EDM wellbore_name: 15/9-F-11 B; WITSML: 15/9-F-11 B; WITSML: NO 15/9-F-11 B; Well perforations: NO 15/9-F-11 B; Well picks: NO 15/9-F-11 B |
| 15/9-F-12 | yes | DDR: NO 15/9-F-12 (NPDID); EDM well_legal_name: NO 15/9-F-12; Production daily: 15/9-F-12 (NPDID); Production daily: NO 15/9-F-12 H (NPDID); Production monthly: 15/9-F-12 (NPDID); WITSML: 15/9-F-12; WITSML: 15/9-F-12 - Main Wellbore; WITSML: NO 15/9-F-12; Well perforations: NO 15/9-F-12; Well picks: NO 15/9-F-12 |
| 15/9-F-14 | yes | DDR: NO 15/9-F-14 (NPDID); EDM well_legal_name: NO 15/9-F-14; Production daily: 15/9-F-14 (NPDID); Production daily: NO 15/9-F-14 H (NPDID); Production monthly: 15/9-F-14 (NPDID); WITSML: 15/9-F-14; WITSML: 15/9-F-14 - Main Wellbore; WITSML: NO 15/9-F-14; Well perforations: NO 15/9-F-14; Well picks: NO 15/9-F-14 |
| 15/9-F-15 | yes | DDR: NO 15/9-F-15 (NPDID); EDM well_legal_name: NO 15/9-F-15; WITSML: 15/9-F-15; WITSML: 15/9-F-15 - Main Wellbore; WITSML: NO 15/9-F-15; Well picks: NO 15/9-F-15 |
| 15/9-F-15 A | yes | DDR: NO 15/9-F-15 A (NPDID); EDM well_legal_name: NO 15/9-F-15 A; WITSML: 15/9-F-15A; WITSML: 15/9-F-15A - Main Wellbore; Well picks: NO 15/9-F-15 A |
| 15/9-F-15 B | yes | DDR: NO 15/9-F-15 B (NPDID); EDM well_legal_name: NO 15/9-F-15 B; WITSML: 15/9-F-15B; WITSML: 15/9-F-15B - Main Wellbore; Well picks: NO 15/9-F-15 B |
| 15/9-F-15 C | yes | DDR: NO 15/9-F-15 C (NPDID); EDM well_legal_name: NO 15/9-F-15 C; WITSML: NO 15/9-F-15 C; Well perforations: NO 15/9-F-15 C; Well picks: NO 15/9-F-15 C |
| 15/9-F-15 D | yes | DDR: NO 15/9-F-15 D (NPDID); EDM well_legal_name: NO 15/9-F-15 D; Production daily: 15/9-F-15 D (NPDID); Production daily: NO 15/9-F-15 D (NPDID); Production monthly: 15/9-F-15 D (NPDID); WITSML: NO 15/9-F-15 D; Well picks: NO 15/9-F-15 D |
| 15/9-F-4 | yes | DDR: NO 15/9-F-4 (NPDID); EDM well_legal_name: NO 15/9-F-4; Production daily: 15/9-F-4 (NPDID); Production daily: NO 15/9-F-4 AH (NPDID); Production monthly: 15/9-F-4 (NPDID); WITSML: 15/9-F-4; WITSML: 15/9-F-4 - Main Wellbore; WITSML: NO 15/9-F-4; Well perforations: NO 15/9-F-4; Well picks: NO 15/9-F-4 |
| 15/9-F-5 | yes | DDR: NO 15/9-F-5 (NPDID); EDM well_legal_name: NO 15/9-F-5; Production daily: 15/9-F-5 (NPDID); Production daily: NO 15/9-F-5 AH (NPDID); Production monthly: 15/9-F-5 (NPDID); WITSML: 15/9-F-5; WITSML: 15/9-F-5 - Main Wellbore; WITSML: NO 15/9-F-5; Well perforations: NO 15/9-F-5; Well picks: NO 15/9-F-5 |
| 15/9-F-7 | yes | DDR: NO 15/9-F-7 (NPDID); EDM well_legal_name: NO 15/9-F-7; WITSML: 15/9-F-7; WITSML: 15/9-F-7 - Main Wellbore; WITSML: NO 15/9-F-7; Well picks: NO 15/9-F-7 |
| 15/9-F-9 | yes | DDR: NO 15/9-F-9 (NPDID); EDM well_legal_name: NO 15/9-F-9; WITSML: 15/9-F-9; WITSML: 15/9-F-9 - Main Wellbore; WITSML: NO 15/9-F-9; Well picks: NO 15/9-F-9 |
| 15/9-F-9 A | yes | DDR: NO 15/9-F-9 A (NPDID); EDM well_legal_name: NO 15/9-F-9 A; WITSML: 15/9-F-9 A; WITSML: 15/9-F-9 A - Main Wellbore; WITSML: NO 15/9-F-9 A |

**Cannot be matched** to any Sodir wellbore (59 names):

| Raw name | Sources |
|---|---|
| 15/9-F-11 T2 | EDM wellbore_name |
| 15/9-F-15S | WITSML |
| 15/9-F-15S - Main Wellbore | WITSML |
| 17 1/2" Final QAQCd Data | WITSML |
| 19 A | EDM wellbore_name |
| 19 B | EDM wellbore_name |
| 19 BT2 | EDM wellbore_name |
| 19 S | EDM wellbore_name |
| 19 SR | EDM wellbore_name |
| EcoScope_Customer_Run5 | WITSML |
| F-1 | EDM wellbore_name |
| F-1 A | EDM wellbore_name |
| F-1 A  Northwest Injector 9 5/8" csg.shoe | EDM wellbore_name |
| F-1 A Northwest Injector 9 5/8" csg. shoe | EDM wellbore_name |
| F-1 A Nortwest Injector 9 5/8" csg. shoe | EDM wellbore_name |
| F-1 B | EDM wellbore_name |
| F-1 B 9 5/8" csg.shoe | EDM wellbore_name |
| F-1 C | EDM wellbore_name |
| F-1 North Upside Pilot 13 3/8" csg. shoe | EDM wellbore_name |
| F-1 North Upside Pilot 13 3/8" csg.shoe | EDM wellbore_name |
| F-10 | EDM wellbore_name |
| F-10 A | EDM well_legal_name, EDM wellbore_name |
| F-12 | EDM wellbore_name |
| F-13 | EDM wellbore_name |
| F-14 | EDM wellbore_name |
| F-14 A | EDM wellbore_name |
| F-15 | EDM wellbore_name |
| F-15 C Top Reservoir Intersection | EDM wellbore_name |
| F-15 C Top Resevoir Intersection | EDM wellbore_name |
| F-15 D | EDM wellbore_name |
| F-15A | EDM wellbore_name |
| F-15B | EDM wellbore_name |
| F-15C | EDM wellbore_name |
| F-15D | EDM wellbore_name |
| F-2 | EDM wellbore_name |
| F-3 | EDM wellbore_name |
| F-4 | EDM wellbore_name |
| F-5 | EDM wellbore_name |
| F-6 | EDM wellbore_name |
| F-7 | EDM wellbore_name |
| F-8 | EDM wellbore_name |
| F-8 A | EDM wellbore_name |
| F-9 | EDM wellbore_name |
| F-9 A | EDM wellbore_name |
| NO 15/9-19 | EDM well_legal_name |
| NO 15/9-19 BT2 | EDM well_legal_name, Well picks |
| NO 15/9-C-2 AHT2 | Well perforations, Well picks |
| NO 15/9-F-11 T2 | EDM well_legal_name, WITSML, Well picks |
| NO 15/9-F-12 pilot | Well picks |
| NO 15/9-F-13 | EDM well_legal_name |
| NO 15/9-F-2 | EDM well_legal_name |
| NO 15/9-F-3 | EDM well_legal_name |
| NO 15/9-F-6 | EDM well_legal_name |
| NO 15/9-F-8 | EDM well_legal_name |
| Relief well 1049m West | EDM wellbore_name |
| Relief well 1352m South | EDM wellbore_name |
| Relief well 508m West | EDM wellbore_name |
| Relief well 966m North | EDM wellbore_name |
| test | WITSML |

Computed by `well_ops.ingestion.audit.audit_identifiers`, `well_ops.ingestion.audit.match_well_names`, `well_ops.ingestion.audit.normalise_well_name`.
<!-- /audit:identifiers -->

How to read the unmatched list:

- **Technical sidetracks** (`F-11 T2`, `19 BT2`, `19 ST2`) are not separate wellbores in Sodir.
  The drilling reports link them to the parent wellbore through the NPD number; sources without
  an NPD number cannot be matched by name.
- **Production workbook suffixes** (`AH`, `H` in `WELL_BORE_CODE`) differ from Sodir names. These
  rows are matched only because the workbook carries the NPDID.
- **EDM short names** (`F-1`, `19 A`) lack the `15/9-` prefix, and some EDM wellbores are planning
  objects (relief wells, "csg. shoe" and "Top Reservoir Intersection" targets), not drilled
  wellbores.
- **WITSML** folder names include names that are not wellbores, and `15/9-F-15S`, which has no
  Sodir counterpart under any rule used here.
- **EDM wells without a Sodir wellbore:** `NO 15/9-F-2`, `F-3`, `F-6`, `F-8` and `F-13`.

The well picks and perforations files also cover wells outside the Volve field; these are marked
"no" in the "Volve field in Sodir" column.

## 5. Sodir monthly production for VOLVE

Files: `data/raw/sodir/field_production_monthly.csv`, exported from the FactPages table view
*Field > Table view > Production > Saleable > Monthly*, and
`data/raw/sodir/field_production_gross_monthly.csv`, exported from
*Field > Table view > Production > Sum wellbores > Monthly – by field*.

<!-- audit:sodir-production -->
**Table `field_production_monthly`**, rows with `prfInformationCarrier` = VOLVE: 114 months, 2008-02 to 2017-07.

Columns: `prfInformationCarrier`, `prfYear`, `prfMonth`, `prfPrdOilNetMillSm3`, `prfPrdGasNetBillSm3`, `prfPrdNGLNetMillSm3`, `prfPrdCondensateNetMillSm3`, `prfPrdOeNetMillSm3`, `prfPrdProducedWaterInFieldMillSm3`, `prfNpdidInformationCarrier`

| Column | Unit (from the column name) | Decimal places |
|---|---|---|
| prfPrdOilNetMillSm3 | million Sm3 | 5 |
| prfPrdGasNetBillSm3 | billion Sm3 | 5 |
| prfPrdNGLNetMillSm3 | million Sm3 | 5 |
| prfPrdCondensateNetMillSm3 | million Sm3 | 5 |
| prfPrdOeNetMillSm3 | million Sm3 | 5 |
| prfPrdProducedWaterInFieldMillSm3 | million Sm3 | 5 |

**Table `field_production_gross_monthly`**, rows with `prfInformationCarrier` = VOLVE: 114 months, 2008-02 to 2017-07.

Columns: `prfInformationCarrier`, `prfYear`, `prfMonth`, `prfPrdOilGrossMillSm3`, `prfPrdGasGrossBillSm3`, `prfPrdCondensateGrossMillSm3`, `prfPrdOeGrossMillSm3`, `prfPrdProducedWaterInFieldMillSm3`, `prfNpdidInformationCarrier`

| Column | Unit (from the column name) | Decimal places |
|---|---|---|
| prfPrdOilGrossMillSm3 | million Sm3 | 5 |
| prfPrdGasGrossBillSm3 | billion Sm3 | 5 |
| prfPrdCondensateGrossMillSm3 | million Sm3 | 5 |
| prfPrdOeGrossMillSm3 | million Sm3 | 5 |
| prfPrdProducedWaterInFieldMillSm3 | million Sm3 | 5 |

Computed by `well_ops.ingestion.audit.audit_sodir_production`.
<!-- /audit:sodir-production -->

## 6. Reporting basis: Sodir field volumes versus the Volve workbook

**Definitions.** Sodir's *Guidelines for monthly production data to authorities (Green Book)*,
version 1.1, 1 January 2024
(<https://www.sodir.no/48dfb3/globalassets/1-sodir/regelverk/veiledninger/green-book.pdf>),
section 2.1, defines the two bases:

> The "saleable quantity", as it occurs in the MPRML-file, is the quantity where fuel and flare
> are deducted.

> The "allocated quantity", as it occurs in the MPRML-file, is the sum of all wells belonging to
> that field or facility.

**Which table is which.** The FactPages table *Production > Saleable*
(`field_production_monthly`) is on the saleable basis: the attribute page
(<https://factpages.sodir.no/en/field/Attributes>, retrieved 2026-10-28) labels its columns
"Net – oil [mill Sm3]" (`prfPrdOilNetMillSm3`) and "Net – gas [bill Sm3]" (`prfPrdGasNetBillSm3`).
The table *Production > Sum wellbores* (`field_production_gross_monthly`) is on the allocated,
sum-of-wells basis: its columns are labelled "Gross – oil [mill Sm3]" (`prfPrdOilGrossMillSm3`)
and "Gross – gas [bill Sm3]" (`prfPrdGasGrossBillSm3`). The Green Book defines quantities in the
MPRML report file and does not name the FactPages tables, so this correspondence rests on the
table and column names.

**Does the workbook match the gross basis?** Largely, yes, for oil and gas. The workbook's monthly
sheet, summed over wells (`Oil`, `Gas`, in `Sm3`), equals the Sodir gross figures to within 1 % in
almost every month compared, with median ratios of 1.0000 for oil and 0.9999 for gas (table
below). It does not match the net basis for gas, which is lower than the workbook in every month
compared, as expected if fuel and flare are deducted. A few months differ from the gross figures
by more than 1 % (see the minimum ratios and the per-month tables); the reason for those months is
**unknown**. Also **unknown**: why Sodir net oil is slightly higher than gross oil in most months.
The Green Book notes that "Some of these liquid figures will be value adjusted and allocated by
means of its quality", but whether that explains the difference for VOLVE is not verified. Sodir
figures are published to five decimals of million or billion Sm3, which limits the precision of
any monthly ratio for small volumes (resolution given below). The daily sheet's volumes
(`BORE_OIL_VOL`, `BORE_GAS_VOL`, `BORE_WAT_VOL`) carry no unit and are not compared here.

<!-- audit:production-comparison -->
Three sources, VOLVE, converted to Sm3: the workbook's monthly sheet summed over wellbores; Sodir `field_production_gross_monthly` (sum wellbores, gross); Sodir `field_production_monthly` (saleable, net). Produced water has the same column in both Sodir tables.

Months with data per source ('listed' = the source has a row for the month):

| Source | Quantity | First | Last | Months listed | Months non-zero | Total Sm3 |
|---|---|---|---|---|---|---|
| Workbook (sum of wells) | Oil | 2007-09 | 2016-12 | 112 | 104 | 10,037,081 |
| Sodir gross (sum wellbores) | Oil | 2008-02 | 2017-07 | 114 | 104 | 10,069,630 |
| Sodir net (saleable) | Oil | 2008-02 | 2017-07 | 114 | 104 | 10,171,990 |
| Workbook (sum of wells) | Gas | 2007-09 | 2016-12 | 112 | 104 | 1,475,370,436 |
| Sodir gross (sum wellbores) | Gas | 2008-02 | 2017-07 | 114 | 101 | 1,449,570,000 |
| Sodir net (saleable) | Gas | 2008-02 | 2017-07 | 114 | 101 | 812,550,000 |
| Workbook (sum of wells) | Water | 2007-09 | 2016-12 | 112 | 104 | 15,318,578 |
| Sodir gross (sum wellbores) | Water | 2008-02 | 2017-07 | 114 | 99 | 15,343,620 |
| Sodir net (saleable) | Water | 2008-02 | 2017-07 | 114 | 99 | 15,343,620 |

Ratios, over months where both sides are non-zero:

| Quantity | Ratio | Months compared | Within 1 % | Median | Min | Max |
|---|---|---|---|---|---|---|
| Oil | workbook / gross | 104 | 100 | 1.0000 | 0.9226 | 1.0002 |
| Oil | workbook / net | 104 | 35 | 0.9837 | 0.8987 | 1.0148 |
| Oil | gross / net | 104 | 39 | 0.9863 | 0.8987 | 1.0152 |
| Gas | workbook / gross | 101 | 96 | 0.9999 | 0.8175 | 1.0088 |
| Gas | workbook / net | 101 | 0 | 1.8563 | 1.1903 | 764.6877 |
| Gas | gross / net | 99 | 0 | 1.8569 | 1.1903 | 765.0000 |
| Water | workbook / gross | 99 | 93 | 1.0000 | 0.3363 | 8.2522 |
| Water | workbook / net | 99 | 93 | 1.0000 | 0.3363 | 8.2522 |
| Water | gross / net | 99 | 99 | 1.0000 | 1.0000 | 1.0000 |

Resolution of the Sodir figures (largest number of decimals used, as Sm3): `prfPrdGasGrossBillSm3` 5 decimals = 10,000 Sm3, `prfPrdGasNetBillSm3` 5 decimals = 10,000 Sm3, `prfPrdOilGrossMillSm3` 5 decimals = 10 Sm3, `prfPrdOilNetMillSm3` 5 decimals = 10 Sm3.

<details>
<summary>Oil: ratios per month</summary>

| Month | Workbook Sm3 | Sodir gross Sm3 | Sodir net Sm3 | Workbook / gross | Workbook / net | Gross / net |
|---|---|---|---|---|---|---|
| 2007-09 | 0 | no row | no row |  |  |  |
| 2007-10 | 0 | no row | no row |  |  |  |
| 2007-11 | 0 | no row | no row |  |  |  |
| 2007-12 | 0 | no row | no row |  |  |  |
| 2008-01 | 0 | no row | no row |  |  |  |
| 2008-02 | 49,091 | 49,150 | 49,090 | 0.9988 | 1.0000 | 1.0012 |
| 2008-03 | 83,361 | 83,360 | 84,410 | 1.0000 | 0.9876 | 0.9876 |
| 2008-04 | 74,532 | 74,930 | 75,760 | 0.9947 | 0.9838 | 0.9890 |
| 2008-05 | 125,479 | 125,480 | 126,890 | 1.0000 | 0.9889 | 0.9889 |
| 2008-06 | 143,787 | 144,080 | 144,280 | 0.9980 | 0.9966 | 0.9986 |
| 2008-07 | 166,280 | 166,660 | 165,170 | 0.9977 | 1.0067 | 1.0090 |
| 2008-08 | 165,444 | 165,440 | 167,050 | 1.0000 | 0.9904 | 0.9904 |
| 2008-09 | 192,263 | 192,660 | 194,140 | 0.9979 | 0.9903 | 0.9924 |
| 2008-10 | 237,174 | 237,170 | 236,640 | 1.0000 | 1.0023 | 1.0022 |
| 2008-11 | 250,325 | 250,330 | 250,330 | 1.0000 | 1.0000 | 1.0000 |
| 2008-12 | 276,639 | 276,640 | 276,640 | 1.0000 | 1.0000 | 1.0000 |
| 2009-01 | 269,250 | 269,250 | 269,200 | 1.0000 | 1.0002 | 1.0002 |
| 2009-02 | 235,786 | 235,790 | 236,460 | 1.0000 | 0.9971 | 0.9972 |
| 2009-03 | 183,603 | 188,410 | 189,510 | 0.9745 | 0.9688 | 0.9942 |
| 2009-04 | 237,900 | 237,900 | 237,510 | 1.0000 | 1.0016 | 1.0016 |
| 2009-05 | 257,214 | 257,210 | 257,210 | 1.0000 | 1.0000 | 1.0000 |
| 2009-06 | 219,084 | 226,690 | 226,570 | 0.9664 | 0.9670 | 1.0005 |
| 2009-07 | 170,977 | 185,320 | 185,770 | 0.9226 | 0.9204 | 0.9976 |
| 2009-08 | 224,908 | 224,910 | 224,550 | 1.0000 | 1.0016 | 1.0016 |
| 2009-09 | 180,449 | 180,450 | 179,760 | 1.0000 | 1.0038 | 1.0038 |
| 2009-10 | 223,647 | 223,650 | 224,520 | 1.0000 | 0.9961 | 0.9961 |
| 2009-11 | 234,059 | 234,640 | 234,260 | 0.9975 | 0.9991 | 1.0016 |
| 2009-12 | 247,516 | 250,860 | 252,080 | 0.9867 | 0.9819 | 0.9952 |
| 2010-01 | 231,880 | 231,880 | 232,160 | 1.0000 | 0.9988 | 0.9988 |
| 2010-02 | 165,119 | 165,120 | 165,830 | 1.0000 | 0.9957 | 0.9957 |
| 2010-03 | 168,561 | 168,570 | 168,530 | 0.9999 | 1.0002 | 1.0002 |
| 2010-04 | 159,289 | 159,290 | 160,320 | 1.0000 | 0.9936 | 0.9936 |
| 2010-05 | 164,923 | 165,190 | 165,540 | 0.9984 | 0.9963 | 0.9979 |
| 2010-06 | 144,927 | 144,930 | 145,070 | 1.0000 | 0.9990 | 0.9990 |
| 2010-07 | 133,640 | 133,640 | 135,480 | 1.0000 | 0.9864 | 0.9864 |
| 2010-08 | 68,531 | 68,530 | 68,920 | 1.0000 | 0.9944 | 0.9943 |
| 2010-09 | 106,718 | 106,720 | 107,150 | 1.0000 | 0.9960 | 0.9960 |
| 2010-10 | 130,186 | 130,190 | 131,610 | 1.0000 | 0.9892 | 0.9892 |
| 2010-11 | 107,024 | 107,020 | 107,660 | 1.0000 | 0.9941 | 0.9941 |
| 2010-12 | 109,104 | 109,100 | 110,300 | 1.0000 | 0.9892 | 0.9891 |
| 2011-01 | 106,075 | 106,080 | 107,100 | 1.0000 | 0.9904 | 0.9905 |
| 2011-02 | 73,224 | 73,220 | 74,710 | 1.0001 | 0.9801 | 0.9801 |
| 2011-03 | 94,105 | 94,110 | 95,250 | 0.9999 | 0.9880 | 0.9880 |
| 2011-04 | 89,634 | 89,630 | 91,560 | 1.0000 | 0.9790 | 0.9789 |
| 2011-05 | 88,326 | 88,330 | 90,190 | 1.0000 | 0.9793 | 0.9794 |
| 2011-06 | 53,221 | 53,220 | 53,510 | 1.0000 | 0.9946 | 0.9946 |
| 2011-07 | 32,674 | 32,670 | 32,550 | 1.0001 | 1.0038 | 1.0037 |
| 2011-08 | 86,110 | 86,110 | 87,290 | 1.0000 | 0.9865 | 0.9865 |
| 2011-09 | 81,052 | 81,050 | 82,000 | 1.0000 | 0.9884 | 0.9884 |
| 2011-10 | 34,455 | 34,460 | 34,650 | 0.9998 | 0.9944 | 0.9945 |
| 2011-11 | 56,833 | 56,830 | 58,250 | 1.0001 | 0.9757 | 0.9756 |
| 2011-12 | 52,257 | 52,260 | 52,340 | 0.9999 | 0.9984 | 0.9985 |
| 2012-01 | 45,527 | 45,530 | 46,310 | 0.9999 | 0.9831 | 0.9832 |
| 2012-02 | 64,160 | 64,160 | 64,700 | 1.0000 | 0.9917 | 0.9917 |
| 2012-03 | 61,425 | 61,430 | 62,860 | 0.9999 | 0.9772 | 0.9773 |
| 2012-04 | 60,598 | 60,600 | 62,360 | 1.0000 | 0.9717 | 0.9718 |
| 2012-05 | 57,467 | 57,470 | 58,430 | 0.9999 | 0.9835 | 0.9836 |
| 2012-06 | 52,553 | 52,550 | 54,100 | 1.0001 | 0.9714 | 0.9713 |
| 2012-07 | 54,168 | 54,170 | 54,960 | 1.0000 | 0.9856 | 0.9856 |
| 2012-08 | 21,688 | 21,690 | 22,260 | 0.9999 | 0.9743 | 0.9744 |
| 2012-09 | 2,669 | 2,670 | 2,630 | 0.9996 | 1.0148 | 1.0152 |
| 2012-10 | 53,557 | 53,560 | 53,460 | 0.9999 | 1.0018 | 1.0019 |
| 2012-11 | 53,951 | 53,950 | 56,140 | 1.0000 | 0.9610 | 0.9610 |
| 2012-12 | 46,444 | 46,440 | 48,380 | 1.0001 | 0.9600 | 0.9599 |
| 2013-01 | 47,593 | 47,590 | 49,310 | 1.0001 | 0.9652 | 0.9651 |
| 2013-02 | 41,683 | 41,680 | 42,090 | 1.0001 | 0.9903 | 0.9903 |
| 2013-03 | 25,122 | 25,120 | 25,630 | 1.0001 | 0.9802 | 0.9801 |
| 2013-04 | 35,227 | 35,230 | 36,810 | 0.9999 | 0.9570 | 0.9571 |
| 2013-05 | 43,975 | 43,980 | 44,760 | 0.9999 | 0.9825 | 0.9826 |
| 2013-06 | 34,198 | 34,200 | 35,810 | 0.9999 | 0.9550 | 0.9550 |
| 2013-07 | 38,387 | 38,390 | 40,160 | 0.9999 | 0.9559 | 0.9559 |
| 2013-08 | 62,310 | 62,310 | 63,180 | 1.0000 | 0.9862 | 0.9862 |
| 2013-09 | 50,869 | 50,870 | 52,120 | 1.0000 | 0.9760 | 0.9760 |
| 2013-10 | 60,861 | 60,860 | 62,120 | 1.0000 | 0.9797 | 0.9797 |
| 2013-11 | 61,806 | 61,810 | 62,930 | 0.9999 | 0.9821 | 0.9822 |
| 2013-12 | 55,981 | 55,980 | 57,410 | 1.0000 | 0.9751 | 0.9751 |
| 2014-01 | 61,911 | 61,910 | 63,000 | 1.0000 | 0.9827 | 0.9827 |
| 2014-02 | 56,956 | 56,960 | 57,730 | 0.9999 | 0.9866 | 0.9867 |
| 2014-03 | 62,163 | 62,160 | 63,670 | 1.0000 | 0.9763 | 0.9763 |
| 2014-04 | 76,199 | 76,200 | 77,360 | 1.0000 | 0.9850 | 0.9850 |
| 2014-05 | 83,827 | 83,830 | 84,910 | 1.0000 | 0.9872 | 0.9873 |
| 2014-06 | 79,538 | 79,540 | 81,900 | 1.0000 | 0.9712 | 0.9712 |
| 2014-07 | 74,981 | 74,980 | 75,730 | 1.0000 | 0.9901 | 0.9901 |
| 2014-08 | 49,376 | 49,380 | 51,580 | 0.9999 | 0.9573 | 0.9573 |
| 2014-09 | 62,389 | 62,390 | 63,740 | 1.0000 | 0.9788 | 0.9788 |
| 2014-10 | 64,515 | 64,520 | 65,540 | 0.9999 | 0.9844 | 0.9844 |
| 2014-11 | 52,920 | 52,920 | 54,450 | 1.0000 | 0.9719 | 0.9719 |
| 2014-12 | 18,333 | 18,330 | 20,240 | 1.0002 | 0.9058 | 0.9056 |
| 2015-01 | 81,246 | 81,250 | 83,900 | 1.0000 | 0.9684 | 0.9684 |
| 2015-02 | 66,272 | 66,270 | 68,540 | 1.0000 | 0.9669 | 0.9669 |
| 2015-03 | 81,739 | 81,740 | 82,750 | 1.0000 | 0.9878 | 0.9878 |
| 2015-04 | 90,224 | 90,220 | 91,130 | 1.0000 | 0.9901 | 0.9900 |
| 2015-05 | 87,064 | 87,060 | 88,720 | 1.0000 | 0.9813 | 0.9813 |
| 2015-06 | 83,848 | 83,850 | 85,270 | 1.0000 | 0.9833 | 0.9833 |
| 2015-07 | 73,995 | 74,000 | 75,970 | 0.9999 | 0.9740 | 0.9741 |
| 2015-08 | 56,296 | 56,300 | 57,460 | 0.9999 | 0.9797 | 0.9798 |
| 2015-09 | 63,097 | 63,100 | 64,510 | 1.0000 | 0.9781 | 0.9781 |
| 2015-10 | 57,681 | 57,680 | 59,440 | 1.0000 | 0.9704 | 0.9704 |
| 2015-11 | 60,469 | 60,470 | 61,480 | 1.0000 | 0.9836 | 0.9836 |
| 2015-12 | 59,816 | 59,820 | 61,590 | 0.9999 | 0.9712 | 0.9713 |
| 2016-01 | 51,577 | 51,580 | 53,130 | 0.9999 | 0.9708 | 0.9708 |
| 2016-02 | 47,368 | 47,370 | 48,900 | 1.0000 | 0.9687 | 0.9687 |
| 2016-03 | 42,802 | 42,800 | 44,490 | 1.0001 | 0.9621 | 0.9620 |
| 2016-04 | 32,310 | 32,310 | 33,700 | 1.0000 | 0.9588 | 0.9588 |
| 2016-05 | 39,030 | 39,030 | 40,240 | 1.0000 | 0.9699 | 0.9699 |
| 2016-06 | 35,659 | 35,660 | 36,950 | 1.0000 | 0.9651 | 0.9651 |
| 2016-07 | 31,059 | 31,060 | 33,420 | 1.0000 | 0.9294 | 0.9294 |
| 2016-08 | 24,955 | 24,960 | 26,280 | 0.9998 | 0.9496 | 0.9498 |
| 2016-09 | 8,609 | 8,610 | 9,580 | 0.9999 | 0.8987 | 0.8987 |
| 2016-10 | 0 | 0 | 0 |  |  |  |
| 2016-11 | 0 | 0 | 0 |  |  |  |
| 2016-12 | 0 | 0 | 0 |  |  |  |
| 2017-01 | no row | 0 | 0 |  |  |  |
| 2017-02 | no row | 0 | 0 |  |  |  |
| 2017-03 | no row | 0 | 0 |  |  |  |
| 2017-04 | no row | 0 | 0 |  |  |  |
| 2017-05 | no row | 0 | 0 |  |  |  |
| 2017-06 | no row | 0 | 0 |  |  |  |
| 2017-07 | no row | 0 | 0 |  |  |  |

</details>

<details>
<summary>Gas: ratios per month</summary>

| Month | Workbook Sm3 | Sodir gross Sm3 | Sodir net Sm3 | Workbook / gross | Workbook / net | Gross / net |
|---|---|---|---|---|---|---|
| 2007-09 | 0 | no row | no row |  |  |  |
| 2007-10 | 0 | no row | no row |  |  |  |
| 2007-11 | 0 | no row | no row |  |  |  |
| 2007-12 | 0 | no row | no row |  |  |  |
| 2008-01 | 0 | no row | no row |  |  |  |
| 2008-02 | 7,068,009 | 0 | 0 |  |  |  |
| 2008-03 | 12,191,171 | 0 | 2,300,000 |  | 5.3005 |  |
| 2008-04 | 11,506,441 | 0 | 7,580,000 |  | 1.5180 |  |
| 2008-05 | 19,091,872 | 19,100,000 | 13,930,000 | 0.9996 | 1.3706 | 1.3711 |
| 2008-06 | 21,512,334 | 21,500,000 | 320,000 | 1.0006 | 67.2260 | 67.1875 |
| 2008-07 | 24,655,303 | 24,440,000 | 17,380,000 | 1.0088 | 1.4186 | 1.4062 |
| 2008-08 | 23,923,541 | 23,900,000 | 14,080,000 | 1.0010 | 1.6991 | 1.6974 |
| 2008-09 | 27,526,459 | 27,530,000 | 17,710,000 | 0.9999 | 1.5543 | 1.5545 |
| 2008-10 | 33,757,700 | 33,760,000 | 22,680,000 | 0.9999 | 1.4884 | 1.4885 |
| 2008-11 | 35,743,142 | 35,740,000 | 25,850,000 | 1.0001 | 1.3827 | 1.3826 |
| 2008-12 | 40,062,615 | 40,060,000 | 32,950,000 | 1.0001 | 1.2159 | 1.2158 |
| 2009-01 | 38,973,679 | 38,970,000 | 31,460,000 | 1.0001 | 1.2388 | 1.2387 |
| 2009-02 | 33,681,429 | 33,680,000 | 26,430,000 | 1.0000 | 1.2744 | 1.2743 |
| 2009-03 | 25,826,010 | 26,520,000 | 21,220,000 | 0.9738 | 1.2171 | 1.2498 |
| 2009-04 | 32,857,764 | 32,860,000 | 27,590,000 | 0.9999 | 1.1909 | 1.1910 |
| 2009-05 | 35,311,402 | 35,310,000 | 27,740,000 | 1.0000 | 1.2729 | 1.2729 |
| 2009-06 | 29,929,357 | 31,030,000 | 23,380,000 | 0.9645 | 1.2801 | 1.3272 |
| 2009-07 | 23,849,828 | 25,870,000 | 17,260,000 | 0.9219 | 1.3818 | 1.4988 |
| 2009-08 | 31,340,972 | 31,340,000 | 23,780,000 | 1.0000 | 1.3180 | 1.3179 |
| 2009-09 | 25,118,055 | 25,120,000 | 18,580,000 | 0.9999 | 1.3519 | 1.3520 |
| 2009-10 | 31,376,279 | 31,380,000 | 25,220,000 | 0.9999 | 1.2441 | 1.2443 |
| 2009-11 | 33,003,467 | 33,090,000 | 26,440,000 | 0.9974 | 1.2482 | 1.2515 |
| 2009-12 | 34,713,770 | 35,180,000 | 27,430,000 | 0.9867 | 1.2655 | 1.2825 |
| 2010-01 | 32,605,906 | 32,610,000 | 23,780,000 | 0.9999 | 1.3711 | 1.3713 |
| 2010-02 | 23,271,838 | 23,270,000 | 16,600,000 | 1.0001 | 1.4019 | 1.4018 |
| 2010-03 | 23,700,324 | 23,700,000 | 2,200,000 | 1.0000 | 10.7729 | 10.7727 |
| 2010-04 | 22,449,616 | 22,450,000 | 18,860,000 | 1.0000 | 1.1903 | 1.1903 |
| 2010-05 | 23,460,677 | 23,500,000 | 18,890,000 | 0.9983 | 1.2420 | 1.2440 |
| 2010-06 | 20,701,111 | 20,700,000 | 15,270,000 | 1.0001 | 1.3557 | 1.3556 |
| 2010-07 | 19,356,911 | 19,360,000 | 14,040,000 | 0.9998 | 1.3787 | 1.3789 |
| 2010-08 | 9,889,757 | 9,890,000 | 6,130,000 | 1.0000 | 1.6133 | 1.6134 |
| 2010-09 | 16,010,763 | 16,010,000 | 7,650,000 | 1.0000 | 2.0929 | 2.0928 |
| 2010-10 | 19,595,224 | 19,600,000 | 12,900,000 | 0.9998 | 1.5190 | 1.5194 |
| 2010-11 | 16,232,426 | 16,230,000 | 9,850,000 | 1.0001 | 1.6480 | 1.6477 |
| 2010-12 | 16,673,820 | 16,670,000 | 10,560,000 | 1.0002 | 1.5790 | 1.5786 |
| 2011-01 | 16,177,205 | 16,180,000 | 9,660,000 | 0.9998 | 1.6747 | 1.6749 |
| 2011-02 | 11,349,337 | 11,350,000 | 6,650,000 | 0.9999 | 1.7067 | 1.7068 |
| 2011-03 | 14,493,974 | 14,490,000 | 9,090,000 | 1.0003 | 1.5945 | 1.5941 |
| 2011-04 | 13,929,704 | 13,930,000 | 8,850,000 | 1.0000 | 1.5740 | 1.5740 |
| 2011-05 | 13,774,668 | 13,780,000 | 8,740,000 | 0.9996 | 1.5760 | 1.5767 |
| 2011-06 | 8,247,938 | 8,250,000 | 4,660,000 | 0.9998 | 1.7699 | 1.7704 |
| 2011-07 | 4,888,317 | 4,890,000 | 2,480,000 | 0.9997 | 1.9711 | 1.9718 |
| 2011-08 | 13,128,124 | 13,130,000 | 8,020,000 | 0.9999 | 1.6369 | 1.6372 |
| 2011-09 | 12,587,791 | 12,590,000 | 6,810,000 | 0.9998 | 1.8484 | 1.8488 |
| 2011-10 | 5,326,003 | 5,330,000 | 2,830,000 | 0.9993 | 1.8820 | 1.8834 |
| 2011-11 | 8,623,671 | 8,620,000 | 4,670,000 | 1.0004 | 1.8466 | 1.8458 |
| 2011-12 | 7,793,463 | 7,790,000 | 4,320,000 | 1.0004 | 1.8040 | 1.8032 |
| 2012-01 | 6,878,732 | 6,880,000 | 3,750,000 | 0.9998 | 1.8343 | 1.8347 |
| 2012-02 | 9,888,484 | 9,890,000 | 5,400,000 | 0.9998 | 1.8312 | 1.8315 |
| 2012-03 | 9,654,375 | 9,650,000 | 5,140,000 | 1.0005 | 1.8783 | 1.8774 |
| 2012-04 | 9,539,380 | 9,540,000 | 5,090,000 | 0.9999 | 1.8741 | 1.8743 |
| 2012-05 | 9,126,346 | 9,130,000 | 4,170,000 | 0.9996 | 2.1886 | 2.1894 |
| 2012-06 | 8,375,058 | 8,380,000 | 3,650,000 | 0.9994 | 2.2945 | 2.2959 |
| 2012-07 | 8,626,031 | 8,630,000 | 4,190,000 | 0.9995 | 2.0587 | 2.0597 |
| 2012-08 | 3,350,389 | 3,350,000 | 1,620,000 | 1.0001 | 2.0681 | 2.0679 |
| 2012-09 | 402,901 | 400,000 | 90,000 | 1.0073 | 4.4767 | 4.4444 |
| 2012-10 | 8,222,643 | 8,220,000 | 4,230,000 | 1.0003 | 1.9439 | 1.9433 |
| 2012-11 | 8,572,125 | 8,570,000 | 4,010,000 | 1.0002 | 2.1377 | 2.1372 |
| 2012-12 | 7,572,179 | 7,570,000 | 4,120,000 | 1.0003 | 1.8379 | 1.8374 |
| 2013-01 | 7,715,896 | 7,720,000 | 3,800,000 | 0.9995 | 2.0305 | 2.0316 |
| 2013-02 | 6,657,580 | 6,660,000 | 2,700,000 | 0.9996 | 2.4658 | 2.4667 |
| 2013-03 | 3,837,458 | 3,840,000 | 1,420,000 | 0.9993 | 2.7024 | 2.7042 |
| 2013-04 | 5,731,549 | 5,730,000 | 2,470,000 | 1.0003 | 2.3205 | 2.3198 |
| 2013-05 | 7,283,687 | 7,280,000 | 2,960,000 | 1.0005 | 2.4607 | 2.4595 |
| 2013-06 | 5,689,963 | 5,690,000 | 1,090,000 | 1.0000 | 5.2201 | 5.2202 |
| 2013-07 | 6,063,604 | 6,060,000 | 2,310,000 | 1.0006 | 2.6249 | 2.6234 |
| 2013-08 | 9,485,747 | 9,490,000 | 4,620,000 | 0.9996 | 2.0532 | 2.0541 |
| 2013-09 | 7,816,250 | 7,820,000 | 3,990,000 | 0.9995 | 1.9590 | 1.9599 |
| 2013-10 | 9,313,443 | 9,310,000 | 4,890,000 | 1.0004 | 1.9046 | 1.9039 |
| 2013-11 | 9,370,028 | 9,370,000 | 5,080,000 | 1.0000 | 1.8445 | 1.8445 |
| 2013-12 | 8,622,571 | 8,620,000 | 4,630,000 | 1.0003 | 1.8623 | 1.8618 |
| 2014-01 | 9,207,271 | 9,210,000 | 4,960,000 | 0.9997 | 1.8563 | 1.8569 |
| 2014-02 | 8,534,705 | 8,540,000 | 4,310,000 | 0.9994 | 1.9802 | 1.9814 |
| 2014-03 | 9,348,668 | 9,350,000 | 4,390,000 | 0.9999 | 2.1295 | 2.1298 |
| 2014-04 | 11,256,659 | 11,260,000 | 30,000 | 0.9997 | 375.2220 | 375.3333 |
| 2014-05 | 11,826,032 | 11,830,000 | 30,000 | 0.9997 | 394.2011 | 394.3333 |
| 2014-06 | 11,707,631 | 11,710,000 | 30,000 | 0.9998 | 390.2544 | 390.3333 |
| 2014-07 | 11,183,246 | 11,180,000 | 20,000 | 1.0003 | 559.1623 | 559.0000 |
| 2014-08 | 7,646,877 | 7,650,000 | 10,000 | 0.9996 | 764.6877 | 765.0000 |
| 2014-09 | 9,788,352 | 9,790,000 | 20,000 | 0.9998 | 489.4176 | 489.5000 |
| 2014-10 | 9,978,066 | 9,980,000 | 20,000 | 0.9998 | 498.9033 | 499.0000 |
| 2014-11 | 8,273,448 | 8,270,000 | 20,000 | 1.0004 | 413.6724 | 413.5000 |
| 2014-12 | 3,040,919 | 3,720,000 | 0 | 0.8175 |  |  |
| 2015-01 | 11,980,379 | 11,980,000 | 100,000 | 1.0000 | 119.8038 | 119.8000 |
| 2015-02 | 10,025,733 | 10,030,000 | 80,000 | 0.9996 | 125.3217 | 125.3750 |
| 2015-03 | 12,032,559 | 12,030,000 | 50,000 | 1.0002 | 240.6512 | 240.6000 |
| 2015-04 | 13,155,180 | 13,160,000 | 30,000 | 0.9996 | 438.5060 | 438.6667 |
| 2015-05 | 12,700,588 | 12,700,000 | 30,000 | 1.0000 | 423.3529 | 423.3333 |
| 2015-06 | 12,276,975 | 12,280,000 | 30,000 | 0.9998 | 409.2325 | 409.3333 |
| 2015-07 | 10,999,937 | 11,000,000 | 30,000 | 1.0000 | 366.6646 | 366.6667 |
| 2015-08 | 8,524,506 | 8,530,000 | 20,000 | 0.9994 | 426.2253 | 426.5000 |
| 2015-09 | 9,518,188 | 9,520,000 | 20,000 | 0.9998 | 475.9094 | 476.0000 |
| 2015-10 | 8,789,915 | 8,790,000 | 20,000 | 1.0000 | 439.4957 | 439.5000 |
| 2015-11 | 9,256,115 | 9,260,000 | 20,000 | 0.9996 | 462.8058 | 463.0000 |
| 2015-12 | 9,163,768 | 9,160,000 | 20,000 | 1.0004 | 458.1884 | 458.0000 |
| 2016-01 | 8,075,649 | 8,080,000 | 5,400,000 | 0.9995 | 1.4955 | 1.4963 |
| 2016-02 | 7,468,629 | 7,470,000 | 4,810,000 | 0.9998 | 1.5527 | 1.5530 |
| 2016-03 | 6,900,267 | 6,900,000 | 4,280,000 | 1.0000 | 1.6122 | 1.6121 |
| 2016-04 | 5,287,855 | 5,290,000 | 2,780,000 | 0.9996 | 1.9021 | 1.9029 |
| 2016-05 | 6,157,954 | 6,220,000 | 3,520,000 | 0.9900 | 1.7494 | 1.7670 |
| 2016-06 | 5,738,861 | 5,740,000 | 3,240,000 | 0.9998 | 1.7713 | 1.7716 |
| 2016-07 | 4,989,890 | 4,990,000 | 3,410,000 | 1.0000 | 1.4633 | 1.4633 |
| 2016-08 | 3,991,208 | 3,990,000 | 580,000 | 1.0003 | 6.8814 | 6.8793 |
| 2016-09 | 1,458,816 | 1,460,000 | 0 | 0.9992 |  |  |
| 2016-10 | 0 | 0 | 0 |  |  |  |
| 2016-11 | 0 | 0 | 0 |  |  |  |
| 2016-12 | 0 | 0 | 0 |  |  |  |
| 2017-01 | no row | 0 | 0 |  |  |  |
| 2017-02 | no row | 0 | 0 |  |  |  |
| 2017-03 | no row | 0 | 0 |  |  |  |
| 2017-04 | no row | 0 | 0 |  |  |  |
| 2017-05 | no row | 0 | 0 |  |  |  |
| 2017-06 | no row | 0 | 0 |  |  |  |
| 2017-07 | no row | 0 | 0 |  |  |  |

</details>

Computed by `well_ops.ingestion.audit.workbook_monthly_sums`, `well_ops.ingestion.audit.sodir_series`, `well_ops.ingestion.audit.compare_production`.
<!-- /audit:production-comparison -->

## 7. CIRA centrifugal pumps

Files: `data/raw/cira/*.csv` and the dataset `README.md`.

<!-- audit:cira -->
| File | Delimiter | Rows | Empty rows | Rows with a blank value | First (UTC) | Last | Span | Sampling intervals (most common) |
|---|---|---|---|---|---|---|---|---|
| A_2024-04-10.csv | `,` | 4,980 | 1 | 121 | 2024-04-10 12:00:00 | 13:59:59 | 1:59:59 | 1 s x 4,424, 5 s x 555 |
| A_2024-06-11.csv | `,` | 21,429 | 0 | 2,265 | 2024-06-11 10:00:00 | 15:59:59 | 5:59:59 | 1 s x 21,427, 172 s x 1 |
| A_2024-10-30.csv | `;` (decimal comma) | 21,600 | 0 | 8 | 2024-10-30 10:30:00 | 16:29:59 | 5:59:59 | 1 s x 21,599 |
| B_2024-04-10.csv | `,` | 4,980 | 1 | 344 | 2024-04-10 12:00:00 | 13:59:59 | 1:59:59 | 1 s x 4,424, 5 s x 555 |
| B_2024-06-11.csv | `,` | 35,829 | 0 | 1,873 | 2024-06-11 06:00:00 | 15:59:59 | 9:59:59 | 1 s x 35,827, 172 s x 1 |
| B_2024-10-30.csv | `,` | 29,700 | 0 | 19,513 | 2024-10-30 08:15:00 | 16:29:59 | 8:14:59 | 1 s x 29,699 |
| C_2024-04-10.csv | `,` | 4,980 | 1 | 109 | 2024-04-10 12:00:00 | 13:59:59 | 1:59:59 | 1 s x 4,424, 5 s x 555 |
| C_2024-06-11.csv | `,` | 21,429 | 0 | 2,211 | 2024-06-11 10:00:00 | 15:59:59 | 5:59:59 | 1 s x 21,427, 172 s x 1 |

Blank values by column:

| File | Blank values by column |
|---|---|
| A_2024-04-10.csv | A_ACR_Mot.PV 13, A_ACR_Mot.SV 13, A_ACR_Mot.TV 13, A_ACR_Pmp.PV 33, A_ACR_Pmp.SV 33, A_ACR_Pmp.TV 33, A_Pres.PV 18, A_Temp.PV 75, Barometer 15, Temperature 14 |
| A_2024-06-11.csv | A_ACR_Mot.PV 458, A_ACR_Mot.SV 458, A_ACR_Mot.TV 458, A_ACR_Pmp.PV 471, A_ACR_Pmp.SV 471, A_ACR_Pmp.TV 471, A_Pres.PV 306, A_Temp.PV 474, Barometer 341, Temperature 2,211 |
| A_2024-10-30.csv | A_ACR_Mot.PV 2, A_ACR_Mot.SV 2, A_ACR_Mot.TV 2, A_ACR_Pmp.PV 6, A_ACR_Pmp.SV 6, A_ACR_Pmp.TV 6 |
| B_2024-04-10.csv | B_ACR_Mot.PV 54, B_ACR_Mot.SV 54, B_ACR_Mot.TV 54, B_ACR_Pmp.PV 23, B_ACR_Pmp.SV 23, B_ACR_Pmp.TV 137, B_Pres.PV 3, B_Temp.PV 171, Barometer 15, Temperature 14 |
| B_2024-06-11.csv | B_ACR_Mot.PV 477, B_ACR_Mot.SV 477, B_ACR_Mot.TV 477, B_ACR_Pmp.PV 622, B_ACR_Pmp.SV 622, B_ACR_Pmp.TV 1,799, B_Pres.PV 288, B_Temp.PV 479, Barometer 340, Temperature 464 |
| B_2024-10-30.csv | B_ACR_Mot.PV 3, B_ACR_Mot.SV 3, B_ACR_Mot.TV 3, B_ACR_Pmp.PV 67, B_ACR_Pmp.SV 67, B_ACR_Pmp.TV 67, Barometer 19,443, Temperature 19,443 |
| C_2024-04-10.csv | C_ACR_Mot.PV 34, C_ACR_Mot.SV 34, C_ACR_Mot.TV 34, C_ACR_Pmp.PV 11, C_ACR_Pmp.SV 11, C_ACR_Pmp.TV 11, C_Pres.PV 2, C_Temp.PV 76, Barometer 15, Temperature 14 |
| C_2024-06-11.csv | C_ACR_Mot.PV 383, C_ACR_Mot.SV 383, C_ACR_Mot.TV 383, C_ACR_Pmp.PV 438, C_ACR_Pmp.SV 438, C_ACR_Pmp.TV 438, C_Pres.PV 453, C_Temp.PV 420, Barometer 341, Temperature 2,211 |

Columns compared with the dataset README (with `X` replaced by the pump letter):

| File | README columns not in file | File columns not in README |
|---|---|---|
| A_2024-04-10.csv | A_Temp.SV, A_Pres.SV | A_Pres.PV, A_Temp.PV |
| A_2024-06-11.csv | A_Temp.SV, A_Pres.SV | A_Pres.PV, A_Temp.PV |
| A_2024-10-30.csv | A_Temp.SV, A_Pres.SV | A_Pres.PV, A_Temp.PV |
| B_2024-04-10.csv | B_Temp.SV, B_Pres.SV | B_Pres.PV, B_Temp.PV |
| B_2024-06-11.csv | B_Temp.SV, B_Pres.SV | B_Pres.PV, B_Temp.PV |
| B_2024-10-30.csv | B_Temp.SV, B_Pres.SV | B_Pres.PV, B_Temp.PV |
| C_2024-04-10.csv | C_Temp.SV, C_Pres.SV | C_Pres.PV, C_Temp.PV |
| C_2024-06-11.csv | C_Temp.SV, C_Pres.SV | C_Pres.PV, C_Temp.PV |

Header of each file: `A_2024-04-10.csv`: Timestamp, A_ACR_Mot.PV, A_ACR_Mot.SV, A_ACR_Mot.TV, A_ACR_Pmp.PV, A_ACR_Pmp.SV, A_ACR_Pmp.TV, A_Pres.PV, A_Temp.PV, Barometer, Temperature (other files use their own pump letter).

Computed by `well_ops.ingestion.audit.audit_cira`, `well_ops.ingestion.audit.audit_cira_file`.
<!-- /audit:cira -->

The columns match the README in number, and in the accelerometer, barometer and ambient
temperature columns. The pressure and casing temperature columns are named `.PV` in the files and
`.SV` in the README, and appear in the other order (pressure before temperature). Units are stated
only in the README; the files carry none. The 2024-04-10 files mix 5-second and 1-second
intervals; the other files are at 1 second with at most one longer gap. All timestamps end in `Z`
(UTC).

## Open questions

1. **Depth reference in drilling reports.** Is the status-block `md` measured from the rotary
   kelly bushing? No `datum` attribute says so. To find out: read the `datum` attributes on other
   elements of the same reports (fluid samples, survey stations) and compare with `elevKelly`.
2. **Lost time.** Which activity codes count as lost or non-productive time? The reports give no
   classification beyond `proprietaryCode`. To find out: agree a definition (see decisions) and
   check it against the `comments` of `interruption` activities.
3. **Months where the workbook and Sodir gross differ.** The workbook matches the Sodir gross
   (sum of wells) basis in most months but not all (section 6). Why do the other months differ?
   To find out: compare those months with the daily sheet and look for corrections in the Volve
   Data Village documentation (the `Reports` folder).
4. **Daily sheet units.** The units of pressure, temperature and volumes are unknown. To find out:
   the same documentation search, plus a check that daily volumes sum to the monthly sheet.
5. **`15/9-F-15S`.** Which Sodir wellbore does the WITSML wellbore `15/9-F-15S` correspond to? To
   find out: compare its trajectory with those of the Sodir wellbores of well 15/9-F-15.
6. **CIRA column names.** Are the `.PV` columns in the files the ones the README calls `.SV`? To
   find out: ask the dataset authors through the Zenodo record.
7. **Sodir months after the workbook ends.** The Sodir table extends beyond the workbook's last
   month (sections 3 and 5). Do those months hold non-zero volumes? To find out: a small addition
   to `audit_sodir_production`.
8. **Personal names in free text.** Daily drilling report free text may contain personal names;
   Phase 3 needs a redaction rule for agent output.

## Surprises

1. Almost all of the WITSML volume is real-time `log` data that exists only in the zip; the
   extracted folders hold no log curves.
2. Two 15/9-19 A reports end on or before that wellbore's spud date; one of them is dated
   1979-12-31 (section 1.1).
3. The workbook's `WELL_BORE_CODE` uses suffixes (`AH`, `H`) found in no other source, while
   `NPD_WELL_BORE_NAME` in the same row uses the Sodir name.
4. Workbook gas differs from Sodir net (saleable) gas by a large and variable factor but matches
   Sodir gross (sum of wells) gas in most months; Sodir net oil is slightly higher than gross oil
   (section 6).
5. The EDM file and the CIRA README contain personal data (user IDs, email addresses). The audit
   reads only name attributes from EDM, and this report reproduces none of it.
6. The CIRA README and the CSV headers disagree on two column names, and one CIRA file uses a
   different CSV dialect (`;` with decimal commas).
7. In `B_2024-10-30.csv` most `Barometer` and `Temperature` values are blank (section 7).

## Decisions needed before Phase 2

1. **Canonical wellbore key.** Adopt the Sodir NPDID as the key and `wlbWellboreName` as the
   display name? And decide how technical sidetracks (`T2`) are keyed: under the parent NPDID with
   a sidetrack qualifier, or as separate project-local wellbores.
2. **WITSML scope.** Extract the `log` data from the zip in Phase 2 (section 2 gives its size), or
   limit Phase 2 to the non-log objects and a subset of wellbores?
3. **Lost-time definition.** Decide which `proprietaryCode` categories and subcategories count as
   lost time, before the evaluation rules for the lost-time agent are written.
4. **Production reference.** Which basis do agents compare against: Sodir gross (sum of wells,
   which the workbook matches in most months) for well-level work, and Sodir net (saleable) only
   for field sales figures? And how are the months where the workbook and Sodir gross disagree
   flagged?
5. **Missing values.** Treat `-999.99` (drilling reports), the text `NULL` (workbook monthly
   sheet) and blank cells (CIRA) as missing, the same way, at ingestion.
6. **Out-of-scope names.** Drop EDM planning objects and WITSML folders that are not wellbores from
   the identifier table, or keep them with an explicit "not a wellbore" status?
