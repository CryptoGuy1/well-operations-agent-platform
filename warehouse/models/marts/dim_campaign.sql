-- Drilling-report campaigns per wellbore: reports in start order, without those flagged as dated
-- before spud (ADR 0002 D4); a gap of more than 30 days between the end of one report and the
-- start of the next starts a new campaign.
-- - span_days: from the first report's start to the last report's end, in days of 24 h.
-- - active_days: operations days (local report dates) with a report.
-- - operation_phase: the activity category with the most hours in the campaign, ignoring
--   interruption, with the tie order of dim_hole_section; 'none' without such hours.
with reports as (
    select
        report_file,
        wellbore_key,
        start_utc,
        end_utc,
        cast({{ local_time('start_utc', 'start_offset') }} as date) as operations_day
    from {{ ref('stg_ddr__report') }}
    where report_file not in (
        select report_file from {{ ref('int_ddr__report_flag') }}
        where flag in ('before_report_spud', 'before_sodir_spud')
    )
),

gaps as (
    select
        *,
        lag(end_utc) over (
            partition by wellbore_key order by start_utc, report_file
        ) as previous_end_utc
    from reports
),

numbered as (
    select
        *,
        sum(
            case
                when previous_end_utc is null or start_utc - previous_end_utc > interval 30 day
                    then 1
                else 0
            end
        ) over (
            partition by wellbore_key
            order by start_utc, report_file
            rows between unbounded preceding and current row
        ) as campaign_number
    from gaps
),

hours as (
    select numbered.wellbore_key, numbered.campaign_number, activity.category,
           sum(activity.duration_hours) as hours
    from numbered
    inner join {{ ref('stg_ddr__activity') }} as activity
        on activity.report_file = numbered.report_file
    where activity.category <> 'interruption'
    group by all
    having sum(activity.duration_hours) > 0
),

ranked as (
    select
        *,
        row_number() over (
            partition by wellbore_key, campaign_number
            order by
                hours desc,
                case category
                    when 'drilling' then 1
                    when 'formation evaluation' then 2
                    when 'completion' then 3
                    when 'workover' then 4
                    when 'plug abandon' then 5
                    when 'moving' then 6
                end
        ) as rank
    from hours
)

select
    numbered.wellbore_key || '#' || numbered.campaign_number as campaign_id,
    numbered.wellbore_key,
    numbered.campaign_number,
    min(numbered.operations_day) as start_date_local,
    max(numbered.operations_day) as end_date_local,
    epoch(max(numbered.end_utc) - min(numbered.start_utc)) / 86400.0 as span_days,
    count(distinct numbered.operations_day) as active_days,
    count(*) as report_count,
    coalesce(any_value(ranked.category), 'none') as operation_phase
from numbered
left join ranked
    on ranked.wellbore_key = numbered.wellbore_key
    and ranked.campaign_number = numbered.campaign_number
    and ranked.rank = 1
group by numbered.wellbore_key, numbered.campaign_number
