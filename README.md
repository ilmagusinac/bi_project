# Olist BI Agent

Olist BI Agent is an AI-powered Business Intelligence final project for e-commerce analytics. It transforms the Olist Brazilian E-Commerce Public Dataset into a Supabase PostgreSQL analytical warehouse, exposes the warehouse through safe read-only MCP tools for Codex CLI, enriches selected metrics with external market intelligence, and presents results in Apache Superset dashboards.

## 1. Project Overview

The project demonstrates an end-to-end BI agent architecture:

- Raw Olist CSV files are profiled, transformed, loaded, and validated with Python ETL scripts.
- The transformed data is stored in a PostgreSQL star/snowflake warehouse hosted on Supabase.
- Analytical SQL views provide stable, dashboard-ready metric layers.
- Codex CLI connects to the warehouse through the `olist-postgres` MCP server for safe BI question answering.
- Brave Search MCP supports an external intelligence layer for market, logistics, and customer experience context.
- Superset MCP supports interaction with Apache Superset datasets, charts, and dashboards.

The final architecture is centered on Olist, Codex CLI, MCP integrations, Supabase PostgreSQL, and Apache Superset.

## 2. Business Objective

The main objective is to build an AI-powered BI system that helps analyze e-commerce performance across revenue, products, sellers, delivery, customer satisfaction, geography, payment behavior, and external market signals.

Key business metrics include:

- Total revenue
- Product revenue
- Freight revenue
- Total orders
- Average order value
- Late delivery rate
- Average review score
- Average delivery days
- Freight ratio

## 3. Dataset

The project uses the **Olist Brazilian E-Commerce Public Dataset** from Kaggle.

The raw dataset includes CSV files for customers, orders, order items, order payments, order reviews, products, sellers, geolocation, and product category name translations.

Raw Kaggle files are stored locally in `data/raw/` and are intentionally not committed to GitHub. This keeps the repository small and avoids redistributing downloaded source data. The reproducible external intelligence artifact, `data/external/external_intelligence.json`, is committed because it supports the external intelligence layer used by the warehouse and dashboards.

## 4. Architecture

```text
Kaggle Olist CSV files
    -> data/raw/ (local only)
    -> Python ETL with pandas and psycopg
    -> Supabase PostgreSQL warehouse
    -> Analytical SQL views
    -> Apache Superset dashboards

Supabase PostgreSQL warehouse
    -> olist-postgres MCP server
    -> Codex CLI BI agent

Business targets and warehouse metrics
    -> Brave Search MCP
    -> data/external/external_intelligence.json
    -> dim_external_intelligence
    -> External intelligence analytical views

Codex CLI BI agent
    -> Superset MCP
    -> Superset datasets, charts, and dashboards
```

The architecture separates controlled write operations from AI query access. ETL scripts are the controlled write path for loading and validating data. The AI agent uses read-only MCP tools and is blocked from destructive SQL.

## 5. Repository Structure

```text
agent_eval/                   Golden query suite and evaluator
data/external/                Committed external intelligence JSON
data/raw/                     Local Kaggle CSV files, excluded from Git
docs/                         Reports, architecture notes, prompts, evidence, screenshots
etl/                          Python profiling, transformation, loading, and validation scripts
mcp_server/                   PostgreSQL MCP server and BI agent instructions
supabase/migrations/          PostgreSQL schema, indexes, views, and intelligence layer
```

## 6. Data Warehouse Design

The warehouse uses a snowflake schema with `fact_order_items` as the central fact table.

Core warehouse tables:

- `dim_date`
- `dim_customer`
- `dim_product`
- `dim_seller`
- `dim_payment_summary`
- `dim_review`
- `dim_geolocation`
- `fact_order_items`

External intelligence table:

- `dim_external_intelligence`

Important analytical views include:

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

Surrogate keys are used in warehouse dimension tables, and PostgreSQL-compatible SQL is used throughout the schema and views.

## 7. ETL Pipeline

The ETL pipeline is implemented with Python, `pandas`, and `psycopg`.

Pipeline responsibilities:

- Test the Supabase PostgreSQL connection.
- Profile the raw Olist CSV files.
- Transform raw records into warehouse-ready dimensions and facts.
- Load dimensions and facts into PostgreSQL.
- Validate row counts, metrics, relationships, and business rules.
- Load curated external intelligence into `dim_external_intelligence`.

ETL scripts are controlled write scripts. They are separate from the AI agent, which only receives read-only database access through MCP.

## 8. MCP Integrations

The project uses three MCP integrations.

### PostgreSQL MCP: `olist-postgres`

The `olist-postgres` MCP server gives Codex CLI controlled access to the Supabase PostgreSQL warehouse. It supports schema inspection, metric lookup, foreign key lookup, and SQL execution.

### Brave Search MCP

Brave Search MCP provides external market intelligence for selected product, geography, logistics, and customer experience questions. The curated output is stored in `data/external/external_intelligence.json`, loaded into `dim_external_intelligence`, and exposed through external intelligence views for Superset and agent queries.

### Superset MCP

