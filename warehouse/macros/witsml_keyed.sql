{#- A staged WITSML table with the D1 key and D2 status of its wellbore name, taken from the
    alias table. Names the alias table does not resolve keep a null key and their status. -#}
{% macro witsml_keyed(relation) -%}
select
    alias.wellbore_key,
    alias.status as alias_status,
    obj.*
from {{ relation }} as obj
left join {{ ref('stg_identifiers__wellbore_alias') }} as alias
    on alias.source = 'WITSML' and alias.source_name = obj.source_wellbore_name
{%- endmacro %}

{#- A length in metres, converted to inches (WITSML stores diameters in m). -#}
{% macro m_to_in(column) -%}
round({{ witsml_null(column) }} / 0.0254, 3)
{%- endmacro %}

{#- An angle in degrees from a value in 'dega' or 'rad'; other units give null and fail the
    staging unit tests. -#}
{% macro to_degrees(column, uom) -%}
case {{ uom }}
    when 'dega' then {{ witsml_null(column) }}
    when 'rad' then degrees({{ witsml_null(column) }})
end
{%- endmacro %}

{#- -999.25, the standard WITSML null value, as null (ADR 0002 D3, amended 2026-10-30). -#}
{% macro witsml_null(column) -%}
nullif({{ column }}, -999.25)
{%- endmacro %}
