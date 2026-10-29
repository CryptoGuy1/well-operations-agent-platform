select
    cast(npdid as varchar) as wellbore_key,
    npdid,
    wellbore_name,
    well_name,
    field_name,
    purpose,
    status,
    entry_date,
    completion_date,
    total_depth_m,
    source_table
from {{ source('sodir', 'wellbore') }}
