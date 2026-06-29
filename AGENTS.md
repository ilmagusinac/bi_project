# AGENTS.md

## Project Context

This is an IT 501 Business Intelligence final project.

The project builds an AI-powered BI system using:
- Olist Brazilian E-Commerce dataset
- Supabase PostgreSQL
- Python ETL with pandas and psycopg
- Codex CLI as the AI coding assistant
- MCP server for controlled database access
- Apache Superset for dashboards

## Main Goal

Transform the raw Olist CSV files into a PostgreSQL star/snowflake data warehouse, expose the schema safely through an MCP server, evaluate the BI agent with golden queries, and build Superset dashboards.

## Important Rules

- Do not use the old OnlineRetail.csv as the final dataset.
- Treat the old Online Retail files as professor reference only.
- Do not commit `.env`, database passwords, tokens, or Supabase credentials.
- Use `.env.example` for placeholder environment variables.
- Prefer clear, readable Python code over overly complex code.
- Use PostgreSQL-compatible SQL.
- Use surrogate keys in warehouse dimension tables.
- Use idempotent ETL where possible.
- Use logging and validation in ETL scripts.
- Do not run destructive SQL unless explicitly requested.
- For AI SQL tools, only allow read-only SELECT queries.

## Target Warehouse Tables

Expected warehouse tables:
- dim_date
- dim_customer
- dim_product
- dim_seller
- dim_payment_summary
- dim_review
- dim_geolocation
- fact_order_items

## Business Metrics

Important metrics:
- total revenue
- product revenue
- freight revenue
- total orders
- average order value
- late delivery rate
- average review score
- average delivery days
- freight ratio

## Coding Standards

- Keep code modular.
- Put ETL scripts in `etl/`.
- Put database migration scripts in `supabase/migrations/`.
- Put MCP server code in `mcp_server/`.
- Put dashboard SQL in `superset/dashboard_sql/`.
- Put documentation in `docs/`.