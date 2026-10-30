select
    log_id,
    wellbore_key,
    source_wellbore_name,
    log_name,
    index_type,
    index_curve,
    index_uom,
    start_index,
    end_index,
    direction,
    service_company,
    run_number,
    chunks,
    rows
from {{ source('witsml_log', 'log') }}
