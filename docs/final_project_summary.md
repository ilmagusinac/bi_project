# Final Project Summary

## 1. Project Overview

This project implements an AI-powered Business Intelligence system for Brazilian e-commerce analysis. It transforms raw Olist order data into a PostgreSQL analytical warehouse, exposes safe read-only database access through PostgreSQL MCP, evaluates the BI agent with golden queries, enriches internal metrics with Brave Search MCP external intelligence, and uses Superset MCP for chart and dashboard interaction in Apache Superset.

The final system supports both traditional BI workflows and AI-assisted analysis. Users can inspect dashboards, query curated warehouse views, ask a Codex CLI agent to answer business questions using controlled PostgreSQL access, and request Superset chart creation when a visual result is needed.

## 2. Dataset Used

The final dataset is the **Olist Brazilian E-Commerce Public Dataset**. It includes orders, customers, products, sellers, payments, reviews, order items, geolocation data, and product category translations.

The old `OnlineRetail.csv` file was treated only as professor reference material and was not used as the final project dataset.

## 3. Architecture

The system follows a layered BI architecture:

1. **Olist CSV files**: Raw source files stored under the project data directory.
2. **Python ETL**: Modular ETL scripts profile, transform, load, and validate the data using `pandas` and `psycopg`.
3. **Supabase PostgreSQL warehouse**: Hosted PostgreSQL stores the star/snowflake warehouse tables, indexes, and analytical views.
4. **PostgreSQL MCP server**: Provides controlled read-only database tools for the AI agent, including schema inspection, metric lookup, and safe `SELECT` query execution.
5. **Brave Search MCP external intelligence layer**: Adds current market, logistics, and customer experience context from web sources to complement internal Olist metrics.
6. **Superset MCP server**: Provides controlled interaction with Superset datasets, charts, and dashboards.
7. **Codex CLI agent**: Uses MCP tools to answer BI questions against approved warehouse objects, gather external context, and create Superset visuals when explicitly requested.
8. **Apache Superset dashboards**: Presents executive, product/seller, delivery, satisfaction, and external intelligence analysis.

## 4. Warehouse Schema Summary

The core warehouse uses surrogate keys and separates business dimensions from the order item fact table.

Core dimensions:

- `dim_date`: calendar attributes for order, approval, delivery, and review dates.
- `dim_customer`: customer identifiers, city, state, ZIP prefix, and geolocation reference.
- `dim_product`: product identifiers, Portuguese and English categories, product attributes, weight, dimensions, and volume.
- `dim_seller`: seller identifiers, city, state, ZIP prefix, and geolocation reference.
- `dim_payment_summary`: order-level payment method summary, installment count, payment value, and payment flags.
- `dim_review`: order-level review score, comments, response timing, and canonical review tracking.
- `dim_geolocation`: ZIP prefix, city, state, latitude, longitude, and source row count.

Core fact:

- `fact_order_items`: one row per order item with links to dimensions, order timestamps, product revenue, freight value, total item value, delivery days, delay days, and late-delivery flag.

External intelligence dimension:

- `dim_external_intelligence`: stores curated Brave Search intelligence by track, entity, search query, market summary, customer segment, recommendation, risk, and source URLs.

Key analytical views:

- `vw_sales_overview`
- `vw_monthly_revenue`
- `vw_product_category_performance`
- `vw_seller_performance`
- `vw_delivery_performance`
- `vw_customer_satisfaction`
- `vw_payment_analysis`
- `vw_geographic_revenue`
- `vw_product_category_intelligence`
- `vw_geographic_intelligence`
- `vw_delivery_intelligence`

## 5. ETL Pipeline Summary

The ETL pipeline is organized into clear scripts:

