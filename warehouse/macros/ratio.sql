{#- numerator / denominator where both are non-zero; null otherwise. -#}
{% macro ratio(numerator, denominator) -%}
case when {{ numerator }} <> 0 and {{ denominator }} <> 0 then {{ numerator }} / {{ denominator }} end
{%- endmacro %}
