-- Dashboard-ready analytical views for the Olist warehouse.
-- These views are read-only query definitions over the existing star schema.

-- Overall sales KPI view for executive dashboard cards.
CREATE OR REPLACE VIEW vw_sales_overview AS
SELECT
    SUM(f.total_item_value) AS total_revenue,
    SUM(f.product_revenue) AS product_revenue,
    SUM(f.freight_value) AS freight_revenue,
    COUNT(DISTINCT f.order_id) AS total_orders,
    COUNT(*) AS total_order_items,
    SUM(f.total_item_value) / NULLIF(COUNT(DISTINCT f.order_id), 0) AS average_order_value,
    AVG(CASE WHEN f.is_late THEN 1.0 ELSE 0.0 END) AS late_delivery_rate,
    AVG(r.review_score) AS average_review_score,
    AVG(f.delivery_days) AS average_delivery_days,
    SUM(f.freight_value) / NULLIF(SUM(f.total_item_value), 0) AS freight_ratio
FROM fact_order_items f
LEFT JOIN dim_review r
    ON f.review_sk = r.review_sk;

-- Monthly revenue trend using purchase date as the default sales date.
CREATE OR REPLACE VIEW vw_monthly_revenue AS
SELECT
    d.year,
    d.month,
    d.month_name,
    DATE_TRUNC('month', d.full_date)::date AS month_start_date,
    SUM(f.total_item_value) AS total_revenue,
    SUM(f.product_revenue) AS product_revenue,
    SUM(f.freight_value) AS freight_revenue,
    COUNT(DISTINCT f.order_id) AS total_orders,
    COUNT(*) AS total_order_items,
    SUM(f.total_item_value) / NULLIF(COUNT(DISTINCT f.order_id), 0) AS average_order_value,
    AVG(CASE WHEN f.is_late THEN 1.0 ELSE 0.0 END) AS late_delivery_rate,
    AVG(r.review_score) AS average_review_score,
    AVG(f.delivery_days) AS average_delivery_days,
    SUM(f.freight_value) / NULLIF(SUM(f.total_item_value), 0) AS freight_ratio
FROM fact_order_items f
JOIN dim_date d
    ON f.purchase_date_sk = d.date_sk
LEFT JOIN dim_review r
    ON f.review_sk = r.review_sk
GROUP BY
    d.year,
    d.month,
    d.month_name,
    DATE_TRUNC('month', d.full_date)::date;

-- Product category performance for category ranking and merchandising analysis.
CREATE OR REPLACE VIEW vw_product_category_performance AS
SELECT
    COALESCE(p.product_category_name_english, 'unknown') AS product_category_name_english,
    COALESCE(p.product_category_name, 'unknown') AS product_category_name,
    COUNT(DISTINCT f.order_id) AS total_orders,
    COUNT(*) AS total_order_items,
    SUM(f.total_item_value) AS total_revenue,
    SUM(f.product_revenue) AS product_revenue,
    SUM(f.freight_value) AS freight_revenue,
    SUM(f.total_item_value) / NULLIF(COUNT(DISTINCT f.order_id), 0) AS average_order_value,
    AVG(r.review_score) AS average_review_score,
    AVG(f.delivery_days) AS average_delivery_days,
    AVG(CASE WHEN f.is_late THEN 1.0 ELSE 0.0 END) AS late_delivery_rate,
    SUM(f.freight_value) / NULLIF(SUM(f.total_item_value), 0) AS freight_ratio
FROM fact_order_items f
JOIN dim_product p
    ON f.product_sk = p.product_sk
LEFT JOIN dim_review r
    ON f.review_sk = r.review_sk
GROUP BY
    COALESCE(p.product_category_name_english, 'unknown'),
    COALESCE(p.product_category_name, 'unknown');

-- Seller-level performance for marketplace operations and seller management.
CREATE OR REPLACE VIEW vw_seller_performance AS
SELECT
    s.seller_id,
    s.seller_city,
    s.seller_state,
    COUNT(DISTINCT f.order_id) AS total_orders,
    COUNT(*) AS total_order_items,
    SUM(f.total_item_value) AS total_revenue,
    SUM(f.product_revenue) AS product_revenue,
    SUM(f.freight_value) AS freight_revenue,
    SUM(f.total_item_value) / NULLIF(COUNT(DISTINCT f.order_id), 0) AS average_order_value,
    AVG(r.review_score) AS average_review_score,
    AVG(f.delivery_days) AS average_delivery_days,
    AVG(CASE WHEN f.is_late THEN 1.0 ELSE 0.0 END) AS late_delivery_rate,
    SUM(f.freight_value) / NULLIF(SUM(f.total_item_value), 0) AS freight_ratio
FROM fact_order_items f
JOIN dim_seller s
    ON f.seller_sk = s.seller_sk
LEFT JOIN dim_review r
    ON f.review_sk = r.review_sk
GROUP BY
    s.seller_id,
    s.seller_city,
    s.seller_state;

