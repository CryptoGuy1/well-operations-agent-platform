{#- Local time from a UTC timestamp and its original offset text ('+02:00'). -#}
{% macro local_time(utc_column, offset_column) -%}
    (
        {{ utc_column }}
        + (case when left({{ offset_column }}, 1) = '-' then -1 else 1 end)
        * (
            cast(substr({{ offset_column }}, 2, 2) as integer) * 60
            + cast(substr({{ offset_column }}, 5, 2) as integer)
        )
        * interval 1 minute
    )
{%- endmacro %}
