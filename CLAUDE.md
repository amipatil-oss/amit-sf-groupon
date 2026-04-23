# CoS — Chief of Stuff

Root workspace for all projects. Shared skills and conventions live here; individual projects live in `projects/` organized by category.

## Project Organization
Projects are routed to category subfolders under `projects/`:
- `projects/groupon/` — Groupon-related projects
- `projects/personal/` — Personal projects
- `projects/hce/` — HC Energie (hockey) projects
- `projects/pfc/` — Pale Fire Capital projects
- `projects/CoS_*` — Cloned reference repos (gitignored)

## Core Principles
- **Simplicity First**: Make every change as simple as possible. Touch only what's necessary. Avoid over-engineering and introducing bugs.
- **No Laziness**: Find root causes. No shallow analysis. High standards of rigor.
- **Goal-Driven Execution**: Define success criteria. Loop until verified.

## Workflow Orchestration
- **Plan Mode Default**
   - Enter plan mode for ANY non-trivial task (3+ steps or significant decisions)
   - If something goes sideways, STOP and re-plan immediately — don't keep pushing
   - Use plan mode for verification steps, not just execution
   - Write detailed specs upfront to reduce ambiguity
- **Iterative Review Loop**
   - Every plan/design gets up to 3 rounds of second-opinion review before execution
   - Each round: revise based on feedback, then re-review. Stop early if clean (no critical/major issues)
   - During execution: use Ralph Loop per task for iterative refinement
   - After each task completes, run second-opinion gate before moving to next task
   - Use all available reviewers (claude, codex, gemini) for diverse perspectives
   - Review focus: plans → completeness/feasibility; analysis/research → logic/coverage; code → correctness/tests
   - Trigger: invoke second-opinion after ANY plan, analysis, research output, or recommendation — not just code
- **Subagent Strategy**
   - Use subagents liberally to keep main context window clean
   - Offload research, exploration, and parallel analysis to subagents
   - For complex problems, throw more compute at it via subagents
   - One task per subagent for focused execution
- **Self-Improvement Loop**
   - After ANY correction from the user: update `tasks/lessons.md` with the pattern
   - Write rules for yourself that prevent the same mistake
   - Ruthlessly iterate on these lessons until mistake rate drops
   - Review lessons at session start for relevant project
- **Verification Before Done**
   - Never mark a task complete without proving the output meets requirements
   - For analysis: verify conclusions are supported by evidence
   - For documents: verify completeness, accuracy, and clarity
   - For code: run tests, check logs, demonstrate correctness
   - Ask yourself: "Would an expert in this domain approve this?"
- **Demand Elegance (Balanced)**
   - For non-trivial work: pause and ask "is there a clearer, more effective approach?"
   - If an output feels incomplete or poorly structured: refine before presenting
   - Skip this for simple, straightforward tasks
   - Challenge your own work before presenting it
- **Autonomous Fixing**
   - For issues with clear symptoms — fix them. No hand-holding.
   - Code bugs with clear repro/failing tests: just fix.
   - Document errors, formatting issues, broken links: just fix.
   - If the cause isn't obvious quickly, switch to plan mode instead of guessing.
- **Inputs Auto-Processing**
   - When entering a project context, check `inputs/` for unprocessed files
   - Compare against `inputs/.processed.md` — process anything not listed
   - For each new file: extract content, create `knowledge/<filename-slug>.md`
   - Log processed files in `inputs/.processed.md` with timestamp
   - Update `knowledge/README.md` navigation map
   - On failure: log as `(failed: reason)` in .processed.md and continue — never block on a single file
   - Supported formats: PDF, DOCX, PPTX, XLSX, TXT, HTML, MHTML, images, CSV, JSON, MD
   - For URLs: check `inputs/urls.txt` (one per line), fetch and summarize each
   - Re-process files whose modification time is newer than their .processed.md timestamp

## Task Management
- **Plan First**: Write plan to `tasks/todo.md` with checkable items (in root folder for CoS work or in specific project directory when working on project)
- **Verify Plan**: Check in before starting execution
- **Track Progress**: Mark items complete as you go
- **Explain Changes**: High-level summary at each step
- **Document Results**: Add review section to `tasks/todo.md`
- **Capture Lessons**: Update `tasks/lessons.md` after corrections

## Project Learnings
Each project has a `CLAUDE.md` with a `## Domain Learnings` section where Claude captures key domain knowledge automatically. This builds institutional memory across sessions.

- **When to write**: After completing research, analysis, or second opinions that surface non-obvious findings. Not after every action — only meaningful discoveries.
- **What to write**: Domain facts, validated conclusions, key numbers, strategic insights. Each entry must include a brief source: `- Finding [source: round 2 analysis]`
- **What NOT to write**: Session context, operational notes, tool preferences, speculative conclusions, anything that duplicates existing CLAUDE.md instructions.
- **Format**: One bullet per finding. Group under `### Topic` headers. No duplicates — check existing entries before appending.
- **Size cap**: Keep the Domain Learnings section under ~100 lines. When a topic exceeds ~10 entries, consolidate into a summary preserving the highest-confidence findings. If the whole section exceeds ~100 lines, split detailed topics into `knowledge/learnings/<topic>.md` and reference from CLAUDE.md.
- **Bootstrap**: When entering a project without a CLAUDE.md, create one using the enhanced template from the `new-project` skill. Also ensure `inputs/`, `knowledge/`, and `deliverables/` folders exist with their tracking files (`inputs/.processed.md`, `knowledge/README.md`).

## Publishing
- **Platform**: Cloudflare Pages at `foundryai.pages.dev`, protected by Cloudflare Zero Trust Access (email OTP + Google SSO)
- **Deploy command**: `CLOUDFLARE_API_TOKEN="$CLOUDFLARE_API_TOKEN" wrangler pages deploy <dir> --project-name foundryai --commit-dirty=true`
- **Structure**: Each published project is a subfolder (e.g., `foundryai.pages.dev/cos-setup-guide/`)
- **Access control**: Per-path policies in Cloudflare Zero Trust dashboard. Team name: `foundryai`
- **Workflow**: Prepare files in a temp directory, deploy via wrangler, clean up

## Rules
- **Temp files**: Any temporary downloads, scratch files, or throwaway work go in `temp/`. Never litter the root or other directories.
- **Cloned repos**: Any repository cloned for reference or analysis goes in `projects/` root with a `CoS_` prefix (e.g., `projects/CoS_some-repo`). These are gitignored.
- **Directory prefixes**: Directories created by Claude must start with `CoS_` to distinguish them from user-created content.
- **Plans**: Design docs and implementation plans go in `docs/plans/`. Filename format: `YYYY-MM-DD-HH-MM-description.md` (local time, e.g., `2026-02-28-14-30-update-checker.md`).
- **Logs**: When asked to log actions, write to `logs/`. Filename format: `YYYY-MM-DDTHH-MM-SSZ-description.md` (UTC, max 3 words, e.g., `2026-02-28T14-30-00Z-mcp-server-setup.md`).

## Navigation
- `docs/projects.md` — registry of all projects
- `docs/conventions.md` — conventions and preferences
- `docs/people.md` — people directory across all contexts
- `docs/external-skills.md` — external skill repos to install
- `.claude/skills/` — invocable workflow skills
- `projects/` — project repos by category: `groupon/`, `personal/`, `hce/`, `pfc/` (gitignored)
- `temp/` — temporary downloads and scratch files (gitignored)
- `logs/` — action logs, UTC-timestamped (gitignored)
- `tasks/` — todo lists and lessons learned
