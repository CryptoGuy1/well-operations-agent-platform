-- Curve values of every extracted log, one row per data row. Columns are the union of all
-- curves (by name); a curve absent from a log is null there. Filter on log_id.
select
    regexp_extract(filename, 'witsml_log_values/([^/]+)/', 1) as wellbore_key,
    regexp_extract(filename, 'witsml_log_values/([^/]+)/', 1) || '#'
    || replace(regexp_extract(filename, '/([^/]+)\.parquet$', 1), '_', '/') as log_id,
    * exclude (filename)
from {{ source('witsml_log_values', 'log_value') }}
