# Asana: Use API, Not MCP

For ANY Asana data access, prefer the REST API via `ASANA_PAT` over MCP tools (`mcp__claude_ai_Asana_2__*`).

**Why:** MCP tools consume context window heavily and are slow for bulk operations. The REST API is 10x faster and zero context cost.

## How

Use `asana_api.py` or `asana_query.py` from the current project's `scripts/` directory (if available), or write direct `urllib` calls against `https://app.asana.com/api/1.0/` with Bearer token from `ASANA_PAT` env var.

## When MCP Is Still OK

- Creating or updating tasks (API scripts are read-only)
- The user explicitly asks to use MCP
- `ASANA_PAT` is not available in the environment
