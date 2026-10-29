-- fct_lost_time must account for every activity hour: per wellbore, its hours equal the sum of
-- activity durations. Returns the wellbores where they differ.
with facts as (
    select wellbore_key, sum(hours) as hours from {{ ref('fct_lost_time') }} group by 1
),

activities as (
    select wellbore_key, sum(duration_hours) as hours from {{ ref('stg_ddr__activity') }} group by 1
)

select activities.wellbore_key, activities.hours, facts.hours as fact_hours
from activities
full outer join facts on facts.wellbore_key = activities.wellbore_key
where abs(coalesce(activities.hours, 0) - coalesce(facts.hours, 0)) > 1e-6
