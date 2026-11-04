-- Data-quality flags on attributed workbook monthly rows: one row per flag per wellbore and month.
-- Values are kept as published; flags only mark them.
with monthly as (
    select * from {{ ref('int_production__monthly_attributed') }}
),

completion as (
    select wellbore_key, date_trunc('month', completion_date) as completion_month
    from {{ ref('dim_wellbore') }}
    where completion_date is not null
),

flags as (
    select
        attributed_wellbore_key as wellbore_key,
        month_start,
        published_npdid,
        'attribution_override' as flag,
        'published NPDID ' || published_npdid as detail
    from monthly
    where attribution_source = 'override'

    union all

    select
        monthly.attributed_wellbore_key,
        monthly.month_start,
        monthly.published_npdid,
        'production_before_completion' as flag,
        'Sodir completion month ' || strftime(completion.completion_month, '%Y-%m') as detail
    from monthly
    inner join completion on completion.wellbore_key = monthly.attributed_wellbore_key
    where monthly.month_start < completion.completion_month
      and (monthly.oil_sm3 > 0 or monthly.gas_sm3 > 0 or monthly.water_sm3 > 0)
)

select
    wellbore_key || '|' || strftime(month_start, '%Y-%m') || '#' || flag as monthly_flag_id,
    wellbore_key,
    month_start,
    published_npdid,
    flag,
    detail
from flags
