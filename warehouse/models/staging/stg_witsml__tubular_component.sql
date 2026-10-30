with keyed as ({{ witsml_keyed(source('witsml', 'tubular_component')) }})

select
    source_file || '#' || row_uid as component_id,
    wellbore_key,
    alias_status,
    source_wellbore_name,
    source_file,
    object_uid as tubular_uid,
    object_name as tubular_name,
    type_tubular_assy,
    type_tubular_comp,
    {{ witsml_null('sequence') }} as sequence,
    {{ m_to_in('id') }} as id_in,
    id_uom,
    {{ m_to_in('od') }} as od_in,
    od_uom,
    {{ witsml_null('len') }} as len_m,
    len_uom,
    {{ m_to_in('dia_bit') }} as dia_bit_in,
    dia_bit_uom,
    vendor
from keyed
