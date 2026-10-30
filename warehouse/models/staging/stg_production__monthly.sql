select
    wellbore_key,
    npdid,
    source_wellbore_name,
    year,
    month,
    make_date(year, month, 1) as month_start,
    on_stream_hours,
    oil_sm3,
    gas_sm3,
    water_sm3,
    gas_injected_sm3,
    water_injected_sm3,
    nulled_columns
from {{ source('production', 'monthly') }}
