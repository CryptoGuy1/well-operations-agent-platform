{#- Fails where a ratio is set although a side is zero or null, or missing although both are
    non-zero. -#}
{% test ratio_requires_nonzero(model, column_name, numerator, denominator) %}
select * from {{ model }}
where ({{ column_name }} is not null)
    <> coalesce({{ numerator }} <> 0 and {{ denominator }} <> 0, false)
{% endtest %}
