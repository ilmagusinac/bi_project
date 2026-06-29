# Olist BI Agent

AI-powered Business Intelligence project for the Olist Brazilian E-Commerce dataset. The project builds a PostgreSQL analytical warehouse, exposes it safely through a PostgreSQL MCP server for Codex CLI, enriches warehouse metrics with Brave Search MCP external intelligence, and uses Superset MCP for controlled chart and dashboard interaction in Apache Superset.

## Technology Stack

- Codex CLI
- PostgreSQL MCP server
- Brave Search MCP server
- Superset MCP server
- Supabase PostgreSQL
- Python ETL with `pandas` and `psycopg`
- Apache Superset

## Dataset

The project uses the **Olist Brazilian E-Commerce Public Dataset**.

Raw source files include customers, orders, order items, payments, reviews, products, sellers, geolocation, and product category translations. The legacy Online Retail dataset is not used as the final BI dataset.

## Architecture

```text
Olist CSV files
    -> Python pandas/psycopg ETL
    -> Supabase PostgreSQL warehouse
    -> Analytical SQL views
    -> Apache Superset dashboards

Supabase PostgreSQL warehouse
    -> PostgreSQL MCP server
    -> Codex CLI BI agent

Warehouse target queries
    -> Brave Search MCP
    -> data/external/external_intelligence.json
    -> dim_external_intelligence
    -> external intelligence Superset views

Codex CLI BI agent
    -> Superset MCP server
    -> Apache Superset charts and dashboards
```

The core warehouse stores historical Olist business metrics. PostgreSQL MCP lets the agent inspect schema, explain metrics, and run safe read-only warehouse queries. Brave Search MCP adds current market, logistics, and customer experience context. Superset MCP lets the agent inspect Superset assets and create or place charts on dashboards when explicitly requested.

## Folder Structure

```text
agent_eval/                  Golden query evaluator and test cases
data/raw/                    Raw Olist CSV files
data/processed/              Processed ETL outputs
data/external/               Brave Search external intelligence JSON
docs/                        Reports, summaries, prompts, and documentation
etl/                         Python ETL, validation, and external intelligence loaders
mcp_server/                  PostgreSQL MCP server tools and prompts
supabase/migrations/         PostgreSQL schema, indexes, views, and intelligence layer
superset/dashboard_sql/      Dashboard SQL assets
superset/exported_dashboards/ Superset dashboard export location
legacy_professor_reference/  Old reference material, not the final dataset
```

## Setup

1. Create and activate a Python virtual environment.

```bash
python -m venv .venv
.\.venv\Scripts\activate
```

2. Install dependencies.

```bash
pip install -r requirements.txt
```

3. Create a local `.env` file from `.env.example`.

```bash
copy .env.example .env
```

4. Fill in local Supabase PostgreSQL and API settings in `.env`.

Required database variables:

```env
POSTGRES_HOST=your_supabase_host
POSTGRES_PORT=5432
POSTGRES_DATABASE=postgres
POSTGRES_USER=your_supabase_user
POSTGRES_PASSWORD=your_supabase_password
POSTGRES_SSLMODE=require
```

Optional external integration variables:

```env
SUPABASE_PROJECT_URL=your_supabase_project_url
SUPABASE_ANON_KEY=your_supabase_anon_key
BRAVE_API_KEY=your_brave_api_key_here
```

5. Apply database migrations in `supabase/migrations/` to create the warehouse tables, indexes, analytical views, external intelligence table, and external intelligence views.

## How To Run

Run commands from the project root.

### Connection Test

```bash
python etl\00_test_connection.py
```

### Data Profiling

```bash
python etl\01_profile_data.py
```

### Dimension ETL

```bash
python etl\03_load_dimensions.py
```

### Fact ETL

```bash
python etl\04_load_facts.py
```

### Load Validation

```bash
python etl\05_validate_load.py
```

The validation script checks row counts, revenue totals, required foreign keys, nullable relationship fields, delivery metrics, and review metrics.

### Golden Query Evaluator

