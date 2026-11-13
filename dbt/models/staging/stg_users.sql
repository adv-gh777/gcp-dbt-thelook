-- Names, email and street address deliberately not carried forward (PII minimisation).
select
    id             as customer_id,
    age,
    gender,
    city,
    state,
    country,
    traffic_source,
    created_at     as signed_up_at
from {{ source('thelook', 'users') }}