- `00_test_connection.py`: verifies Supabase PostgreSQL connectivity.
- `01_profile_data.py`: profiles raw Olist files, required columns, duplicates, relationships, date quality, and basic metrics.
- `02_transform_dimensions.py`: transforms raw CSVs into clean dimension-ready dataframes.
- `03_load_dimensions.py`: loads dimensions using idempotent upserts.
- `04_load_facts.py`: resolves surrogate keys and loads `fact_order_items` idempotently.
- `05_validate_load.py`: validates row counts, revenue totals, foreign keys, delivery metrics, and review metrics.
- `06_load_external_intelligence.py`: loads Brave Search intelligence from JSON into `dim_external_intelligence` using idempotent upserts.

Validation confirmed that the core warehouse loaded successfully, with expected row counts and revenue totals matching exactly. Golden query evaluation also passed all 8 tests.

## 6. MCP Agent Capabilities

The project uses three MCP servers for different parts of the BI workflow:

- **PostgreSQL MCP**: safe warehouse querying.
- **Brave Search MCP**: external intelligence collection.
- **Superset MCP**: chart and dashboard interaction.

### PostgreSQL MCP

The PostgreSQL MCP server allows the Codex CLI agent to work as a controlled BI assistant. It can:

- Inspect supported warehouse schema.
- List foreign key relationships.
- List and explain approved BI metrics.
- Run read-only PostgreSQL `SELECT` queries.
- Answer business questions using warehouse views and documented metric definitions.

The MCP layer is intentionally constrained. It does not allow destructive SQL, credential exposure, or unrestricted database access. This makes the AI agent useful for BI analysis while keeping the database interaction safe and auditable.

### Brave Search MCP

The Brave Search MCP server is used to collect external intelligence that complements historical Olist metrics. It supports market, logistics, and customer-experience context for categories, geographies, and delivery-risk areas. The collected outputs are curated into JSON, loaded into `dim_external_intelligence`, and exposed through Superset-ready intelligence views.

### Superset MCP

The Superset MCP server is used for controlled Superset interaction. It can list dashboards, list datasets, inspect chart configuration, create charts when requested, and add charts to dashboards.

Superset MCP was tested successfully by creating a table chart:

- Chart ID: `128`
- Name: `Top 5 Product Categories - Revenue and Risk Signals`
- Dataset: `vw_product_category_performance` / dataset ID `24`
- Dashboard: `Product & Seller Performance` / dashboard ID `11`
- Fields: `product_category_name_english`, `total_revenue`, `total_orders`, `late_delivery_rate`, `average_review_score`, `freight_ratio`
- Configuration: top 5 rows, ordered by `total_revenue` descending

## 7. Superset Dashboards And Charts

The project includes three main Superset dashboards:

1. **Executive Overview**
   - Total revenue, product revenue, freight revenue, total orders, average order value, late delivery rate, average review score, and average delivery days.
   - Monthly revenue and order trends.
   - High-level business health indicators.

2. **Product & Seller Performance**
   - Top product categories by revenue.
   - Product revenue, freight revenue, average order value, review score, and freight ratio by category.
   - Seller-level revenue, order volume, delivery performance, and satisfaction metrics.

3. **Delivery & Customer Satisfaction**
   - Late delivery rate over time.
   - Average delivery days and delay days.
   - Review score distribution and satisfaction metrics.
   - Delivery performance by order status, category, and geography.

The external intelligence views can extend these dashboards with market summaries, recommendations, risks, and source URLs for category, geography, and delivery analysis.

The Superset MCP chart creation test added `Top 5 Product Categories - Revenue and Risk Signals` to the `Product & Seller Performance` dashboard. The chart highlights high-revenue categories alongside possible delivery and customer satisfaction risks using late delivery rate, average review score, and freight ratio.

## 8. Advanced Brave Search Integration

The Brave Search MCP layer was added to connect historical internal BI metrics with current external market context. The Olist dataset is historical, so external search helps answer questions that the warehouse alone cannot, such as current Brazilian e-commerce trends, Pix adoption, marketplace behavior, social commerce, logistics pressure, and customer experience best practices.

Three intelligence tracks were created:

