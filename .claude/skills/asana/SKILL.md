---
name: asana
description: Use when bulk-downloading Asana tasks, syncing Asana data to local DB, or when MCP would require too many API calls that bloat context window. Also use when user needs to query/analyze Asana data offline.
---

# Asana Bulk Sync

Sync Asana workspaces to local SQLite via Python script. Zero context window cost — runs entirely in shell.

## When to Use

- Downloading tens or hundreds of Asana tasks
- Building local DB of Asana data for analysis
- Any operation where MCP tool calls would exceed ~20 requests
- Querying Asana data without repeated API calls

**Use MCP instead** for: single task lookups, creating/updating tasks, interactive work with <10 items.

## Setup

### 1. Personal Access Token

User needs `ASANA_PAT` env var. Get token at: https://app.asana.com/0/my-apps → Create new token

```bash
# Add to ~/.zshrc for persistence
export ASANA_PAT="1/1234567890:abcdef..."
```

### 2. Verify Access

```bash
uv run .claude/skills/asana/sync.py --list-workspaces
```

## Usage

```bash
# List workspaces
uv run .claude/skills/asana/sync.py --list-workspaces

# List projects in workspace
uv run .claude/skills/asana/sync.py -w "My Workspace" --list-projects

# Sync all projects → asana.db
uv run .claude/skills/asana/sync.py -w "My Workspace"

# Sync specific projects only
uv run .claude/skills/asana/sync.py -w "My Workspace" -p "Engineering,Marketing"

# Include completed tasks + comments
uv run .claude/skills/asana/sync.py -w "My Workspace" --include-completed --include-stories

# Custom DB path
uv run .claude/skills/asana/sync.py -w "My Workspace" --db /path/to/data.db
```

## Querying the Data

After sync, query with SQLite:

```bash
# Task counts by project
sqlite3 asana.db "SELECT p.name, COUNT(t.gid) FROM projects p JOIN task_projects tp ON p.gid=tp.project_gid JOIN tasks t ON t.gid=tp.task_gid GROUP BY p.name"

# Overdue incomplete tasks
sqlite3 asana.db "SELECT name, due_on, assignee_name FROM tasks WHERE completed=0 AND due_on < date('now') ORDER BY due_on"

# Tasks by assignee
sqlite3 asana.db "SELECT assignee_name, COUNT(*) as cnt FROM tasks WHERE completed=0 GROUP BY assignee_name ORDER BY cnt DESC"
```

## DB Schema

| Table | Key columns |
|-------|------------|
| `workspaces` | gid, name |
| `projects` | gid, name, notes, owner_name, archived |
| `sections` | gid, project_gid, name |
| `tasks` | gid, name, notes, completed, assignee_name, due_on, custom_fields_json, tags_json |
| `task_projects` | task_gid, project_gid, section_gid |
| `task_stories` | gid, task_gid, text, resource_subtype, created_by_name |
| `sync_log` | timestamps, counts, status |

## Performance Notes

- **Projects + tasks**: ~1 API call per project (paginated automatically)
- **Stories**: 1 API call per task — use `--include-stories` only when needed
- **Typical sync**: 50 projects × 100 tasks = ~50 API calls, takes ~30 seconds
- All data stored with `synced_at` timestamp for freshness tracking
