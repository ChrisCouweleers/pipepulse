create or replace table dim_customers as
select
    cast(customer_id as bigint) as customer_id,
    trim(customer_name) as customer_name,
    lower(trim(email)) as email,
    region,
    segment,
    cast(created_at as date) as created_at,
    cast(source_updated_at as timestamp) as source_updated_at
from raw_customers;

create or replace table dim_products as
select
    cast(product_id as bigint) as product_id,
    product_name,
    product_family,
    cast(list_price as decimal(14,2)) as list_price
from raw_products;
