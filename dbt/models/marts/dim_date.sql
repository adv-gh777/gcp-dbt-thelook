-- Calendar spanning all order dates (also the MetricFlow time spine).
with bounds as (
    select min(order_date) as min_d, max(order_date) as max_d
    from {{ ref('core_order_items') }}
)
select
    d                                   as date_day,
    extract(year from d)                as year,
    extract(quarter from d)             as quarter,
    extract(month from d)               as month,
    format_date('%b', d)                as month_name,
    date_trunc(d, month)                as month_start,
    extract(isoweek from d)             as iso_week,
    format_date('%a', d)                as day_name,
    extract(dayofweek from d) in (1, 7) as is_weekend
from bounds, unnest(generate_date_array(min_d, max_d)) as d
