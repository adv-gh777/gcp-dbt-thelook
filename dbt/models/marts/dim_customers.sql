select
    customer_id,
    age,
    gender,
    city,
    state,
    country,
    traffic_source,
    signup_date
from {{ ref('core_customers') }}
