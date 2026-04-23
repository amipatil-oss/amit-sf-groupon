---
name: new-project
description: Create a new project in the CoS workspace. Scaffolds folders, CLAUDE.md, and registry entry.
---

# New Project

## Step 1: Category first

Ask the user to pick a category:

```
Which category?
  [1] Groupon
  [2] Personal
  [3] HC Energie
  [4] Pale Fire Capital
```

Prefix mapping: groupon → `GRPN_`, personal → `PERS_`, hce → `HCE_`, pfc → `PFC_`

## Step 2: Name and description

Ask for:
- **Project name** — will become `<PREFIX><PascalCaseName>` (e.g., `GRPN_SalesCalls`)
- **One-line description**

That's it. No type, no git remote, no workflow selection. Keep it fast.

## Step 3: Create everything

Create the folder structure and files in one shot:

```bash
mkdir -p projects/<category>/<FULL_NAME>/{inputs,knowledge,deliverables}
```

**`inputs/.processed.md`:**
```markdown
# Processed Inputs

| File | Processed | Output | Notes |
|------|-----------|--------|-------|
```

**`knowledge/README.md`:**
```markdown
# Knowledge Map

## Sources (from inputs/)
| File | Source | Summary |
|------|--------|---------|

## Synthesis (cross-source analysis)
| File | Purpose |
|------|---------|

## Total: 0 source files, 0 synthesis files
```

**`CLAUDE.md`:**
```markdown
# <FULL_NAME>

<one-line description>

## Metadata
- **Category:** <category>
- **Status:** active
- **Created:** <YYYY-MM-DD>

## Purpose

<one-line description repeated — user can expand later>

## Inputs Processing

On session start:
1. Scan `inputs/` for files not listed in `inputs/.processed.md`
2. For each new file: extract content, create `knowledge/<filename-slug>.md`
3. Log in `inputs/.processed.md` with timestamp
4. Update `knowledge/README.md` navigation map

If processing fails for any file, log as "(failed: reason)" and continue.

## Key Files

| Path | Description |
|------|-------------|
| `inputs/` | Source materials |
| `knowledge/README.md` | Knowledge navigation map |
| `deliverables/` | Final outputs |

## Domain Learnings

<!-- Claude: append findings here as you discover them. -->
```

## Step 4: Update registry

Add row to `docs/projects.md` Active Projects table:

```
| [<FULL_NAME>](../projects/<category>/<FULL_NAME>/) | <category> | — | <YYYY-MM-DD> | <description> |
```

Update the stats line.

## Step 5: Confirm

```
Created <FULL_NAME> at projects/<category>/<FULL_NAME>/
  → inputs/     — drop source materials here
  → knowledge/  — processed content
  → deliverables/ — final outputs

Ready to work. Drop files into inputs/ or tell me what to do.
```
