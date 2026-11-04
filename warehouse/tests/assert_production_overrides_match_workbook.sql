-- Every production attribution override names an NPDID and daily-sheet wellbore code that the
-- workbook publishes together, and its NPDID has monthly rows.
select overrides.published_npdid
from {{ ref('production_attribution_overrides') }} as overrides
where not exists (
    select 1 from {{ ref('stg_production__daily') }} as daily
    where daily.npdid = overrides.published_npdid
      and daily.source_wellbore_code = overrides.published_wellbore_code
)
or not exists (
    select 1 from {{ ref('stg_production__monthly') }} as monthly
    where monthly.npdid = overrides.published_npdid
)
