# Conventions

## Git

- Use conventional commits: `feat:`, `fix:`, `docs:`, `chore:`
- Commit frequently in small increments
- Each project has its own repo inside `Projects/`

## Skills — Progressive Disclosure

Skills use a three-tier structure to keep context windows lean:

### Tier 1: Frontmatter (Always Loaded)
- YAML frontmatter in `SKILL.md` (~100 words max)
- Contains: `name`, `description`, trigger conditions
- Claude reads this to decide whether to invoke the skill

### Tier 2: Skill Body (On Trigger)
- Main content of `SKILL.md` (<5K words)
- Contains: instructions, workflow steps, checklists
- Loaded when the skill is invoked

### Tier 3: References (On Demand)
- `references/` directory alongside `SKILL.md` (unlimited size)
- Contains: detailed checklists, templates, examples, lookup tables
- Loaded only when the skill body explicitly reads them

### File Structure

**Simple skill** (single file):
```
.claude/skills/my-skill/SKILL.md
```

**Complex skill** (with references):
```
.claude/skills/my-skill/
  SKILL.md                        # Tiers 1+2
  references/
    checklist.md                   # Tier 3
    templates/
      component.md                 # Tier 3
```

### Guidelines
- Keep Tier 1 under 100 words — it's read on every message
- Keep Tier 2 under 5K words — it's loaded per invocation
- Move large content (examples, tables, templates) to Tier 3
- Reference Tier 3 files with explicit Read instructions in Tier 2

## Output Preferences

*(Add format, tone, and output conventions as they emerge)*
