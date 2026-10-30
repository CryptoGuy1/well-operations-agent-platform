select
    field_npdid,
    field_name,
    year,
    month,
    make_date(year, month, 1) as month_start,
    oil_gross_mill_sm3,
    gas_gross_bill_sm3,
    condensate_gross_mill_sm3,
    oe_gross_mill_sm3,
    produced_water_in_field_mill_sm3
from {{ source('sodir', 'field_production_gross_monthly') }}
