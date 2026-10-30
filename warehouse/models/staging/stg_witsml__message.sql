with keyed as ({{ witsml_keyed(source('witsml', 'message')) }})

select
    source_file as message_id,
    wellbore_key,
    alias_status,
    source_wellbore_name,
    object_uid as message_uid,
    object_name as message_name,
    message_utc,
    message_offset,
    {{ witsml_null('md') }} as md_m,
    md_uom,
    type_message,
    severity,
    message_text
from keyed
