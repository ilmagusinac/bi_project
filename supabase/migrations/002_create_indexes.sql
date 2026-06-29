CREATE INDEX IF NOT EXISTS idx_fact_order_items_customer_sk
    ON fact_order_items (customer_sk);

CREATE INDEX IF NOT EXISTS idx_fact_order_items_product_sk
    ON fact_order_items (product_sk);

CREATE INDEX IF NOT EXISTS idx_fact_order_items_seller_sk
    ON fact_order_items (seller_sk);

CREATE INDEX IF NOT EXISTS idx_fact_order_items_payment_summary_sk
    ON fact_order_items (payment_summary_sk);

CREATE INDEX IF NOT EXISTS idx_fact_order_items_review_sk
    ON fact_order_items (review_sk);

CREATE INDEX IF NOT EXISTS idx_fact_order_items_customer_geolocation_sk
    ON fact_order_items (customer_geolocation_sk);

CREATE INDEX IF NOT EXISTS idx_fact_order_items_seller_geolocation_sk
    ON fact_order_items (seller_geolocation_sk);

CREATE INDEX IF NOT EXISTS idx_fact_order_items_approved_date_sk
    ON fact_order_items (approved_date_sk);

CREATE INDEX IF NOT EXISTS idx_fact_order_items_delivered_carrier_date_sk
    ON fact_order_items (delivered_carrier_date_sk);

CREATE INDEX IF NOT EXISTS idx_fact_order_items_delivered_customer_date_sk
    ON fact_order_items (delivered_customer_date_sk);

CREATE INDEX IF NOT EXISTS idx_fact_order_items_estimated_delivery_date_sk
    ON fact_order_items (estimated_delivery_date_sk);

CREATE INDEX IF NOT EXISTS idx_dim_customer_customer_state
    ON dim_customer (customer_state);

CREATE INDEX IF NOT EXISTS idx_dim_customer_customer_unique_id
    ON dim_customer (customer_unique_id);

CREATE INDEX IF NOT EXISTS idx_dim_customer_geolocation_sk
    ON dim_customer (geolocation_sk);

CREATE INDEX IF NOT EXISTS idx_dim_product_category_english
    ON dim_product (product_category_name_english);

CREATE INDEX IF NOT EXISTS idx_dim_seller_seller_state
    ON dim_seller (seller_state);

CREATE INDEX IF NOT EXISTS idx_dim_seller_geolocation_sk
    ON dim_seller (geolocation_sk);

CREATE INDEX IF NOT EXISTS idx_dim_geolocation_state_city
    ON dim_geolocation (state, city);

CREATE INDEX IF NOT EXISTS idx_dim_payment_summary_primary_payment_type
    ON dim_payment_summary (primary_payment_type);

CREATE INDEX IF NOT EXISTS idx_dim_payment_summary_max_installments
    ON dim_payment_summary (max_payment_installments);

CREATE INDEX IF NOT EXISTS idx_dim_review_review_score
    ON dim_review (review_score);

CREATE INDEX IF NOT EXISTS idx_fact_order_items_order_status
    ON fact_order_items (order_status);

CREATE INDEX IF NOT EXISTS idx_fact_order_items_revenue_by_purchase_date
    ON fact_order_items (purchase_date_sk)
    INCLUDE (product_revenue, freight_value, total_item_value);

CREATE INDEX IF NOT EXISTS idx_fact_order_items_product_revenue
    ON fact_order_items (product_sk, purchase_date_sk)
    INCLUDE (product_revenue, freight_value, total_item_value);

CREATE INDEX IF NOT EXISTS idx_fact_order_items_seller_revenue
    ON fact_order_items (seller_sk, purchase_date_sk)
    INCLUDE (product_revenue, freight_value, total_item_value);

CREATE INDEX IF NOT EXISTS idx_fact_order_items_customer_revenue
    ON fact_order_items (customer_sk, purchase_date_sk)
    INCLUDE (product_revenue, freight_value, total_item_value);

CREATE INDEX IF NOT EXISTS idx_fact_order_items_delivery_performance
    ON fact_order_items (is_late, delivered_customer_date_sk)
    INCLUDE (delivery_days, estimated_delivery_days, delay_days);

CREATE INDEX IF NOT EXISTS idx_fact_order_items_delay_days
    ON fact_order_items (delay_days);

CREATE INDEX IF NOT EXISTS idx_fact_order_items_review_analysis
    ON fact_order_items (review_sk, purchase_date_sk)
    INCLUDE (product_revenue, freight_value, total_item_value);

CREATE INDEX IF NOT EXISTS idx_fact_order_items_customer_geo_analysis
    ON fact_order_items (customer_geolocation_sk, purchase_date_sk)
    INCLUDE (product_revenue, freight_value, total_item_value);

CREATE INDEX IF NOT EXISTS idx_fact_order_items_seller_geo_analysis
    ON fact_order_items (seller_geolocation_sk, purchase_date_sk)
    INCLUDE (product_revenue, freight_value, total_item_value);
