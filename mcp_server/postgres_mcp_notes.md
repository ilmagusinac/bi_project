# PostgreSQL Access for Codex

The professor used the Gemini CLI PostgreSQL extension to allow the AI assistant to query the Supabase PostgreSQL database.

In this project, Gemini CLI is replaced by Codex CLI. Therefore, PostgreSQL access will be implemented through an MCP server.

The MCP server will expose controlled database tools to Codex:
- schema inspection
- list tables
- list columns
- run read-only SQL
- explain business metrics

For safety, destructive SQL commands such as INSERT, UPDATE, DELETE, DROP, ALTER, TRUNCATE, and CREATE will not be allowed through the AI agent.