```bash
python agent_eval\evaluate_agent.py
```

The evaluator runs the golden BI query suite in `agent_eval/golden_queries.yml` and writes the report to `docs/golden_query_evaluation_report.txt`.

### External Intelligence Loader

```bash
python etl\06_load_external_intelligence.py
```

This loads `data/external/external_intelligence.json` into `dim_external_intelligence` using idempotent upserts.

## Warehouse Tables And Views

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

Dashboard and analysis views include:

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

## Superset Dashboards

The project includes three main Apache Superset dashboards:

1. **Executive Overview**
   - Revenue KPIs
   - Total orders
   - Average order value
   - Late delivery rate
   - Average review score
   - Monthly revenue trends

2. **Product & Seller Performance**
   - Product category revenue
   - Seller performance
   - Freight ratio
   - Average order value
   - Review and delivery metrics by category or seller

3. **Delivery & Customer Satisfaction**
   - Late delivery trends
   - Average delivery days
   - Delay metrics
   - Review score analysis
   - Delivery and satisfaction risk areas

The external intelligence views can be added to Superset as tables or detail panels to show market summaries, recommendations, risks, and source URLs beside internal BI metrics.

## MCP Integrations

The project uses three MCP integrations:

### PostgreSQL MCP

The PostgreSQL MCP server gives Codex CLI safe BI access to the Supabase warehouse. It supports schema inspection, metric lookup, foreign key lookup, and read-only SQL execution. Destructive SQL is blocked by design.

### Brave Search MCP

The Brave Search MCP integration collects current external intelligence for three tracks:

- `product_category_market`: market context for the top 10 revenue product categories.
- `geographic_logistics`: logistics and consumer behavior context for the top 5 customer states.
- `delivery_customer_experience`: best practices and risks for high late-delivery categories.

Collected intelligence is stored in:

- `data/external/external_intelligence.json`
- `docs/external_intelligence_search_log.md`
- `dim_external_intelligence`

Superset-ready views expose the results:

- `vw_product_category_intelligence`
- `vw_geographic_intelligence`
- `vw_delivery_intelligence`

### Superset MCP

The Superset MCP server lets Codex CLI interact with Apache Superset dashboards, datasets, and charts through controlled tools. It is used for Superset asset inspection and, when explicitly requested, chart/dashboard operations such as creating a chart and adding it to a dashboard.

Successful Superset MCP test:

- Created chart ID `128`: `Top 5 Product Categories - Revenue and Risk Signals`
- Dataset: `vw_product_category_performance` / dataset ID `24`
- Dashboard: `Product & Seller Performance` / dashboard ID `11`
- Fields: `product_category_name_english`, `total_revenue`, `total_orders`, `late_delivery_rate`, `average_review_score`, `freight_ratio`
- Configuration: table chart, top 5 rows, ordered by `total_revenue` descending

## Demo Flow

1. A user asks the Codex CLI BI agent a business question, such as which product categories generate the most revenue and carry delivery or satisfaction risk.
2. The agent uses PostgreSQL MCP to inspect approved warehouse views, generate PostgreSQL-compatible SQL, and fetch read-only data from the warehouse.
3. When the user asks for a visual result, the agent uses Superset MCP to create a Superset chart from the relevant dataset.
4. Superset displays the visual result on the target dashboard for review and presentation.

## Security Notes

- `.env` is local only and must not be committed.
- Database passwords, Supabase credentials, Superset credentials, Brave API keys, and tokens must not be committed.
- `.env.example` contains placeholders only.
- MCP SQL access is read-only for agent queries.
- External intelligence stores source URLs and summaries, not API keys.

## Known Limitations

- The Olist dataset is historical, so it does not represent live marketplace activity.
- Some external intelligence items rely on broad Brazil e-commerce sources when category-specific sources were weak.
- Brave Search intelligence is curated from search results and should be periodically refreshed.
- Superset dashboards depend on predefined analytical views.
- The BI agent is intentionally constrained to read-only SQL for safety.
- External intelligence is loaded as a curated batch, not as a real-time streaming feed.
