-- Averages keep their published SI units in the column names.
with keyed as ({{ witsml_keyed(source('witsml', 'mud_log_interval')) }})

select
    source_file || '#' || row_uid as interval_id,
    wellbore_key,
    alias_status,
    source_wellbore_name,
    source_file,
    object_uid as mud_log_uid,
    object_name as mud_log_name,
    mud_log_company,
    interval_utc,
    interval_offset,
    type_lithology,
    {{ witsml_null('md_top') }} as md_top_m,
    md_top_uom,
    {{ witsml_null('md_bottom') }} as md_bottom_m,
    md_bottom_uom,
    {{ witsml_null('rop_av') }} as rop_av_m_per_s,
    rop_av_uom,
    {{ witsml_null('wob_av') }} as wob_av_n,
    wob_av_uom,
    {{ witsml_null('tq_av') }} as tq_av_n_m,
    tq_av_uom,
    {{ witsml_null('rpm_av') }} as rpm_av_c_per_s,
    rpm_av_uom,
    {{ witsml_null('wt_mud_av') }} as wt_mud_av_kg_m3,
    wt_mud_av_uom,
    {{ witsml_null('ecd_td_av') }} as ecd_td_av_kg_m3,
    ecd_td_av_uom
from keyed
