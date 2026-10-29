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

File: `data/raw/sodir/field_production_monthly.csv`, exported from the FactPages table view
*Field > Table view > Production > Saleable > Monthly*.

<!-- audit:sodir-production -->
Table `field_production_monthly`, rows with `prfInformationCarrier` = VOLVE: 114 months, 2008-02 to 2017-07.

Columns: `prfInformationCarrier`, `prfYear`, `prfMonth`, `prfPrdOilNetMillSm3`, `prfPrdGasNetBillSm3`, `prfPrdNGLNetMillSm3`, `prfPrdCondensateNetMillSm3`, `prfPrdOeNetMillSm3`, `prfPrdProducedWaterInFieldMillSm3`, `prfNpdidInformationCarrier`

Units, as encoded in the column names:

| Column | Unit |
|---|---|
| prfPrdOilNetMillSm3 | million Sm3 |
| prfPrdGasNetBillSm3 | billion Sm3 |
| prfPrdNGLNetMillSm3 | million Sm3 |
| prfPrdCondensateNetMillSm3 | million Sm3 |
| prfPrdOeNetMillSm3 | million Sm3 |
| prfPrdProducedWaterInFieldMillSm3 | million Sm3 |

Computed by `well_ops.ingestion.audit.audit_sodir_production`.
<!-- /audit:sodir-production -->

## 6. Reporting basis: Sodir field volumes versus the Volve workbook

The Sodir table is the "Saleable" production table. The FactPages attribute page
(<https://factpages.sodir.no/en/field/Attributes>, retrieved 2026-10-28) lists its columns under
"Sub level – Production , saleable" and describes them as "Net – oil [mill Sm3]", "Production for
Oil, net [mill Sm3]" (`prfPrdOilNetMillSm3`), and "Net – gas [bill Sm3]", "Production for Gas, net
[bill Sm3]" (`prfPrdGasNetBillSm3`). The same page lists a separate "Sub level – Production , sum
wellbores" table with "Gross – oil [mill Sm3]" (`prfPrdOilGrossMillSm3`) and "Gross – gas [bill
Sm3]" (`prfPrdGasGrossBillSm3`), which this project has not downloaded. The attribute page does
not define "net", "gross" or "saleable" further, and Sodir's technical information page refused
scripted access (HTTP 403), so the exact Sodir definitions are **unknown** from the documentation
used. The Volve workbook gives per-wellbore `Oil`, `Gas` and `Water` in `Sm3` (monthly sheet) and
`BORE_OIL_VOL`, `BORE_GAS_VOL` and `BORE_WAT_VOL` without units (daily sheet). Whether these
volumes are metered or allocated, and whether the gas includes fuel, flared or re-injected gas, is
**unknown**, because the workbook carries no documentation. The comparison below is computed, not
documented: oil and water totals over the period are close, although individual months differ
(see the ratio ranges), while workbook gas is higher than Sodir net gas in every month compared. A gross-versus-net difference would be one explanation, but it is
not verified.

<!-- audit:production-comparison -->
Workbook monthly sheet, summed over wellbores per month, versus Sodir `field_production_monthly` for VOLVE (converted to Sm3). Ratio = workbook / Sodir, over months where both are non-zero. Totals are over the months in the Sodir table; the last column counts workbook months with a non-zero volume that Sodir does not list.

| Quantity | Sodir column | Months compared | Within 1 % | Median ratio | Min ratio | Max ratio | Workbook total Sm3 | Sodir total Sm3 | Workbook-only months |
|---|---|---|---|---|---|---|---|---|---|
| Oil | prfPrdOilNetMillSm3 | 104 | 35 | 0.9837 | 0.8987 | 1.0148 | 10,037,081 | 10,171,990 | 0 |
| Gas | prfPrdGasNetBillSm3 | 101 | 0 | 1.8563 | 1.1903 | 764.6877 | 1,475,370,436 | 812,550,000 | 0 |
| Water | prfPrdProducedWaterInFieldMillSm3 | 99 | 93 | 1.0000 | 0.3363 | 8.2522 | 15,318,578 | 15,343,620 | 0 |

Computed by `well_ops.ingestion.audit.compare_monthly_volumes`.
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
3. **Workbook basis.** Are workbook volumes metered or allocated, and does `Gas` include re-injected
   or fuel gas? To find out: look for documentation elsewhere in the Volve Data Village (the
   `Reports` folder), and compare with the Sodir "sum wellbores" (gross) table.
4. **Daily sheet units.** The units of pressure, temperature and volumes are unknown. To find out:
   the same documentation search, plus a check that daily volumes sum to the monthly sheet.
5. **`15/9-F-15S`.** Which Sodir wellbore does the WITSML wellbore `15/9-F-15S` correspond to? To
   find out: compare its trajectory with those of the Sodir wellbores of well 15/9-F-15.
6. **CIRA column names.** Are the `.PV` columns in the files the ones the README calls `.SV`? To
   find out: ask the dataset authors through the Zenodo record.
7. **Sodir months after the workbook ends.** The Sodir table extends beyond the workbook's last
   month (sections 3 and 5). Do those months hold non-zero volumes? To find out: a small addition
   to `audit_sodir_production`.

## Surprises

1. Almost all of the WITSML volume is real-time `log` data that exists only in the zip; the
   extracted folders hold no log curves.
2. Two 15/9-19 A reports end on or before that wellbore's spud date; one of them is dated
   1979-12-31 (section 1.1).
3. The workbook's `WELL_BORE_CODE` uses suffixes (`AH`, `H`) found in no other source, while
   `NPD_WELL_BORE_NAME` in the same row uses the Sodir name.
4. Workbook gas differs from Sodir net gas by a large and variable factor, while oil and water
   totals are close (section 6).
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
4. **Production reference.** Which volumes are the reference for comparisons: Sodir net, the
   workbook, or Sodir gross after downloading the "sum wellbores" table?
5. **Missing values.** Treat `-999.99` (drilling reports), the text `NULL` (workbook monthly
   sheet) and blank cells (CIRA) as missing, the same way, at ingestion.
6. **Out-of-scope names.** Drop EDM planning objects and WITSML folders that are not wellbores from
   the identifier table, or keep them with an explicit "not a wellbore" status?
