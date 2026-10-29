-- One row per D1 key (ADR 0002): every Sodir wellbore, plus one row per technical sidetrack
-- found in the Volve sources. Sidetracks take well and field from their parent; Sodir
-- publishes no purpose, status, dates or depth for them, so those stay null.
with sodir as (
    select * from {{ ref('stg_sodir__wellbore') }}
),

sidetracks as (
    select distinct
        wellbore_key,
        wellbore_name,
        split_part(wellbore_key, ':', 1) as parent_key
    from {{ ref('stg_identifiers__wellbore_alias') }}
    where status = 'wellbore' and wellbore_key like '%:%'
),

heldout as (
    select wellbore_key from {{ ref('stg_evaluation__heldout_wellbore') }}
),

wellbores as (
    select
        wellbore_key,
        wellbore_name,
        npdid,
        cast(null as varchar) as parent_key,
        false as is_technical_sidetrack,
        well_name,
        field_name,
        coalesce(field_name = 'VOLVE', false) as in_volve_field,
        purpose,
        status,
        entry_date,
        completion_date,
        total_depth_m
    from sodir

    union all

    select
        sidetracks.wellbore_key,
        sidetracks.wellbore_name,
        parent.npdid,
        sidetracks.parent_key,
        true as is_technical_sidetrack,
        parent.well_name,
        parent.field_name,
        coalesce(parent.field_name = 'VOLVE', false) as in_volve_field,
        null as purpose,
        null as status,
        null as entry_date,
        null as completion_date,
        null as total_depth_m
    from sidetracks
    inner join sodir as parent on parent.wellbore_key = sidetracks.parent_key
)

select
    wellbores.*,
    heldout.wellbore_key is not null as is_heldout
from wellbores
left join heldout on heldout.wellbore_key = wellbores.wellbore_key
