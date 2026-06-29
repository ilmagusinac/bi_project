# External Intelligence Targets

This document defines the warehouse target queries for the Brave Search MCP external intelligence layer. The goal is to select high-value Olist BI entities, search for current external context, and store curated results in `dim_external_intelligence`.

The external intelligence layer does not replace warehouse metrics. It adds market context beside the Superset dashboards so business users can compare internal performance with current e-commerce trends in Brazil.

## 1. Product Category Market Intelligence

**Track:** `product_category_market`

**Purpose:** Understand external market context for top revenue categories.

This track identifies the product categories that matter most financially, then uses Brave Search MCP to gather current market signals such as consumer demand, marketplace competition, pricing pressure, Pix adoption, social commerce trends, and category-specific risks.

```sql
SELECT
    product_category_name_english,
    product_category_name,
    total_orders,
    total_revenue,
    product_revenue,
    freight_revenue,
    average_order_value,
    average_review_score,
    late_delivery_rate,
    freight_ratio
FROM vw_product_category_performance
ORDER BY total_revenue DESC
LIMIT 10;
```

**Why this matters:** Revenue-ranked categories are the strongest candidates for merchandising and market expansion decisions. External intelligence helps explain whether a strong internal category is aligned with broader Brazilian e-commerce trends, marketplace demand, or emerging customer behavior.

**Superset dashboard connection:** Use this track alongside the product category performance dashboard. The dashboard shows which categories generate revenue; the external intelligence explains what is happening in the market around those categories.

## 2. Geographic / Logistics Intelligence

**Track:** `geographic_logistics`

**Purpose:** Understand external logistics and regional e-commerce context for top customer states.

`vw_geographic_revenue` is available at customer city and ZIP-code granularity, so this target query rolls it up to the state level before selecting the highest-revenue states.

```sql
SELECT
    customer_state,
    SUM(total_orders) AS total_orders,
    SUM(total_order_items) AS total_order_items,
    SUM(total_revenue) AS total_revenue,
    SUM(product_revenue) AS product_revenue,
    SUM(freight_revenue) AS freight_revenue,
    SUM(total_revenue) / NULLIF(SUM(total_orders), 0) AS average_order_value,
    AVG(average_review_score) AS average_review_score,
    AVG(average_delivery_days) AS average_delivery_days,
    AVG(late_delivery_rate) AS late_delivery_rate,
    SUM(freight_revenue) / NULLIF(SUM(total_revenue), 0) AS freight_ratio
FROM vw_geographic_revenue
WHERE customer_state IS NOT NULL
GROUP BY customer_state
ORDER BY total_revenue DESC
LIMIT 5;
```

**Why this matters:** High-revenue states are where logistics, delivery cost, customer expectations, and regional marketplace behavior have the largest business impact. Brave Search MCP can add context about regional fulfillment, transport bottlenecks, marketplace penetration, and Brazilian e-commerce adoption patterns.

**Superset dashboard connection:** Use this track alongside the geographic revenue dashboard. The dashboard identifies where revenue comes from; the external intelligence explains logistics and market conditions that may affect those regions.

## 3. Delivery & Customer Experience Intelligence

**Track:** `delivery_customer_experience`

**Purpose:** Understand external best practices and risks related to late delivery and review satisfaction.

This track focuses on product categories where delivery performance is a customer experience risk and revenue is large enough to matter. The query keeps categories whose revenue is at or above the average category revenue, then ranks by late delivery rate.

```sql
SELECT
    product_category_name_english,
    product_category_name,
    total_orders,
    total_revenue,
    average_order_value,
    average_review_score,
    average_delivery_days,
    late_delivery_rate,
    freight_ratio
FROM vw_product_category_performance
WHERE total_revenue >= (
    SELECT AVG(total_revenue)
    FROM vw_product_category_performance
)
ORDER BY
    late_delivery_rate DESC,
    total_revenue DESC
LIMIT 5;
```

**Why this matters:** Late delivery can reduce review satisfaction, repeat purchase behavior, and marketplace trust. Pairing late-delivery categories with external research helps identify best practices such as delivery expectation management, fulfillment improvements, seller quality controls, and customer communication patterns.

**Superset dashboard connection:** Use this track alongside the delivery performance, customer satisfaction, and product category dashboards. The dashboards show internal delivery and review outcomes; the external intelligence provides current best practices and risk context for categories where customer experience problems carry meaningful revenue exposure.

## Suggested Brave Search Query Patterns

The selected warehouse rows can be converted into repeatable Brave Search MCP prompts:

- Product category market: `Brazil e-commerce trends <category> marketplace Pix social commerce 2026`
- Geographic logistics: `Brazil e-commerce logistics delivery trends <state> marketplace fulfillment 2026`
- Delivery customer experience: `Brazil e-commerce late delivery customer satisfaction <category> best practices`

Each result should be saved with the matching `intelligence_track`, `entity_type`, `entity_value`, `search_query`, source titles, source URLs, and a concise business recommendation.
