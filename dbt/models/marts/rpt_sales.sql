-- Denormalised reporting table for Data Studio, formerly Looker Studio (BI tools work best on one wide table).
-- Grain = one order item, same as fct_order_items.
select
    f.order_item_id,
    f.order_id,
    f.customer_id,
    f.product_id,
    f.order_date,
    d.month_start,
    d.year,
    f.item_status,
    f.sale_price,
    f.net_revenue,
    c.country,
    c.gender,
    c.age,
    c.traffic_source,
    p.category,
    p.brand,
    p.department
from {{ ref('fct_order_items') }} as f
left join {{ ref('dim_customers') }} as c using (customer_id)
left join {{ ref('dim_products') }}  as p using (product_id)
left join {{ ref('dim_date') }}      as d on d.date_day = f.order_date
