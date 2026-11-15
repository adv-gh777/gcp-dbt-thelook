-- The reporting table must not drop or duplicate rows/revenue relative to the fact.
select *
from (select count(*) as n, sum(net_revenue) as rev from {{ ref('rpt_sales') }}) r
cross join (select count(*) as n, sum(net_revenue) as rev from {{ ref('fct_order_items') }}) f
where r.n != f.n or r.rev != f.rev
