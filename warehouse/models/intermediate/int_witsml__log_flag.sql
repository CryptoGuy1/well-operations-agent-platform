-- Data-quality flags on extracted logs: one row per flag per log. Logs are kept; flags only
-- mark them.
with logs as (
    select
        log_id,
        wellbore_key,
        log_name,
        cast(start_index as timestamptz) at time zone 'UTC' as start_utc,
        cast(end_index as timestamptz) at time zone 'UTC' as end_utc
    from {{ ref('stg_witsml__log') }}
    where index_type = 'date time'
),

report_periods as (
    select wellbore_key, min(start_utc) as first_start_utc, max(end_utc) as last_end_utc
    from {{ ref('stg_ddr__report') }}
    group by 1
),

flags as (
    -- A time-indexed log lying wholly before the wellbore's first drilling report starts or
    -- wholly after its last report ends.
    select
        logs.log_id,
        logs.wellbore_key,
        'outside_report_period' as flag,
        'log ' || strftime(logs.start_utc, '%Y-%m-%d %H:%M') || ' to '
        || strftime(logs.end_utc, '%Y-%m-%d %H:%M') || ' UTC; reports '
        || strftime(report_periods.first_start_utc, '%Y-%m-%d %H:%M') || ' to '
        || strftime(report_periods.last_end_utc, '%Y-%m-%d %H:%M') || ' UTC' as detail
    from logs
    inner join report_periods on report_periods.wellbore_key = logs.wellbore_key
    where logs.end_utc < report_periods.first_start_utc
        or logs.start_utc > report_periods.last_end_utc
)

select log_id || '#' || flag as log_flag_id, log_id, wellbore_key, flag, detail
from flags
