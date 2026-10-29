select
    report_file || '#' || activity_number as activity_id,
    report_file,
    activity_number,
    wellbore_key,
    start_utc,
    start_offset,
    end_utc,
    end_offset,
    duration_hours,
    md_m,
    phase,
    proprietary_code,
    category,
    subcategory,
    state,
    state_detail,
    comments
from {{ source('ddr', 'activity') }}
