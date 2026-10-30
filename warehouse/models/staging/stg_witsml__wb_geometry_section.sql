with keyed as ({{ witsml_keyed(source('witsml', 'wb_geometry_section')) }})

select
    source_file || '#' || row_uid as geometry_section_id,
    wellbore_key,
    alias_status,
    source_wellbore_name,
    source_file,
    object_uid as wb_geometry_uid,
    object_name as wb_geometry_name,
    report_utc,
    report_offset,
    type_hole_casing,
    {{ witsml_null('md_top') }} as md_top_m,
    md_top_uom,
    {{ witsml_null('md_bottom') }} as md_bottom_m,
    md_bottom_uom,
    {{ witsml_null('tvd_top') }} as tvd_top_m,
    tvd_top_uom,
    {{ witsml_null('tvd_bottom') }} as tvd_bottom_m,
    tvd_bottom_uom,
    {{ m_to_in('id_section') }} as id_section_in,
    id_section_uom,
    {{ m_to_in('od_section') }} as od_section_in,
    od_section_uom,
    grade
from keyed
