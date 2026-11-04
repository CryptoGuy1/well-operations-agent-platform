-- Data-quality flags on attributed workbook daily rows: one row per flag per wellbore and day.
-- Values are kept as published; flags only mark them. Volumes are Sm3 (int_production__daily_units_check).
{% set volumes = ['oil', 'gas', 'water', 'water_injected'] %}
with daily as (
    select
        attributed_wellbore_key as wellbore_key,
        published_npdid,
        production_date,
        {% for v in volumes %}
        {{ v }}_volume as {{ v }}_sm3{{ ',' if not loop.last }}
        {% endfor %}
    from {{ ref('int_production__daily_attributed') }}
),

flags as (
    select
        wellbore_key,
        published_npdid,
        production_date,
        'negative_volume' as flag,
        concat_ws(
            ', ',
            {% for v in volumes %}
            case when {{ v }}_sm3 < 0 then '{{ v }}_sm3' end{{ ',' if not loop.last }}
            {% endfor %}
        ) as detail
    from daily
    where {% for v in volumes %}{{ v }}_sm3 < 0{{ ' or ' if not loop.last }}{% endfor %}
)

select
    wellbore_key || '|' || production_date || '#' || flag as daily_flag_id,
    wellbore_key,
    published_npdid,
    production_date,
    flag,
    detail
from flags
