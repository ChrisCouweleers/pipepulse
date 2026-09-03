create or replace table mart_daily_revenue as
select
    f.order_date,
    c.region,
    c.segment,
    p.product_family,
    count(distinct f.order_id) as order_count,
    count(distinct f.customer_id) as customer_count,
    sum(f.quantity) as units,
    round(sum(f.net_revenue),2) as net_revenue,
    round(avg(f.net_revenue),2) as avg_order_value
from fct_orders f
join dim_customers c using (customer_id)
join dim_products p using (product_id)
group by 1,2,3,4;

create or replace table mart_customer_value as
select
    c.customer_id,
    c.customer_name,
    c.region,
    c.segment,
    count(distinct f.order_id) as lifetime_orders,
    round(sum(f.net_revenue),2) as lifetime_revenue,
    min(f.order_date) as first_order_date,
    max(f.order_date) as last_order_date
from dim_customers c
left join fct_orders f using (customer_id)
group by 1,2,3,4;
