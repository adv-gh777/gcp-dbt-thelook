select
    product_id,
    product_name,
    brand,
    category,
    department,
    retail_price,
    unit_cost
from {{ ref('stg_products') }}
