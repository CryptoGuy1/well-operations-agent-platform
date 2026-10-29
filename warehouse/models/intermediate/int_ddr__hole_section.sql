-- Hole sections per wellbore from the drilling report status fields, with reports taken in start
-- order:
-- - Reports before the wellbore's first stated diaHole form the section 'before_first_section'
--   (hole size unknown).
-- - After that, a new section starts where diaHole is stated and differs from the current size,
--   or where dTimDiaHoleStart changes. A section that starts with a new dTimDiaHoleStart but no
--   diaHole has hole size unknown: the old size is not carried into it (for example plug-back
--   after section TD).
-- - Within a section, a missing diaHole carries the section's size forward and the report is
--   marked inferred; inferred_share is the share of such reports.
with reports as (
    select
        report_file,
        wellbore_key,
        start_utc,
        end_utc,
        md_m,
        dia_hole_in,
        md_dia_hole_start_m,
        dia_hole_start_utc
    from {{ ref('stg_ddr__report') }}
),

ordered as (
    select
        *,
        count(dia_hole_in) over (
            partition by wellbore_key
            order by start_utc, report_file
            rows between unbounded preceding and current row
        ) = 0 as before_first,
        last_value(dia_hole_in ignore nulls) over (
            partition by wellbore_key
            order by start_utc, report_file
            rows between unbounded preceding and 1 preceding
        ) as previous_size_in,
        last_value(dia_hole_start_utc ignore nulls) over (
            partition by wellbore_key
            order by start_utc, report_file
            rows between unbounded preceding and 1 preceding
        ) as previous_stated_start_utc
    from reports
),

boundaries as (
    select
        *,
        case
            when before_first then false
            when previous_size_in is null then true  -- first stated diaHole
            when dia_hole_in is not null and dia_hole_in <> previous_size_in then true
            when dia_hole_start_utc is distinct from previous_stated_start_utc
                and dia_hole_start_utc is not null then true
            else false
        end as starts_section
    from ordered
),

numbered as (
    select
        *,
        sum(case when starts_section then 1 else 0 end) over (
            partition by wellbore_key
            order by start_utc, report_file
            rows between unbounded preceding and current row
        ) as section_number
    from boundaries
),

sized as (
    select
        *,
        -- The section's size is the last stated diaHole within the section; null if none yet.
        last_value(dia_hole_in ignore nulls) over (
            partition by wellbore_key, section_number
            order by start_utc, report_file
            rows between unbounded preceding and current row
        ) as hole_size_in
    from numbered
)

select
    wellbore_key || '#'
    || case when section_number = 0 then 'before_first_section' else cast(section_number as varchar) end
    as section_id,
    wellbore_key,
    section_number,
    case
        when section_number = 0 then 'before_first_section'
        when max(hole_size_in) is null then 'hole size unknown'
        else max(hole_size_in) || ' in'
    end as section_label,
    -- A section's stated size; null where no report in it states one.
    max(hole_size_in) as hole_size_in,
    case when max(hole_size_in) is null then 'unknown' else 'report' end as hole_size_source,
    min(start_utc) as start_utc,
    max(end_utc) as end_utc,
    -- Where and when the section started, as stated by its first report.
    arg_min(dia_hole_start_utc, start_utc) as stated_start_utc,
    arg_min(md_dia_hole_start_m, start_utc) as start_md_m,
    max(md_m) as end_md_m,
    count(*) as report_count,
    avg(
        case when dia_hole_in is null and hole_size_in is not null then 1.0 else 0.0 end
    ) as inferred_share
from sized
group by wellbore_key, section_number
