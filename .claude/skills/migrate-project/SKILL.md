---
name: migrate-project
description: Migrate an existing project to the enhanced folder structure and CLAUDE.md template. Non-destructive — only adds, renames casing, never deletes content.
---

# Migrate Project

Can be run on a single project or batch ("migrate all projects in groupon/").

## Steps

### 1. Read current project state

For the target project directory, check:
- What folders exist? (`inputs/`, `Inputs/`, `knowledge/`, `deliverables/`, `tasks/`, `data/`)
- Is there a `CLAUDE.md`? What sections does it have?
- Is there an `inputs/` or `Inputs/` folder? What files are in it?
- Is there a `knowledge/` folder? What's in it?
- Is there a `deliverables/` folder?

### 2. Fix casing

If `Inputs/` exists (capital I) and `inputs/` does not:
```bash
mv "Inputs" "_inputs_tmp" && mv "_inputs_tmp" "inputs"
```
(Two-step rename required on macOS case-insensitive filesystem.)

### 3. Create missing structure

**inputs/.processed.md** — If missing, create and backfill with existing files:

```markdown
# Processed Inputs

| File | Processed | Output | Notes |
|------|-----------|--------|-------|
| existing-file.pdf | pre-migration | — | Existed before migration, not yet extracted |
```

List every file currently in `inputs/` with "pre-migration" as the processed date and no output path.

**knowledge/** — Create if missing.

**knowledge/README.md** — Create if missing. If knowledge/ already has files, generate the nav map from existing contents:

```markdown
# Knowledge Map

## Sources (from inputs/)
| File | Source | Summary |
|------|--------|---------|

## Synthesis (cross-source analysis)
| File | Purpose |
|------|---------|

## Total: N source files, M synthesis files
```

**deliverables/** — Create if missing.

### 4. Enhance CLAUDE.md

**If CLAUDE.md does not exist:** Create from the enhanced template (see new-project skill step 7). Infer metadata:
- **Name:** from folder name
- **Category:** from parent folder (groupon/personal/hce/pfc)
- **Status:** active
- **Type:** infer from contents — if has data/ → analysis, if has drafts → document, default to research
- **Created:** use earliest file modification date, or "—"
- **Description:** infer from README.md if present, otherwise use folder name

**If CLAUDE.md exists:** Add missing sections WITHOUT modifying existing content:
- If `## Metadata` missing → add after title
- If `## Inputs Processing` missing → add after Metadata or Purpose
- If `## Workflow` missing → add default workflow for inferred type
- If `## Key Files` missing → add, populate from actual folder contents
- If `## Active Decisions` missing → add with "*None yet.*"
- **NEVER modify existing `## Domain Learnings`** — this is the most valuable section
- **NEVER modify existing `## Purpose`** or project-specific content
- **NEVER reorder existing sections** — add new sections at logical positions

### 5. Update registry

Ensure the project has a row in `docs/projects.md`:
- If missing → add to Active Projects section
- If present → update metadata if CLAUDE.md has newer info

### 6. Report changes

For each project migrated, list:
- Folders created
- Files created
- CLAUDE.md sections added
- Casing fixes applied
- Registry updates made
