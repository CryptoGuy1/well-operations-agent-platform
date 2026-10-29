select
    source,
    source_name,
    normalised_name,
    source_npdid,
    match_method,
    wellbore_key,
    wellbore_name,
    status
from {{ source('identifiers', 'wellbore_alias') }}
