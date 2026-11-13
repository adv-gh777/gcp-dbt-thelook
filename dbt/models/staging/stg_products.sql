select
    id                            as product_id,
    name                          as product_name,
    brand,
    category,
    department,
    cast(retail_price as numeric) as retail_price,
    cast(cost as numeric)         as unit_cost
from {{ source('thelook', 'products') }}
