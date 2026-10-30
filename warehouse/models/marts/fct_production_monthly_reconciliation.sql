-- Volve field production per month from three sources, each with its basis (ADR 0002 D9).
-- Sodir figures are converted to Sm3 from million Sm3 (oil, water) and billion Sm3 (gas).
{% set quantities = ['oil', 'gas', 'water'] %}
with workbook as (
    select
        month_start,
        sum(oil_sm3) as oil_workbook_sm3,
        sum(gas_sm3) as gas_workbook_sm3,
        sum(water_sm3) as water_workbook_sm3
    from {{ ref('stg_production__monthly') }}
    group by all
),

gross as (
    select
        month_start,
        oil_gross_mill_sm3 * 1e6 as oil_sodir_gross_sm3,
        gas_gross_bill_sm3 * 1e9 as gas_sodir_gross_sm3,
        produced_water_in_field_mill_sm3 * 1e6 as water_sodir_gross_sm3
    from {{ ref('stg_sodir__field_production_gross_monthly') }}
    where field_name = '{{ var("volve_field_name") }}'
),

net as (
    select
        month_start,
        oil_net_mill_sm3 * 1e6 as oil_sodir_net_sm3,
        gas_net_bill_sm3 * 1e9 as gas_sodir_net_sm3,
        produced_water_in_field_mill_sm3 * 1e6 as water_sodir_net_sm3
    from {{ ref('stg_sodir__field_production_net_monthly') }}
    where field_name = '{{ var("volve_field_name") }}'
),

months as (
    select month_start from workbook
    union
    select month_start from gross
    union
    select month_start from net
)

select
    months.month_start,
    'Volve workbook monthly sheet, sum of wellbores (allocated)' as workbook_basis,
    'Sodir sum wellbores (gross)' as sodir_gross_basis,
    'Sodir saleable (net): fuel and flare deducted' as sodir_net_basis,
    {% for q in quantities %}
    {{ q }}_workbook_sm3,
    {{ q }}_sodir_gross_sm3,
    {{ q }}_sodir_net_sm3,
    {{ ratio(q ~ '_workbook_sm3', q ~ '_sodir_gross_sm3') }} as {{ q }}_workbook_to_gross,
    {{ ratio(q ~ '_workbook_sm3', q ~ '_sodir_net_sm3') }} as {{ q }}_workbook_to_net,
    {{ ratio(q ~ '_sodir_gross_sm3', q ~ '_sodir_net_sm3') }} as {{ q }}_gross_to_net{{ ',' if not loop.last }}
    {% endfor %}
from months
left join workbook on workbook.month_start = months.month_start
left join gross on gross.month_start = months.month_start
left join net on net.month_start = months.month_start
