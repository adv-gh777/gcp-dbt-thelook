# Looker Studio dashboard

A one-page dashboard on the `mart` star schema. About 15 minutes of clicking.

> Open-source MetricFlow has no BI connector (the hosted Semantic Layer APIs are dbt platform only).
> So Looker Studio reads the marts directly, and the four metrics are re-created below
> with the **same definitions** as `dbt/models/semantic/sem_sales.yml`.

## 1. Data source (blended star schema)

1. Go to <https://lookerstudio.google.com> → **Create → Report**.
2. Choose the **BigQuery** connector → **My projects** → your project → dataset `mart` → table `fct_order_items` → **Add**.
3. Add three more BigQuery sources the same way: `dim_customers`, `dim_products`, `dim_date`.
4. **Resource → Manage blends → Add a blend**:
   - Left table: `fct_order_items`, all columns.
   - Join `dim_customers` with **Left outer** on `customer_id = customer_id`; keep `country`, `gender`, `traffic_source`.
   - Join `dim_products` with **Left outer** on `product_id = product_id`; keep `category`, `brand`, `department`.
   - Join `dim_date` with **Left outer** on `order_date = date_day`; keep `month_start`, `year`.
   - Name it `sales` → **Save**.

## 2. Calculated fields (match the dbt metric definitions)

On the `sales` blend, **Add a field** for each:

| Field | Formula |
|---|---|
| Revenue | `SUM(net_revenue)` |
| Orders | `COUNT_DISTINCT(order_id)` |
| Customers | `COUNT_DISTINCT(customer_id)` |
| Average order value | `SUM(net_revenue) / COUNT_DISTINCT(order_id)` |

## 3. Charts

1. **Scorecards** (4): Revenue, Orders, Customers, Average order value.
2. **Time series**: dimension `month_start`, metric Revenue.
3. **Bar chart**: dimension `category`, metric Revenue, sorted descending, top 10.
4. **Geo chart or table**: dimension `country`, metrics Revenue and Customers.
5. **Controls**: add a **Date range control** (date dimension `order_date`) and a **Drop-down list** on `traffic_source`.

## 4. Check it

Compare the Revenue scorecard (with the date range set to all time) against:

```bash
cd dbt && mf query --metrics revenue,orders,average_order_value
```

They should match.

## 5. Sharing (optional)

**Share → Manage access**. By default the data source uses **Owner's credentials**, so viewers see the data without needing BigQuery access. Every view runs queries billed to your project, which is negligible at this data size and well inside the free tier.
