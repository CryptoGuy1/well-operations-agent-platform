-- Each activity with the hole section active at its start time: the latest section of the same
-- wellbore that started at or before it.
select
    activities.activity_id,
    activities.report_file,
    activities.wellbore_key,
    sections.section_id,
    sections.section_label,
    sections.hole_size_in,
    activities.start_utc,
    activities.end_utc,
    activities.duration_hours,
    activities.category,
    activities.subcategory
from {{ ref('stg_ddr__activity') }} as activities
asof left join {{ ref('int_ddr__hole_section') }} as sections
    on sections.wellbore_key = activities.wellbore_key
    and activities.start_utc >= sections.start_utc
