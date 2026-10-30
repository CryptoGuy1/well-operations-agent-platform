with keyed as ({{ witsml_keyed(source('witsml', 'rig')) }})

select
    source_file as rig_id,
    wellbore_key,
    alias_status,
    source_wellbore_name,
    object_uid as rig_uid,
    object_name as rig_name,
    owner,
    type_rig
from keyed
