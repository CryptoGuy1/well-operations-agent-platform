-- One row per hole section with its operation phase, activity hours and new hole drilled.
-- - operation_phase: the activity category with the most hours in the section, ignoring
--   interruption; ties go to drilling > formation evaluation > completion > workover >
--   plug abandon > moving. A section with no hours outside interruption has phase 'none'.
-- - new_hole_drilled_m: the section's max md minus the wellbore's max md in earlier sections,
--   floored at 0 and rounded to 0.01 m. The first section (or one after sections without a
--   recorded md) uses its stated start md instead.
-- - bit_size_evidence_in: evidence only, never used as hole size. The bit size of the latest
--   WITSML bit run that started at or up to 7 days before the section's stated start, rounded to
--   1/8 in; null where there is none or several sizes share that run start. See
--   docs/data/hole-size-bit-source-experiment.md.
with hours as (
    select section_id, category, sum(duration_hours) as hours
    from {{ ref('int_ddr__activity_section') }}
    group by all
),

ranked as (
    select
        section_id,
        category,
        row_number() over (
            partition by section_id
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
    where category <> 'interruption' and hours > 0
),

totals as (
    select
        section_id,
        sum(hours) as activity_hours,
        coalesce(sum(hours) filter (where category = 'interruption'), 0) as interruption_hours
    from hours
    group by section_id
),

sections as (
    select
        *,
        max(end_md_m) over (
            partition by wellbore_key
            order by section_number
            rows between unbounded preceding and 1 preceding
        ) as previous_max_md_m
    from {{ ref('int_ddr__hole_section') }}
),

-- WITSML bit runs: a BHA run whose tubular assembly holds a bit with a stated size. Every
-- tubular component may carry a bitRecord, so only components typed as bits count.
bit_runs as (
    select
        runs.wellbore_key,
        runs.run_start_utc,
        round(bits.dia_bit_in * 8) / 8 as bit_size_in
    from {{ ref('stg_witsml__bha_run') }} as runs
    inner join {{ ref('stg_witsml__tubular_component') }} as bits
        on bits.source_wellbore_name = runs.source_wellbore_name
        and bits.tubular_uid = runs.tubular_uid
    where runs.wellbore_key is not null
        and runs.run_start_utc is not null
        and bits.type_tubular_comp like 'bit %'
        and bits.dia_bit_in is not null
),

candidate_bits as (
    select
        sections.section_id,
        bit_runs.run_start_utc,
        bit_runs.bit_size_in,
        max(bit_runs.run_start_utc) over (partition by sections.section_id) as latest_start_utc
    from sections
    inner join bit_runs
        on bit_runs.wellbore_key = sections.wellbore_key
        and bit_runs.run_start_utc <= sections.stated_start_utc
        and bit_runs.run_start_utc >= sections.stated_start_utc - interval 7 day
),

section_bits as (
    select
        section_id,
        case when count(distinct bit_size_in) = 1 then min(bit_size_in) end as bit_size_in
    from candidate_bits
    where run_start_utc = latest_start_utc
    group by section_id
)

select
    sections.* exclude (previous_max_md_m),
    coalesce(ranked.category, 'none') as operation_phase,
    coalesce(totals.activity_hours, 0) as activity_hours,
    coalesce(totals.interruption_hours, 0) as interruption_hours,
    round(greatest(
        sections.end_md_m - coalesce(sections.previous_max_md_m, sections.start_md_m), 0
    ), 2) as new_hole_drilled_m,
    section_bits.bit_size_in as bit_size_evidence_in
from sections
left join ranked on ranked.section_id = sections.section_id and ranked.rank = 1
left join totals on totals.section_id = sections.section_id
left join section_bits on section_bits.section_id = sections.section_id
