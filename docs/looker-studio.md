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

Each chart works the same way:
1. **Insert → \<chart type\>**, then click on the canvas to place it.
2. The **Setup** panel opens on the right. Click the existing field chip under **Dimension** or **Metric** to swap it for the field you want, or click **Add dimension** / **Add metric**.

Check that **Data source** reads `rpt_sales` and **Date range dimension** reads `order_date`.

1. **Scorecards.**
   - **Insert → Scorecard**, then set **Metric** to `Revenue`.
   - Copy and paste it three times (⌘C, ⌘V), then change the metric on each copy to `Orders`, `Customers` and `Average order value`.
   - Line the four up along the top.
2. **Revenue over time.**
   - **Insert → Time series chart**, then set **Dimension** to `month_start` and **Metric** to `Revenue`.
   - If the line is daily, click the calendar icon on the `month_start` chip and set **Type → Date & Time → Year Month**.
3. **Revenue by category.**
   - **Insert → Bar chart**, then set **Dimension** to `category` and **Metric** to `Revenue`.
   - **Sort**: `Revenue`, Descending.
   - In the **Style** tab, set **Bars** to 10.
4. **Revenue by country.**
   - **Insert → Table**, then set **Dimension** to `country` and **Metrics** to `Revenue` and `Customers`.
   - Sort by `Revenue`, descending.
5. **Filters.**
   - **Insert → Date range control**, and place it at the top right. In its panel, set **Default date range → Advanced**, with a start date of 1 Jan 2019 and an end date of today. That way the charts show all data by default.
   - **Insert → Drop-down list**, then set **Control field** to `traffic_source`.

Click **View** (top right) to try the filters. The report saves automatically. Rename it by clicking "Untitled Report".

## 4. Check it

Compare the Revenue scorecard (with the date range set to all time) against:

```bash
source .venv/bin/activate          # from the repo root; mf lives in the venv
export GCP_PROJECT=<PROJECT_ID>
cd dbt && mf query --metrics revenue,orders,average_order_value
```

They should match.

## 5. Sharing (optional)

**Share → Manage access**. By default the data source uses **Owner's credentials**, so viewers see the data without needing BigQuery access. Every view runs queries billed to your project, which is negligible at this data size and well inside the free tier.
