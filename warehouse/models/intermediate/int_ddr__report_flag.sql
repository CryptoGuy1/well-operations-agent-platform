-- D4 data-quality flags (ADR 0002, as amended): one row per flag per report. Flags mark doubtful
-- records; nothing is corrected or removed.
with reports as (
    select * from {{ ref('stg_ddr__report') }}
),

wellbores as (
    select wellbore_key, entry_date, is_technical_sidetrack from {{ ref('dim_wellbore') }}
),

-- Activities in start order; a gap or overlap is where one does not start when the previous ends.
activity_steps as (
    select
        report_file,
        start_utc,
        lag(end_utc) over (
            partition by report_file order by start_utc, activity_number
        ) as previous_end_utc
    from {{ ref('stg_ddr__activity') }}
),

breaks as (
    select report_file, count(*) as breaks
    from activity_steps
    where previous_end_utc is not null and start_utc <> previous_end_utc
    group by report_file
),

flags as (
    -- Report ends on or before the Sodir entry (spud) date, compared in the report's local
    -- time. Technical sidetracks are not checked: Sodir has no entry date for them.
    select
        reports.report_file,
        reports.wellbore_key,
        'before_sodir_spud' as flag,
        'report ends ' || cast({{ local_time('reports.end_utc', 'reports.end_offset') }} as date)
        || ', Sodir spud ' || wellbores.entry_date as detail
    from reports
    inner join wellbores on wellbores.wellbore_key = reports.wellbore_key
    where not wellbores.is_technical_sidetrack
        and cast({{ local_time('reports.end_utc', 'reports.end_offset') }} as date)
        <= wellbores.entry_date

    union all

    -- Report ends on or before the spud time stated in the report itself (dTimSpud).
    select
        report_file,
        wellbore_key,
        'before_report_spud' as flag,
        'report ends ' || strftime(end_utc, '%Y-%m-%d %H:%M') || ' UTC, report spud '
        || strftime(report_spud_utc, '%Y-%m-%d %H:%M') || ' UTC' as detail
    from reports
    where report_spud_utc is not null and end_utc <= report_spud_utc

    union all

    select report_file, wellbore_key, 'no_activities' as flag, null as detail
    from reports
    where activities = 0

    union all

    select
        reports.report_file,
        reports.wellbore_key,
        'activity_gap_or_overlap' as flag,
        breaks.breaks || ' between consecutive activities' as detail
    from reports
    inner join breaks on breaks.report_file = reports.report_file

    union all

    -- Status md given as -999.99 (D4 as amended: md only).
    select report_file, wellbore_key, 'depth_not_recorded' as flag, 'md' as detail
    from reports
    where list_contains(string_split(nulled_elements, ', '), 'md')
)

select
    report_file || '#' || flag as report_flag_id,
    report_file,
    wellbore_key,
    flag,
    detail
from flags
