{#- A staged workbook sheet with its rows attributed to a wellbore (ADR 0002 D1 amendment of
    2026-11-03): the published NPDID's key, unless the overrides seed names another wellbore.
    The published NPDID and key are kept. -#}
{% macro production_attributed(relation) -%}
select
    coalesce(override.attributed_wellbore_key, sheet.wellbore_key) as attributed_wellbore_key,
    case when override.published_npdid is null then 'npdid' else 'override' end
        as attribution_source,
    override.attribution_reason,
    sheet.npdid as published_npdid,
    sheet.wellbore_key as published_wellbore_key,
    sheet.* exclude (wellbore_key, npdid)
from {{ relation }} as sheet
left join {{ ref('production_attribution_overrides') }} as override
    on override.published_npdid = sheet.npdid
{%- endmacro %}
