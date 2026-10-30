# Data-quality report (Phase 2)

This report states what the Phase 2 warehouse holds after a rebuild from `data/raw/`: rows per
model, nulls per column, values read as null, data-quality flags and dbt test results.

**How it is produced.** `make rebuild` deletes `data/staging/` and the DuckDB database, runs every
parser (`make stage`) and builds and tests the dbt project (`make dbt-build`). `make quality` then
computes the sections between `<!-- quality:... -->` markers from the database, the staged Parquet
files and the dbt build results (`warehouse/target/`). Each computed section names the function
that produced it. Re-running both commands on the same raw data reproduces this report exactly.

**Held-out wellbores.** Every section is aggregate (counts per model, column, flag or test), so
no wellbore is named (ADR 0002 D8). The warehouse builds all wellbores, held-out ones included.

**Scope.** Real-time log values are staged only for wellbores extracted with `make extract-log`
(ADR 0002 D6); the log rows below cover those wellbores only.

## 1. Models and row counts

<!-- quality:models -->
| Layer | Model | Type | Rows | Columns |
|---|---|---|---|---|
| staging | `stg_ddr__activity` | model | 23,447 | 17 |
| staging | `stg_ddr__report` | model | 1,759 | 26 |
| staging | `stg_evaluation__heldout_wellbore` | model | 5 | 1 |
| staging | `stg_identifiers__wellbore_alias` | model | 223 | 8 |
| staging | `stg_production__daily` | model | 15,634 | 26 |
| staging | `stg_production__monthly` | model | 526 | 13 |
| staging | `stg_sodir__field_production_gross_monthly` | model | 28,562 | 10 |
| staging | `stg_sodir__field_production_net_monthly` | model | 28,562 | 11 |
| staging | `stg_sodir__wellbore` | model | 8,487 | 11 |
| staging | `stg_witsml__bha_run` | model | 161 | 21 |
| staging | `stg_witsml__log` | model | 256 | 14 |
| staging | `stg_witsml__log_curve` | model | 4,377 | 7 |
| staging | `stg_witsml__log_value` | model | 4,554,889 | 699 |
| staging | `stg_witsml__message` | model | 11,134 | 13 |
| staging | `stg_witsml__mud_log_interval` | model | 2,882 | 27 |
| staging | `stg_witsml__rig` | model | 19 | 8 |
| staging | `stg_witsml__trajectory_station` | model | 5,561 | 26 |
| staging | `stg_witsml__tubular_component` | model | 1,392 | 19 |
| staging | `stg_witsml__wb_geometry_section` | model | 109 | 23 |
| intermediate | `int_ddr__activity_section` | model | 23,447 | 11 |
| intermediate | `int_ddr__hole_section` | model | 261 | 13 |
| intermediate | `int_ddr__report_flag` | model | 488 | 5 |
| intermediate | `int_production__daily_flag` | model | 4 | 5 |
| intermediate | `int_production__daily_units_check` | model | 526 | 23 |
| intermediate | `int_witsml__log_flag` | model | 1 | 5 |
| marts | `dim_hole_section` | model | 261 | 18 |
| marts | `dim_wellbore` | model | 8,491 | 14 |
| marts | `fct_lost_time` | model | 1,766 | 9 |
| marts | `fct_production_monthly_reconciliation` | model | 119 | 22 |
| reference | `lost_time_codes` | seed | 14 | 3 |

Computed by `well_ops.warehouse.quality.load_nodes`, `well_ops.warehouse.quality.null_counts`.
<!-- /quality:models -->

## 2. Nulls by column

<!-- quality:nulls -->
Columns with at least one null, per model; a model without nulls is listed once.

