-- Daily workbook volumes summed per wellbore and month, against the monthly sheet (Sm3), with
-- the ADR 0002 D9 unit decision. See the model description for the rule.
{% set quantities = ['oil', 'gas', 'water'] %}
with daily as (
    select
        wellbore_key,
        date_trunc('month', production_date) as month_start,
        count(*) as daily_rows,
        {% for q in quantities %}
        sum({{ q }}_volume) as {{ q }}_daily_sm3{{ ',' if not loop.last }}
        {% endfor %}
    from {{ ref('stg_production__daily') }}
    group by all
),

monthly as (
    select wellbore_key, month_start, oil_sm3, gas_sm3, water_sm3
    from {{ ref('stg_production__monthly') }}
),

joined as (
    select
        coalesce(daily.wellbore_key, monthly.wellbore_key) as wellbore_key,
        cast(coalesce(daily.month_start, monthly.month_start) as date) as month_start,
        coalesce(daily.daily_rows, 0) as daily_rows,
        monthly.wellbore_key is not null as in_monthly_sheet,
        {% for q in quantities %}
        daily.{{ q }}_daily_sm3,
        monthly.{{ q }}_sm3 as {{ q }}_monthly_sm3{{ ',' if not loop.last }}
        {% endfor %}
    from daily
    full outer join monthly
        on monthly.wellbore_key = daily.wellbore_key and monthly.month_start = daily.month_start
),

compared as (
    select
        *,
        {% for q in quantities %}
        {{ ratio(q ~ '_daily_sm3', q ~ '_monthly_sm3') }} as {{ q }}_ratio,
        coalesce({{ q }}_daily_sm3, 0) <> 0 or coalesce({{ q }}_monthly_sm3, 0) <> 0
            as {{ q }}_nonzero{{ ',' if not loop.last }}
        {% endfor %}
    from joined
),

agreement as (
    select
        *,
        {% for q in quantities %}
        coalesce(abs({{ q }}_ratio - 1) <= 0.01, false) as {{ q }}_agrees,
        {% endfor %}
        {% for q in quantities %}
        count_if(coalesce(abs({{ q }}_ratio - 1) <= 0.01, false)) over ()
            / nullif(count_if({{ q }}_nonzero) over (), 0) as {{ q }}_agree_share{{ ',' if not loop.last }}
        {% endfor %}
    from compared
)

select
    *,
    case
        when {% for q in quantities %}{{ q }}_agree_share >= 0.95{{ ' and ' if not loop.last }}{% endfor %}
            then 'Sm3'
        else 'unknown'
    end as daily_volume_unit
from agreement
