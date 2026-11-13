-- Order-item grain, enriched with order-level attributes and revenue logic.
select
    oi.order_item_id,
    oi.order_id,
    oi.customer_id,
    oi.product_id,
    oi.ordered_at,
    date(oi.ordered_at)                                   as order_date,
    oi.item_status,
    o.order_status,
    oi.sale_price,
    p.unit_cost,
    oi.item_status not in ('cancelled', 'returned')       as is_revenue,
    if(oi.item_status not in ('cancelled', 'returned'), oi.sale_price, 0) as net_revenue
from {{ ref('stg_order_items') }} as oi
left join {{ ref('stg_orders') }}   as o using (order_id)
left join {{ ref('stg_products') }} as p using (product_id)
