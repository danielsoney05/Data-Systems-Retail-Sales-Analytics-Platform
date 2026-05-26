--------append into order_payments------------
merge olist-494110.olist.order_payments as target
using (
  with append_payment as (
    select order_id, payment_sequential, payment_type, payment_installments, round(sum(price)+sum(freight_value), 2) as total_price
    from olist-494110.olist_staging.stg_daily_orders_raw
    group by order_id, payment_sequential, payment_type, payment_installments
  )
  select * from append_payment
) as source
on (target.order_id = source.order_id)
when matched then 
  update set target.payment_sequential = source.payment_sequential
when not matched then 
  insert (order_id, payment_sequential, payment_type, payment_installments, payment_value)
  values (source.order_id, source.payment_sequential, source.payment_type, source.payment_installments, source.total_price);

--------append into orders------------
merge olist-494110.olist.orders as target 
using (
  with append_order as (
    select order_id, customer_id, order_status, safe.parse_timestamp('%Y-%m-%d %H:%M:%S', order_purchase_timestamp) as order_purchase_timestamp , safe.parse_timestamp('%Y-%m-%d %H:%M:%S', order_approved_at) as order_approved_at, safe.parse_timestamp('%Y-%m-%d %H:%M:%S', order_delivered_carrier_date) as order_delivered_carrier_date , safe.parse_timestamp('%Y-%m-%d %H:%M:%S', order_delivered_customer_date) as order_delivered_customer_date, safe.parse_timestamp('%Y-%m-%d %H:%M:%S', order_estimated_delivery_date) as order_estimated_delivery_date
    from olist-494110.olist_staging.stg_daily_orders_raw
    group by order_id, customer_id, order_status, order_purchase_timestamp, order_approved_at, order_delivered_carrier_date, order_delivered_customer_date, order_estimated_delivery_date
  )
  select * from append_order
) as source
on (target.order_id = source.order_id)
when matched then 
  update set target.order_id = source.order_id
when not matched then 
  insert (order_id, order_status, order_purchase_timestamp, order_approved_at, order_delivered_carrier_date, order_delivered_customer_date, order_estimated_delivery_date)
  values (source.order_id, source.order_status, source.order_purchase_timestamp, source.order_approved_at, source.order_delivered_carrier_date, source.order_delivered_customer_date, source.order_estimated_delivery_date);

--------append into order_items------------
merge olist-494110.olist.order_items as target 
using (
  with append_order_items as (
    select order_id, order_item_id, product_id, seller_id, safe.parse_timestamp('%Y-%m-%d %H:%M:%S',shipping_limit_date) as shipping_limit_date, price, freight_value
    from olist-494110.olist_staging.stg_daily_orders_raw
  )
  select * from append_order_items
) as source
on (target.order_id = source.order_id and target.order_item_id = source.order_item_id)
when matched then 
  update set target.order_id = source.order_id
when not matched then 
  insert (order_id, order_item_id, product_id, seller_id, shipping_limit_date, price, freight_value)
  values (source.order_id, source.order_item_id, source.product_id, source.seller_id, source.shipping_limit_date, source.price, source.freight_value);