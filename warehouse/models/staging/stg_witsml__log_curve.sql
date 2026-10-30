select
    log_id || '|' || mnemonic || '|' || coalesce(unit, '') as log_curve_id,
    log_id,
    mnemonic,
    unit,
    type_log_data,
    curve_description,
    chunks
from {{ source('witsml_log', 'log_curve') }}
