select
    customer_id,
    age,
    gender,
    city,
    state,
    country,
    traffic_source,
    date(signed_up_at) as signup_date
from {{ ref('stg_users') }}
