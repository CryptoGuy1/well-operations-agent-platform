with keyed as ({{ witsml_keyed(source('witsml', 'trajectory_station')) }})

select
    source_file || '#' || row_uid as station_id,
    wellbore_key,
    alias_status,
    source_wellbore_name,
    source_file,
    object_uid as trajectory_uid,
    object_name as trajectory_name,
    station_utc,
    station_offset,
    type_traj_station,
    type_survey_tool,
    status_traj_station,
    {{ witsml_null('md') }} as md_m,
    md_uom,
    {{ witsml_null('tvd') }} as tvd_m,
    tvd_uom,
    {{ to_degrees('incl', 'incl_uom') }} as incl_deg,
    incl_uom,
    {{ to_degrees('azi', 'azi_uom') }} as azi_deg,
    azi_uom,
    {{ witsml_null('disp_ns') }} as disp_ns_m,
    disp_ns_uom,
    {{ witsml_null('disp_ew') }} as disp_ew_m,
    disp_ew_uom,
    -- Dogleg severity in degrees per 30 m.
    case dls_uom
        when 'dega/30m' then {{ witsml_null('dls') }}
        when 'dega/m' then {{ witsml_null('dls') }} * 30
        when 'rad/m' then degrees({{ witsml_null('dls') }}) * 30
    end as dls_deg_per_30m,
    dls_uom
from keyed
