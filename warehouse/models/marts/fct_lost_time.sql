-- Activity hours by wellbore, hole section, code and lost-time tier (ADR 0002 D7). Codes not in
-- the lost_time_codes seed have tier 'none'. Lost time is measured in hours, never counts.
select
    activities.wellbore_key,
    activities.section_id,
    activities.section_label,
    activities.hole_size_in,
    activities.category,
    activities.subcategory,
    coalesce(codes.tier, 'none') as tier,
    sum(activities.duration_hours) as hours,
    count(*) as activities
from {{ ref('int_ddr__activity_section') }} as activities
left join {{ ref('lost_time_codes') }} as codes
    on codes.category = activities.category
    and codes.subcategory = activities.subcategory
group by all