-- Delivery performance by purchase month and order status.
CREATE OR REPLACE VIEW vw_delivery_performance AS
SELECT
    d.year,
    d.month,
    d.month_name,
    DATE_TRUNC('month', d.full_date)::date AS month_start_date,
    f.order_status,
    COUNT(DISTINCT f.order_id) AS total_orders,
    COUNT(*) AS total_order_items,
    COUNT(*) FILTER (WHERE f.is_late IS TRUE) AS late_delivery_count,
    AVG(CASE WHEN f.is_late THEN 1.0 ELSE 0.0 END) AS late_delivery_rate,
    AVG(f.delivery_days) AS average_delivery_days,
    AVG(f.estimated_delivery_days) AS average_estimated_delivery_days,
    AVG(f.delay_days) AS average_delay_days,
    SUM(f.total_item_value) AS total_revenue
FROM fact_order_items f
JOIN dim_date d
    ON f.purchase_date_sk = d.date_sk
GROUP BY
    d.year,
    d.month,
    d.month_name,
    DATE_TRUNC('month', d.full_date)::date,
    f.order_status;

-- Customer satisfaction metrics by review score.
CREATE OR REPLACE VIEW vw_customer_satisfaction AS
SELECT
    r.review_score,
    COUNT(DISTINCT f.order_id) AS total_orders,
    COUNT(*) AS total_order_items,
    SUM(f.total_item_value) AS total_revenue,
    SUM(f.product_revenue) AS product_revenue,
    SUM(f.freight_value) AS freight_revenue,
    SUM(f.total_item_value) / NULLIF(COUNT(DISTINCT f.order_id), 0) AS average_order_value,
    AVG(f.delivery_days) AS average_delivery_days,
    AVG(f.delay_days) AS average_delay_days,
    AVG(CASE WHEN f.is_late THEN 1.0 ELSE 0.0 END) AS late_delivery_rate,
    AVG(r.review_response_days) AS average_review_response_days
FROM fact_order_items f
LEFT JOIN dim_review r
    ON f.review_sk = r.review_sk
GROUP BY
    r.review_score;

-- Payment method analysis for checkout and payment behavior dashboards.
CREATE OR REPLACE VIEW vw_payment_analysis AS
SELECT
    ps.primary_payment_type,
    ps.payment_type_count,
    ps.max_payment_installments,
    ps.has_credit_card,
    ps.has_boleto,
    ps.has_voucher,
    ps.has_debit_card,
    COUNT(DISTINCT f.order_id) AS total_orders,
    COUNT(*) AS total_order_items,
    SUM(f.total_item_value) AS total_revenue,
    SUM(f.product_revenue) AS product_revenue,
    SUM(f.freight_value) AS freight_revenue,
    SUM(f.total_item_value) / NULLIF(COUNT(DISTINCT f.order_id), 0) AS average_order_value,
    AVG(r.review_score) AS average_review_score,
    AVG(CASE WHEN f.is_late THEN 1.0 ELSE 0.0 END) AS late_delivery_rate
FROM fact_order_items f
JOIN dim_payment_summary ps
    ON f.payment_summary_sk = ps.payment_summary_sk
LEFT JOIN dim_review r
    ON f.review_sk = r.review_sk
GROUP BY
    ps.primary_payment_type,
    ps.payment_type_count,
    ps.max_payment_installments,
    ps.has_credit_card,
    ps.has_boleto,
    ps.has_voucher,
    ps.has_debit_card;

-- Geographic revenue by customer location for regional sales analysis.
CREATE OR REPLACE VIEW vw_geographic_revenue AS
SELECT
    c.customer_state,
    c.customer_city,
    g.zip_code_prefix AS customer_zip_code_prefix,
    g.latitude,
    g.longitude,
    COUNT(DISTINCT f.order_id) AS total_orders,
    COUNT(*) AS total_order_items,
    SUM(f.total_item_value) AS total_revenue,
    SUM(f.product_revenue) AS product_revenue,
    SUM(f.freight_value) AS freight_revenue,
    SUM(f.total_item_value) / NULLIF(COUNT(DISTINCT f.order_id), 0) AS average_order_value,
    AVG(r.review_score) AS average_review_score,
    AVG(f.delivery_days) AS average_delivery_days,
    AVG(CASE WHEN f.is_late THEN 1.0 ELSE 0.0 END) AS late_delivery_rate,
    SUM(f.freight_value) / NULLIF(SUM(f.total_item_value), 0) AS freight_ratio
FROM fact_order_items f
JOIN dim_customer c
    ON f.customer_sk = c.customer_sk
LEFT JOIN dim_geolocation g
    ON f.customer_geolocation_sk = g.geolocation_sk
LEFT JOIN dim_review r
    ON f.review_sk = r.review_sk
GROUP BY
    c.customer_state,
    c.customer_city,
    g.zip_code_prefix,
    g.latitude,
    g.longitude;
