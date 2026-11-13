-- Reconciliation: row count and total sale_price in the fact must equal the public source.
-- The source is regenerated continuously, so compare up to the fact's latest timestamp.
with mart as (
    select count(*) as row_count, sum(sale_price) as revenue
    from {{ ref('fct_order_items') }}
),

src as (
    select count(*) as row_count, sum(cast(sale_price as numeric)) as revenue
    from {{ source('thelook', 'order_items') }}
    where created_at <= (select max(ordered_at) from {{ ref('fct_order_items') }})
)

select
    mart.row_count as mart_rows,
    src.row_count  as source_rows,
    mart.revenue   as mart_revenue,
    src.revenue    as source_revenue
from mart cross join src
where mart.row_count != src.row_count
   or abs(mart.revenue - src.revenue) > 0.01
