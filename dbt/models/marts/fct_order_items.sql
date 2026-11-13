select
    order_item_id,
    order_id,
    customer_id,
    product_id,
    order_date,
    ordered_at,
    item_status,
    sale_price,
    unit_cost,
    is_revenue,
    net_revenue
from {{ ref('core_order_items') }}