Superset MCP allows Codex CLI to interact with Apache Superset datasets, charts, and dashboards through controlled tools. It supports dashboard evidence collection and chart/dashboard operations when explicitly requested.

## 9. Golden Query Evaluation

The golden query suite is stored in `agent_eval/golden_queries.yml`.

It contains 9 golden queries that evaluate whether the BI agent can answer approved business questions using the correct PostgreSQL views, metrics, joins, filters, and ordering.

The evaluator is implemented in `agent_eval/evaluate_agent.py` and generates:

```text
docs/golden_query_evaluation_report.txt
```

The golden queries cover executive KPIs, monthly revenue, product category performance, seller performance, delivery performance, customer satisfaction, payment analysis, geographic revenue, and external market intelligence.

## 10. Superset Dashboards

The main Apache Superset dashboards are:

1. **Executive Overview**
   - Revenue KPIs
   - Total orders
   - Average order value
   - Late delivery rate
   - Average review score
   - Monthly revenue trends

2. **Product & Seller Performance**
   - Product category revenue
   - Seller revenue and order performance
   - Freight ratio
   - Delivery and review metrics by product category or seller

3. **Delivery & Customer Satisfaction**
   - Late delivery trends
   - Average delivery days
   - Delay metrics
   - Review score analysis
   - Delivery and satisfaction risk areas

4. **External Market Intelligence**
   - Product category market context
   - Geographic logistics context
   - Delivery and customer experience risks
   - Business recommendations and source URLs

Dashboard evidence and screenshots are stored in `docs/screenshots/`.

## 11. Security and Git Hygiene

The repository must not contain real secrets, passwords, tokens, API keys, Supabase credentials, Brave API keys, or local `.env` contents.

Excluded from Git:

- `.env`
- `.codex/`
- `.venv/`
- `data/raw/`
- `__pycache__/`
- Python bytecode files

Committed for reproducibility:

- `.env.example` with placeholder variable names only
- `data/external/external_intelligence.json`
- SQL migrations
- ETL source code
- MCP server source code
- Documentation, reports, and dashboard evidence

Security boundary:

- ETL scripts are controlled write scripts used to load and validate the warehouse.
- Codex CLI uses MCP tools for BI analysis.
- The `olist-postgres` MCP server only allows safe read-only warehouse queries for the AI agent.
- Destructive SQL is blocked by design.

## 12. Setup Instructions

Run commands from the project root.

1. Create and activate a Python virtual environment.

```bash
python -m venv .venv
.\.venv\Scripts\activate
```

2. Install Python dependencies.

```bash
pip install -r requirements.txt
```

3. Create a local `.env` file from `.env.example`.

```bash
copy .env.example .env
```

4. Add local Supabase PostgreSQL, Superset, and Brave Search settings to `.env`.

Do not commit `.env` or any real credentials.

5. Download the Olist Brazilian E-Commerce Public Dataset from Kaggle and place the raw CSV files in `data/raw/`.

6. Apply the migrations in `supabase/migrations/` to create the warehouse schema, indexes, analytical views, and external intelligence layer.

## 13. How To Run The Pipeline

Run the ETL scripts in order:

```bash
python etl\00_test_connection.py
python etl\01_profile_data.py
python etl\02_transform_dimensions.py
python etl\03_load_dimensions.py
python etl\04_load_facts.py
python etl\05_validate_load.py
python etl\06_load_external_intelligence.py
```

## 14. How To Run Validation And Golden Query Evaluation

Run load validation:

```bash
python etl\05_validate_load.py
```

The validation script checks row counts, revenue totals, required foreign keys, nullable relationship fields, delivery metrics, and review metrics. It writes validation evidence to:

```text
docs/load_validation_report.txt
```

Run golden query evaluation:

```bash
python agent_eval\evaluate_agent.py
```

The evaluator reads `agent_eval/golden_queries.yml` and writes:

```text
docs/golden_query_evaluation_report.txt
```

## 15. Demo Workflow

1. A user asks Codex CLI a BI question, such as which product categories generate the most revenue and have delivery or satisfaction risk.
2. Codex uses the `olist-postgres` MCP server to inspect the approved schema and run read-only PostgreSQL `SELECT` queries.
3. Codex explains the result using approved business metrics and warehouse views.
4. If external context is needed, Brave Search MCP intelligence is referenced through the committed external intelligence layer.
5. If a visual result is needed, Superset MCP is used to inspect or interact with Superset datasets, charts, and dashboards.
6. Apache Superset presents the result in the relevant dashboard.

## 16. Project Documentation And Evidence

Important documentation and evidence files:

- `docs/architecture.md`
- `docs/business_metrics.md`
- `docs/data_dictionary.md`
- `docs/data_profile_report.txt`
- `docs/load_validation_report.txt`
- `docs/golden_query_evaluation_report.txt`
- `docs/external_intelligence_targets.md`
- `docs/external_intelligence_search_log.md`
- `docs/final_project_summary.md`
- `docs/screenshots/`
- `mcp_server/prompts/system_instructions.md`

These files document the warehouse design, BI metrics, agent behavior, validation results, golden query evaluation, external intelligence evidence, and Superset dashboard evidence for the university final project submission.
