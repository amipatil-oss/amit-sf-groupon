---
name: refresh-registry
description: Scan projects/ filesystem and reconcile docs/projects.md with actual project folders. Use when registry is stale or after bulk changes.
---

# Refresh Registry

## Steps

### 1. Scan filesystem

- List all directories in `projects/groupon/`, `projects/personal/`, `projects/hce/`, `projects/pfc/`
- Skip `CoS_*` prefixed directories (cloned reference repos)
- Skip `archive/` subdirectories
- For each directory: read `CLAUDE.md` if present to get metadata (name, category, status, type, created date, description)
- If no `CLAUDE.md`: infer what you can from README.md or folder name/contents

### 2. Read current registry

- Parse `docs/projects.md` into a data structure (project name → metadata)

### 3. Ensure required files exist

For each project directory, check and create if missing:

**CLAUDE.md** — If missing, create from the enhanced template (see `new-project` skill step 7):
- Infer name from folder name
- Infer category from parent folder (groupon/personal/hce/pfc)
- Set status to `active`, type and created to `—`
- Infer description from README.md if present, otherwise from folder name
- Include all standard sections: Metadata, Purpose, Inputs Processing, Workflow, Key Files, Active Decisions, Domain Learnings

**README.md** — If missing, create a minimal one:
```markdown
# <folder-name>

## Status
Active

## Structure
- `inputs/` — source materials (drop files here)
- `knowledge/` — processed content and analysis
- `deliverables/` — final outputs
- `CLAUDE.md` — project context for Claude
```

### 4. Reconcile

- **On filesystem but not in registry** → add with status "active" and flag `(auto-added, verify)` in notes
- **In registry but not on filesystem** → mark as `(missing from filesystem)` and flag for human review
- **In both** → update metadata from CLAUDE.md if it differs from registry

### 4. Write updated registry

Use this format:

```markdown
# Project Registry

*Auto-maintained. Last updated: <YYYY-MM-DD>.*

## Active Projects

| Project | Category | Type | Created | Description |
|---------|----------|------|---------|-------------|
| [PROJECT_NAME](../projects/<category>/<folder>/) | <category> | <type> | <date> | <description> |

## Paused Projects

| Project | Category | Type | Paused | Description |
|---------|----------|------|--------|-------------|

## Completed Projects

| Project | Category | Type | Completed | Description |
|---------|----------|------|-----------|-------------|

## Stats
- **Total:** N projects (N active, N paused, N completed)
- **By category:** groupon: N, personal: N, hce: N, pfc: N

## Adding a project

Use the `new-project` skill — it handles scaffolding and registry automatically.
To refresh this registry from the filesystem, use the `refresh-registry` skill.
```

Rules:
- Sort each section alphabetically by project name
- Link project names to their folder path (relative from docs/)
- Update stats counts
- Update "Last updated" timestamp

### 6. Report

List what was:
- **Files created** (CLAUDE.md, README.md per project)
- **Projects added** to registry (new on filesystem)
- **Metadata updated** (changed from CLAUDE.md)
- **Flagged** (issues needing human review)

### 7. Commit

```bash
cd /PATH/TO/YOUR/CoS
git add docs/projects.md
git commit -m "docs: refresh project registry (<N> projects)"
```
