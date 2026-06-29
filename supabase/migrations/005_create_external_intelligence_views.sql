-- Analytical views for the external intelligence layer.
-- These views join curated Brave Search intelligence to dashboard-ready
-- warehouse metrics without modifying the underlying fact or dimension tables.

-- Product category intelligence combines internal category performance with
-- external market context for merchandising, demand, and risk analysis.
CREATE OR REPLACE VIEW vw_product_category_intelligence AS
SELECT
    p.product_category_name_english,
    p.total_revenue,
    p.product_revenue,
    p.freight_revenue,
    p.total_orders,
    p.average_order_value,
    p.average_review_score,
    p.late_delivery_rate,
    p.freight_ratio,
    e.market_summary,
    e.target_customer_segment,
    e.business_recommendation,
    e.risk_or_challenge,
    e.source_titles,
    e.source_urls,
    e.intelligence_date,
    e.search_query
FROM vw_product_category_performance p
INNER JOIN dim_external_intelligence e
    ON e.intelligence_track = 'product_category_market'
    AND e.entity_type = 'product_category'
    AND e.entity_value = p.product_category_name_english;

COMMENT ON VIEW vw_product_category_intelligence IS
    'Combines product category performance metrics with external product-category market intelligence for Superset merchandising and category strategy dashboards.';

-- Geographic intelligence rolls customer revenue up to state level and joins
-- regional logistics and consumer behavior context from external sources.
CREATE OR REPLACE VIEW vw_geographic_intelligence AS
WITH customer_state_performance AS (
    SELECT
        customer_state,
        SUM(total_revenue) AS total_revenue,
        SUM(product_revenue) AS product_revenue,
        SUM(freight_revenue) AS freight_revenue,
        SUM(total_orders) AS total_orders,
        SUM(total_revenue) / NULLIF(SUM(total_orders), 0) AS average_order_value,
        AVG(average_review_score) AS average_review_score,
        AVG(late_delivery_rate) AS late_delivery_rate,
        AVG(average_delivery_days) AS average_delivery_days
    FROM vw_geographic_revenue
    WHERE customer_state IS NOT NULL
    GROUP BY customer_state
)
SELECT
    g.customer_state,
    g.total_revenue,
    g.product_revenue,
    g.freight_revenue,
    g.total_orders,
    g.average_order_value,
    g.average_review_score,
    g.late_delivery_rate,
    g.average_delivery_days,
    e.market_summary,
    e.target_customer_segment,
    e.business_recommendation,
    e.risk_or_challenge,
    e.source_titles,
    e.source_urls,
    e.intelligence_date,
    e.search_query
FROM customer_state_performance g
INNER JOIN dim_external_intelligence e
    ON e.intelligence_track = 'geographic_logistics'
    AND e.entity_type = 'customer_state'
    AND e.entity_value = g.customer_state;

COMMENT ON VIEW vw_geographic_intelligence IS
    'Combines customer-state revenue and delivery metrics with external logistics and regional e-commerce intelligence for Superset geographic analysis.';

-- Delivery intelligence exposes external customer experience findings for
-- categories with meaningful revenue and elevated late-delivery risk.
CREATE OR REPLACE VIEW vw_delivery_intelligence AS
SELECT
    entity_type,
    entity_value,
    internal_metric_context,
    market_summary,
    target_customer_segment,
    business_recommendation,
    risk_or_challenge,
    source_titles,
    source_urls,
    intelligence_date,
    search_query
FROM dim_external_intelligence
WHERE intelligence_track = 'delivery_customer_experience';

COMMENT ON VIEW vw_delivery_intelligence IS
    'Exposes external delivery and customer experience intelligence for Superset dashboards focused on late delivery, review satisfaction, and operational best practices.';
