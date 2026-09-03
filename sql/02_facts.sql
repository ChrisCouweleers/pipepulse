create or replace table fct_orders as
select
    cast(o.order_id as bigint) as order_id,
    cast(o.order_date as date) as order_date,
    cast(o.customer_id as bigint) as customer_id,
    cast(o.product_id as bigint) as product_id,
    cast(o.quantity as integer) as quantity,
    cast(o.unit_price as decimal(14,2)) as unit_price,
    cast(o.gross_amount as decimal(14,2)) as gross_amount,
    lower(o.status) as status,
    case when lower(o.status)='refunded' then -1 * cast(o.gross_amount as decimal(14,2))
         else cast(o.gross_amount as decimal(14,2)) end as net_revenue,
    cast(o.source_updated_at as timestamp) as source_updated_at
from raw_orders o;