| Model | Column | Nulls | Share of rows |
|---|---|---|---|
| `stg_ddr__activity` | all 17 columns | 0 |  |
| `stg_ddr__report` | `dia_hole_start_utc` | 7 | 0.4% |
| `stg_ddr__report` | `dia_hole_start_offset` | 7 | 0.4% |
| `stg_ddr__report` | `md_m` | 331 | 18.8% |
| `stg_ddr__report` | `tvd_m` | 530 | 30.1% |
| `stg_ddr__report` | `md_planned_m` | 1,759 | 100.0% |
| `stg_ddr__report` | `dist_drill_m` | 1,247 | 70.9% |
| `stg_ddr__report` | `dia_hole_in` | 990 | 56.3% |
| `stg_ddr__report` | `md_dia_hole_start_m` | 127 | 7.2% |
| `stg_ddr__report` | `dia_pilot_in` | 1,740 | 98.9% |
| `stg_ddr__report` | `md_csg_last_m` | 57 | 3.2% |
| `stg_ddr__report` | `tvd_csg_last_m` | 438 | 24.9% |
| `stg_ddr__report` | `md_kickoff_m` | 1,511 | 85.9% |
| `stg_ddr__report` | `md_plug_top_m` | 1,430 | 81.3% |
| `stg_ddr__report` | `elev_kelly_m` | 8 | 0.5% |
| `stg_evaluation__heldout_wellbore` | all 1 columns | 0 |  |
| `stg_identifiers__wellbore_alias` | `source_npdid` | 176 | 78.9% |
| `stg_identifiers__wellbore_alias` | `wellbore_key` | 56 | 25.1% |
| `stg_identifiers__wellbore_alias` | `wellbore_name` | 56 | 25.1% |
| `stg_production__daily` | `on_stream_hours` | 285 | 1.8% |
| `stg_production__daily` | `avg_downhole_pressure` | 6,654 | 42.6% |
| `stg_production__daily` | `avg_downhole_temperature` | 6,654 | 42.6% |
| `stg_production__daily` | `avg_dp_tubing` | 6,654 | 42.6% |
| `stg_production__daily` | `avg_annulus_pressure` | 7,744 | 49.5% |
| `stg_production__daily` | `avg_choke_size` | 6,715 | 43.0% |
| `stg_production__daily` | `avg_choke_uom` | 6,473 | 41.4% |
| `stg_production__daily` | `avg_whp` | 6,479 | 41.4% |
| `stg_production__daily` | `avg_wht` | 6,488 | 41.5% |
| `stg_production__daily` | `dp_choke_size` | 294 | 1.9% |
| `stg_production__daily` | `oil_volume` | 6,473 | 41.4% |
| `stg_production__daily` | `gas_volume` | 6,473 | 41.4% |
| `stg_production__daily` | `water_volume` | 6,473 | 41.4% |
| `stg_production__daily` | `water_injected_volume` | 9,928 | 63.5% |
| `stg_production__monthly` | `on_stream_hours` | 11 | 2.1% |
| `stg_production__monthly` | `oil_sm3` | 215 | 40.9% |
| `stg_production__monthly` | `gas_sm3` | 215 | 40.9% |
| `stg_production__monthly` | `water_sm3` | 215 | 40.9% |
| `stg_production__monthly` | `gas_injected_sm3` | 526 | 100.0% |
| `stg_production__monthly` | `water_injected_sm3` | 325 | 61.8% |
| `stg_sodir__field_production_gross_monthly` | all 10 columns | 0 |  |
| `stg_sodir__field_production_net_monthly` | all 11 columns | 0 |  |
| `stg_sodir__wellbore` | `field_name` | 1,273 | 15.0% |
| `stg_sodir__wellbore` | `purpose` | 15 | 0.2% |
| `stg_sodir__wellbore` | `status` | 107 | 1.3% |
| `stg_sodir__wellbore` | `entry_date` | 261 | 3.1% |
| `stg_sodir__wellbore` | `completion_date` | 336 | 4.0% |
| `stg_sodir__wellbore` | `total_depth_m` | 347 | 4.1% |
| `stg_witsml__bha_run` | `run_stop_utc` | 47 | 29.2% |
| `stg_witsml__bha_run` | `run_stop_offset` | 47 | 29.2% |
| `stg_witsml__bha_run` | `drilling_start_utc` | 146 | 90.7% |
| `stg_witsml__bha_run` | `drilling_start_offset` | 146 | 90.7% |
| `stg_witsml__bha_run` | `drilling_stop_utc` | 151 | 93.8% |
| `stg_witsml__bha_run` | `drilling_stop_offset` | 151 | 93.8% |
| `stg_witsml__bha_run` | `num_bit_run` | 150 | 93.2% |
| `stg_witsml__bha_run` | `md_hole_start_m` | 142 | 88.2% |
| `stg_witsml__bha_run` | `md_hole_start_uom` | 142 | 88.2% |
| `stg_witsml__bha_run` | `md_hole_stop_m` | 142 | 88.2% |
| `stg_witsml__bha_run` | `md_hole_stop_uom` | 142 | 88.2% |
| `stg_witsml__log` | `index_uom` | 121 | 47.3% |
| `stg_witsml__log` | `direction` | 4 | 1.6% |
| `stg_witsml__log` | `service_company` | 6 | 2.3% |
| `stg_witsml__log` | `run_number` | 3 | 1.2% |
| `stg_witsml__log_curve` | `unit` | 119 | 2.7% |
| `stg_witsml__log_curve` | `curve_description` | 75 | 1.7% |
| `stg_witsml__message` | `severity` | 11,102 | 99.7% |
| `stg_witsml__message` | `message_text` | 1 | 0.0% |
| `stg_witsml__mud_log_interval` | `rop_av_m_per_s` | 4 | 0.1% |
| `stg_witsml__mud_log_interval` | `rop_av_uom` | 4 | 0.1% |
| `stg_witsml__mud_log_interval` | `wob_av_n` | 15 | 0.5% |
| `stg_witsml__mud_log_interval` | `wob_av_uom` | 15 | 0.5% |
| `stg_witsml__mud_log_interval` | `tq_av_n_m` | 4 | 0.1% |
| `stg_witsml__mud_log_interval` | `tq_av_uom` | 4 | 0.1% |
| `stg_witsml__mud_log_interval` | `rpm_av_c_per_s` | 4 | 0.1% |
| `stg_witsml__mud_log_interval` | `rpm_av_uom` | 4 | 0.1% |
| `stg_witsml__mud_log_interval` | `wt_mud_av_kg_m3` | 33 | 1.1% |
| `stg_witsml__mud_log_interval` | `wt_mud_av_uom` | 33 | 1.1% |
| `stg_witsml__mud_log_interval` | `ecd_td_av_kg_m3` | 34 | 1.2% |
| `stg_witsml__mud_log_interval` | `ecd_td_av_uom` | 34 | 1.2% |
| `stg_witsml__rig` | all 8 columns | 0 |  |
| `stg_witsml__trajectory_station` | `wellbore_key` | 165 | 3.0% |
| `stg_witsml__trajectory_station` | `station_utc` | 146 | 2.6% |
| `stg_witsml__trajectory_station` | `station_offset` | 146 | 2.6% |
| `stg_witsml__trajectory_station` | `type_survey_tool` | 2,901 | 52.2% |
| `stg_witsml__trajectory_station` | `status_traj_station` | 20 | 0.4% |
| `stg_witsml__trajectory_station` | `tvd_m` | 18 | 0.3% |
| `stg_witsml__trajectory_station` | `tvd_uom` | 18 | 0.3% |
| `stg_witsml__trajectory_station` | `azi_deg` | 67 | 1.2% |
| `stg_witsml__trajectory_station` | `azi_uom` | 67 | 1.2% |
| `stg_witsml__trajectory_station` | `disp_ns_m` | 18 | 0.3% |
| `stg_witsml__trajectory_station` | `disp_ns_uom` | 18 | 0.3% |
| `stg_witsml__trajectory_station` | `disp_ew_m` | 18 | 0.3% |
| `stg_witsml__trajectory_station` | `disp_ew_uom` | 18 | 0.3% |
| `stg_witsml__trajectory_station` | `dls_deg_per_30m` | 18 | 0.3% |
| `stg_witsml__trajectory_station` | `dls_uom` | 18 | 0.3% |
| `stg_witsml__tubular_component` | `id_in` | 62 | 4.5% |
| `stg_witsml__tubular_component` | `od_in` | 1 | 0.1% |
| `stg_witsml__tubular_component` | `len_m` | 1 | 0.1% |
| `stg_witsml__tubular_component` | `dia_bit_in` | 1,353 | 97.2% |
| `stg_witsml__tubular_component` | `dia_bit_uom` | 440 | 31.6% |
| `stg_witsml__wb_geometry_section` | `od_section_in` | 23 | 21.1% |
| `stg_witsml__wb_geometry_section` | `od_section_uom` | 23 | 21.1% |
| `stg_witsml__wb_geometry_section` | `grade` | 99 | 90.8% |
| `int_ddr__activity_section` | `hole_size_in` | 14,901 | 63.6% |
| `int_ddr__hole_section` | `hole_size_in` | 173 | 66.3% |
| `int_ddr__hole_section` | `stated_start_utc` | 2 | 0.8% |
| `int_ddr__hole_section` | `start_md_m` | 17 | 6.5% |
| `int_ddr__hole_section` | `end_md_m` | 37 | 14.2% |
| `int_ddr__report_flag` | `detail` | 9 | 1.8% |
| `int_production__daily_flag` | all 5 columns | 0 |  |
| `int_production__daily_units_check` | `oil_daily_sm3` | 215 | 40.9% |
| `int_production__daily_units_check` | `oil_monthly_sm3` | 215 | 40.9% |
| `int_production__daily_units_check` | `gas_daily_sm3` | 215 | 40.9% |
| `int_production__daily_units_check` | `gas_monthly_sm3` | 215 | 40.9% |
| `int_production__daily_units_check` | `water_daily_sm3` | 215 | 40.9% |
| `int_production__daily_units_check` | `water_monthly_sm3` | 215 | 40.9% |
| `int_production__daily_units_check` | `oil_ratio` | 228 | 43.3% |
| `int_production__daily_units_check` | `gas_ratio` | 228 | 43.3% |
| `int_production__daily_units_check` | `water_ratio` | 241 | 45.8% |
| `int_witsml__log_flag` | all 5 columns | 0 |  |
| `dim_hole_section` | `hole_size_in` | 173 | 66.3% |
| `dim_hole_section` | `stated_start_utc` | 2 | 0.8% |
| `dim_hole_section` | `start_md_m` | 17 | 6.5% |
| `dim_hole_section` | `end_md_m` | 37 | 14.2% |
| `dim_hole_section` | `bit_size_evidence_in` | 235 | 90.0% |
| `dim_wellbore` | `parent_key` | 8,487 | 100.0% |
| `dim_wellbore` | `field_name` | 1,273 | 15.0% |
| `dim_wellbore` | `purpose` | 19 | 0.2% |
| `dim_wellbore` | `status` | 111 | 1.3% |
| `dim_wellbore` | `entry_date` | 265 | 3.1% |
| `dim_wellbore` | `completion_date` | 340 | 4.0% |
| `dim_wellbore` | `total_depth_m` | 351 | 4.1% |
| `fct_lost_time` | `hole_size_in` | 957 | 54.2% |
| `fct_production_monthly_reconciliation` | `oil_workbook_sm3` | 15 | 12.6% |
| `fct_production_monthly_reconciliation` | `oil_sodir_gross_sm3` | 5 | 4.2% |
| `fct_production_monthly_reconciliation` | `oil_sodir_net_sm3` | 5 | 4.2% |
| `fct_production_monthly_reconciliation` | `oil_workbook_to_gross` | 15 | 12.6% |
| `fct_production_monthly_reconciliation` | `oil_workbook_to_net` | 15 | 12.6% |
| `fct_production_monthly_reconciliation` | `oil_gross_to_net` | 15 | 12.6% |
| `fct_production_monthly_reconciliation` | `gas_workbook_sm3` | 15 | 12.6% |
| `fct_production_monthly_reconciliation` | `gas_sodir_gross_sm3` | 5 | 4.2% |
| `fct_production_monthly_reconciliation` | `gas_sodir_net_sm3` | 5 | 4.2% |
| `fct_production_monthly_reconciliation` | `gas_workbook_to_gross` | 18 | 15.1% |
| `fct_production_monthly_reconciliation` | `gas_workbook_to_net` | 18 | 15.1% |
| `fct_production_monthly_reconciliation` | `gas_gross_to_net` | 20 | 16.8% |
| `fct_production_monthly_reconciliation` | `water_workbook_sm3` | 15 | 12.6% |
| `fct_production_monthly_reconciliation` | `water_sodir_gross_sm3` | 5 | 4.2% |
| `fct_production_monthly_reconciliation` | `water_sodir_net_sm3` | 5 | 4.2% |
| `fct_production_monthly_reconciliation` | `water_workbook_to_gross` | 20 | 16.8% |
| `fct_production_monthly_reconciliation` | `water_workbook_to_net` | 20 | 16.8% |
| `fct_production_monthly_reconciliation` | `water_gross_to_net` | 20 | 16.8% |
| `lost_time_codes` | all 3 columns | 0 |  |

