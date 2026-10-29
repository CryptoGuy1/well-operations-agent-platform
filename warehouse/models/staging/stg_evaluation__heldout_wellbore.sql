-- Keys only: wellbore names from the held-out list are not carried into the warehouse.
select entry.key as wellbore_key
from {{ source('evaluation', 'splits') }} as splits, unnest(splits.held_out) as held(entry)
