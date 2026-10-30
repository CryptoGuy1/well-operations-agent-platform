-- Every extracted log has exactly as many staged value rows as its chunk files hold data rows.
with value_rows as (
    select log_id, count(*) as rows from {{ ref('stg_witsml__log_value') }} group by 1
)

select logs.log_id, logs.rows, value_rows.rows as value_rows
from {{ ref('stg_witsml__log') }} as logs
full outer join value_rows on value_rows.log_id = logs.log_id
where coalesce(logs.rows, -1) <> coalesce(value_rows.rows, -1)
