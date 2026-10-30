with keyed as ({{ witsml_keyed(source('witsml', 'bha_run')) }})

select
    source_file as bha_run_id,
    wellbore_key,
    alias_status,
    source_wellbore_name,
    object_uid as bha_run_uid,
    object_name as bha_run_name,
    tubular_uid,
    run_start_utc,
    run_start_offset,
    run_stop_utc,
    run_stop_offset,
    drilling_start_utc,
    drilling_start_offset,
    drilling_stop_utc,
    drilling_stop_offset,
    num_bit_run,
    num_string_run,
    {{ witsml_null('md_hole_start') }} as md_hole_start_m,
    md_hole_start_uom,
    {{ witsml_null('md_hole_stop') }} as md_hole_stop_m,
    md_hole_stop_uom
from keyed