- `product_category_market`: external market context for the top 10 revenue product categories.
- `geographic_logistics`: logistics and regional e-commerce context for the top 5 customer states by revenue.
- `delivery_customer_experience`: delivery delay, review satisfaction, and operational best-practice context for high-risk categories.

The collection step used:

- Olist warehouse queries through the PostgreSQL MCP server to select target categories and states.
- Brave Search MCP to gather current external sources.
- Structured JSON stored in `data/external/external_intelligence.json`.
- A readable audit log stored in `docs/external_intelligence_search_log.md`.

The loading step used `etl/06_load_external_intelligence.py` to insert or update rows in `dim_external_intelligence` with JSONB fields for internal metric context, source titles, and source URLs.

The visualization layer uses:

- `vw_product_category_intelligence`: joins category performance with product-market intelligence.
- `vw_geographic_intelligence`: joins state-level performance with logistics intelligence.
- `vw_delivery_intelligence`: exposes delivery and customer experience recommendations.

These views are designed for Superset tables, markdown/detail panels, and drill-down charts that combine internal metrics with source-backed external recommendations.

## 9. Demo Flow

1. A user asks the Codex CLI BI agent a business question, for example: "Which product categories generate the most revenue and have delivery or customer satisfaction risk?"
2. The agent uses PostgreSQL MCP to inspect the approved warehouse views, generate PostgreSQL-compatible SQL, and fetch read-only data from the warehouse.
3. The agent uses Brave Search MCP when external market or logistics context is needed.
4. When the user requests a visual result, the agent uses Superset MCP to create a chart from the relevant Superset dataset.
5. The Superset dashboard shows the visual result for review and presentation.

## 10. Final Business Insights

1. **Revenue is concentrated in categories where delivery and trust still matter.**
   Health and beauty, watches/gifts, bed/bath/table, sports/leisure, and computers/accessories lead revenue. Several high-revenue categories also show meaningful late-delivery rates or review-score pressure, so growth strategy should include fulfillment reliability, product-content quality, and trust signals.

2. **Geography creates different delivery and satisfaction patterns.**
   Sao Paulo generates the most revenue and has comparatively strong delivery performance, while Rio de Janeiro shows higher late-delivery risk and lower review satisfaction. Regional strategy should not treat Brazil as one uniform market; logistics planning should be state-aware.

3. **External trends reinforce the importance of Pix, marketplaces, social commerce, and logistics transparency.**
   Brave Search intelligence shows that Brazilian e-commerce continues to be shaped by Pix payments, marketplace discovery, mobile-first shopping, social and conversational commerce, and shipping-cost sensitivity. Internal BI decisions should consider both historical Olist performance and these current market expectations.

## 11. Limitations And Trade-Offs

- The Olist dataset is historical, so it does not directly represent current market volume or recent consumer behavior.
- Some external intelligence sources were broad Brazil e-commerce sources rather than category-specific sources, especially for categories such as housewares, auto, and garden tools.
- Brave Search results require human judgment to exclude weak or irrelevant sources.
- External intelligence is curated as a dimension table, not a fully automated real-time feed.
- The BI agent is intentionally read-only, which improves safety but means it cannot directly repair or transform data through MCP.
- Superset dashboards depend on predefined views, which improves consistency but limits ad hoc modeling inside Superset.
- Superset MCP can create and place charts when explicitly requested, but credentials and connection settings remain outside project documentation.

## 12. Recommended Future Improvements

- Add scheduled refreshes for the Brave Search intelligence layer.
- Add confidence scores or source-quality ratings for each external intelligence item.
- Expand external intelligence to include competitor pricing, marketplace rankings, and macroeconomic indicators.
- Add more Superset charts using `vw_product_category_intelligence`, `vw_geographic_intelligence`, and `vw_delivery_intelligence`.
- Build a dashboard page dedicated to AI-generated business recommendations.
- Add automated tests for external intelligence row counts and join coverage.
- Add row-level metadata for source publication dates when available.
- Extend the MCP server with curated prompt templates for executive, merchandising, logistics, and customer-experience questions.
