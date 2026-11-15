# Data Studio (formerly Looker Studio) dashboard

A one-page dashboard on the `mart` layer. About 15 minutes of clicking.

> Open-source MetricFlow has no BI connector (the hosted Semantic Layer APIs are dbt platform only).
> So Data Studio reads the marts directly, and the four metrics are re-created below
> with the **same definitions** as `dbt/models/semantic/sem_sales.yml`.

## 1. Data source

1. Go to <https://datastudio.google.com> → **Create → Report**. On first use, complete the account setup; *Company* is required, but any value works.
2. Choose the **BigQuery** connector → **My projects** → your project → dataset `mart` → table **`rpt_sales`** → **Add**.

`rpt_sales` is the star schema pre-joined into one wide table, one row per order item. Data Studio blends aggregate each table separately before joining, which is easy to get wrong, so BI reads a single table instead. A dbt test checks that its row count and revenue equal `fct_order_items`.

## 2. Calculated fields (match the dbt metric definitions)

**Resource → Manage added data sources → rpt_sales → Edit → Add a field** for each:

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