Models with more than 100 columns, summarised (a curve absent from a log is null in that log's rows):

| Model | Columns | Cells | Null cells | Columns wholly null |
|---|---|---|---|---|
| `stg_witsml__log_value` | 699 | 3,183,867,411 | 3,002,658,661 | 0 |

Computed by `well_ops.warehouse.quality.null_counts`, `well_ops.warehouse.quality.render_nulls`.
<!-- /quality:nulls -->

## 3. Values read as null

ADR 0002 D3 (as amended) reads -999.99 in drilling reports, the text NULL and empty cells in the
production workbook, and -999.25, the standard WITSML null value, as missing. The counts below are
of source values replaced by null.

<!-- quality:null-values -->
| Source | Value read as null | Values |
|---|---|---|
| drilling reports | `-999.99` | 30,872 |
| production workbook, daily | `NULL or empty` | 83,787 |
| production workbook, monthly | `NULL or empty` | 1,507 |
| WITSML bha_run | `-999.25` | 0 |
| WITSML message | `-999.25` | 0 |
| WITSML mud_log_interval | `-999.25` | 0 |
| WITSML rig | `-999.25` | 0 |
| WITSML trajectory_station | `-999.25` | 0 |
| WITSML tubular_component | `-999.25` | 977 |
| WITSML wb_geometry_section | `-999.25` | 0 |
| WITSML log values (extracted wellbores) | `declared null or -999.25` | 0 |

Array-curve elements equal to -9,999, which the curves do not declare as null. They are kept as published.

| Curve | Elements | Rows containing one |
|---|---|---|
| `ABDCX` | 1,653 | 341 |
| `FABDCX` | 108 | 46 |

Computed by `well_ops.warehouse.quality.null_value_counts`, `well_ops.warehouse.quality.undeclared_array_values`.
<!-- /quality:null-values -->

## 4. Data-quality flags

<!-- quality:flags -->
Flags mark doubtful records; flagged records are kept as published.

| Model | Flag | Rows | Wellbores |
|---|---|---|---|
| `int_ddr__report_flag` | `activity_gap_or_overlap` | 24 | 9 |
| `int_ddr__report_flag` | `before_report_spud` | 50 | 5 |
| `int_ddr__report_flag` | `before_sodir_spud` | 74 | 10 |
| `int_ddr__report_flag` | `depth_not_recorded` | 331 | 15 |
| `int_ddr__report_flag` | `no_activities` | 9 | 7 |
| `int_production__daily_flag` | `negative_volume` | 4 | 2 |
| `int_witsml__log_flag` | `outside_report_period` | 1 | 1 |

Computed by `well_ops.warehouse.quality.flag_counts`.
<!-- /quality:flags -->

## 5. Daily production volume unit

ADR 0002 D9: workbook daily volumes summed per wellbore and month against the monthly sheet (Sm3);
a month agrees when the ratio is within 1 % of 1.

<!-- quality:units-check -->
| Quantity | Agreeing wellbore-months | Non-zero wellbore-months | Share |
|---|---|---|---|
| oil | 298 | 298 | 100.0% |
| gas | 298 | 298 | 100.0% |
| water | 285 | 285 | 100.0% |

Result: `daily_volume_unit` = `Sm3`.

Computed by `well_ops.warehouse.quality.units_check`.
<!-- /quality:units-check -->

## 6. dbt test results

<!-- quality:tests -->
From the last `dbt build` (dbt 1.12.6).

| Node type | Status | Count |
|---|---|---|
| model | success | 29 |
| seed | success | 1 |
| test | pass | 217 |

Tests by type:

| Test | Status | Count |
|---|---|---|
| `accepted_values` | pass | 48 |
| `non_negative` | pass | 13 |
| `not_null` | pass | 87 |
| `ratio_requires_nonzero` | pass | 12 |
| `relationships` | pass | 25 |
| `singular` | pass | 2 |
| `unique` | pass | 30 |

Every test passed.

Computed by `well_ops.warehouse.quality.dbt_test_results`.
<!-- /quality:tests -->
