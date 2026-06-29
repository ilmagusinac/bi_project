# Architecture

## Phase 2: Agent Engineering

The professor reference architecture used Gemini CLI with a PostgreSQL
extension to let an AI assistant inspect and query a PostgreSQL database. This
project adapts that pattern by using Codex CLI with a PostgreSQL MCP server.
Supabase remains the hosted PostgreSQL database for the Olist Brazilian
E-Commerce warehouse.

The `olist-postgres` MCP server exposes controlled tools for the BI agent:

- `list_tables`
- `describe_table`
- `get_schema`
- `get_foreign_keys`
- `list_metrics`
- `explain_metric`
- `run_readonly_sql`

The MCP server is read-only for agent query execution and blocks destructive
SQL. The BI agent is instructed to generate only PostgreSQL-compatible `SELECT`
queries against the approved warehouse tables.

Agent behavior is governed by
`mcp_server/prompts/system_instructions.md`. Those instructions define the
allowed warehouse scope, approved BI metrics, SQL safety rules, default business
assumptions, result explanation requirements, and safe SQL error handling.

This satisfies the AI Agent Implementation part of the project by connecting
Codex CLI to the Supabase PostgreSQL warehouse through a safe MCP interface and
documenting the rules that control SQL generation and business-answer behavior.
